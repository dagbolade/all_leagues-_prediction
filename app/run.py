"""Canonical WSGI application. Legacy blueprints are intentionally retired."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sportslab.web import create_app
app=create_app()
if __name__=='__main__':
    from waitress import serve
    serve(app,host='127.0.0.1',port=5000,threads=4)
