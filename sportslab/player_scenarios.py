"""Transparent conditional scenarios, deliberately not calibrated forecasts."""
import json
import math
from datetime import datetime, timezone
from .public_players import initialize
from .catalog import team_id


def analyse(store, player_id, minutes=70):
    minutes=float(minutes)
    if not math.isfinite(minutes) or not 1<=minutes<=90:
        raise ValueError('Assumed minutes must be between 1 and 90')
    initialize(store)
    with store.connect() as c:
        rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM public_player_matches WHERE player_id=? ORDER BY date DESC,match_id DESC',(player_id,))]
    if not rows:raise ValueError('Player history not found')
    recent=rows[:10];total=sum(r['minutes'] for r in recent)
    age=(datetime.now(timezone.utc).date()-datetime.fromisoformat(recent[0]['date']).date()).days
    team=recent[0].get('team');fixtures=[]
    if team:
        for m in store.matches('football'):
            if m['status'] in ['scheduled','timed'] and m['date']>datetime.now(timezone.utc).isoformat() and team_id('football',team) in [team_id('football',m['home']),team_id('football',m['away'])]:
                fixtures.append({k:m[k] for k in ['id','date','home','away']})
    result={'player':recent[0]['player'],'team':team,'fixtures':sorted(fixtures,key=lambda m:m['date'])[:10],
            'appearances':len(recent),'sample_minutes':total,'latest':recent[0]['date'],'assumed_minutes':minutes,
            'validated':False,'notice':'Conditional Poisson scenario from the last 10 appearances: constant xG/xA rates and independent goal/assist events. No opponent, lineup, penalty-role or injury adjustment. Not a calibrated match prediction.'}
    if total<450 or len(recent)<5 or age>45:
        return {**result,'unavailable':'At least 5 appearances, 450 minutes and a result within 45 days are required.'}
    goal_rate=sum(r['xg'] for r in recent)/total
    assist_rate=sum(r['xa'] for r in recent)/total
    return {**result,'scorer':-math.expm1(-goal_rate*minutes),'score_or_assist':-math.expm1(-(goal_rate+assist_rate)*minutes),
            'xg_per90':goal_rate*90,'xa_per90':assist_rate*90}
