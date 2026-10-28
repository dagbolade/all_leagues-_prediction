"""Package only public matches and validated active models for deployment."""
import gzip
import hashlib
import json
import shutil
from pathlib import Path
from .store import Store, ROOT, utcnow
from .model import ARTIFACTS


def package(destination=None):
    target=Path(destination or ROOT/'deployment');target.mkdir(parents=True,exist_ok=True)
    store=Store();count=0
    from .player_bundle import export_bundle
    player_counts=export_bundle(store,target/'players.json.gz')
    with store.connect() as c, (target/'matches.jsonl.gz').open('wb') as raw:
        with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as zipped:
            for row in c.execute('SELECT payload,updated_at FROM matches ORDER BY id'):
                entry={'match':json.loads(row['payload']),'updated_at':row['updated_at']}
                zipped.write((json.dumps(entry,ensure_ascii=False)+'\n').encode('utf-8'));count+=1
    versions={}
    for sport in ['football','basketball','tennis']:
        source=ARTIFACTS/sport;version=json.loads((source/'active.json').read_text())['version']
        directory=target/'models'/sport/version;directory.mkdir(parents=True,exist_ok=True)
        for name in ['models.joblib','manifest.json']:shutil.copyfile(source/version/name,directory/name)
        shutil.copyfile(source/'active.json',directory.parent/'active.json');versions[sport]=version
    metadata={'created_at':utcnow(),'records':count,'models':versions,'sha256':hashlib.sha256((target/'matches.jsonl.gz').read_bytes()).hexdigest()}
    metadata['public_players']=player_counts
    metadata['players_sha256']=hashlib.sha256((target/'players.json.gz').read_bytes()).hexdigest()
    (target/'snapshot.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))
    return metadata

if __name__=='__main__':package()
