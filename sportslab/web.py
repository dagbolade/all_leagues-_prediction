from __future__ import annotations

import json
import os
import secrets
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session

from .catalog import NAMES, team_id
from .store import Store, utcnow, ROOT
from .model import Predictor, ARTIFACTS
from .matchday import initialize, forecast, LiveFeed


def create_app(store=None):
    store=store or Store()
    app=Flask(__name__,template_folder='templates',static_folder='static')
    keyfile=store.path.parent/'session.key'
    if not keyfile.exists():
        try:
            with keyfile.open('x') as f:f.write(secrets.token_hex(32))
        except FileExistsError:pass
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY') or keyfile.read_text(),MAX_CONTENT_LENGTH=16384,
                      SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE')=='1')
    predictor=Predictor(store);prediction_lock=threading.Lock()
    initialize(store);live_feed=LiveFeed(store)
    with store.connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS rate_limits (owner TEXT, minute INTEGER, calls INTEGER, PRIMARY KEY(owner,minute))')

    @app.before_request
    def protect():
        if 'owner' not in session:session['owner']=secrets.token_hex(24)
        if 'csrf' not in session:session['csrf']=secrets.token_hex(24)
        if request.method in ['POST','PUT','DELETE','PATCH']:
            if not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),session['csrf']):
                return jsonify(error='Session token missing. Reload this page and try again.'),403
            minute=int(time.time()//60)
            with store.connect() as c:
                c.execute('DELETE FROM rate_limits WHERE minute<?',(minute-2,))
                c.execute('INSERT INTO rate_limits VALUES (?,?,1) ON CONFLICT(owner,minute) DO UPDATE SET calls=calls+1',(session['owner'],minute))
                count=c.execute('SELECT calls FROM rate_limits WHERE owner=? AND minute=?',(session['owner'],minute)).fetchone()[0]
            if count>20:return jsonify(error='Too many requests. Please wait a minute.'),429

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(ValueError)
    def value_error(error):return jsonify(error=str(error)),422

    @app.errorhandler(404)
    def missing(error):return jsonify(error='Not found'),404

    @app.errorhandler(500)
    def failure(error):return jsonify(error='The request could not be completed. Check the server logs.'),500

    @app.get('/')
    @app.get('/predict')
    @app.get('/accuracy')
    @app.get('/live-predictions')
    @app.get('/statistics')
    @app.get('/multi/')
    @app.get('/multi/<sport>')
    def index(sport=None):
        return render_template('index.html',csrf=session['csrf'])

    @app.get('/health')
    def health():
        return jsonify(status='ok',database=store.path.exists(),model_sports=[s for s in ['football','basketball','tennis'] if (ARTIFACTS/s/'active.json').exists()])

    @app.get('/ready')
    def ready():
        available=[s for s in ['football','basketball','tennis'] if (ARTIFACTS/s/'active.json').exists()]
        with store.connect() as c:n=c.execute('SELECT COUNT(*) FROM matches').fetchone()[0]
        ok=n>0 and len(available)==3
        return jsonify(ready=ok,models=available,matches=n),200 if ok else 503

    @app.get('/api/overview')
    def overview():
        coverage=store.coverage()
        totals={s:{'matches':sum(c['completed'] for c in coverage['competitions'] if c['sport']==s),
                   'competitions':sum(c['sport']==s for c in coverage['competitions'])} for s in ['football','basketball','tennis']}
        return jsonify(totals=totals,competitions=[{**c,'name':NAMES.get(c['competition'],c['competition'])} for c in coverage['competitions']],now=utcnow())

    def match_listing(results_only=False):
        sport=request.args.get('sport','football')
        if sport not in ['football','basketball','tennis']:raise ValueError('Unknown sport')
        records=store.matches(sport,request.args.get('competition') or None)
        mode='finished' if results_only else request.args.get('status','auto')
        if mode not in ['auto','upcoming','finished','all']:raise ValueError('Unknown match status')
        date=request.args.get('date')
        if date:
            datetime.strptime(date,'%Y-%m-%d')
            records=[m for m in records if m['date'][:10]==date]
        query=request.args.get('q','').strip().casefold()
        if query:
            records=[m for m in records if query in (m['home']+' '+m['away']).casefold()]
        upcoming=[m for m in records if m['status'] in ['scheduled','timed'] and m['date']>utcnow()]
        if mode=='auto':mode='all' if date else ('upcoming' if upcoming else 'finished')
        if mode=='upcoming':records=upcoming
        elif mode=='finished':records=[m for m in records if m['status']=='finished']
        records=sorted(records,key=lambda m:(m['date'],m['id']),reverse=mode=='finished')
        try:
            offset=int(request.args.get('offset',0));limit=int(request.args.get('limit',24))
        except (ValueError,TypeError):raise ValueError('Invalid page parameters')
        if offset<0 or not 1<=limit<=100:raise ValueError('Page size must be 1–100 and offset non-negative')
        total=len(records)
        return jsonify(**{'results' if results_only else 'fixtures':records[offset:offset+limit]},
                       total=total,offset=offset,limit=limit,has_more=offset+limit<total,mode=mode)

    @app.get('/api/fixtures')
    def fixtures():return match_listing()

    @app.post('/api/predictions')
    def board_predictions():
        body=request.get_json(silent=True)
        ids=body.get('fixture_ids') if isinstance(body,dict) else None
        if not isinstance(ids,list) or not 1<=len(ids)<=24 or any(not isinstance(i,str) or len(i)>150 for i in ids):
            raise ValueError('Provide 1–24 fixture IDs')
        predictions={};versions={}
        with prediction_lock:
            for fid in dict.fromkeys(ids):
                fixture=store.fixture(fid)
                try:
                    if not fixture:raise ValueError('Fixture not found')
                    sport=fixture['sport']
                    if sport not in versions:versions[sport]=store.version(sport)
                    predictions[fid]={'forecast':forecast(store,predictor,fixture,versions[sport])}
                except ValueError as e:predictions[fid]={'unavailable':str(e)}
        return jsonify(predictions=predictions)

    @app.get('/api/live')
    def live_matches():
        sport=request.args.get('sport','football')
        if sport not in ['football','basketball','tennis']:raise ValueError('Unknown sport')
        if sport!='football':return jsonify(matches=[],available=False,error='Live score coverage is currently connected for football only.',fetched_at=None)
        result=live_feed.get();result['matches']=live_feed.baselines(result['matches'])
        result['notice']='Provider-reported scores may be delayed. Refreshing this view does not remove provider delays. In-play probabilities are not available: no validated in-play model is connected.'
        result['source']='football-data.org';result['date']=datetime.now(timezone.utc).date().isoformat()
        return jsonify(result)

    @app.get('/api/teams')
    def teams():
        sport=request.args.get('sport','football');comp=request.args.get('competition')
        records=store.matches(sport,comp);found={}
        for m in records:
            for side in ['home','away']:
                participant=found.setdefault(m[side+'_id'],{'id':m[side+'_id'],'name':m[side],'last_seen':None,'completed':0,'latest_result':None})
                participant['last_seen']=max(participant['last_seen'] or '',m['date'][:10])
                if m['status']=='finished':
                    participant['completed']+=1
                    participant['latest_result']=max(participant['latest_result'] or '',m['date'][:10])
        return jsonify(teams=sorted(found.values(),key=lambda t:t['name']))

    def requested_fixture(body):
        if not isinstance(body,dict):raise ValueError('A JSON object is required')
        if body.get('fixture_id'):
            match=store.fixture(str(body['fixture_id']))
            if not match:raise ValueError('Fixture not found')
            return match
        sport=body.get('sport','football')
        if sport not in ['football','basketball','tennis']:raise ValueError('Unknown sport')
        home,away=body.get('home_id'),body.get('away_id')
        if not isinstance(home,str) or not isinstance(away,str) or not home or home==away:raise ValueError('Choose two different participants')
        records=store.matches(sport);names={}
        for m in records:
            names[m['home_id']]=m['home'];names[m['away_id']]=m['away']
        if home not in names or away not in names:raise ValueError('Participant is not in the dataset')
        date=str(body.get('date') or datetime.now(timezone.utc).date())
        datetime.strptime(date,'%Y-%m-%d')
        if date<datetime.now(timezone.utc).date().isoformat():raise ValueError('Historical forecasts require the offline evaluation pipeline.')
        competition=str(body.get('competition') or ('E0' if sport=='football' else 'NBA' if sport=='basketball' else 'ATP'))
        if competition not in {m['competition'] for m in records}:raise ValueError('Competition is not covered')
        if sport=='tennis' and body.get('surface','Hard') not in ['Hard','Clay','Grass','Carpet']:raise ValueError('Choose a supported tennis surface')
        return {'id':'scenario','sport':sport,'competition':competition,'date':date+'T23:59:00+00:00','date_precision':'scenario',
                'home':names[home],'away':names[away],'home_id':home,'away_id':away,'neutral':sport=='tennis','surface':body.get('surface','Hard') if sport=='tennis' else '',
                'status':'scenario','source':'User-selected matchup; not a verified fixture'}

    @app.post('/api/analyse')
    def analyse():
        fixture=requested_fixture(request.get_json(silent=True))
        if fixture['status'] not in ['scheduled','timed','scenario'] or fixture['date']<=utcnow():
            raise ValueError('This match has started or finished. Use its recorded pre-match forecast or the results view.')
        with prediction_lock:result=predictor.predict(fixture)
        return jsonify(result)

    @app.get('/api/models')
    def models():
        manifests=[]
        for sport in ['football','basketball','tennis']:
            try:manifests.append(predictor.load(sport)[0])
            except ValueError as e:manifests.append({'sport':sport,'unavailable':str(e)})
        return jsonify(models=manifests)

    @app.get('/api/performance')
    def performance():
        from .tracking import performance as report
        sport=request.args.get('sport','football')
        if sport not in ['football','basketball','tennis']:raise ValueError('Unknown sport')
        horizon=int(request.args.get('horizon','24'))
        if horizon not in [1,24]:raise ValueError('Choose 1 or 24 hours')
        return jsonify(report(store,sport,horizon))

    @app.get('/api/players/scenario')
    def player_scenario():
        from .player_scenarios import analyse
        return jsonify(analyse(store,request.args.get('player',''),request.args.get('minutes',70)))

    @app.get('/api/players/fixture')
    def player_fixture():
        from .player_markets import board
        return jsonify(board(store,request.args.get('fixture','')))

    @app.get('/api/players/status')
    def player_status():
        from .players import status
        return jsonify(status(store))

    @app.get('/api/players/public')
    def public_player_history():
        from .public_players import summary
        return jsonify(summary(store,request.args.get('league',''),request.args.get('q','').strip(),
                               int(request.args.get('offset','0')),int(request.args.get('limit','24'))))

    @app.get('/api/coverage')
    def coverage():
        result=store.coverage()
        rows=store.matches('football',status='finished')
        result['xg']={'observed_matches':sum(m.get('xg_source') is not None and m.get('home_xg') is not None for m in rows),'total':len(rows)}
        return jsonify(result)

    @app.get('/api/journal')
    def journal():return jsonify(predictions=store.journal(session['owner']))

    @app.post('/api/journal')
    def save():
        fixture=requested_fixture(request.get_json(silent=True))
        if fixture['id']=='scenario':raise ValueError('Only provider-verified fixtures can enter the prediction journal.')
        with prediction_lock:prediction=predictor.predict(fixture)
        pid=store.save_prediction(session['owner'],fixture,prediction)
        return jsonify(id=pid,status='saved')

    @app.post('/api/journal/settle')
    def settle():return jsonify(updated=store.settle(session['owner']))

    @app.get('/api/results')
    def results():return match_listing(results_only=True)

    app.extensions['sportslab_store']=store
    app.extensions['sportslab_predictor']=predictor
    return app
