"""Optional API-Football history adapter; no unvalidated player probabilities.

IDs stay in the provider namespace. Missing statistics stay null, never zero.
Only completed, regulation-time fixtures are accepted for the initial dataset.
"""
import json
import os

import requests
from dotenv import load_dotenv

from .store import ROOT, utcnow

MARKETS=[
    {'name':'Anytime scorer','needs':'Goals, shots, minutes, starts and penalty role'},
    {'name':'2+ shots on target','needs':'Per-match shots on target and expected minutes'},
    {'name':'Score or assist','needs':'Goals and assists in the same match, plus minutes'},
    {'name':'Shown a card','needs':'Cards, fouls, minutes, position and referee context'},
]


def initialize(store):
    with store.connect() as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS player_fixture_snapshots (
                fixture_id INTEGER PRIMARY KEY, observed_at TEXT, payload TEXT);
            CREATE TABLE IF NOT EXISTS player_appearances (
                fixture_id INTEGER, player_id INTEGER, team_id INTEGER, date TEXT,
                payload TEXT, PRIMARY KEY(fixture_id,player_id));
        ''')


def configured():
    load_dotenv(ROOT/'.env')
    return bool(os.getenv('API_FOOTBALL_KEY'))


def fetch(endpoint, params):
    if not configured():raise ValueError('Set API_FOOTBALL_KEY on the server to import player history.')
    try:
        response=requests.get('https://v3.football.api-sports.io/'+endpoint,params=params,
            headers={'x-apisports-key':os.environ['API_FOOTBALL_KEY']},timeout=(5,30))
        response.raise_for_status();body=response.json()
        if not isinstance(body,dict) or body.get('errors') or not isinstance(body.get('response'),list):
            raise ValueError('Provider returned an error or invalid data; check account coverage and quota.')
        return body['response']
    except requests.RequestException:
        raise ValueError('Player provider request failed; check connectivity, credentials and quota.') from None


def number(value):
    if value is None:return None
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not 0<=value<=1000:
        raise ValueError('Invalid player statistic')
    return value


def normalize(fixture, blocks):
    meta=fixture['fixture'];fid=meta['id'];date=meta['date']
    if meta['status']['short']!='FT':raise ValueError('Only completed regulation-time fixtures are supported; extra-time games require separate statistics.')
    from .tracking import instant
    if instant(date)>=instant(utcnow()):raise ValueError('Completed fixture cannot have a future kickoff')
    team_ids={fixture['teams'][s]['id'] for s in ['home','away']}
    rows=[];seen=set()
    for block in blocks:
        team=block['team']
        if team['id'] not in team_ids:raise ValueError('Player team does not match the fixture')
        for entry in block['players']:
            player=entry['player'];pid=player['id']
            if pid in seen:raise ValueError('Duplicate player in fixture response')
            seen.add(pid)
            stats=entry['statistics']
            if len(stats)!=1:raise ValueError('Ambiguous player statistics')
            s=stats[0];games=s.get('games') or {};shots=s.get('shots') or {};goals=s.get('goals') or {};cards=s.get('cards') or {}
            row={'provider':'api-football','fixture_id':fid,'player_id':pid,'player':player['name'],
                 'team_id':team['id'],'team':team['name'],'date':date,'competition_id':fixture['league']['id'],
                 'season':fixture['league']['season'],'minutes':number(games.get('minutes')),
                 'substitute':games.get('substitute'),'position':games.get('position'),
                 'shots':number(shots.get('total')),'shots_on_target':number(shots.get('on')),
                 'goals':number(goals.get('total')),'assists':number(goals.get('assists')),
                 'yellow_cards':number(cards.get('yellow')),'red_cards':number(cards.get('red')),
                 'fouls_committed':number((s.get('fouls') or {}).get('committed'))}
            if row['minutes'] is not None and row['minutes']>130:raise ValueError('Invalid minutes')
            if row['shots'] is not None and row['shots_on_target'] is not None and row['shots_on_target']>row['shots']:
                raise ValueError('Shots on target exceed total shots')
            rows.append(row)
    if not rows:raise ValueError('No player statistics available for this fixture')
    return rows


def import_fixture(store,fid):
    if type(fid) is not int or fid<1:raise ValueError('Invalid API-Football fixture ID')
    fixtures=fetch('fixtures',{'id':fid})
    if len(fixtures)!=1 or fixtures[0]['fixture']['id']!=fid:raise ValueError('Provider fixture identity mismatch')
    blocks=fetch('fixtures/players',{'fixture':fid})
    rows=normalize(fixtures[0],blocks);initialize(store)
    with store.connect() as c:
        c.execute('INSERT OR REPLACE INTO player_fixture_snapshots VALUES (?,?,?)',
                  (fid,utcnow(),json.dumps({'fixture':fixtures[0],'players':blocks},allow_nan=False)))
        c.execute('DELETE FROM player_appearances WHERE fixture_id=?',(fid,))
        c.executemany('INSERT INTO player_appearances VALUES (?,?,?,?,?)',
                      [(fid,r['player_id'],r['team_id'],r['date'],json.dumps(r,allow_nan=False)) for r in rows])
    return {'provider_fixture':fid,'appearances':len(rows)}


def status(store):
    initialize(store)
    with store.connect() as c:
        n=c.execute('SELECT COUNT(*),COUNT(DISTINCT fixture_id) FROM player_appearances').fetchone()
        latest=c.execute('SELECT MAX(observed_at) FROM player_fixture_snapshots').fetchone()[0]
    return {'configured':configured(),'appearances':n[0],'fixtures':n[1],'last_import':latest,
            'probabilities_available':False,'markets':MARKETS,
            'notice':'Player probabilities remain unavailable until history, fixture mapping, expected minutes and a separately validated model are ready.'}
