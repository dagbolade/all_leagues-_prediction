import json
from pathlib import Path
from sportslab.store import Store
from sportslab.player_bundle import import_bundle
from sportslab.web import create_app


def test_public_seed_clean_restart_and_newer_preservation(tmp_path):
    store=Store(tmp_path/'clean.sqlite3')
    seed=Path(__file__).resolve().parents[1]/'deployment/players.json.gz'
    assert import_bundle(store,seed)>0
    client=create_app(store).test_client()
    data=client.get('/api/players/public').get_json()
    assert data['total_players']==2623
    assert data['appearances']==17678
    assert sum(c['covered_matches'] for c in data['coverage'])==504
    assert sum(c['expected_matches'] for c in data['coverage'])==505
    page=client.get('/api/players/public?offset=24').get_json()
    assert not {p['id'] for p in data['players']} & {p['id'] for p in page['players']}
    assert client.get('/api/players/public?q=Palmer&league=EPL').get_json()['players'][0]['name']=='Cole Palmer'
    assert import_bundle(store,seed)==0
    with store.connect() as c:
        row=c.execute('SELECT * FROM public_player_matches LIMIT 1').fetchone()
        payload=json.loads(row['payload']);payload['observed_at']='2099-01-01T00:00:00+00:00';payload['minutes']=1
        c.execute('UPDATE public_player_matches SET payload=? WHERE player_id=? AND match_id=?',(json.dumps(payload),row['player_id'],row['match_id']))
        # A corrected newer roster may legitimately remove a previous appearance.
        mid=c.execute('SELECT match_id FROM public_roster_snapshots LIMIT 1').fetchone()[0]
        c.execute('UPDATE public_roster_snapshots SET observed_at=? WHERE match_id=?',('2099-01-01T00:00:00+00:00',mid))
        c.execute('DELETE FROM public_player_matches WHERE match_id=?',(mid,))
    import_bundle(store,seed)
    with store.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM public_player_matches WHERE match_id=?',(mid,)).fetchone()[0]==0
        saved=c.execute('SELECT payload FROM public_player_matches WHERE player_id=? AND match_id=?',(row['player_id'],row['match_id'])).fetchone()
        if saved:assert json.loads(saved[0])['minutes']==1
