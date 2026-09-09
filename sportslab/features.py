"""One feature builder for historical evaluation and prospective inference.

Features for every UTC calendar day are emitted before any result from that day
updates state. This is conservative for sources that only supply match dates.
"""
from collections import defaultdict, deque
from datetime import datetime
import math
import numpy as np
import pandas as pd

CATEGORICAL=['competition','surface']
NUMERIC=['home_elo','away_elo','elo_difference','home_matches','away_matches','home_form','away_form',
         'home_scored','away_scored','home_conceded','away_conceded','home_scoring_std','away_scoring_std',
         'home_rest','away_rest','home_density','away_density','home_venue_scored','away_venue_scored',
         'home_xg','away_xg','home_xga','away_xga','home_xg_coverage','away_xg_coverage',
         'h2h_matches','h2h_home_rate','h2h_total','neutral','month','home_surface_form','away_surface_form']
FEATURES=CATEGORICAL+NUMERIC


def valid_result(m):
    return m.get('status')=='finished' and m.get('hg') is not None and m.get('ag') is not None


class FeatureState:
    def __init__(self,sport):
        self.sport=sport
        self.history=defaultdict(lambda:deque(maxlen=50))
        self.elo=defaultdict(lambda:1500.)
        self.h2h=defaultdict(lambda:deque(maxlen=10))
        self.default=1.35 if sport=='football' else 105. if sport=='basketball' else .5

    @staticmethod
    def day(m):
        return datetime.fromisoformat(m['date'].replace('Z','+00:00')).date()

    def team_features(self,team,day,venue,surface):
        hist=list(self.history[team]); recent=hist[-10:]
        def avg(field,rows=recent,default=None):
            vals=[r[field] for r in rows if r.get(field) is not None]
            return float(np.mean(vals)) if vals else (self.default if default is None else default)
        n=len(recent)
        return {'elo':self.elo[team],'matches':len(hist),'form':avg('result',default=.5),
            'scored':avg('for'),'conceded':avg('against'),'scoring_std':float(np.std([r['for'] for r in recent])) if n else 0.,
            'rest':min(90,(day-hist[-1]['day']).days) if hist else 14,
            'density':sum((day-r['day']).days<=14 for r in hist),
            'venue_scored':avg('for',[r for r in hist if r['venue']==venue][-10:]),
            'xg':avg('xg',default=float('nan')),'xga':avg('xga',default=float('nan')),
            'xg_coverage':sum(r.get('xg') is not None for r in recent)/max(n,1),
            'surface_form':avg('result',[r for r in hist if r.get('surface')==surface][-10:],.5)}

    def features(self,m):
        day=self.day(m); h,a=m['home_id'],m['away_id']; surface=m.get('surface') or 'unknown'
        hf=self.team_features(h,day,'home',surface); af=self.team_features(a,day,'away',surface)
        f={'competition':m['competition'],'surface':surface}
        f.update({'home_'+k:v for k,v in hf.items()}); f.update({'away_'+k:v for k,v in af.items()})
        neutral=bool(m.get('neutral',False))
        f['elo_difference']=hf['elo']-af['elo']+(0 if neutral else 55 if self.sport=='football' else 70)
        pair=list(self.h2h[tuple(sorted([h,a]))])
        f.update({'h2h_matches':len(pair),'h2h_home_rate':float(np.mean([r['result'] if r['home_id']==h else 1-r['result'] for r in pair])) if pair else .5,
                  'h2h_total':float(np.mean([r['total'] for r in pair])) if pair else 2*self.default,'neutral':int(neutral),'month':day.month})
        return {k:f[k] for k in FEATURES}

    def update(self,m):
        if not valid_result(m): return
        h,a=m['home_id'],m['away_id']; hg,ag=float(m['hg']),float(m['ag'])
        day=self.day(m)
        result=1. if hg>ag else .5 if hg==ag else 0.
        advantage=0 if m.get('neutral') else 55 if self.sport=='football' else 70
        expected=1/(1+10**((self.elo[a]-self.elo[h]-advantage)/400))
        delta=24*(result-expected)
        self.elo[h]+=delta;self.elo[a]-=delta
        for team,opp,for_,against,res,venue,xg,xga in [
            (h,a,hg,ag,result,'home',m.get('home_xg'),m.get('away_xg')),
            (a,h,ag,hg,1-result,'away',m.get('away_xg'),m.get('home_xg'))]:
            self.history[team].append({'day':day,'for':for_,'against':against,'result':res,'venue':venue,
                'xg':xg if m.get('xg_source') else None,'xga':xga if m.get('xg_source') else None,'surface':m.get('surface'),
                'opponent':opp,'competition':m['competition']})
        self.h2h[tuple(sorted([h,a]))].append({'home_id':h,'result':result,'total':hg+ag})


def build_history(records,sport):
    state=FeatureState(sport); output=[]; eligible=[]
    grouped=defaultdict(list)
    for m in records:
        if valid_result(m): grouped[m['date'][:10]].append(m)
    for day in sorted(grouped):
        batch=sorted(grouped[day],key=lambda m:m['id'])
        for m in batch:
            output.append(state.features(m));eligible.append(m)
        for m in batch: state.update(m)
    return pd.DataFrame(output,columns=FEATURES),eligible,state


def state_before(records,sport,as_of):
    # Same conservative daily cutoff as build_history.
    day=as_of[:10]
    state=FeatureState(sport)
    for m in sorted((m for m in records if m['date'][:10]<day and valid_result(m)),key=lambda m:(m['date'][:10],m['id'])):
        state.update(m)
    return state
