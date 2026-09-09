"""Read-only project evidence collection; writes only audit/evidence.json."""
from pathlib import Path
import ast
import collections
import contextlib
import io
import json
import types
import typing
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'audit'
evidence = {}
files = []
for folder in [ROOT, *[ROOT / p for p in ['app','api','core','footy','sports','scrapers','scripts','tests','utils']]]:
    files.extend(folder.glob('*.py') if folder == ROOT else folder.rglob('*.py'))
files = sorted(set(files))
syntax = []
for p in files:
    try:
        ast.parse(p.read_text(encoding='utf-8-sig'), filename=str(p))
    except Exception as e:
        syntax.append({'file':str(p.relative_to(ROOT)), 'error':str(e)})
evidence['python_inventory'] = {'files':len(files), 'lines':sum(len(p.read_text(encoding='utf-8-sig').splitlines()) for p in files), 'syntax_errors':syntax}
evidence['artifacts'] = [{'path':str(p.relative_to(ROOT)), 'bytes':p.stat().st_size, 'lfs_pointer':p.open('rb').read(80).startswith(b'version https://git-lfs.github.com/spec/v1')} for d in ['models','data/processed','data/raw'] for p in (ROOT/d).rglob('*') if p.is_file()]
evidence['datasets'] = {}
for p in [*(ROOT/'data').rglob('*.csv'),*(ROOT/'data/processed').glob('*.csv.zip')]:
    try:
        df = pd.read_csv(p, low_memory=False)
        r = {'rows':len(df), 'columns':len(df.columns)}
        for col in ['Date','date','Season','League']:
            if col in df:
                if col.lower() == 'date':
                    dates = pd.to_datetime(df[col], errors='coerce', format='mixed', dayfirst=False)
                    r[col] = {'min':str(dates.min()), 'max':str(dates.max()), 'invalid':int(dates.isna().sum())}
                else:
                    r[col] = {str(k):int(v) for k,v in df[col].value_counts(dropna=False).items()}
        keys = [c for c in ['Date','HomeTeam','AwayTeam'] if c in df]
        if len(keys) == 3:
            r['duplicate_match_keys'] = int(df.duplicated(keys).sum())
        if {'FTHG','FTAG','FTR'} <= set(df.columns):
            hg,ag = pd.to_numeric(df.FTHG,errors='coerce'),pd.to_numeric(df.FTAG,errors='coerce')
            valid = hg.notna() & ag.notna() & df.FTR.isin(['H','D','A'])
            r['invalid_outcomes'] = int((~valid).sum())
            r['score_result_disagreement'] = int((valid & (df.FTR != np.where(hg>ag,'H',np.where(hg<ag,'A','D')))).sum())
            r['actual_result_rates'] = df.loc[valid,'FTR'].value_counts(normalize=True).to_dict()
            if 'BayesianExpectedTotal' in df:
                r['altered_goal_labels'] = {}
                for threshold in [1.5,2.5,3.5]:
                    actual = hg+ag > threshold
                    altered = actual | (df.BayesianExpectedTotal > threshold+.3)
                    r['altered_goal_labels'][str(threshold)] = {'flipped':int((actual!=altered).sum()), 'actual_positive_rate':float(actual.mean()), 'training_positive_rate':float(altered.mean())}
        r['xg_fields'] = {c:{'non_null':int(df[c].notna().sum()),'non_zero':int(pd.to_numeric(df[c],errors='coerce').fillna(0).ne(0).sum())} for c in df if 'xg' in c.lower()}
        if {'HomexG','HS','HST'} <= set(df):
            r['home_xg_matches_shot_proxy'] = int(np.isclose(df.HomexG, (df.HS*.08 + df.HST*.25).fillna(0)).sum())
        if {'HTHG','HTAG','HTR'} <= set(df):
            r['halftime']={'null_goals':int((df.HTHG.isna() | df.HTAG.isna()).sum()),'invalid_result':int((~df.HTR.isin(['H','D','A'])).sum()),'zero_goals_invalid_result':int(((df.HTHG==0)&(df.HTAG==0)&~df.HTR.isin(['H','D','A'])).sum())}
        if 'League' in df and 'Date' in df:
            r['league_last_date'] = df.groupby('League').Date.max().to_dict()
        evidence['datasets'][str(p.relative_to(ROOT))] = r
    except Exception as e:
        evidence['datasets'][str(p.relative_to(ROOT))] = {'error':str(e)}

def method(path, cls, name):
    tree = ast.parse((ROOT/path).read_text(encoding='utf-8-sig'))
    cl = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
    fn = next(n for n in cl.body if isinstance(n,ast.FunctionDef) and n.name==name)
    fn.decorator_list=[]
    ns = dict(vars(typing),pd=pd,np=np)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec'),ns)
    return ns[name]

