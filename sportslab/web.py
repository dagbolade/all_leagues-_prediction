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

    @app.get('/api/fixtures')
    def fixtures():
        sport=request.args.get('sport','football');competition=request.args.get('competition')
        if sport not in ['football','basketball','tennis']:raise ValueError('Unknown sport')
        records=store.matches(sport,competition)
        date=request.args.get('date')
        if date:
            datetime.strptime(date,'%Y-%m-%d')
            records=[m for m in records if m['date'][:10]==date]
        else:
            upcoming=[m for m in records if m['status'] in ['scheduled','timed'] and m['date']>=utcnow()]
            records=upcoming[:40] if upcoming else [m for m in records if m['status']=='finished'][-30:][::-1]
        return jsonify(fixtures=records[:100],total=len(records))

    @app.get('/api/teams')
    def teams():
        sport=request.args.get('sport','football');comp=request.args.get('competition')
        records=store.matches(sport,comp);found={}
        for m in records:
            for side in ['home','away']:found[m[side+'_id']]={'id':m[side+'_id'],'name':m[side],'last_seen':m['date'][:10]}
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
    def results():
        sport=request.args.get('sport','football');comp=request.args.get('competition')
        return jsonify(results=store.matches(sport,comp,'finished')[-80:][::-1])

    app.extensions['sportslab_store']=store
    app.extensions['sportslab_predictor']=predictor
    return app
