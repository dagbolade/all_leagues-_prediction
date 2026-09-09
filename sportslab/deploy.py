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
    with store.connect() as c:
        populated=c.execute('SELECT 1 FROM matches LIMIT 1').fetchone()
    if not populated:
        with gzip.open(bundle/'matches.jsonl.gz','rt',encoding='utf-8') as f:
            records=[json.loads(line) for line in f]
        store.upsert(records)
        store.log_import('deployment:public-seed','ok',len(records),'Public match seed; no user journals or credentials included')
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
