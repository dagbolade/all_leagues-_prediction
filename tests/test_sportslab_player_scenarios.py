import json
import pytest
from sportslab.store import Store
from sportslab.public_players import initialize
from sportslab.player_scenarios import analyse
from datetime import datetime,timezone


def test_scenario_rates_and_minutes_validation(tmp_path):
    s=Store(tmp_path/'players.db');initialize(s)
    today=datetime.now(timezone.utc).date().isoformat()
    with s.connect() as c:
        for i in range(5):
            r={'player':'Test','date':today,'minutes':90,'xg':0.5,'xa':0.2}
            c.execute('INSERT INTO public_player_matches VALUES (?,?,?,?)',('p',str(i),today,json.dumps(r)))
    d=analyse(s,'p',90)
    assert d['validated'] is False
    assert d['scorer']==pytest.approx(0.39346934)
    assert d['score_or_assist']>d['scorer']
    assert analyse(s,'p',45)['scorer']<d['scorer']
    for minutes in [0,91,'nan','inf']:
        with pytest.raises(ValueError):analyse(s,'p',minutes)
    with s.connect() as c:c.execute('DELETE FROM public_player_matches WHERE match_id=?',('0',))
    assert 'unavailable' in analyse(s,'p')
