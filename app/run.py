from flask import Flask, jsonify
from app.routes import routes
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)


    # Register blueprint for routes
    app.register_blueprint(routes)

    # Simple error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            'error': 'Page not found',
            'status': 404
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal server error',
            'status': 500
        }), 500

    return app


# CREATE APP INSTANCE AT MODULE LEVEL (for deployment)
app = create_app()


def main():
    print("🚀 Starting Football Predictor...")
    print("🌐 Access your app at: http://localhost:5000")

    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )


if __name__ == '__main__':
    main()