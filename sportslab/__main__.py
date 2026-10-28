import argparse
import json
from .store import Store

def main():
    parser=argparse.ArgumentParser(description='Matchday data, training and verification')
    parser.add_argument('command',choices=['bootstrap','refresh','train','pipeline','settle','status','serve','track','player-import','player-pages','player-rosters'])
    parser.add_argument('--input',help='Rendered public player history JSON file or directory')
    parser.add_argument('--provider-fixture',type=int,help='API-Football fixture ID, not football-data.org ID')
    parser.add_argument('--sport',choices=['football','basketball','tennis','all'],default='all')
    parser.add_argument('--iterations',type=int,default=220)
    parser.add_argument('--skip-xg',action='store_true')
    parser.add_argument('--port',type=int,default=5000)
    args=parser.parse_args();store=Store()
    if args.command=='player-rosters':
        from .rosters import import_directory
        if not args.input:parser.error('Supply --input directory')
        report=import_directory(store,args.input)
        print(json.dumps(report,ensure_ascii=True))
        if report['errors']:raise SystemExit(1)
    if args.command=='player-pages':
        from pathlib import Path
        from .public_players import import_pages
        if not args.input:parser.error('Supply --input file or directory')
        path=Path(args.input)
        files=sorted(path.glob('understat-*.json')) if path.is_dir() else [path]
        if not files:parser.error('No player page files found')
        for file in files:print(json.dumps(import_pages(store,file),ensure_ascii=True))
    from contextlib import nullcontext
    from .locking import pipeline_lock
    with pipeline_lock() if args.command in ['bootstrap','refresh','train','pipeline','settle','track','player-import'] else nullcontext():
        if args.command=='player-import':
            from .players import import_fixture
            if not args.provider_fixture or args.provider_fixture<1:parser.error('Supply --provider-fixture with an API-Football fixture ID')
            print(json.dumps(import_fixture(store,args.provider_fixture)))
        if args.command=='track':
            from .model import Predictor
            from .tracking import capture
            print(json.dumps(capture(store,Predictor(store))))
        if args.command in ['bootstrap','pipeline','refresh']:
            from .ingest import Importer
            importer=Importer(store);importer.bootstrap()
            if args.command!='bootstrap': importer.refresh(not args.skip_xg)
        if args.command in ['train','pipeline']:
            from .model import train
            for sport in ['football','basketball','tennis'] if args.sport=='all' else [args.sport]:
                train(store,sport,args.iterations)
        if args.command=='settle': print('Settled:',store.settle())
    if args.command=='status': print(json.dumps(store.coverage(),indent=2))
    if args.command=='serve':
        from waitress import serve
        from .web import create_app
        serve(create_app(store),host='127.0.0.1',port=args.port,threads=4)

if __name__=='__main__': main()
