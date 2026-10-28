"""Fixture-specific experimental player event forecasts, conditional on appearance.

Beta-smoothed player event frequencies are adjusted by opponent event allowance.
All evidence is strictly before the target day; no current-match minutes are used.
"""
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from .catalog import team_id
from .public_players import initialize
from .tracking import instant

MARKETS = {'scorer':('To score', 'goals',1), 'assist':('To assist','assists',1),
           'score_assist':('To score or assist',None,1), 'shots_2':('2+ total shots','shots',2),
           'shots_3':('3+ total shots','shots',3), 'yellow':('Shown a yellow card','yellow_cards',1)}
MISSING = {'shots_on_target':'Per-match shots-on-target history is missing.',
           'fouls':'Player foul history is missing.', 'saves':'Goalkeeper save history is missing.',
           'red_cards':'Too few red-card events for a reliable player model.',
           'clean_sheet':'Goalkeeper lineup and minutes eligibility are not verified.'}


def records(store):
    initialize(store)
    with store.connect() as c:
        return [json.loads(r[0]) for r in c.execute("SELECT payload FROM public_player_matches WHERE json_extract(payload,'$.league') IS NOT NULL ORDER BY date,match_id,player_id")]


def event(r, market):
    _,key,threshold=MARKETS[market]
    if key is None:return int(r['goals']+r['assists']>0)
    return None if r.get(key) is None else int(r[key]>=threshold)


def opponent(r):
    return r['away'] if team_id('football',r['team'])==team_id('football',r['home']) else r['home']


def estimate(history, league_rows, opposition, market):
    own=[event(r,market) for r in history];own=[x for x in own if x is not None]
    population=[event(r,market) for r in league_rows];population=[x for x in population if x is not None]
    allowed=[event(r,market) for r in league_rows if team_id('football',opponent(r))==team_id('football',opposition)]
    allowed=[x for x in allowed if x is not None]
    if len(own)<5 or len(population)<100 or len(allowed)<30:return None
    base=(sum(population)+1)/(len(population)+2)
    personal=(sum(own)+8*base)/(len(own)+8)
    opponent_rate=(sum(allowed)+60*base)/(len(allowed)+60)
    factor=max(0.5,min(2.,(opponent_rate/(1-opponent_rate))/(base/(1-base))))
    odds=personal/(1-personal)*factor
    return {'probability':odds/(1+odds),'baseline':base,'opponent_factor':factor,'sample':len(own)}


def board(store, fixture_id):
    fixture=store.fixture(fixture_id)
    if not fixture or fixture['sport']!='football':raise ValueError('Football fixture not found')
    now=datetime.now(timezone.utc)
    if fixture['status'] not in ['scheduled','timed'] or instant(fixture['date'])<=now:
        raise ValueError('Choose an upcoming scheduled fixture')
    day=fixture['date'][:10]
    rows=[r for r in records(store) if r['date']<day and instant(r['observed_at'])<=now]
    histories=defaultdict(list)
    for r in rows:histories[r['player_id']].append(r)
    predictions=[];excluded=[]
    teams={team_id('football',fixture['home']):fixture['away'],team_id('football',fixture['away']):fixture['home']}
    leagues=defaultdict(list)
    for r in rows:leagues[r['league']].append(r)
    for pid,history in histories.items():
        latest=history[-1];tid=team_id('football',latest['team'])
        if tid not in teams:continue
        recent=[r for r in history if r['league']==latest['league']][-10:]
        if len(recent)<5 or sum(r['minutes'] for r in recent)<450 or (instant(fixture['date']).date()-datetime.fromisoformat(latest['date']).date()).days>45:
            excluded.append({'player':latest['player'],'reason':'Insufficient or stale appearance history'});continue
        for key,(label,_,_) in MARKETS.items():
            result=estimate(recent,leagues[latest['league']],teams[tid],key)
            if result:
                predictions.append({'player_id':pid,'player':latest['player'],'team':latest['team'],
                    'market':key,'label':label,'latest':latest['date'],'mean_minutes':sum(r['minutes'] for r in recent)/len(recent),
                    'starts':sum(bool(r.get('started')) for r in recent),**result})
    return {'fixture':{k:fixture[k] for k in ['id','home','away','date']},'predictions':sorted(predictions,key=lambda p:-p['probability']),
        'excluded':excluded,'unavailable':MISSING,'model_version':'player-events-v1-experimental','validated':False,
        'notice':'Experimental probabilities conditional on the player appearing. Recent event history is shrunk toward league rates and adjusted for the named opponent. Squad membership is inferred from the latest recorded appearance; injuries, confirmed lineups, referee and penalty role are not available. Not bookmaker settlement probabilities. No proven predictive edge.'}
