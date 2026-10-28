from copy import deepcopy

import pytest

from sportslab.rosters import normalize, HEADERS
from sportslab.public_players import summary
from sportslab.store import Store, utcnow
from sportslab.web import create_app


def document():
    def side(code,start):
        return {'source':'https://understat.com/match/123','title':'Home 0 - 0 Away (October 01 2025) | EPL',
            'breadcrumb':['Home','EPL','Oct 01 2025'],'team':code,'teams':['Home','Away'],
            'headers':HEADERS,'cards':[{'player_url':'https://understat.com/player/1','titles':['Yellow card']}],
            'rows':[{'player_url':f'https://understat.com/player/{n}',
                     'cells':[str(n),f'Player {n}','GK' if n==start else 'DC','90','0','0','0','0','0.00','0.00']}
                    for n in range(start,start+11)]}
    return {'observed_at':utcnow(),'league':'EPL','home':side('h',1),'away':side('a',12)}


def test_both_teams_and_reported_cards():
    mid,rows=normalize(document())
    assert mid=='understat:123' and len(rows)==22
    assert rows[0]['team']=='Home' and rows[-1]['team']=='Away'
    assert rows[0]['yellow_cards']==1 and rows[-1]['yellow_cards']==0
    assert all(r['shots_on_target'] is None for r in rows)


@pytest.mark.parametrize('issue',['duplicate','wrong_side','missing_starter','changed_cards','header'])
def test_incomplete_rosters_fail_closed(issue):
    d=document()
    if issue=='duplicate':d['home']['rows'].append(deepcopy(d['home']['rows'][0]))
    if issue=='wrong_side':d['away']['team']='h'
    if issue=='missing_starter':d['home']['rows'][0]['cells'][2]='Sub'
    if issue=='changed_cards':d['away']['cards']=[]
    if issue=='header':d['home']['headers']=['Other']
    with pytest.raises(ValueError):normalize(d)


def test_unknown_card_definition_is_not_zero():
    d=document()
    for side in ['home','away']:d[side]['cards'][0]['titles']=['Other card']
    _,rows=normalize(d)
    assert all(r['yellow_cards'] is None and r['red_cards'] is None for r in rows)


def test_public_player_pagination_validation(tmp_path):
    store=Store(tmp_path/'test.db');client=create_app(store).test_client()
    for query in ['offset=-1','limit=100','league=CL','offset=bad']:
        assert client.get('/api/players/public?'+query).status_code==422
    d=summary(store)
    assert d['total_players']==0 and not d['has_more'] and d['coverage']==[]