with contextlib.redirect_stdout(io.StringIO()):
    features=method('footy/predictor_utils.py','BayesianMatchPredictor','_get_bayesian_team_features')
    df=pd.DataFrame([
        {'Date':pd.Timestamp('2025-01-01'),'HomeTeam':'A','AwayTeam':'B','HomeForm_5':.2,'AwayForm_5':.3,'H2H_AvgGoals':1.,'HomeElo':1500.,'AwayElo':1400.},
        {'Date':pd.Timestamp('2026-01-01'),'HomeTeam':'A','AwayTeam':'C','HomeForm_5':.9,'AwayForm_5':.8,'H2H_AvgGoals':7.,'HomeElo':1700.,'AwayElo':1600.},
    ])
    obj=types.SimpleNamespace(df=df,feature_columns=['HomeForm_5','AwayForm_5','H2H_AvgGoals','HomeElo','AwayElo','EloAdvantage'])
    a=features(obj,'A','B',pd.Timestamp('2025-06-01'))
    b=features(obj,'A','B',pd.Timestamp('2027-06-01'))
    evidence['inference_date_probe']={'historical':a.to_dict('records')[0],'future':b.to_dict('records')[0],'identical':a.equals(b),'expected_historical_home_form':.2,'expected_pair_h2h':1.}
    cons=method('footy/model_training.py','BayesianLogicalConstraintValidator','apply_bayesian_over_under_constraints')
    pred,probs,_=cons({'over_1_5':0,'over_2_5':0,'over_3_5':0},{'over_1_5':.1,'over_2_5':.2,'over_3_5':.3})
    evidence['probability_hierarchy_probe']={'output':probs,'valid':probs['over_1_5']>=probs['over_2_5']>=probs['over_3_5']}
    rest=method('footy/rolling_features.py','BayesianRollingFeatureGenerator','_calculate_rest_features')
    fixtures=pd.DataFrame({'Date':pd.to_datetime(['2025-01-01','2025-01-04','2025-01-07']),'Season':['2024-2025']*3,'HomeTeam':['A','C','A'],'AwayTeam':['B','A','D']})
    rr=rest(None,fixtures)
    evidence['rest_probe']={'reported':float(rr.iloc[-1].DaysSinceLastMatch_Home),'actual_days':3}
    class FixedBinaryModel:
        def predict_proba(self,X):
            return np.array([[.8,.2]])
    predict=method('footy/predictor_utils.py','BayesianMatchPredictor','predict_match_bayesian')
    obj=types.SimpleNamespace(PREDICTION_TASKS={'over_2_5':'Over 2.5 Goals'},models={'over_2_5':{'model':FixedBinaryModel(),'features':['x']}},feature_columns=['x'],_get_bayesian_team_features=lambda *a:pd.DataFrame({'x':[1]}),apply_bayesian_logical_constraints=lambda p,q:(p,q,[]),calculate_bayesian_total_goals=lambda *a:2.)
    pred,prob=predict(obj,'A','B')
    evidence['binary_probability_probe']={'prediction':pred['Over 2.5 Goals'],'returned_probability':prob['Over 2.5 Goals'],'actual_positive_probability':.2}
    refs=method('footy/feature_engineering.py','BayesianFootballFeatureEngineering','create_bayesian_referee_analysis')
    ref_obj=types.SimpleNamespace(_calculate_referee_league_priors=lambda df:{'E0':{'avg_goals':2.5}},_bayesian_update=lambda p,e,c:(1-c)*p+c*e)
    rdf=pd.DataFrame({'Date':pd.date_range('2025-01-01',periods=4),'Referee':['R']*4,'League':['E0']*4,'TotalGoals':[2,2,2,2],'FTR':['H']*4,'BTTS':[1]*4})
    before=refs(ref_obj,rdf).iloc[0].RefAvgGoals
    future=rdf.iloc[[-1]].copy(); future['Date']=pd.Timestamp('2026-01-01');future['TotalGoals']=10
    after=refs(ref_obj,pd.concat([rdf,future],ignore_index=True)).iloc[0].RefAvgGoals
    evidence['referee_future_probe']={'before':float(before),'after_adding_future_match':float(after),'unchanged':bool(before==after)}
evidence['raw_workbooks'] = {}
for p in (ROOT/'data/raw').glob('*.xlsx'):
    sheets=pd.read_excel(p,sheet_name=None)
    evidence['raw_workbooks'][p.name] = {k:{'rows':len(v),'columns':len(v.columns),'last_date':str(pd.to_datetime(v.Date,errors='coerce',dayfirst=True,format='mixed').max()) if 'Date' in v else None,'missing_ht_goals':int(v.HTHG.isna().sum()) if 'HTHG' in v else len(v)} for k,v in sheets.items()}
OUT.mkdir(exist_ok=True)
(OUT/'evidence.json').write_text(json.dumps(evidence,indent=2,default=str),encoding='utf-8')
print(f"Wrote {OUT/'evidence.json'}: {len(files)} Python files, {len(evidence['datasets'])} datasets, {len(evidence['raw_workbooks'])} raw workbooks.")
