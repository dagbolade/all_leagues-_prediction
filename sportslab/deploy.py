"""Initialize a hosted instance from public deployment assets before WSGI starts."""
import gzip
import json
import os
import shutil
from pathlib import Path
from .store import Store, ROOT
from .model import ARTIFACTS


def prepare():
    bundle=ROOT/'deployment'
    store=Store()
    metadata=bundle/'snapshot.json'
    snapshot=json.loads(metadata.read_text(encoding='utf-8')) if metadata.exists() else None
    with store.connect() as c:
        existing={r['id']:r['updated_at'] for r in c.execute('SELECT id,updated_at FROM matches')}
    records=[];stamps={}
    with gzip.open(bundle/'matches.jsonl.gz','rt',encoding='utf-8') as f:
        for line in f:
            entry=json.loads(line)
            record=entry.get('match',entry)
            stamp=entry.get('updated_at') or (snapshot['created_at'] if snapshot else None)
            if record['id'] not in existing or (stamp and stamp>existing[record['id']]):
                records.append(record)
                if stamp:stamps[record['id']]=stamp
    changed=store.upsert(records,observed_at=stamps)
    store.log_import('deployment:public-seed','ok',len(records),f'{changed} new/corrected records; newer live data and private journals retained')
    for sport in ['football','basketball','tennis']:
        source=bundle/'models'/sport
        version=json.loads((source/'active.json').read_text())['version']
        target=ARTIFACTS/sport/version
        target.mkdir(parents=True,exist_ok=True)
        for name in ['models.joblib','manifest.json']:
            shutil.copyfile(source/version/name,target/name)
        pointer=target.parent/'active.json'
        temp=pointer.with_suffix('.deploy.tmp')
        temp.write_text(json.dumps({'version':version}),encoding='utf-8')
        temp.replace(pointer)
    print('Matchday deployment assets ready',flush=True)


if __name__=='__main__':prepare()
