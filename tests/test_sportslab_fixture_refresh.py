from sportslab.store import Store
from sportslab.fixture_refresh import status,refresh,ensure


def test_refresh_failure_preserves_data_and_retries(tmp_path):
    s=Store(tmp_path/'test.sqlite3');status(s)
    class Broken:
        def __init__(self,s):pass
        def fixtures(self):raise ValueError('secret must not leak')
    refresh(s,Broken)
    assert 'secret' not in status(s)['error']
    assert status(s)['refreshing'] is False
    with s.connect() as c:assert c.execute('SELECT next_check FROM fixture_refresh').fetchone()[0]>0


def test_shared_lease_prevents_duplicate_workers(tmp_path,monkeypatch):
    s=Store(tmp_path/'test.sqlite3');calls=[]
    class Thread:
        def __init__(self,**kwargs):calls.append(kwargs)
        def start(self):pass
    monkeypatch.setattr('sportslab.fixture_refresh.threading.Thread',Thread)
    assert ensure(s)['refreshing']
    assert ensure(s)['refreshing']
    assert len(calls)==1


def test_success_records_freshness(tmp_path):
    s=Store(tmp_path/'test.sqlite3');status(s)
    class Provider:
        def __init__(self,s):pass
        def fixtures(self):return [{'id':'a'}]
    s.upsert=lambda rows:len(rows)
    refresh(s,Provider)
    assert status(s)['updated_at']
    assert status(s)['error'] is None
