import os

from flask import Flask, jsonify

from config import config_map

from .celery_app import celery_init_app
from .extensions import bcrypt, cors, db, jwt, mail, migrate


def create_app(config_name=None):
    config_name = config_name or os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app)
    mail.init_app(app)
    celery_init_app(app)

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify(message="Login required."), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify(message="Invalid token. Please log in again."), 401

    @jwt.expired_token_loader
    def expired_token(header, payload):
        return jsonify(message="Session expired. Please log in again."), 401

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(message="File is too large. Maximum size is 5 MB."), 413

    from . import models  # noqa: F401

    from .applications import applications_bp
    from .auth import auth_bp
    from .interviews import interviews_bp
    from .jobs import jobs_bp
    from .main import main_bp
    from .pipeline import pipeline_bp
    from .resumes import resumes_bp
    from .analytics import analytics_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(resumes_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(interviews_bp)
    app.register_blueprint(analytics_bp)

    return app