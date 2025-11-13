from dotenv import load_dotenv  # Load first
load_dotenv()  # Fixed: Before any other imports

from flask import Flask
from flask_login import LoginManager
from config import Config  # Now sees loaded env
from models import db
from auth import register_routes
from routes import main_routes
from admin import admin_routes
from werkzeug.security import generate_password_hash
from flask_mail import Mail
import os

# # Debug print after load (remove after)
# print("Loaded MAIL_USERNAME:", os.environ.get('MAIL_USERNAME'))
# print("Loaded MAIL_PASSWORD len:", len(os.environ.get('MAIL_PASSWORD', '')))

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # Now gets fresh env values

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Direct Flask-Mail init
    app.mail = Mail(app)

    # Register routes
    register_routes(app)
    main_routes(app)
    admin_routes(app)

    # Create upload folder
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    return app

# ... (seed_db unchanged)

# Seeding (only runs in prod/main context)
def seed_db(app):
    from models import User, Category, Post, Comment, Vote, Notification, Flag  # Fixed: Import here for modularity
    
    with app.app_context():
        db.create_all()
        
        # Seed categories if none
        if Category.query.count() == 0:
            categories = [
                Category(name="Programming", slug="programming"),
                Category(name="AI", slug="ai"),
                Category(name="Web Dev", slug="web-dev"),
                Category(name="General", slug="general")
            ]
            db.session.add_all(categories)
            db.session.commit()
        
        # Seed admin if not exists (with is_admin=True)
        admin_user = db.session.query(User).filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(username='admin', email='admin@example.com', password_hash=generate_password_hash('password'), bio='Admin user - building cool apps!', is_admin=True)
            db.session.add(admin_user)
            db.session.commit()
        else:
            admin_user.is_admin = True
            admin_user.bio = 'Admin user - building cool apps!'
            db.session.commit()
        
        # Seed demo if not exists
        demo_user = db.session.query(User).filter_by(username='demo').first()
        if not demo_user:
            demo_user = User(username='demo', email='demo@example.com', password_hash=generate_password_hash('demopass'), bio='Demo user - testing features!')
            db.session.add(demo_user)
            db.session.commit()
        else:
            demo_user.bio = 'Demo user - testing features!'
            db.session.commit()
        
        # Seed sample posts if < 3
        if Post.query.count() < 3:
            cat_programming = Category.query.filter_by(slug='programming').first()
            cat_ai = Category.query.filter_by(slug='ai').first()
            cat_web_dev = Category.query.filter_by(slug='web-dev').first()
            
            post1 = Post(title="What's the best way to learn Python in 2025?", user_id=admin_user.id, category_id=cat_programming.id)
            post2 = Post(title="Share your favorite app ideas!", image_path="/uploads/sample_image.jpg", user_id=demo_user.id, category_id=cat_web_dev.id)
            post3 = Post(title="How does AI change web dev?", user_id=admin_user.id, category_id=cat_ai.id)
            
            db.session.add_all([post1, post2, post3])
            db.session.commit()
            
            # Comments
            comment1 = Comment(text="Start with freeCodeCamp—it's hands-on!", user_id=demo_user.id, post_id=post1.id)
            comment2 = Comment(text="Agreed! Add some Flask projects too.", user_id=admin_user.id, post_id=post1.id)
            comment3 = Comment(text="Something conversational like this app!", user_id=demo_user.id, post_id=post3.id)
            db.session.add_all([comment1, comment2, comment3])
            db.session.commit()
        
        # Seed sample votes
        if db.session.query(Vote).filter_by(post_id=1).count() == 0:
            post1 = db.session.get(Post, 1)
            post3 = db.session.get(Post, 3)
            db.session.add(Vote(user_id=admin_user.id, post_id=post1.id, value=1))
            db.session.add(Vote(user_id=demo_user.id, post_id=post1.id, value=1))
            db.session.add(Vote(user_id=demo_user.id, post_id=post3.id, value=-1))
            db.session.commit()
        
        # Seed sample notifications
        if Notification.query.count() == 0:
            post1 = db.session.get(Post, 1)
            post3 = db.session.get(Post, 3)
            comment1 = db.session.get(Comment, 1)
            comment3 = db.session.get(Comment, 3)
            db.session.add(Notification(user_id=post1.user_id, post_id=post1.id, comment_id=comment1.id, message=f"New comment by {demo_user.username} on your post '{post1.title}'", is_read=False))  # Fixed: Explicit False
            db.session.add(Notification(user_id=post3.user_id, post_id=post3.id, comment_id=comment3.id, message=f"New comment by {demo_user.username} on your post '{post3.title}'", is_read=False))  # Fixed
            db.session.commit()
        
        # Seed sample flag
        if Flag.query.count() == 0:
            post2 = db.session.get(Post, 2)
            db.session.add(Flag(user_id=demo_user.id, post_id=post2.id, reason="Spam or off-topic"))
            db.session.commit()
        
        print("Seeding complete!")

if __name__ == '__main__':
    app = create_app()
    seed_db(app)  # Seed only on main run
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)