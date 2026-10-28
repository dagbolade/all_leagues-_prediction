import json
from copy import deepcopy

import pytest

from sportslab.public_players import HEADERS, normalize, import_pages, summary
from sportslab.store import Store, utcnow


def document():
    return {'observed_at':utcnow(),'pages':[{'source':'https://understat.com/player/1','player':'Example',
        'headers':HEADERS,'page':'1','next':False,'rows':[{'match_url':'https://understat.com/match/2',
        'cells':['1','2025-01-01','Home','1-0','Away','FW','80','3','1','2','0','0.62-0.38','0.20+0.20']}]}]}


def test_display_differences_and_missing_markets():
    pid,rows=normalize(document());r=rows[0]
    assert pid=='understat:1' and r['xg']==.62 and r['xa']==.2
    assert r['shots']==3 and r['shots_on_target'] is None and r['yellow_cards'] is None
    assert r['team'] is None


@pytest.mark.parametrize('change',['incomplete','duplicate','header','future','bad_count'])
def test_bad_snapshots_rejected(change):
    d=document();p=d['pages'][0]
    if change=='incomplete':p['next']=True
    if change=='duplicate':p['rows']*=2
    if change=='header':p['headers']=['Unexpected']
    if change=='future':p['rows'][0]['cells'][1]='2099-01-01'
    if change=='bad_count':p['rows'][0]['cells'][6]='-10'
    with pytest.raises(ValueError):normalize(d)


def test_atomic_import_and_correction(tmp_path):
    store=Store(tmp_path/'test.db');path=tmp_path/'page.json';d=document()
    path.write_text(json.dumps(d),encoding='utf8');import_pages(store,path);import_pages(store,path)
    assert summary(store)['appearances']==1
    broken=deepcopy(d);broken['pages'][0]['rows'][0]['cells'][6]='bad'
    path.write_text(json.dumps(broken),encoding='utf8')
    with pytest.raises(ValueError):import_pages(store,path)
    assert summary(store)['appearances']==1
    d['observed_at']=utcnow();d['pages'][0]['rows'][0]['cells'][8]='0'
    path.write_text(json.dumps(d),encoding='utf8');import_pages(store,path)
    assert summary(store)['players'][0]['recent'][0]['goals']==0
