import pytest
import os
from app import create_app
from models import db
from flask_sqlalchemy import SQLAlchemy  # For engine access

@pytest.fixture
def app():
    os.environ['TESTING'] = '1'
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()  # Close any open sessions
        db.drop_all()
        if hasattr(db, 'engine'):  # Explicitly dispose engine
            db.engine.dispose()
    del os.environ['TESTING']

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()