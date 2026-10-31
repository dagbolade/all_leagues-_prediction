"""Demand-driven fixture refresh, shared across web workers via a SQLite lease."""
import threading
import time
from .store import utcnow


def status(store):
    with store.connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS fixture_refresh (id INTEGER PRIMARY KEY, next_check REAL, lease_until REAL, updated_at TEXT, error TEXT)')
        c.execute('INSERT OR IGNORE INTO fixture_refresh VALUES (1,0,0,NULL,NULL)')
        row=dict(c.execute('SELECT * FROM fixture_refresh WHERE id=1').fetchone())
    return {'updated_at':row['updated_at'],'refreshing':row['lease_until']>time.time(),'error':row['error']}


def refresh(store, importer_factory=None):
    try:
        if importer_factory is None:
            from .ingest import Importer
            importer_factory=Importer
        rows=importer_factory(store).fixtures()
        if not rows:raise ValueError('Empty fixture response')
        store.upsert(rows)
        store.log_import('football:upcoming','ok',len(rows),'Automatic rolling fixture refresh')
        with store.connect() as c:
            c.execute('UPDATE fixture_refresh SET next_check=?,lease_until=0,updated_at=?,error=NULL WHERE id=1',(time.time()+600,utcnow()))
    except Exception:
        # Provider errors can include request details; never expose credentials.
        with store.connect() as c:
            c.execute('UPDATE fixture_refresh SET next_check=?,lease_until=0,error=? WHERE id=1',
                      (time.time()+60,'Fixture refresh failed. Showing saved matches; today’s coverage may be incomplete.'))


def ensure(store):
    status(store)
    now=time.time()
    with store.connect() as c:
        claimed=c.execute('UPDATE fixture_refresh SET lease_until=?,next_check=? WHERE id=1 AND lease_until<=? AND next_check<=?',
                          (now+180,now+180,now,now)).rowcount
    if claimed:threading.Thread(target=refresh,args=(store,),daemon=True).start()
    return status(store)
