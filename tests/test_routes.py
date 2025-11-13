from flask import url_for
from models import db, User, Category
from werkzeug.security import generate_password_hash

def test_login_successful(client, app):
    # Register a test user first
    with app.app_context():
        test_user = User(username='testlogin', email='test@example.com', password_hash=generate_password_hash('testpass'))
        db.session.add(test_user)
        db.session.commit()

    # Test login
    response = client.post('/login', data={
        'username': 'testlogin',
        'password': 'testpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Logged in as testlogin' in response.data  # Check for user info in template

def test_index_requires_login(client):
    response = client.get('/')
    assert response.status_code == 302  # Redirect to login
    assert '/login' in response.headers['Location']

def test_post_creation(client, app):
    with app.app_context():
        # Create test user
        test_user = User(username='postuser', email='post@example.com', password_hash=generate_password_hash('postpass'))
        db.session.add(test_user)
        db.session.commit()
        
        # Create test category (to satisfy FK)
        test_category = Category(name='Test Cat', slug='test-cat')
        db.session.add(test_category)
        db.session.commit()
        
        # Ensure user_id and category_id are correct
        user_id = test_user.id
        category_id = test_category.id
    
    # Simulate login
    client.post('/login', data={'username': 'postuser', 'password': 'postpass'})
    
    # Post creation
    response = client.post('/', data={
        'title': 'Test Post',
        'category_id': category_id
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Test Post' in response.data  # Verify post appears in index