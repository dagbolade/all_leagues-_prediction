"""Provider-specific imports with immutable raw downloads and transactional upserts."""
from __future__ import annotations

import concurrent.futures
import hashlib
import io
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from .catalog import DOMESTIC, GLOBAL, canonical, team_id
from .store import Store, ROOT, digest


def number(v):
    try:
        n=float(v)
        return n if pd.notna(n) and abs(n)<1e8 else None
    except (TypeError,ValueError):
        return None


def football_rows(df, competition, source, season=None):
    df=df.rename(columns={'Home':'HomeTeam','Away':'AwayTeam','HG':'FTHG','AG':'FTAG','Res':'FTR'})
    if not {'Date','HomeTeam','AwayTeam'} <= set(df):
        raise ValueError('Provider response lacks fixture columns')
    records=[]
    for row in df.to_dict('records'):
        date=pd.to_datetime(row['Date'],errors='coerce',dayfirst=True,format='mixed')
        if pd.isna(date) or pd.isna(row['HomeTeam']) or pd.isna(row['AwayTeam']):
            continue
        home,away=canonical(row['HomeTeam']),canonical(row['AwayTeam'])
        hg,ag=number(row.get('FTHG')),number(row.get('FTAG'))
        if hg is None or ag is None or row.get('FTR') not in ['H','D','A']:
            continue  # Result downloads are not a source of invented future scores.
        if hg<0 or ag<0 or hg>30 or ag>30 or hg%1 or ag%1:
            continue
        if date.date()>datetime.now(timezone.utc).date(): continue
        date=date.strftime('%Y-%m-%dT00:00:00+00:00')
        hid,aid=team_id('football',home),team_id('football',away)
        m={'id':'fdc:'+digest([competition,date[:10],hid,aid])[:24], 'sport':'football','competition':competition,
           'date':date,'date_precision':'day','season':str(season or row.get('Season','')),'home':home,'away':away,
           'home_id':hid,'away_id':aid,'hg':hg,'ag':ag,'status':'finished','source':source,
           'hhg':number(row.get('HTHG')),'hag':number(row.get('HTAG')),'referee':str(row.get('Referee','')),
           'neutral':False,'surface':'','home_xg':None,'away_xg':None,'xg_source':None}
        records.append(m)
    return records


