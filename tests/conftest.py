import pytest
import os
from app import create_app
from models import db, User
from flask import session as flask_session
from flask_login import login_user

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
        db.session.remove()
        db.drop_all()
        if hasattr(db, 'engine'):
            db.engine.dispose()
    del os.environ['TESTING']

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

# Updated: Fixture to login a user in test client
@pytest.fixture
def login(app, client):
    def _login(username, password):
        with app.app_context():
            user = db.session.query(User).filter_by(username=username).first()
            if not user:
                from werkzeug.security import generate_password_hash
                user = User(username=username, email=f'{username}@example.com', password_hash=generate_password_hash(password))
                db.session.add(user)
                db.session.commit()
            
            # Access ID inside context to avoid detached error
            user_id = user.id
            
            # Use login_user in test request context to set session properly
            with app.test_request_context():
                login_user(user)
                # Copy the set session to test client
                client.session = dict(flask_session)
        
        return user
    return _login