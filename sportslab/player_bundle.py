"""Public-only player seed; repeat deployments preserve newer observations."""
import gzip
import json
from pathlib import Path

from .rosters import initialize
from .tracking import instant

TABLES = {
    'public_player_pages': ('player_id',),
    'public_roster_snapshots': ('match_id',),
    'public_roster_inventory': ('league',),
    'public_player_matches': ('player_id', 'match_id'),
}


def export_bundle(store, path):
    initialize(store)
    with store.connect() as c:
        data = {table: [dict(r) for r in c.execute(
            f'SELECT * FROM {table} ORDER BY {",".join(keys)}')]
            for table, keys in TABLES.items()}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as f:
        f.write(json.dumps({'version': 1, 'tables': data}, ensure_ascii=False, allow_nan=False).encode('utf8'))
    return {table: len(rows) for table, rows in data.items()}


def import_bundle(store, path):
    with gzip.open(path, 'rt', encoding='utf8') as f:
        document = json.load(f)
    if document['version'] != 1 or set(document['tables']) != set(TABLES):
        raise ValueError('Unsupported player bundle')
    initialize(store)
    changed = 0
    with store.connect() as c:
        roster_stamps = {r['match_id']: r['observed_at'] for r in c.execute('SELECT match_id,observed_at FROM public_roster_snapshots')}
        # The transaction includes source snapshots, inventories and normalized rows.
        for table, keys in TABLES.items():
            columns = [r[1] for r in c.execute(f'PRAGMA table_info({table})')]
            for row in document['tables'][table]:
                if set(row) != set(columns):
                    raise ValueError('Invalid player bundle columns')
                payload = json.loads(row['payload'])
                stamp = row.get('observed_at') or payload['observed_at']
                if table == 'public_player_matches' and row['match_id'] in roster_stamps:
                    if instant(roster_stamps[row['match_id']]) > instant(stamp):
                        continue
                old = c.execute(f'SELECT * FROM {table} WHERE ' + ' AND '.join(k+'=?' for k in keys),
                                [row[k] for k in keys]).fetchone()
                if old:
                    old_payload = json.loads(old['payload'])
                    old_stamp = old['observed_at'] if 'observed_at' in old.keys() else old_payload['observed_at']
                    if instant(old_stamp) >= instant(stamp):
                        continue
                    if table == 'public_player_matches' and old_payload.get('league') and not payload.get('league'):
                        continue
                c.execute(f'INSERT OR REPLACE INTO {table} ({",".join(columns)}) VALUES ({",".join("?" for _ in columns)})',
                          [row[k] for k in columns])
                changed += 1
    return changed