class Importer:
    def __init__(self,store=None):
        self.store=store or Store()
        self.raw=self.store.path.parent/'raw'
        self.raw.mkdir(exist_ok=True)
        load_dotenv(ROOT/'.env')

    def fetch(self,url,headers=None):
        # No credentials are ever written to logs or saved request metadata.
        for attempt in range(3):
            try:
                response=requests.get(url,headers=headers or {},timeout=(10,35))
            except (requests.Timeout,requests.ConnectionError):
                if attempt==2: raise
                time.sleep(2**attempt);continue
            if response.status_code in [429,500,502,503,504] and attempt<2:
                time.sleep(min(10,2**attempt+1)); continue
            response.raise_for_status()
            body=response.content
            key=hashlib.sha256(body).hexdigest()
            (self.raw/(key+'.response')).write_bytes(body)
            (self.raw/(key+'.json')).write_text(json.dumps({'url':url,'fetched_at':datetime.now(timezone.utc).isoformat(),'sha256':key}),encoding='utf-8')
            return body
        raise RuntimeError('Provider retries exhausted')

    def job(self,label,fn):
        try:
            records=fn()
            if not records:
                self.store.log_import(label,'empty',0,'No eligible records returned; previous data retained')
                print(label,'empty',flush=True); return 0
            n=self.store.upsert(records)
            if label.startswith('basketball:EuroLeague'):
                seasons={r.get('season') for r in records if r['status']=='finished'}
                for season in seasons:
                    finished=sum(r['status']=='finished' and r.get('season')==season for r in records)
                    if finished<350:continue
                    # A complete official season supersedes old mislabeled archive games.
                    year=int(season)
                    with self.store.connect() as c:
                        c.execute("""DELETE FROM matches WHERE competition='EuroLeague' AND source='local archive'
                            AND date>=? AND date<? AND id NOT IN (SELECT fixture_id FROM predictions)""",
                            (f'{year}-07-01',f'{year+1}-07-01'))
            self.store.log_import(label,'ok',len(records),f'{n} inserted or corrected')
            print(label,len(records),'records;',n,'changes',flush=True)
            return n
        except Exception as e:
            # Do not include request headers or provider auth contents.
            detail=f'{type(e).__name__}: {str(e)[:300]}'
            self.store.log_import(label,'error',0,detail)
            print(label,detail,flush=True)
            return 0

    def bootstrap(self):
        with self.store.connect() as c:
            completed={r[0] for r in c.execute("SELECT source FROM imports WHERE status='ok' AND source LIKE 'local:%'")}
        for path in sorted((ROOT/'data/raw').glob('all-euro-data-*.xlsx')):
            season=path.stem[-9:]
            book=pd.ExcelFile(path)
            if all(f'local:{path.name}:{l}' in completed for l in book.sheet_names):
                book.close();continue
            sheets={l:book.parse(l) for l in book.sheet_names if f'local:{path.name}:{l}' not in completed}
            book.close()
            for league,df in sheets.items():
                self.job(f'local:{path.name}:{league}',lambda d=df,l=league:football_rows(d,l,'football-data.co.uk (local archive)',season))
        for sport,path in [('basketball',ROOT/'data/basketball/raw/basketball_all_data.csv'),('tennis',ROOT/'data/tennis/raw/tennis_real_data.csv')]:
            if path.exists() and f'local:{sport}' not in completed:
                self.job(f'local:{sport}',lambda s=sport,p=path:self.other_rows(pd.read_csv(p),s))

    def other_rows(self,df,sport,source='local archive'):
        records=[]
        for row in df.to_dict('records'):
            date=pd.to_datetime(row.get('Date'),errors='coerce')
            if pd.isna(date): continue
            if sport=='basketball':
                home,away=row['HomeTeam'],row['AwayTeam']
                hg,ag=number(row.get('HomeScore')),number(row.get('AwayScore'))
                league=str(row.get('League','NBA'))
            else:
                home,away=row['Player1'],row['Player2']
                winner=row.get('Winner')
                if winner not in ['Player1','Player2']: continue
                hg,ag=(1,0) if winner=='Player1' else (0,1)
                league=str(row.get('Tour','ATP'))
                if league not in ['ATP','WTA']: league='ATP'
            if hg is None or ag is None or hg==ag or min(hg,ag)<0 or max(hg,ag)>300 or hg%1 or ag%1: continue
            if date.date()>datetime.now(timezone.utc).date(): continue
            if sport=='tennis' and home>away:
                home,away=away,home;hg,ag=ag,hg
            hid,aid=team_id(sport,home),team_id(sport,away)
            records.append({'id':sport+':'+digest([league,str(date.date()),*sorted([hid,aid]),''])[:24],
                'sport':sport,'competition':league,'date':date.strftime('%Y-%m-%dT00:00:00+00:00'),'date_precision':'day',
                'home':home,'away':away,'home_id':hid,'away_id':aid,'hg':hg,'ag':ag,'status':'finished','source':source,
                'surface':str(row.get('Surface','')),'neutral':sport=='tennis' or bool(row.get('Neutral',False)),'hhg':None,'hag':None,
                'home_xg':None,'away_xg':None,'xg_source':None,'season':str(row.get('Season',''))})
        return records

    def domestic(self,season,league):
        url=f'https://www.football-data.co.uk/mmz4281/{season}/{league}.csv'
        return football_rows(pd.read_csv(io.BytesIO(self.fetch(url))),league,'football-data.co.uk',f'20{season[:2]}-20{season[2:]}')

    def global_league(self,country,league):
        df=pd.read_csv(io.BytesIO(self.fetch(f'https://www.football-data.co.uk/new/{country}.csv')))
        return football_rows(df,league,'football-data.co.uk')

    def ucl(self,year):
        key=os.getenv('FOOTBALL_DATA_API_KEY') or os.getenv('API_KEY')
        if not key: raise ValueError('FOOTBALL_DATA_API_KEY is not configured')
        data=json.loads(self.fetch(f'https://api.football-data.org/v4/competitions/CL/matches?season={year}',{'X-Auth-Token':key}))
        records=[]
        for m in data.get('matches',[]):
            if not m['homeTeam'].get('name') or not m['awayTeam'].get('name'): continue
            home,away=canonical(m['homeTeam']['name']),canonical(m['awayTeam']['name'])
            score=m.get('score',{})
            # fullTime may include extra time. Never silently use it for regulation markets.
            regulation=score.get('regularTime') or (score.get('fullTime',{}) if score.get('duration') in [None,'REGULAR'] else {})
            half=score.get('halfTime') or {}
            status={'FINISHED':'finished','TIMED':'timed','SCHEDULED':'scheduled'}.get(m['status'],m['status'].lower())
            records.append({'id':f"fdo:{m['id']}",'sport':'football','competition':'CL','date':m['utcDate'].replace('Z','+00:00'),
                'date_precision':'kickoff','season':str(year),'home':home,'away':away,'home_id':team_id('football',home),'away_id':team_id('football',away),
                'provider_home_id':m['homeTeam']['id'],'provider_away_id':m['awayTeam']['id'],
                'hg':number(regulation.get('home')),'ag':number(regulation.get('away')),'hhg':number(half.get('home')),'hag':number(half.get('away')),
                'status':status,'source':'football-data.org','stage':m.get('stage'),'matchday':m.get('matchday'),
                'neutral':m.get('stage')=='FINAL','surface':'','provider_score':score,'home_xg':None,'away_xg':None,'xg_source':None})
        return records

    def fixtures(self):
        key=os.getenv('FOOTBALL_DATA_API_KEY') or os.getenv('API_KEY')
        if not key: raise ValueError('FOOTBALL_DATA_API_KEY is not configured')
        from datetime import timedelta
        now=datetime.now(timezone.utc)
        data=json.loads(self.fetch(f'https://api.football-data.org/v4/matches?dateFrom={now-timedelta(days=3):%Y-%m-%d}&dateTo={now+timedelta(days=6):%Y-%m-%d}',{'X-Auth-Token':key}))
        mapping={'PL':'E0','ELC':'E1','PD':'SP1','BL1':'D1','SA':'I1','FL1':'F1','DED':'N1','PPL':'P1','CL':'CL'}
        result=[]
        for m in data.get('matches',[]):
            comp=mapping.get(m['competition']['code'])
            if not comp or not m['homeTeam'].get('name') or not m['awayTeam'].get('name'): continue
            h,a=canonical(m['homeTeam']['name']),canonical(m['awayTeam']['name'])
            hid,aid=team_id('football',h),team_id('football',a)
            mid=f"fdo:{m['id']}" if comp=='CL' else 'fdc:'+digest([comp,m['utcDate'][:10],hid,aid])[:24]
            score=m.get('score',{}); full=score.get('regularTime') or (score.get('fullTime',{}) if score.get('duration') in [None,'REGULAR'] else {})
            result.append({'id':mid,'provider_fixture_id':m['id'],'sport':'football','competition':comp,'home':h,'away':a,'home_id':hid,'away_id':aid,
                'date':m['utcDate'].replace('Z','+00:00'),'date_precision':'kickoff','status':m['status'].lower(),'hg':number(full.get('home')),'ag':number(full.get('away')),
                'hhg':number((score.get('halfTime') or {}).get('home')),'hag':number((score.get('halfTime') or {}).get('away')),
                'source':'football-data.org','neutral':m.get('stage')=='FINAL','surface':'','season':str(m['season']['startDate'][:4])})
        return result

    def tennis(self,tour,year):
        folder=str(year) if tour=='ATP' else f'{year}w'
        from urllib.parse import urljoin, urlparse
        page='https://tennis-data.co.uk/data.php'
        html=self.fetch(page).decode('latin-1')
        links=re.findall(r'''href=["']([^"']+)''',html,re.I)
        links=[urljoin(page,u) for u in links if urlparse(u).path.endswith(f'/{folder}/{year}.xlsx')]
        links=[u for u in links if urlparse(u).hostname in ['tennis-data.co.uk','www.tennis-data.co.uk']]
        if len(set(links))!=1:raise ValueError('Current tennis download link is missing or ambiguous')
        url=links[0]
        df=pd.read_excel(io.BytesIO(self.fetch(url)))
        out=[]
        for r in df.to_dict('records'):
            if str(r.get('Comment','Completed')).lower()!='completed': continue
            if pd.isna(r.get('Winner')) or pd.isna(r.get('Loser')): continue
            names=sorted([r['Winner'],r['Loser']])
            out.append({'Date':r['Date'],'Player1':names[0],'Player2':names[1],
                'Winner':'Player1' if r['Winner']==names[0] else 'Player2','Tour':tour,'Surface':r.get('Surface','')})
        return self.other_rows(pd.DataFrame(out),'tennis',f'tennis-data.co.uk {tour}')

    def nba(self,year):
        # Single-day feeds avoid range/limit failures and silent monthly truncation.
        from datetime import timedelta, date
        last=max((m['date'][:10] for m in self.store.matches('basketball','NBA','finished')),default=f'{year}-01-01')
        today=datetime.now(timezone.utc).date()
        start=max(date.fromisoformat(last)-timedelta(days=2),today-timedelta(days=365))
        days=[start+timedelta(days=i) for i in range((today-start).days+1)]
        def day_rows(day):
            data=json.loads(self.fetch(f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={day:%Y%m%d}'))
            out=[]
            for event in data.get('events',[]):
                # Do not blend preseason exhibitions into regular/postseason history.
                if event.get('season',{}).get('type') not in [2,3]:continue
                for match in event.get('competitions',[]):
                    if not match.get('status',{}).get('type',{}).get('completed'):continue
                    participants={c['homeAway']:c for c in match['competitors']}
                    h,a=participants['home'],participants['away']
                    out.append({'Date':pd.Timestamp(event['date']).tz_convert('America/New_York').date(),
                        'HomeTeam':h['team']['displayName'],'AwayTeam':a['team']['displayName'],
                        'HomeScore':h.get('score'),'AwayScore':a.get('score'),'Neutral':match.get('neutralSite',False),
                        'League':'NBA','Season':str(event['season'].get('year',year))})
            return out
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            rows=[r for batch in pool.map(day_rows,days) for r in batch]
        return self.other_rows(pd.DataFrame(rows),'basketball','ESPN scoreboard') if rows else []

    def euroleague(self,year):
        from .aliases import EUROLEAGUE_CLUBS
        clubs=json.loads((Path(__file__).parent/'euroleague_clubs.json').read_text(encoding='utf-8'))
        data=json.loads(self.fetch(f'https://api-live.euroleague.net/v2/competitions/E/seasons/E{year}/games'))
        if len(data['data'])!=data['total']:raise ValueError('Incomplete EuroLeague response; pagination requires review')
        records=[]
        for m in data['data']:
            if not m.get('utcDate') or m['local']['club'].get('isVirtual') or m['road']['club'].get('isVirtual'):continue
            home=clubs.get(m['local']['club']['code'],EUROLEAGUE_CLUBS.get(m['local']['club']['name'],m['local']['club']['name']))
            away=clubs.get(m['road']['club']['code'],EUROLEAGUE_CLUBS.get(m['road']['club']['name'],m['road']['club']['name']))
            if not m.get('played'):
                if m['utcDate']<datetime.now(timezone.utc).isoformat():continue
                records.append({'id':'euroleague:'+m['identifier'],'provider_fixture_id':'euroleague:'+m['identifier'],
                    'sport':'basketball','competition':'EuroLeague','date':m['utcDate'].replace('Z','+00:00'),'date_precision':'kickoff',
                    'home':home,'away':away,'home_id':team_id('basketball',home),'away_id':team_id('basketball',away),
                    'status':'timed' if m.get('confirmedHour') else 'scheduled','source':'EuroLeague official',
                    'hg':None,'ag':None,'surface':'','neutral':m.get('isNeutralVenue',False),'season':str(year)})
                continue
            rows=self.other_rows(pd.DataFrame([{'Date':m['utcDate'],'HomeTeam':home,'AwayTeam':away,
                'HomeScore':m['local']['score'],'AwayScore':m['road']['score'],'League':'EuroLeague','Season':str(year),
                'Neutral':m.get('isNeutralVenue',False) or m.get('phaseType',{}).get('code')=='FF'}]),'basketball','EuroLeague official')
            for row in rows:
                row.update(date=m['utcDate'].replace('Z','+00:00'),date_precision='kickoff',provider_fixture_id='euroleague:'+m['identifier'],euroleague_fixture=m['identifier'])
                records.append(row)
        return records

    def xg(self,league,year):
        understat={'E0':'EPL','SP1':'La_liga','I1':'Serie_A','D1':'Bundesliga','F1':'Ligue_1'}[league]
        payload=json.loads(self.fetch(f'https://understat.com/getLeagueData/{understat}/{year}',{'X-Requested-With':'XMLHttpRequest'}))
        data=payload['dates']
        index={(m['date'][:10],m['home_id'],m['away_id']):m for m in self.store.matches('football',league)}
        out=[]
        for m in data:
            h,a=canonical(m['h']['title']),canonical(m['a']['title'])
            key=(m['datetime'][:10],team_id('football',h),team_id('football',a))
            existing=index.get(key)
            hx,ax=number(m['xG'].get('h')),number(m['xG'].get('a'))
            if existing and hx is not None and ax is not None:
                out.append({**existing,'home_xg':hx,'away_xg':ax,'xg_source':'Understat'})
        return out

    def refresh(self,include_xg=True):
        year=datetime.now(timezone.utc).year
        start=year if datetime.now(timezone.utc).month>=7 else year-1
        jobs=[]
        for y in [start-1,start]:
            season=f'{y%100:02d}{(y+1)%100:02d}'
            for league in DOMESTIC:
                jobs.append((f'football:{season}:{league}',lambda s=season,l=league:self.domestic(s,l)))
        for country,league in GLOBAL.items():
            jobs.append((f'football:global:{country}',lambda c=country,l=league:self.global_league(c,l)))
        for tour in ['ATP','WTA']:
            jobs.append((f'tennis:{tour}:{year}',lambda t=tour:self.tennis(t,year)))
        jobs.append(('basketball:NBA',lambda:self.nba(year)))
        for y in [start-1,start]:jobs.append((f'basketball:EuroLeague:{y}',lambda y=y:self.euroleague(y)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures=[pool.submit(self.job,label,fn) for label,fn in jobs]
            for future in concurrent.futures.as_completed(futures): future.result()
        for y in range(start-4,start+1):
            self.job(f'football:CL:{y}',lambda y=y:self.ucl(y))
            time.sleep(7)  # Respect football-data.org's basic request allowance.
        self.job('football:upcoming',self.fixtures)
        if include_xg:
            for l in ['E0','SP1','I1','D1','F1']:
                for y in range(start-5,start+1):
                    with self.store.connect() as c:
                        done=c.execute("SELECT 1 FROM imports WHERE source=? AND status='ok'",(f'xg:{l}:{y}',)).fetchone()
                    if y<start-1 and done:continue
                    self.job(f'xg:{l}:{y}',lambda l=l,y=y:self.xg(l,y))
                    time.sleep(1)
        self.store.settle()
