from copy import deepcopy
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
import pytest

from sportslab.features import build_history, state_before, FEATURES
from sportslab.model import score_matrix, matrix_markets, probabilities, settle_markets, labels
from sportslab.store import Store
from sportslab.ingest import football_rows, Importer
from sportslab.catalog import canonical, team_id
from sportslab.web import create_app


def match(i=1,day='2024-01-01',home='Arsenal',away='Chelsea',hg=2,ag=1,**kw):
    return dict(id=f'm{i}',sport='football',competition='E0',date=day+'T15:00:00+00:00',
                date_precision='kickoff',home=home,away=away,home_id=team_id('football',home),
                away_id=team_id('football',away),hg=hg,ag=ag,status='finished',source='test',neutral=False,
                surface='',hhg=None,hag=None,home_xg=None,away_xg=None,xg_source=None,**kw)


def test_current_and_future_scores_cannot_change_prematch_features():
    records=[match(1),match(2,'2024-01-05'),match(3,'2024-01-08')]
    before,_,_=build_history(records,'football')
    changed=deepcopy(records);changed[1]['hg']=9;changed[2]['ag']=7
    after,_,_=build_history(changed,'football')
    pd.testing.assert_frame_equal(before.iloc[:2],after.iloc[:2])
    assert before.iloc[2]['home_scored']!=after.iloc[2]['home_scored']


def test_same_day_is_batched_and_inference_matches_training():
    records=[match(1),match(2,'2024-01-05'),match(3,'2024-01-05',away='Liverpool'),match(4,'2024-01-08')]
    frame,ordered,_=build_history(records,'football')
    for i,m in enumerate(ordered):
        f=state_before(records,'football',m['date']).features(m)
        pd.testing.assert_series_equal(frame.iloc[i],pd.Series(f),check_names=False,check_dtype=False)
    assert frame.iloc[1].home_matches==frame.iloc[2].home_matches==1


def test_rest_crosses_venues_and_h2h_uses_both_participants():
    rows=[match(1),match(2,'2024-01-05',home='Liverpool',away='Arsenal')]
    s=state_before(rows,'football','2024-01-08')
    f=s.features(match(3,'2024-01-08'))
    assert f['home_rest']==3
    assert f['h2h_matches']==1
    assert s.features(match(4,'2024-01-08',away='Everton'))['h2h_matches']==0


def test_labels_only_use_actual_results():
    rows=[match(hg=0,ag=0),match(2,hg=0,ag=1),match(3,hg=3,ag=0)]
    assert labels(rows,'football').tolist()==[1,2,0]
    rows[0]['BayesianExpectedTotal']=4
    assert labels(rows,'football')[0]==1


@pytest.mark.parametrize('target',[[.55,.25,.2],[.15,.55,.3],[.9,.05,.05]])
def test_coherent_goal_probability_distribution(target):
    grid=score_matrix(1.8,1.2,target);p=matrix_markets(grid)
    assert grid.sum()==pytest.approx(1)
    assert [p[k] for k in ['home_win','draw','away_win']]==pytest.approx(target)
    assert 0<=p['over_3_5']<=p['over_2_5']<=p['over_1_5']<=1
    assert p['btts']<=p['over_1_5']
    assert p['home_clean_sheet']+p['btts']<=1+1e-10


def test_class_mapping_uses_classes_not_maximum_confidence():
    class Model:
        classes_=np.array([2,0,1])
        def predict_proba(self,X):return np.array([[.1,.7,.2]])
    assert probabilities(Model(),[1],3)[0]==pytest.approx([.7,.2,.1])


def test_missing_halftime_remains_missing_and_invalid_results_are_rejected():
    df=pd.DataFrame([dict(Date='01/02/2024',HomeTeam='Arsenal FC',AwayTeam='Chelsea FC',FTHG=2,FTAG=1,FTR='H'),
                     dict(Date='01/02/2024',HomeTeam='Arsenal',AwayTeam='Chelsea',FTHG=-1,FTAG=1,FTR='A')])
    rows=football_rows(df,'E0','test');assert len(rows)==1
    assert rows[0]['hhg'] is None and rows[0]['date'].startswith('2024-02-01')
    assert rows[0]['home']=='Arsenal'
    assert canonical('Athletic Club')=='Ath Bilbao'
    assert team_id('football','Arsenal FC')==team_id('football','Arsenal')


def test_upsert_preserves_enrichment_and_kickoff_but_corrects_score(tmp_path):
    store=Store(tmp_path/'test.db');m=match();m.update(home_xg=1.8,away_xg=.7,xg_source='observed')
    assert store.upsert([m])==1
    assert store.upsert([m])==0
    update=match(hg=3);update.update(date='2024-01-01T00:00:00+00:00',date_precision='day')
    store.upsert([update]);saved=store.fixture('m1')
    assert saved['hg']==3 and saved['home_xg']==1.8
    assert saved['date']==m['date']
    update.update(status='scheduled',hg=None,ag=None);store.upsert([update])
    assert store.fixture('m1')['status']=='finished'


