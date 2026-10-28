import pytest
from sportslab.player_markets import estimate,event,MARKETS


def sample(team,other,goals):
    return {'team':team,'home':team,'away':other,'goals':goals,'assists':0,'shots':goals,'yellow_cards':None}


def test_opponent_changes_predictions_and_missing_cards_are_not_zero():
    own=[sample('A','B',i%2) for i in range(8)]
    league=[sample('A','Weak',1) for _ in range(80)]+[sample('A','Strong',0) for _ in range(80)]
    weak=estimate(own,league,'Weak','scorer');strong=estimate(own,league,'Strong','scorer')
    assert 0<strong['probability']<weak['probability']<1
    assert estimate(own,league,'Weak','yellow') is None
    assert estimate(own[:3],league,'Weak','scorer') is None
    assert event({'goals':1,'assists':1},'score_assist')==1


def test_board_rejects_finished_and_unknown(tmp_path):
    from sportslab.store import Store
    from sportslab.player_markets import board
    s=Store(tmp_path/'markets.db')
    with pytest.raises(ValueError):board(s,'missing')

def test_board_excludes_same_day_and_future_observations(monkeypatch):
    from sportslab import player_markets as model
    from datetime import datetime,timezone,timedelta
    now=datetime.now(timezone.utc);day=(now+timedelta(days=1)).date().isoformat()
    fixture={'id':'f','sport':'football','status':'scheduled','date':day+'T18:00:00+00:00','home':'A','away':'B'}
    class FakeStore:
        def fixture(self,_):return fixture
    common={'player_id':'p','player':'P','team':'A','league':'EPL','minutes':90,'home':'A','away':'B','goals':1,'assists':0,'shots':2,'yellow_cards':0}
    rows=[{**common,'date':day,'observed_at':now.isoformat()} for _ in range(6)]
    rows += [{**common,'date':(now-timedelta(days=1)).date().isoformat(),'observed_at':(now+timedelta(days=2)).isoformat()} for _ in range(6)]
    monkeypatch.setattr(model,'records',lambda _:rows)
    assert model.board(FakeStore(),'f')['predictions']==[]
