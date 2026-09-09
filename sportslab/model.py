from __future__ import annotations

import json
import math
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, CatBoostRegressor
from sklearn.metrics import accuracy_score, log_loss, mean_absolute_error
from scipy.stats import poisson

from .features import FEATURES, CATEGORICAL, build_history, state_before, valid_result
from .store import ROOT, digest, utcnow

ARTIFACTS=Path(os.environ.get('SPORTSLAB_MODELS',ROOT/'models'/'sportslab'))
SCHEMA='causal-v1'


def labels(records,sport):
    return np.array([0 if m['hg']>m['ag'] else 1 if sport=='football' and m['hg']==m['ag'] else 2 if sport=='football' else 1 for m in records])


def probabilities(model,X,classes):
    p=np.full((len(X),classes),1e-8)
    raw=model.predict_proba(X)
    for i,c in enumerate(model.classes_): p[:,int(c)]=raw[:,i]
    return p/p.sum(axis=1,keepdims=True)


def temper(p,t):
    p=np.clip(p,1e-8,1)**(1/t)
    return p/p.sum(axis=1,keepdims=True)


def score_matrix(home,away,target=None):
    # Goal grid extends far enough to avoid clipping meaningful tail mass.
    grid=np.arange(26)
    matrix=np.outer(poisson.pmf(grid,home),poisson.pmf(grid,away))
    matrix/=matrix.sum()
    if target is not None:
        h,a=np.indices(matrix.shape)
        for mask,p in zip([h>a,h==a,h<a],target):
            mass=matrix[mask].sum()
            if mass: matrix[mask]*=p/mass
        matrix/=matrix.sum()
    return matrix


def matrix_markets(matrix):
    h,a=np.indices(matrix.shape); total=h+a
    return {'home_win':float(matrix[h>a].sum()),'draw':float(matrix[h==a].sum()),'away_win':float(matrix[h<a].sum()),
            'over_1_5':float(matrix[total>=2].sum()),'over_2_5':float(matrix[total>=3].sum()),'over_3_5':float(matrix[total>=4].sum()),
            'btts':float(matrix[(h>0)&(a>0)].sum()),'home_clean_sheet':float(matrix[a==0].sum()),'away_clean_sheet':float(matrix[h==0].sum())}


def metrics(y,p,classes):
    winner=p.argmax(axis=1)
    hot=np.eye(classes)[y]
    bins=[]
    for low in np.arange(0,1,.1):
        mask=(p.max(axis=1)>=low)&(p.max(axis=1)<low+.1)
        if mask.any(): bins.append({'probability':float(p.max(axis=1)[mask].mean()),'observed':float((winner[mask]==y[mask]).mean()),'count':int(mask.sum())})
    return {'n':len(y),'accuracy':float(accuracy_score(y,winner)), 'log_loss':float(log_loss(y,p,labels=list(range(classes)))),
            'brier':float(np.mean(np.sum((p-hot)**2,axis=1))),'calibration':bins,
            'class_recall':{str(i):float(np.mean(winner[y==i]==i)) if (y==i).any() else None for i in range(classes)}}


def fit(X,records,sport,iterations=220):
    classes=3 if sport=='football' else 2
    y=labels(records,sport)
    classifier=CatBoostClassifier(iterations=iterations,depth=5,learning_rate=.06,loss_function='MultiClass' if classes==3 else 'Logloss',
                                 verbose=False,random_seed=42,thread_count=4,allow_writing_files=False,l2_leaf_reg=8)
    classifier.fit(X,y,cat_features=CATEGORICAL)
    models={'outcome':classifier}
    if sport in ['football','basketball']:
        for key,target in [('home_goals','hg'),('away_goals','ag')]:
            model=CatBoostRegressor(iterations=iterations,depth=5,learning_rate=.05,loss_function='RMSE',verbose=False,
                                   random_seed=42,thread_count=4,allow_writing_files=False,l2_leaf_reg=10)
            model.fit(X,[m[target] for m in records],cat_features=CATEGORICAL)
            models[key]=model
    return models


