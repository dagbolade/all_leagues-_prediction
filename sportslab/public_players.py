"""Import auditable, rendered Understat match tables without an API.

The browser collector reads visible DOM tables, including all pagination pages.
This importer never equates total shots with shots on target or assumes a team
from a player's current club (transfers make that unsafe).
"""
import json
import math
import re
from datetime import date
from pathlib import Path

from .store import utcnow

HEADERS=['№','Date','Home','Score','Away','Pos','Min','Sh','G','KP','A','xG','xA']


def initialize(store):
    with store.connect() as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS public_player_pages (
                player_id TEXT PRIMARY KEY, observed_at TEXT, payload TEXT);
            CREATE TABLE IF NOT EXISTS public_player_matches (
                player_id TEXT, match_id TEXT, date TEXT, payload TEXT,
                PRIMARY KEY(player_id,match_id));
        ''')


def normalize(document):
    from .tracking import instant
    observed=instant(document['observed_at'])
    if observed>instant(utcnow()):raise ValueError('Future observation timestamp')
    pages=document['pages']
    if not pages or pages[-1]['next']:raise ValueError('Incomplete player pagination')
    source=pages[0]['source'];match=re.fullmatch(r'https://understat.com/player/(\d+)',source)
    if not match:raise ValueError('Invalid player source')
    pid='understat:'+match[1];name=pages[0]['player'];rows=[];seen=set()
    for page_number,page in enumerate(pages,1):
        if page['source']!=source or page['player']!=name or page['headers']!=HEADERS or int(page['page'])!=page_number:
            raise ValueError('Player identity, header or page sequence changed')
        for raw in page['rows']:
            cells=raw['cells']
            if len(cells)!=len(HEADERS):raise ValueError('Unexpected column count')
            mid=re.fullmatch(r'https://understat.com/match/(\d+)',raw['match_url'])
            if not mid or mid[1] in seen:raise ValueError('Invalid or duplicate match identity')
            seen.add(mid[1]);day=date.fromisoformat(cells[1])
            if day>observed.date():raise ValueError('Future result')
            if not re.fullmatch(r'\d+-\d+',cells[3]):raise ValueError('Invalid match score')
            values={}
            for key,index in [('minutes',6),('shots',7),('goals',8),('key_passes',9),('assists',10)]:
                if not cells[index].isdigit():raise ValueError('Missing or invalid count')
                values[key]=int(cells[index])
            if values['minutes']>130 or values['goals']>values['shots']:raise ValueError('Inconsistent player statistics')
            for key,index in [('xg',11),('xa',12)]:
                # Displayed xG contains a signed actual-vs-expected difference after the value.
                parsed=re.fullmatch(r'(\d+(?:\.\d+)?)(?:[+-]\d+(?:\.\d+)?)?',cells[index])
                if not parsed:raise ValueError('Invalid expected statistic')
                values[key]=float(parsed[1])
                if not math.isfinite(values[key]):raise ValueError('Non-finite statistic')
            rows.append({'provider':'understat','player_id':pid,'player':name,'match_id':'understat:'+mid[1],
                         'date':day.isoformat(),'home':cells[2],'away':cells[4],'score':cells[3],
                         'position':cells[5],'source':raw['match_url'],'observed_at':document['observed_at'],
                         'team':None,'shots_on_target':None,'yellow_cards':None,'red_cards':None,**values})
    if not rows:raise ValueError('Empty history')
    return pid,rows


def import_pages(store,path):
    document=json.loads(Path(path).read_text(encoding='utf-8'));pid,rows=normalize(document)
    initialize(store)
    with store.connect() as c:
        old=c.execute('SELECT observed_at FROM public_player_pages WHERE player_id=?',(pid,)).fetchone()
        if old and old[0]>document['observed_at']:raise ValueError('Older snapshot would overwrite newer data')
        c.execute('INSERT OR REPLACE INTO public_player_pages VALUES (?,?,?)',(pid,document['observed_at'],json.dumps(document,allow_nan=False)))
        # A player-page refresh must not remove richer match-roster/card records.
        roster_matches={r[0] for r in c.execute("SELECT match_id FROM public_player_matches WHERE player_id=? AND json_extract(payload,'$.league') IS NOT NULL",(pid,))}
        c.executemany('INSERT OR REPLACE INTO public_player_matches VALUES (?,?,?,?)',
                      [(pid,r['match_id'],r['date'],json.dumps(r,allow_nan=False)) for r in rows if r['match_id'] not in roster_matches])
    return {'player':rows[0]['player'],'appearances':len(rows)}


def summary(store,league='',query='',offset=0,limit=24):
    initialize(store)
    with store.connect() as c:
        rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM public_player_matches ORDER BY date DESC,match_id')]
    from .rosters import coverage,LEAGUES
    if league and league not in LEAGUES:raise ValueError('Unknown player league')
    if offset<0 or not 1<=limit<=50 or len(query)>100:raise ValueError('Invalid player page parameters')
    if league:rows=[r for r in rows if r.get('league')==league]
    if query:rows=[r for r in rows if query.casefold() in (r['player']+' '+(r.get('team') or '')).casefold()]
    players={}
    for row in rows:
        players.setdefault(row['player_id'],[]).append(row)
    items=sorted(players.items(),key=lambda item:item[1][0]['player'].casefold())
    return {'appearances':len(rows),'total_players':len(items),'offset':offset,'limit':limit,
        'has_more':offset+limit<len(items),'coverage':coverage(store),'players':[{'id':pid,'name':history[0]['player'],
        'appearances':len(history),'latest':history[0]['date'],'recent':history[:10],
        'source':'https://understat.com/player/'+pid.split(':')[1]} for pid,history in items[offset:offset+limit]],
        'notice':'Current-season coverage is measured against the public league inventories below. Older history varies by player. Cards are provider-reported timeline events; shots on target and UCL are not covered. Appearance statistics are descriptive, not pre-match probabilities.'}