def test_tennis_identity_independent_of_player_order(tmp_path):
    importer=Importer(Store(tmp_path/'test.db'))
    a=dict(Date='2024-01-01',Player1='A',Player2='B',Winner='Player1',Tour='ATP',Surface='Hard')
    b={**a,'Player1':'B','Player2':'A','Winner':'Player2'}
    x=importer.other_rows(pd.DataFrame([a]),'tennis')[0];y=importer.other_rows(pd.DataFrame([b]),'tennis')[0]
    assert x==y


def prediction(f):
    return dict(fixture=f,probabilities=matrix_markets(score_matrix(1.7,.8)),model_version='test-v1',data_version='data-v1')


def future():
    m=match(day=(datetime.now(timezone.utc)+timedelta(days=3)).date().isoformat())
    m.update(status='timed',hg=None,ag=None);return m


def test_journal_is_frozen_owned_and_settles_exact_fixture(tmp_path):
    store=Store(tmp_path/'test.db');f=future();store.upsert([f]);p=prediction(f)
    pid=store.save_prediction('alice',f,p)
    changed=deepcopy(p);changed['probabilities']['home_win']=.01
    assert store.save_prediction('alice',f,changed)==pid
    assert store.journal('alice')[0]['payload']['probabilities']==p['probabilities']
    assert store.journal('bob')==[]
    wrong={**f,'id':'other','away':'Liverpool','away_id':'football:liverpool','status':'finished','hg':2,'ag':0}
    store.upsert([wrong]);assert store.settle()==0
    result={**f,'status':'finished','hg':2,'ag':0};store.upsert([result]);assert store.settle('bob')==0
    assert store.settle('alice')==1;assert store.settle()==0
    store.upsert([{**result,'hg':0,'ag':2}]);assert store.settle()==1
    with store.connect() as c:assert c.execute('SELECT COUNT(*) FROM settlement_events').fetchone()[0]==2


def test_journal_rejects_past_matches(tmp_path):
    with pytest.raises(ValueError):Store(tmp_path/'test.db').save_prediction('alice',match(),prediction(match()))


def test_api_csrf_ownership_validation_and_retired_routes(tmp_path):
    store=Store(tmp_path/'test.db');store.upsert([match(),future()]);app=create_app(store);app.testing=True
    client=app.test_client();response=client.get('/');assert response.status_code==200
    assert b'Matchday' in response.data
    assert "script-src 'self'" in response.headers['Content-Security-Policy']
    assert client.post('/api/analyse',json={}).status_code==403
    with client.session_transaction() as session:csrf=session['csrf']
    headers={'X-CSRF-Token':csrf}
    for body in [[],{},dict(home_id='unknown',away_id='other'),dict(fixture_id='missing')]:
        assert client.post('/api/analyse',json=body,headers=headers).status_code==422
    assert client.post('/api/analyse',json={'fixture_id':'m1'},headers=headers).status_code==422
    assert client.get('/api/journal').json=={'predictions':[]}
    assert client.get('/static/app.js').status_code==200
    assert client.get('/api/nfl/predict').status_code==404
    assert client.post('/api/journal',json={'sport':'football','home_id':'football:arsenal','away_id':'football:chelsea'},headers=headers).status_code==422

def test_postponement_preserves_provider_identity_and_csv_settlement(tmp_path):
    store=Store(tmp_path/'test.db');f=future();f['provider_fixture_id']=1234
    store.upsert([f]);pid=store.save_prediction('alice',f,prediction(f))
    moved={**f,'id':'new-date-hash','date':(datetime.now(timezone.utc)+timedelta(days=10)).isoformat()}
    store.upsert([moved]);assert len(store.matches())==1
    result={**moved,'id':'csv-date-hash','status':'finished','hg':1,'ag':0,'source':'csv'}
    result.pop('provider_fixture_id');store.upsert([result])
    assert len(store.matches())==1 and store.fixture(f['id'])['hg']==1
    assert store.settle()==1
    assert store.journal('alice')[0]['id']==pid


def test_null_or_malformed_participant_ids_are_validation_errors(tmp_path):
    store=Store(tmp_path/'test.db');store.upsert([match()]);app=create_app(store);app.testing=True
    c=app.test_client();c.get('/')
    with c.session_transaction() as session:token=session['csrf']
    for home in [[],{},123,True]:
        r=c.post('/api/analyse',json={'home_id':home,'away_id':'football:chelsea'},headers={'X-CSRF-Token':token})
        assert r.status_code==422

def test_cancelled_forecast_is_void_not_an_incorrect_outcome(tmp_path):
    s=Store(tmp_path/'test.db');f=future();s.upsert([f]);s.save_prediction('alice',f,prediction(f))
    s.upsert([{**f,'status':'cancelled'}]);assert s.settle()==1
    result=s.journal('alice')[0]['settlement']
    assert result['status']=='void' and 'outcome_correct' not in result


def test_unicode_provider_aliases_do_not_split_club_history():
    assert canonical('FC Bayern München')=='Bayern Munich'
    assert canonical('Málaga CF')=='Malaga'
    assert canonical('Vitória SC')=='Guimaraes'
