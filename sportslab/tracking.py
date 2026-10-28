"""Prospective evaluation. Never backfill forecasts from already known results."""
import json
import math
from datetime import datetime, timezone

from .store import utcnow
from .model import settle_markets


def instant(value):
    parsed=datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:raise ValueError('Timestamp must contain a timezone')
    return parsed.astimezone(timezone.utc)


def initialize(store):
    with store.connect() as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS forecast_ledger (
                fixture_id TEXT, kickoff TEXT, horizon INTEGER, sport TEXT,
                competition TEXT, created_at TEXT, payload TEXT, reason TEXT,
                settlement TEXT, PRIMARY KEY(fixture_id,kickoff,horizon));
            CREATE TABLE IF NOT EXISTS forecast_ledger_events (
                id INTEGER PRIMARY KEY, fixture_id TEXT, kickoff TEXT, horizon INTEGER,
                recorded_at TEXT, settlement TEXT);
            CREATE TABLE IF NOT EXISTS tracking_runs (created_at TEXT, report TEXT);
        ''')


def capture(store, predictor):
    """Run every 15 minutes: first observation in 24h/1h +/-15m window wins.

    A withheld forecast occupies its slot too, preventing later cherry-picking.
    Caller holds the pipeline lock. This does not refresh providers or train models.
    """
    initialize(store)
    counts={'recorded':0, 'withheld':0}
    for fixture in store.matches():
        if fixture['status'] not in ['timed','scheduled']:
            continue
        now=datetime.now(timezone.utc)
        hours=(instant(fixture['date'])-now).total_seconds()/3600
        horizon=next((h for h in (24,1) if abs(hours-h)<=.25),None)
        if horizon is None:
            continue
        identity=(fixture['id'],fixture['date'],horizon)
        with store.connect() as c:
            if c.execute('SELECT 1 FROM forecast_ledger WHERE fixture_id=? AND kickoff=? AND horizon=?',identity).fetchone():
                continue
        result=None;reason=None
        if fixture.get('date_precision')!='kickoff':
            reason='Exact kickoff time unavailable'
        else:
            try:
                result=predictor.predict(fixture)
                f=result['features']
                if min(f['home_matches'],f['away_matches'])<5:
                    reason='Fewer than five historical appearances for a participant'
                elif max(f['home_rest'],f['away_rest'])>=90:
                    reason='Participant history is at least 90 days old'
            except ValueError as exc:
                reason=str(exc)
        # Re-check after computation; do not label a late forecast as an earlier slot.
        created=utcnow()
        remaining=(instant(fixture['date'])-instant(created)).total_seconds()/3600
        if remaining<=0 or abs(remaining-horizon)>.25:
            continue
        with store.connect() as c:
            inserted=c.execute('INSERT OR IGNORE INTO forecast_ledger VALUES (?,?,?,?,?,?,?,?,NULL)',
                (*identity,fixture['sport'],fixture['competition'],created,
                 json.dumps(result,allow_nan=False) if result and not reason else None,reason)).rowcount
        counts['withheld' if reason else 'recorded']+=inserted
    counts['settled']=settle(store)
    with store.connect() as c:
        c.execute('INSERT INTO tracking_runs VALUES (?,?)',(utcnow(),json.dumps(counts)))
    return counts


def settle(store):
    initialize(store);changed=0
    with store.connect() as c:
        rows=c.execute('SELECT * FROM forecast_ledger WHERE payload IS NOT NULL').fetchall()
        for row in rows:
            found=c.execute('SELECT payload FROM matches WHERE id=?',(row['fixture_id'],)).fetchone()
            if not found:continue
            m=json.loads(found[0]);p=json.loads(row['payload'])
            if m['status'] in ['cancelled','canceled','awarded'] or instant(m['date'])!=instant(row['kickoff']):
                result={'status':'void','reason':'Cancelled, awarded or kickoff changed'}
            elif m['status']=='finished' and m.get('hg') is not None and m.get('ag') is not None:
                result={**settle_markets(p,m),'status':'settled'}
            else:
                if row['settlement'] is None:continue
                result={'status':'pending','reason':'Previously reported result withdrawn'}
            encoded=json.dumps(result,sort_keys=True)
            if encoded==row['settlement']:continue
            args=(row['fixture_id'],row['kickoff'],row['horizon'])
            c.execute('UPDATE forecast_ledger SET settlement=? WHERE fixture_id=? AND kickoff=? AND horizon=?',(encoded,*args))
            c.execute('INSERT INTO forecast_ledger_events VALUES (NULL,?,?,?,?,?)',(*args,utcnow(),encoded))
            changed+=1
    return changed


def performance(store,sport,horizon=24):
    initialize(store)
    with store.connect() as c:
        rows=c.execute('SELECT * FROM forecast_ledger WHERE sport=? AND horizon=?',(sport,horizon)).fetchall()
        last=c.execute('SELECT created_at,report FROM tracking_runs ORDER BY rowid DESC LIMIT 1').fetchone()
    groups={};settled=0
    for row in rows:
        if not row['settlement']:continue
        result=json.loads(row['settlement'])
        if result['status']!='settled':continue
        settled+=1;p=json.loads(row['payload'])
        key=(row['competition'],p['model_version'])
        g=groups.setdefault(key,{'competition':key[0],'model_version':key[1],'n':0,'correct':0,'log_loss':0.,'brier':0.})
        markets=result['markets'];keys=['home_win','draw','away_win'] if sport=='football' else ['home_win','away_win']
        g['n']+=1;g['correct']+=result['outcome_correct']
        g['log_loss']+=sum(-math.log(max(1e-15,markets[k]['probability'])) for k in keys if markets[k]['occurred'])
        g['brier']+=sum(markets[k]['brier'] for k in keys)
    for g in groups.values():
        g['accuracy']=g.pop('correct')/g['n'];g['log_loss']/=g['n'];g['brier']/=g['n']
    return {'horizon':horizon,'tracked':len(rows),'withheld':sum(bool(r['reason']) for r in rows),
            'void':sum(bool(r['settlement']) and json.loads(r['settlement'])['status']=='void' for r in rows),
            'scheduler_stale':not last or (instant(utcnow())-instant(last['created_at'])).total_seconds()>1800,
            'settled':settled,'groups':list(groups.values()),'last_run':last['created_at'] if last else None,
            'notice':'Prospective forecasts only. Separate lead times and model versions; small samples are not evidence of reliable accuracy.'}
