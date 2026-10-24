"""Public matchboard forecasts and a rate-limited, shared football scoreboard.

Scoreboard observations never enter training or settle private predictions.
A cached pre-match forecast is not an in-play probability model.
"""
import json
import os
import time
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv

from .catalog import canonical, team_id
from .store import ROOT, digest, utcnow

COMPETITIONS={'PL':'E0','ELC':'E1','PD':'SP1','BL1':'D1','SA':'I1','FL1':'F1','DED':'N1','PPL':'P1','CL':'CL'}


def initialize(store):
    with store.connect() as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS board_forecasts (
                fixture_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS live_feed_cache (
                feed TEXT PRIMARY KEY, next_check REAL NOT NULL DEFAULT 0,
                payload TEXT, fetched_at TEXT, error TEXT);
        ''')


def forecast(store,predictor,fixture,data_version=None):
    """Caller owns the predictor lock. Never generate a forecast after kickoff."""
    if fixture['status'] not in ['timed','scheduled'] or fixture['date']<=utcnow():
        raise ValueError('Pre-match forecast unavailable: kickoff has passed or the fixture is not scheduled.')
    manifest,_=predictor.load(fixture['sport'])
    fingerprint=digest([fixture,manifest['version'],data_version or store.version(fixture['sport'])])
    with store.connect() as c:
        row=c.execute('SELECT fingerprint,payload FROM board_forecasts WHERE fixture_id=?',(fixture['id'],)).fetchone()
    if row and row['fingerprint']==fingerprint:return json.loads(row['payload'])
    result=predictor.predict(fixture)
    if fixture['date']<=utcnow():raise ValueError('Kickoff passed while calculating. Pre-match forecast withheld.')
    summary={key:result[key] for key in ['probabilities','scorelines','expected','warnings','model_version','data_version','created_at','history_through']}
    summary['fixture']={key:fixture[key] for key in ['id','sport','competition','date','home_id','away_id']}
    with store.connect() as c:
        c.execute('INSERT OR REPLACE INTO board_forecasts VALUES (?,?,?)',(fixture['id'],fingerprint,json.dumps(summary)))
    return summary


def normalize_match(m):
    comp=COMPETITIONS.get((m.get('competition') or {}).get('code'))
    home=(m.get('homeTeam') or {}).get('name');away=(m.get('awayTeam') or {}).get('name')
    if not comp or not home or not away or not m.get('utcDate') or m.get('id') is None:return None
    home,away=canonical(home),canonical(away)
    score=m.get('score') or {};running=score.get('fullTime') or {}
    def score_value(value):
        return value if isinstance(value,int) and not isinstance(value,bool) and 0<=value<=50 else None
    minute=m.get('minute')
    if not isinstance(minute,int) or isinstance(minute,bool) or not 0<=minute<=150:minute=None
    return {'id':str(m['id']),'sport':'football','competition':comp,'home':home,'away':away,
            'home_id':team_id('football',home),'away_id':team_id('football',away),
            'date':m['utcDate'].replace('Z','+00:00'),'status':str(m.get('status','UNKNOWN')).lower(),
            'hg':score_value(running.get('home')),'ag':score_value(running.get('away')),
            'minute':minute,'duration':score.get('duration'),'updated_at':m.get('lastUpdated'),
            'source':'football-data.org'}


class LiveFeed:
    def __init__(self,store):
        self.store=store
        load_dotenv(ROOT/'.env')

    def get(self):
        key=os.getenv('FOOTBALL_DATA_API_KEY') or os.getenv('API_KEY')
        today=datetime.now(timezone.utc).date().isoformat();feed='football:'+today
        if not key:return {'matches':[],'available':False,'error':'Live scores are not configured on this server. Set FOOTBALL_DATA_API_KEY to enable the football feed.','fetched_at':None,'next_check':None}
        now=time.time()
        # SQLite coordinates the rate limit across Gunicorn workers and visitors.
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('DELETE FROM live_feed_cache WHERE feed<>?',(feed,))
            c.execute('INSERT OR IGNORE INTO live_feed_cache(feed) VALUES (?)',(feed,))
            row=c.execute('SELECT * FROM live_feed_cache WHERE feed=?',(feed,)).fetchone()
            refresh=row['next_check']<=now
            if refresh:c.execute('UPDATE live_feed_cache SET next_check=? WHERE feed=?',(now+60,feed))
        if refresh:
            try:
                response=requests.get('https://api.football-data.org/v4/matches',params={'dateFrom':today,'dateTo':(datetime.fromisoformat(today)+timedelta(days=1)).date().isoformat()},headers={'X-Auth-Token':key},timeout=(3,12))
                response.raise_for_status();data=response.json()
                if not isinstance(data,dict) or not isinstance(data.get('matches'),list):raise ValueError('Invalid provider response')
                matches=[match for m in data['matches'] if isinstance(m,dict) and (match:=normalize_match(m)) and match['date'][:10]==today]
                with self.store.connect() as c:
                    c.execute('UPDATE live_feed_cache SET payload=?,fetched_at=?,error=NULL WHERE feed=?',(json.dumps(matches),utcnow(),feed))
            except (requests.RequestException,ValueError,TypeError,KeyError):
                # Do not return provider bodies, URLs containing credentials, or raw exceptions.
                with self.store.connect() as c:c.execute('UPDATE live_feed_cache SET error=? WHERE feed=?',('The score provider could not be refreshed. Last successful observations are shown; they may be out of date.',feed))
        with self.store.connect() as c:row=c.execute('SELECT * FROM live_feed_cache WHERE feed=?',(feed,)).fetchone()
        return {'matches':json.loads(row['payload'] or '[]'),'available':row['payload'] is not None,
                'error':row['error'],'fetched_at':row['fetched_at'],'next_check':row['next_check'],
                'refreshing':row['payload'] is None and not row['error']}

    def baselines(self,matches):
        """Exact competition, participant and kickoff identity; no fuzzy matching."""
        with self.store.connect() as c:rows=c.execute('SELECT payload FROM board_forecasts').fetchall()
        def identity(m):return (m['competition'],m['home_id'],m['away_id'],m['date'])
        cached={identity(d['fixture']):d for row in rows if (d:=json.loads(row['payload']))['created_at']<d['fixture']['date']}
        for m in matches:
            baseline=cached.get(identity(m))
            # Only show the saved reference for matches that the provider says started.
            m['prematch']=baseline if m['status'] in ['in_play','paused','finished','suspended'] else None
        return matches