def train(store,sport,iterations=220):
    snapshot=store.version(sport)
    records=[m for m in store.matches(sport,status='finished') if m['date']<utcnow()]
    X,records,_=build_history(records,sport)
    mask=(X.home_matches>=5)&(X.away_matches>=5)
    records=[m for m,keep in zip(records,mask) if keep];X=X[mask].reset_index(drop=True)
    if len(records)<500: raise ValueError(f'Insufficient real {sport} history for evaluation')
    days=sorted({m['date'][:10] for m in records})
    # Split by date, never randomly and never across the same date.
    calibration_start=days[int(len(days)*.75)];test_start=days[int(len(days)*.87)]
    tr=np.array([m['date'][:10]<calibration_start for m in records])
    ca=np.array([calibration_start<=m['date'][:10]<test_start for m in records]);te=np.array([m['date'][:10]>=test_start for m in records])
    y=labels(records,sport); classes=3 if sport=='football' else 2
    select=lambda mask:[m for m,keep in zip(records,mask) if keep]
    print(f'Training {sport}: {tr.sum()} train / {ca.sum()} calibration / {te.sum()} untouched test',flush=True)
    benchmark=fit(X[tr],select(tr),sport,iterations)
    cp=probabilities(benchmark['outcome'],X[ca],classes)
    temperature=min([.7,1.,1.3,1.7,2.],key=lambda t:log_loss(y[ca],temper(cp,t),labels=list(range(classes))))
    pred=temper(probabilities(benchmark['outcome'],X[te],classes),temperature)
    base=np.bincount(y[tr],minlength=classes)/tr.sum()
    evaluation=metrics(y[te],pred,classes)
    evaluation['baseline']=metrics(y[te],np.tile(base,(te.sum(),1)),classes)
    evaluation['test_start']=test_start;evaluation['test_end']=days[-1]
    evaluation['calibration_start']=calibration_start;evaluation['temperature']=temperature
    evaluation['competition']={}
    tests=select(te)
    for comp in sorted({m['competition'] for m in tests}):
        cm=np.array([m['competition']==comp for m in tests])
        evaluation['competition'][comp]=metrics(y[te][cm],pred[cm],classes)
    if sport=='football':
        hp=np.clip(benchmark['home_goals'].predict(X[te]),.1,6);ap=np.clip(benchmark['away_goals'].predict(X[te]),.1,6)
        goals={k:[] for k in ['over_1_5','over_2_5','over_3_5','btts']}
        for hg,ag,p in zip(hp,ap,pred):
            markets=matrix_markets(score_matrix(hg,ag,p))
            for k in goals:goals[k].append(markets[k])
        evaluation['goal_markets']={}
        for k,ps in goals.items():
            threshold={'over_1_5':1.5,'over_2_5':2.5,'over_3_5':3.5}.get(k)
            truth=np.array([int(m['hg']+m['ag']>threshold) if threshold else int(m['hg']>0 and m['ag']>0) for m in tests])
            evaluation['goal_markets'][k]=metrics(truth,np.column_stack([1-np.array(ps),ps]),2)
    if evaluation['log_loss']>=evaluation['baseline']['log_loss']:
        raise ValueError('Benchmark does not improve log loss over the prior baseline; active model retained.')
    # Production refit after the untouched benchmark. Report distinguishes these.
    final_cut=(datetime.fromisoformat(days[-1])-timedelta(days=60)).date().isoformat()
    if sum(m['date'][:10]>=final_cut for m in records)<200:
        final_cut=records[-min(200,len(records)//5)]['date'][:10]
    final_train=np.array([m['date'][:10]<final_cut for m in records]); final_cal=~final_train
    production=fit(X[final_train],select(final_train),sport,iterations)
    cp=probabilities(production['outcome'],X[final_cal],classes)
    pt=min([.7,1.,1.3,1.7,2.],key=lambda t:log_loss(y[final_cal],temper(cp,t),labels=list(range(classes))))
    if store.version(sport)!=snapshot:raise ValueError('Data changed during training; previous model retained. Run training again.')
    version=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+digest([sport,store.version(sport),SCHEMA])[:8]
    manifest={'version':version,'sport':sport,'schema':SCHEMA,'features':FEATURES,'created_at':utcnow(),
        'data_version':store.version(sport),'matches':len(records),'latest_result':days[-1],
        'trained_through':max(m['date'][:10] for m,k in zip(records,final_train) if k),
        'calibrated_through':days[-1],'temperature':pt,'evaluation':evaluation,
        'evaluation_scope':'Untouched chronological benchmark of this recipe; the serving model was subsequently refit on newer data.',
        'class_labels':['Home win','Draw','Away win'] if sport=='football' else ['Home / player 1','Away / player 2']}
    directory=ARTIFACTS/sport/version;directory.mkdir(parents=True,exist_ok=True)
    joblib.dump(production,directory/'models.joblib')
    joblib.dump(benchmark,directory/'benchmark.joblib')
    manifest['artifact_sha256']=__import__('hashlib').sha256((directory/'models.joblib').read_bytes()).hexdigest()
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False),encoding='utf-8')
    active=ARTIFACTS/sport/'active.json';temp=active.with_suffix('.tmp')
    temp.write_text(json.dumps({'version':version}),encoding='utf-8');temp.replace(active)
    print(f'{sport} benchmark accuracy {evaluation["accuracy"]:.3f}; log loss {evaluation["log_loss"]:.3f}; prior baseline {evaluation["baseline"]["log_loss"]:.3f}',flush=True)
    return manifest


