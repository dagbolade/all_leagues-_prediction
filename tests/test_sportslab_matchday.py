"""Matchboard forecasts and live-feed boundary regression tests."""
import json
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace

from sportslab.store import Store
from sportslab.web import create_app
from sportslab.matchday import initialize, forecast, LiveFeed, normalize_match


def fixture(mid='future',days=2):
    return dict(id=mid,sport='football',competition='E0',date=(datetime.now(timezone.utc)+timedelta(days=days)).isoformat(),
                home='Arsenal',away='Chelsea',home_id='football:arsenal',away_id='football:chelsea',status='timed',
                source='test',hg=None,ag=None,date_precision='kickoff',surface='',neutral=False)


class Predictor:
    def __init__(self):self.calls=0;self.version='one'
    def load(self,sport):return {'version':self.version},{}
    def predict(self,f):
        self.calls+=1
        return dict(probabilities={'home_win':.5,'draw':.3,'away_win':.2},scorelines=[{'score':'1–0','probability':.1}],
                    expected={'home':1.5,'away':1},warnings=[],model_version=self.version,data_version='test',
                    created_at=datetime.now(timezone.utc).isoformat(),history_through='2026-01-01')


def test_forecast_cache_and_no_postkickoff_generation(tmp_path):
    import pytest
    store=Store(tmp_path/'test.sqlite');initialize(store);p=Predictor();f=fixture()
    assert forecast(store,p,f)==forecast(store,p,f);assert p.calls==1
    p.version='two';assert forecast(store,p,f)['model_version']=='two';assert p.calls==2
    old=deepcopy(f);old['date']=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
    with pytest.raises(ValueError,match='kickoff'):forecast(store,p,old)
    old=deepcopy(f);old['status']='cancelled'
    with pytest.raises(ValueError):forecast(store,p,old)
    assert p.calls==2


def test_prediction_batch_validation_and_partial_unavailable(tmp_path,monkeypatch):
    store=Store(tmp_path/'test.sqlite');f=fixture();store.upsert([f]);p=Predictor()
    monkeypatch.setattr('sportslab.web.Predictor',lambda store:p)
    client=create_app(store).test_client();client.get('/')
    with client.session_transaction() as session:csrf=session['csrf']
    headers={'X-CSRF-Token':csrf}
    data=client.post('/api/predictions',json={'fixture_ids':[f['id'],'missing']},headers=headers).get_json()['predictions']
    assert data[f['id']]['forecast']['probabilities']['home_win']==.5
    assert data['missing']['unavailable']=='Fixture not found'
    for ids in [[],['x']*25,[{}],'not-list']:
        assert client.post('/api/predictions',json={'fixture_ids':ids},headers=headers).status_code==422
    assert client.post('/api/predictions',json={'fixture_ids':['x']}).status_code==403
    assert client.get('/api/live?sport=tennis').get_json()['available'] is False


def provider_match():
    return {'id':123,'competition':{'code':'PL'},'homeTeam':{'name':'Arsenal'},'awayTeam':{'name':'Chelsea'},
            'utcDate':'2026-10-24T14:00:00Z','status':'IN_PLAY','score':{'duration':'REGULAR','fullTime':{'home':1,'away':0}},
            'lastUpdated':'2026-10-24T14:20:00Z'}


def test_missing_clock_and_score_are_never_invented():
    m=provider_match();d=normalize_match(m)
    assert d['hg']==1 and d['ag']==0 and d['minute'] is None
    m['score']['fullTime']={'home':None,'away':None};m['minute']=True
    d=normalize_match(m);assert d['hg'] is None and d['ag'] is None and d['minute'] is None
    m['score']['duration']='EXTRA_TIME';assert normalize_match(m)['duration']=='EXTRA_TIME'
    m['competition']['code']='UNKNOWN';assert normalize_match(m) is None


def test_live_cache_is_shared_and_provider_failure_keeps_last_fetch(tmp_path,monkeypatch):
    store=Store(tmp_path/'test.sqlite');initialize(store);monkeypatch.setenv('FOOTBALL_DATA_API_KEY','test-only')
    feed=LiveFeed(store);calls=[]
    def get(*a,**kw):
        calls.append(1)
        today=datetime.now(timezone.utc).date();tomorrow=today+timedelta(days=1)
        assert kw['params']=={'dateFrom':today.isoformat(),'dateTo':tomorrow.isoformat()}
        m=provider_match();m['utcDate']=today.isoformat()+'T14:00:00Z'
        other=deepcopy(m);other['id']=999;other['utcDate']=tomorrow.isoformat()+'T14:00:00Z'
        return SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'matches':[m,other]})
    monkeypatch.setattr('sportslab.matchday.requests.get',get)
    first=feed.get();second=LiveFeed(store).get()
    assert len(calls)==1 and first['matches']==second['matches'] and first['available']
    assert len(first['matches'])==1
    with store.connect() as c:c.execute('UPDATE live_feed_cache SET next_check=0')
    import requests
    def failure(*a,**kw):raise requests.Timeout('secret must never be returned')
    monkeypatch.setattr('sportslab.matchday.requests.get',failure)
    failed=feed.get()
    assert failed['matches']==first['matches'] and failed['fetched_at']==first['fetched_at']
    assert failed['error'] and 'secret' not in failed['error']
    assert store.matches('football')==[]  # Scoreboard does not contaminate training/settlement.


def test_live_reference_requires_exact_identity_and_pre_kickoff_timestamp(tmp_path):
    store=Store(tmp_path/'test.sqlite');initialize(store);feed=LiveFeed(store)
    m=normalize_match(provider_match());f={k:m[k] for k in ['competition','home_id','away_id','date']}
    with store.connect() as c:
        c.execute('INSERT INTO board_forecasts VALUES (?,?,?)',('test','fingerprint',json.dumps({'fixture':f,'created_at':'2026-10-24T13:59:00+00:00','probabilities':{'home_win':.5}})))
    assert feed.baselines([deepcopy(m)])[0]['prematch'] is not None
    changed=deepcopy(m);changed['date']='2026-10-24T15:00:00+00:00'
    assert feed.baselines([changed])[0]['prematch'] is None
    with store.connect() as c:c.execute('UPDATE board_forecasts SET payload=?',(json.dumps({'fixture':f,'created_at':'2026-10-24T14:01:00+00:00'}),))
    assert feed.baselines([deepcopy(m)])[0]['prematch'] is None
