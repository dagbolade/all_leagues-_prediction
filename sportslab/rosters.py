"""Validated current-season public match rosters and measured coverage."""
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from .public_players import initialize as initialize_players
from .tracking import instant
from .store import utcnow

LEAGUES={'EPL':'Premier League','La_liga':'La Liga','Bundesliga':'Bundesliga',
         'Serie_A':'Serie A','Ligue_1':'Ligue 1','RFPL':'Russian Premier League'}
HEADERS=['№','Player','Pos','Min','Sh','G','KP','A','xG','xA']


def initialize(store):
    initialize_players(store)
    with store.connect() as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS public_roster_snapshots (
                match_id TEXT PRIMARY KEY, league TEXT, observed_at TEXT, payload TEXT);
            CREATE TABLE IF NOT EXISTS public_roster_inventory (
                league TEXT PRIMARY KEY, observed_at TEXT, payload TEXT);
        ''')


def identifier(url,kind):
    m=re.fullmatch(r'https://understat.com/'+kind+r'/(\d+)',url or '')
    if not m:raise ValueError('Invalid public source identity')
    return 'understat:'+m[1]


def normalize(d):
    league=d['league']
    if league not in LEAGUES:raise ValueError('Unsupported league')
    observed=instant(d['observed_at'])
    if observed>instant(utcnow()):raise ValueError('Future observation')
    h,a=d['home'],d['away'];mid=identifier(h['source'],'match')
    if h['source']!=a['source'] or h['teams']!=a['teams'] or h['breadcrumb']!=a['breadcrumb']:
        raise ValueError('Inconsistent match identity')
    teams=h['teams']
    if len(teams)!=2 or teams[0]==teams[1]:raise ValueError('Invalid teams')
    day=datetime.strptime(h['breadcrumb'][-1],'%b %d %Y').date()
    if day>observed.date():raise ValueError('Future result')
    score=re.search(re.escape(teams[0])+r' (\d+) - (\d+) '+re.escape(teams[1])+r' \(',h['title'])
    if not score:raise ValueError('Missing match score')
    cards=Counter();unknown=False
    if h['cards']!=a['cards']:raise ValueError('Card timeline changed during extraction')
    for event in h['cards']:
        pid=identifier(event.get('player_url'),'player')
        for label in event['titles']:
            if label not in ['Yellow card','Red card']:unknown=True
            else:cards[(pid,label)]+=1
    rows=[];seen=set()
    for side,block,team in [('h',h,teams[0]),('a',a,teams[1])]:
        if block['headers']!=HEADERS or block['team']!=side or len(block['rows'])<11:
            raise ValueError('Incomplete or wrong-side roster')
        starters=0
        for raw in block['rows']:
            cells=raw['cells'];pid=identifier(raw['player_url'],'player')
            if pid in seen or len(cells)!=10:raise ValueError('Duplicate player or invalid columns')
            seen.add(pid);values={}
            for key,index in [('minutes',3),('shots',4),('goals',5),('key_passes',6),('assists',7)]:
                if not cells[index].isdigit():raise ValueError('Invalid count')
                values[key]=int(cells[index])
            if values['minutes']>130 or values['goals']>values['shots']:raise ValueError('Inconsistent statistics')
            for key,index in [('xg',8),('xa',9)]:
                value=re.fullmatch(r'(\d+(?:\.\d+)?)(?:[+-]\d+(?:\.\d+)?)?',cells[index])
                if not value:raise ValueError('Invalid expected statistic')
                values[key]=float(value[1])
            starters+=cells[2]!='Sub'
            rows.append({'provider':'understat','player_id':pid,'player':cells[1],'match_id':mid,
                'date':day.isoformat(),'home':teams[0],'away':teams[1],'team':team,'league':league,
                'score':score[1]+'-'+score[2],'position':cells[2],'started':cells[2]!='Sub',
                'source':h['source'],'observed_at':d['observed_at'],'shots_on_target':None,
                'yellow_cards':None if unknown else cards[(pid,'Yellow card')],
                'red_cards':None if unknown else cards[(pid,'Red card')],
                'card_definition':'Counts of provider-reported timeline events; not bookmaker settlement',**values})
        if starters!=11:raise ValueError('Roster does not contain eleven starters')
    return mid,rows


def import_directory(store,root):
    root=Path(root);index=json.loads((root/'match-index.json').read_text(encoding='utf8'))
    initialize(store);report={'matches':0,'appearances':0,'errors':[]}
    for item in index['matches']:
        path=root/'matches'/(item['url'].split('/')[-1]+'.json')
        try:
            d=json.loads(path.read_text(encoding='utf8'))
            if d['league']!=item['league'] or d['home']['source']!=item['url']:raise ValueError('Inventory mismatch')
            mid,rows=normalize(d)
            with store.connect() as c:
                old=c.execute('SELECT observed_at FROM public_roster_snapshots WHERE match_id=?',(mid,)).fetchone()
                if old and instant(old[0])>instant(d['observed_at']):raise ValueError('Older snapshot')
                c.execute('INSERT OR REPLACE INTO public_roster_snapshots VALUES (?,?,?,?)',(mid,d['league'],d['observed_at'],json.dumps(d,allow_nan=False)))
                # Replace this match as a unit, retaining all other player history.
                c.execute('DELETE FROM public_player_matches WHERE match_id=?',(mid,))
                c.executemany('INSERT INTO public_player_matches VALUES (?,?,?,?)',
                    [(r['player_id'],mid,r['date'],json.dumps(r,allow_nan=False)) for r in rows])
            report['matches']+=1;report['appearances']+=len(rows)
        except (ValueError,KeyError,OSError,TypeError) as e:
            report['errors'].append({'match':item['url'],'error':str(e)})
    for league in LEAGUES:
        roster=json.loads((root/(league+'-roster.json')).read_text(encoding='utf8'))
        pages=roster['pages']
        if not pages or not pages[-1]['last'] or [int(p['page']) for p in pages]!=list(range(1,len(pages)+1)):
            raise ValueError('Incomplete league roster inventory')
        players=sorted({identifier(r['url'],'player') for p in pages for r in p['players']})
        payload={'players':players,'matches':[identifier(m['url'],'match') for m in index['matches'] if m['league']==league],
                 'season':2026,'teams':sum(t['league']==league for t in index['teams'])}
        with store.connect() as c:c.execute('INSERT OR REPLACE INTO public_roster_inventory VALUES (?,?,?)',(league,roster['observed_at'],json.dumps(payload)))
    return report


def coverage(store):
    initialize(store)
    with store.connect() as c:
        inventories=c.execute('SELECT * FROM public_roster_inventory ORDER BY league').fetchall()
        snapshots={r['match_id']:r['league'] for r in c.execute('SELECT match_id,league FROM public_roster_snapshots')}
        rows=c.execute("SELECT player_id,match_id,json_extract(payload,'$.league') AS league FROM public_player_matches WHERE json_extract(payload,'$.league') IS NOT NULL").fetchall()
    result=[]
    for inv in inventories:
        data=json.loads(inv['payload']);league=inv['league'];present={r['player_id'] for r in rows if r['league']==league}
        expected=set(data['players']);matches=set(data['matches'])
        done={mid for mid,l in snapshots.items() if l==league}&matches
        result.append({'league':league,'name':LEAGUES[league],'season':data['season'],'teams':data['teams'],
            'expected_players':len(expected),'covered_players':len(expected&present),'extra_players':len(present-expected),
            'expected_matches':len(matches),'covered_matches':len(done),'observed_at':inv['observed_at'],
            'missing_players':sorted(expected-present),'missing_matches':sorted(matches-done)})
    return result
