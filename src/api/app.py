from flask import Flask
from flask_cors import CORS
import logging
import os
from .routes import prediction_bp, optimization_bp


def create_app():
    app = Flask(__name__)

    allowed_origins = []

    if os.getenv("FLASK_ENV") == "development":
        allowed_origins.extend(
            [
                "http://localhost:3000",
                "http://smart-class-server-dev:3000",
                "http://server:3000",
            ]
        )

    else:
        allowed_origins.extend(
            [
                "http://smart-class-server-prod:3000",
                os.getenv("SERVER_URL", "http://server:3000"),
            ]
        )

    CORS(
        app,
        origins=allowed_origins,
        methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    logging.basicConfig(level=logging.INFO)

    # Blueprints
    app.register_blueprint(prediction_bp, url_prefix="/api/predict")
    app.register_blueprint(optimization_bp, url_prefix="/api/optimize")

    @app.route("/health")
    def health_check():
        return {"status": "healthy"}, 200

    return app
