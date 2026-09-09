import argparse
import json
from .store import Store

def main():
    parser=argparse.ArgumentParser(description='Matchday data, training and verification')
    parser.add_argument('command',choices=['bootstrap','refresh','train','pipeline','settle','status','serve'])
    parser.add_argument('--sport',choices=['football','basketball','tennis','all'],default='all')
    parser.add_argument('--iterations',type=int,default=220)
    parser.add_argument('--skip-xg',action='store_true')
    parser.add_argument('--port',type=int,default=5000)
    args=parser.parse_args();store=Store()
    from contextlib import nullcontext
    from .locking import pipeline_lock
    with pipeline_lock() if args.command in ['bootstrap','refresh','train','pipeline','settle'] else nullcontext():
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
