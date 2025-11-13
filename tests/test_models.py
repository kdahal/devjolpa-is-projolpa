from models import db, User

def test_user_creation(app):
    with app.app_context():
        user = User(username='testuser', email='test@example.com', password_hash='hashedpass')
        db.session.add(user)
        db.session.commit()
        assert user.username == 'testuser'
        assert User.query.filter_by(username='testuser').first() is not None

def test_user_karma(app):
    with app.app_context():
        user = User(username='karmauser', email='karma@example.com', password_hash='hashedpass')
        db.session.add(user)
        db.session.commit()
        assert user.karma == 0  # No posts yet