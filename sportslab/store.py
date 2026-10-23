from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('SPORTSLAB_DATA') or (Path(os.environ['RAILWAY_VOLUME_MOUNT_PATH']) / 'sportslab' if os.environ.get('RAILWAY_VOLUME_MOUNT_PATH') else ROOT / 'data' / 'sportslab'))


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class Store:
    def __init__(self, path=None):
        self.path = Path(path or DATA / 'sportslab.sqlite3')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS matches (
                    id TEXT PRIMARY KEY, sport TEXT NOT NULL, competition TEXT NOT NULL,
                    date TEXT NOT NULL, home TEXT NOT NULL, away TEXT NOT NULL,
                    status TEXT NOT NULL, source TEXT NOT NULL, payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL, revision TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS matches_time ON matches(sport,date);
                CREATE INDEX IF NOT EXISTS matches_comp ON matches(competition,date);
                CREATE INDEX IF NOT EXISTS matches_provider ON matches(json_extract(payload,'$.provider_fixture_id'));
                CREATE INDEX IF NOT EXISTS matches_identity ON matches(sport,competition,substr(date,1,10),json_extract(payload,'$.home_id'),json_extract(payload,'$.away_id'));
                CREATE TABLE IF NOT EXISTS imports (
                    id INTEGER PRIMARY KEY, source TEXT NOT NULL, started_at TEXT NOT NULL,
                    status TEXT NOT NULL, rows INTEGER NOT NULL, detail TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS predictions (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, fixture_id TEXT NOT NULL,
                    created_at TEXT NOT NULL, model_version TEXT NOT NULL,
                    data_version TEXT NOT NULL, payload TEXT NOT NULL,
                    settlement TEXT, settled_at TEXT,
                    UNIQUE(owner,fixture_id,model_version));
                CREATE INDEX IF NOT EXISTS predictions_owner ON predictions(owner,created_at);
                CREATE TABLE IF NOT EXISTS settlement_events (
                    id INTEGER PRIMARY KEY, prediction_id TEXT NOT NULL,
                    recorded_at TEXT NOT NULL, payload TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('PRAGMA busy_timeout=30000')
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def upsert(self, records, observed_at=None):
        changed = 0
        with self.connect() as c:
            for record in records:
                m = dict(record)
                for key in ['id','sport','competition','date','home','away','status','source']:
                    if not m.get(key):
                        raise ValueError(f'Match lacks {key}')
                if m['home'] == m['away']:
                    raise ValueError('Participants must differ')
                # Provider IDs survive postponed kickoff dates. Exact participant/date
                # reconciliation connects result CSVs to these verified fixtures.
                provider=m.get('provider_fixture_id')
                if provider:
                    known=c.execute("SELECT id FROM matches WHERE json_extract(payload,'$.provider_fixture_id')=?",(provider,)).fetchone()
                    if known:m['id']=known['id']
                equivalent=c.execute("""SELECT id,payload FROM matches WHERE sport=? AND competition=?
                    AND substr(date,1,10)=? AND json_extract(payload,'$.home_id')=?
                    AND json_extract(payload,'$.away_id')=? AND id!=?""",
                    (m['sport'],m['competition'],m['date'][:10],m.get('home_id'),m.get('away_id'),m['id'])).fetchall()
                if len(equivalent)>1:raise ValueError('Ambiguous fixture identity; import retained for review')
                if equivalent:
                    duplicate=equivalent[0]
                    if not provider:
                        m['id']=duplicate['id']
                    else:
                        previous=json.loads(duplicate['payload'])
                        m={**previous,**{k:v for k,v in m.items() if v is not None}}
                        c.execute('UPDATE predictions SET fixture_id=? WHERE fixture_id=?',(m['id'],duplicate['id']))
                        c.execute('DELETE FROM matches WHERE id=?',(duplicate['id'],))
                old = c.execute('SELECT payload,revision FROM matches WHERE id=?',(m['id'],)).fetchone()
                if old:
                    prev = json.loads(old['payload'])
                    if prev['status']=='finished' and m['status'] in ['scheduled','timed']:
                        continue
                    if prev.get('date_precision')=='kickoff' and m.get('date_precision')=='day':
                        m['date']=prev['date'];m['date_precision']='kickoff'
                    # Enrichment/corrections preserve previously observed optional fields.
                    m = {**prev, **{k:v for k,v in m.items() if v is not None}}
                rev = digest(m)
                if old and rev == old['revision']:
                    continue
                c.execute('''INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET sport=excluded.sport,
                    competition=excluded.competition,date=excluded.date,home=excluded.home,
                    away=excluded.away,status=excluded.status,source=excluded.source,
                    payload=excluded.payload,updated_at=excluded.updated_at,revision=excluded.revision''',
                    (m['id'],m['sport'],m['competition'],m['date'],m['home'],m['away'],m['status'],m['source'],json.dumps(m,allow_nan=False),(observed_at or {}).get(record['id'],utcnow()),rev))
                changed += 1
        return changed

    def matches(self, sport=None, competition=None, status=None):
        sql, args = 'SELECT payload FROM matches WHERE 1=1', []
        for key,value in [('sport',sport),('competition',competition),('status',status)]:
            if value:
                sql += f' AND {key}=?'; args.append(value)
        with self.connect() as c:
            return [json.loads(r[0]) for r in c.execute(sql+' ORDER BY date,id',args)]

    def fixture(self, match_id):
        with self.connect() as c:
            row = c.execute('SELECT payload FROM matches WHERE id=?',(match_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def version(self, sport=None):
        sql='SELECT id,revision FROM matches'; args=[]
        if sport:
            sql+=' WHERE sport=?'; args=[sport]
        with self.connect() as c:
            return digest([tuple(r) for r in c.execute(sql+' ORDER BY id',args)])[:16]

    def log_import(self, source, status, rows, detail):
        with self.connect() as c:
            c.execute('INSERT INTO imports(source,started_at,status,rows,detail) VALUES (?,?,?,?,?)',
                      (source,utcnow(),status,rows,detail[:1000]))

    def coverage(self):
        with self.connect() as c:
            rows=[dict(r) for r in c.execute('''SELECT sport,competition,COUNT(*) AS matches,
                SUM(status='finished') AS completed,MAX(CASE WHEN status='finished' THEN date END) AS latest_result,
                MAX(updated_at) AS checked_at FROM matches GROUP BY sport,competition ORDER BY sport,competition''')]
            imports=[dict(r) for r in c.execute('SELECT * FROM imports ORDER BY id DESC LIMIT 100')]
        with self.connect() as c:
            latest=[dict(r) for r in c.execute('SELECT * FROM imports WHERE id IN (SELECT MAX(id) FROM imports GROUP BY source) ORDER BY id DESC')]
        return {'competitions':rows,'imports':imports,'latest_imports':latest,'version':self.version()}

    def journal(self, owner):
        with self.connect() as c:
            rows=c.execute('SELECT * FROM predictions WHERE owner=? ORDER BY created_at DESC',(owner,)).fetchall()
        return [{**dict(r),'payload':json.loads(r['payload']),'settlement':json.loads(r['settlement']) if r['settlement'] else None} for r in rows]

    def save_prediction(self, owner, fixture, prediction):
        kickoff=datetime.fromisoformat(fixture['date'].replace('Z','+00:00'))
        if kickoff.tzinfo is None:
            kickoff=kickoff.replace(tzinfo=timezone.utc)
        if fixture['status'] not in ['scheduled','timed'] or kickoff <= datetime.now(timezone.utc):
            raise ValueError('Only future, scheduled fixtures can be recorded before kickoff.')
        pid=digest([owner,fixture['id'],prediction['model_version']])[:24]
        with self.connect() as c:
            c.execute('INSERT OR IGNORE INTO predictions VALUES (?,?,?,?,?,?,?,?,?)',
                      (pid,owner,fixture['id'],utcnow(),prediction['model_version'],prediction['data_version'],json.dumps(prediction,allow_nan=False),None,None))
        return pid

    def settle(self, owner=None):
        from sportslab.model import settle_markets
        count=0
        with self.connect() as c:
            rows=c.execute('SELECT * FROM predictions'+(' WHERE owner=?' if owner else ''),[owner] if owner else []).fetchall()
            for r in rows:
                match=c.execute('SELECT payload FROM matches WHERE id=?',(r['fixture_id'],)).fetchone()
                if not match:
                    continue
                m=json.loads(match[0])
                if m['status'] in ['cancelled','canceled','awarded']:
                    result={'status':'void','reason':'Fixture cancelled or awarded; no played result is scored.'}
                elif m['status']!='finished' or m.get('hg') is None or m.get('ag') is None:
                    continue
                elif m.get('date_precision')=='kickoff' and m['date']<=r['created_at']:
                    result={'status':'void','reason':'Corrected kickoff predates the recorded forecast.'}
                else:
                    result={**settle_markets(json.loads(r['payload']),m),'status':'settled'}
                encoded=json.dumps(result,sort_keys=True)
                if encoded==r['settlement']:
                    continue
                c.execute('UPDATE predictions SET settlement=?,settled_at=? WHERE id=?',(encoded,utcnow(),r['id']))
                c.execute('INSERT INTO settlement_events(prediction_id,recorded_at,payload) VALUES (?,?,?)',(r['id'],utcnow(),encoded))
                count+=1
        return count
