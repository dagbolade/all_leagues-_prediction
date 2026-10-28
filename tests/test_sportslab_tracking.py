import json
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

import pytest

from sportslab.store import Store, utcnow
from sportslab.tracking import capture, settle, performance
from sportslab.players import normalize, import_fixture, status, fetch
from sportslab.web import create_app


def fixture():
    return dict(id='one',sport='football',competition='E0',date=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),
                home='A',away='B',home_id='a',away_id='b',status='timed',date_precision='kickoff',source='test',hg=None,ag=None)


def predictor():
    return SimpleNamespace(predict=lambda f:dict(fixture=f,probabilities={'home_win':.6,'draw':.25,'away_win':.15},
        features={'home_matches':10,'away_matches':10,'home_rest':5,'away_rest':5},model_version='v1',data_version='d1',created_at=utcnow()))


def test_capture_is_immutable_and_corrections_are_audited(tmp_path):
    store=Store(tmp_path/'test.db');f=fixture();store.upsert([f])
    assert capture(store,predictor())['recorded']==1
    assert capture(store,predictor())['recorded']==0
    store.upsert([{**f,'status':'finished','hg':2,'ag':0}]);assert settle(store)==1
    report=performance(store,'football',1)
    assert report['settled']==1 and report['groups'][0]['accuracy']==1
    assert report['groups'][0]['brier']==pytest.approx(.245)
    store.upsert([{**f,'status':'finished','hg':0,'ag':2}]);assert settle(store)==1
    assert performance(store,'football',1)['groups'][0]['accuracy']==0
    assert settle(store)==0
    with store.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM forecast_ledger_events').fetchone()[0]==2
        payload=json.loads(c.execute('SELECT payload FROM forecast_ledger').fetchone()[0])
    assert payload['probabilities']['home_win']==.6
    assert performance(store,'football',24)['tracked']==0


def test_withholding_and_rescheduling(tmp_path):
    store=Store(tmp_path/'test.db');f=fixture();store.upsert([f])
    p=predictor();original=p.predict;p.predict=lambda f:{**original(f),'features':{'home_matches':2,'away_matches':10}}
    assert capture(store,p)['withheld']==1
    assert capture(store,predictor())['recorded']==0
    later={**f,'date':(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()}
    store.upsert([later]);assert capture(store,predictor())['recorded']==1
    store.upsert([{**later,'status':'cancelled'}]);assert settle(store)==1
    assert performance(store,'football',24)['void']==1
    assert performance(store,'football',24)['settled']==0


def test_no_backfill_or_imprecise_kickoffs(tmp_path):
    store=Store(tmp_path/'test.db');f=fixture()
    store.upsert([{**f,'date_precision':'day'}]);assert capture(store,predictor())['withheld']==1
    store.upsert([{**f,'id':'old','date':(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()}])
    assert capture(store,predictor())['recorded']==0


def provider_fixture():
    return {'fixture':{'id':20,'date':'2025-01-01T15:00:00+00:00','status':{'short':'FT'}},
            'teams':{'home':{'id':1},'away':{'id':2}},'league':{'id':39,'season':2024}}


def blocks():
    return [{'team':{'id':1,'name':'A'},'players':[{'player':{'id':7,'name':'Player'},
        'statistics':[{'games':{'minutes':75,'substitute':False},'goals':{'total':1},'shots':{'total':3,'on':2}}]}]}]


def test_player_missing_values_identity_and_idempotent_import(tmp_path,monkeypatch):
    store=Store(tmp_path/'test.db');b=blocks();f=provider_fixture()
    r=normalize(f,b)[0];assert r['assists'] is None and r['yellow_cards'] is None
    monkeypatch.setattr('sportslab.players.fetch',lambda endpoint,params:[f] if endpoint=='fixtures' else b)
    assert import_fixture(store,20)['appearances']==1
    import_fixture(store,20);assert status(store)['appearances']==1
    assert status(store)['probabilities_available'] is False
    b[0]['team']['id']=99
    with pytest.raises(ValueError,match='team'):import_fixture(store,20)
    assert status(store)['appearances']==1
    f['fixture']['status']['short']='AET'
    with pytest.raises(ValueError,match='regulation'):normalize(f,blocks())


def test_provider_errors_are_sanitized(monkeypatch):
    import requests
    monkeypatch.setattr('sportslab.players.configured',lambda:True)
    monkeypatch.setenv('API_FOOTBALL_KEY','private-test-key')
    def fail(*args,**kwargs):raise requests.Timeout('private-test-key')
    monkeypatch.setattr('sportslab.players.requests.get',fail)
    with pytest.raises(ValueError) as exc:fetch('fixtures',{'id':1})
    assert 'private-test-key' not in str(exc.value)


def test_public_status_endpoints(tmp_path):
    client=create_app(Store(tmp_path/'test.db')).test_client()
    assert client.get('/api/performance?horizon=4').status_code==422
    assert client.get('/api/performance?sport=bad').status_code==422
    assert client.get('/api/performance').get_json()['scheduler_stale'] is True
    assert client.get('/api/players/status').get_json()['probabilities_available'] is False
    assert b'prospective-results' in client.get('/').data