class Predictor:
    def __init__(self,store):
        self.store=store;self.loaded={};self.states={}

    def load(self,sport):
        pointer=ARTIFACTS/sport/'active.json'
        if not pointer.exists(): raise ValueError(f'{sport.title()} has no validated model artifact yet. Run training first.')
        version=json.loads(pointer.read_text())['version']
        if sport not in self.loaded or self.loaded[sport][0]['version']!=version:
            directory=pointer.parent/version
            manifest=json.loads((directory/'manifest.json').read_text())
            if manifest['schema']!=SCHEMA: raise ValueError('Model feature schema is incompatible')
            actual=__import__('hashlib').sha256((directory/'models.joblib').read_bytes()).hexdigest()
            if actual!=manifest['artifact_sha256']: raise ValueError('Model artifact checksum failed')
            self.loaded[sport]=(manifest,joblib.load(directory/'models.joblib'))
        return self.loaded[sport]

    def predict(self,fixture):
        sport=fixture['sport'];manifest,models=self.load(sport)
        if fixture['date'][:10]<=manifest['calibrated_through']:
            raise ValueError('This model contains later training or calibration data. Use the historical benchmark instead.')
        version=self.store.version(sport);key=(sport,version,fixture['date'][:10])
        if key not in self.states:
            self.states={k:v for k,v in self.states.items() if k[0]!=sport}
            self.states[key]=state_before(self.store.matches(sport,status='finished'),sport,fixture['date'])
        state=self.states[key];f=state.features(fixture)
        if min(f['home_matches'],f['away_matches'])<5:
            raise ValueError('Insufficient history: both participants need at least five earlier matches. No fallback prediction was generated.')
        frame=pd.DataFrame([f],columns=FEATURES)
        p=temper(probabilities(models['outcome'],frame,3 if sport=='football' else 2),manifest['temperature'])[0]
        markets={'home_win':float(p[0]),'away_win':float(p[-1])};scores=[];expected=None
        if sport=='football':
            h=float(np.clip(models['home_goals'].predict(frame)[0],.1,6));a=float(np.clip(models['away_goals'].predict(frame)[0],.1,6))
            matrix=score_matrix(h,a,p);markets=matrix_markets(matrix)
            hi,ai=np.indices(matrix.shape)
            expected={'home':float((hi*matrix).sum()),'away':float((ai*matrix).sum()),'kind':'model goal forecast, not observed xG'}
            for idx in np.argsort(matrix.ravel())[-5:][::-1]:
                home,away=np.unravel_index(idx,matrix.shape);scores.append({'score':f'{home}–{away}','probability':float(matrix[home,away])})
        elif sport=='basketball':
            expected={'home':float(models['home_goals'].predict(frame)[0]),'away':float(models['away_goals'].predict(frame)[0]),'kind':'model points forecast'}
        result={'fixture':fixture,'probabilities':markets,'scorelines':scores,'expected':expected,'features':{k:(None if isinstance(v,float) and not math.isfinite(v) else v) for k,v in f.items()},
            'model_version':manifest['version'],'data_version':version,'created_at':utcnow(),'benchmark':manifest['evaluation'],
            'warnings':[],'form':{},'analysis':[]}
        latest=max((r['day'].isoformat() for team in [fixture['home_id'],fixture['away_id']] for r in state.history[team]),default='')
        result['history_through']=latest
        for side in ['home','away']:
            hist=list(state.history[fixture[side+'_id']])[-5:]
            result['form'][side]=[{'result':'W' if r['result']==1 else 'D' if r['result']==.5 else 'L','date':r['day'].isoformat(),'scored':r['for'],'conceded':r['against']} for r in hist]
        if max(f['home_rest'],f['away_rest'])>45: result['warnings'].append('Long gap since a participant last played in this dataset. Check current squad and coverage.')
        if sport=='football' and min(f['home_xg_coverage'],f['away_xg_coverage'])<.5:result['warnings'].append('Limited observed xG coverage; goal forecasts are model estimates.')
        if fixture['competition']=='CL' and manifest['evaluation']['competition'].get('CL',{}).get('n',0)<100:
            result['warnings'].append('UCL-specific benchmark is limited; cross-competition predictions carry extra uncertainty.')
        result['analysis']=[f"Recent form uses completed matches across home and away venues before {fixture['date'][:10]}.",
            f"Rest: {fixture['home']} {f['home_rest']} days; {fixture['away']} {f['away_rest']} days.",
            f"The model uses {int(f['home_matches'])} / {int(f['away_matches'])} recent historical appearances, opponent results and chronological Elo ratings."]
        result['analysis'].append(f"Last ten scoring averages: {fixture['home']} {f['home_scored']:.2f} scored / {f['home_conceded']:.2f} conceded; {fixture['away']} {f['away_scored']:.2f} / {f['away_conceded']:.2f}.") if sport!='tennis' else None
        result['analysis'].append(f"Recent result rates (wins plus half draws): {f['home_form']:.0%} / {f['away_form']:.0%}. Earlier head-to-head meetings: {int(f['h2h_matches'])}.")
        if sport=='football' and min(f['home_xg_coverage'],f['away_xg_coverage'])>0:
            result['analysis'].append(f"Observed xG average where available: {f['home_xg']:.2f} / {f['away_xg']:.2f}; coverage {f['home_xg_coverage']:.0%} / {f['away_xg_coverage']:.0%} of the last ten matches. Source: Understat.")
        if sport=='tennis':result['analysis'].append(f"Surface-specific recent win rates on {fixture.get('surface','unknown')}: {f['home_surface_form']:.0%} / {f['away_surface_form']:.0%}.")
        return result


def settle_markets(prediction,fixture):
    h,a=fixture['hg'],fixture['ag'];total=h+a
    actual={'home_win':h>a,'away_win':a>h}
    if fixture['sport']=='football':
        actual.update({'draw':h==a,'over_1_5':total>1.5,'over_2_5':total>2.5,'over_3_5':total>3.5,'btts':h>0 and a>0,'home_clean_sheet':a==0,'away_clean_sheet':h==0})
    probs=prediction['probabilities'];outcome_keys=['home_win','draw','away_win'] if fixture['sport']=='football' else ['home_win','away_win']
    selected=max(outcome_keys,key=lambda k:probs[k])
    return {'score':f'{h:g}–{a:g}','outcome_correct':bool(actual[selected]),'selected_outcome':selected,
        'markets':{k:{'probability':p,'occurred':bool(actual[k]),'correct':bool((p>=.5)==actual[k]),'brier':float((p-int(actual[k]))**2)} for k,p in probs.items() if k in actual}}
