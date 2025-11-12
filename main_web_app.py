from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here')  # Use env var on Render

# SQLite config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models - Added is_admin to User, Flag model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    bio = db.Column(db.String(500))
    is_admin = db.Column(db.Boolean, default=False)  # New: Admin role
    def __repr__(self):
        return f'<User {self.username}>'
    @property
    def karma(self):
        return sum(p.score for p in self.posts) if self.posts else 0
    @property
    def unread_notifications(self):
        return db.session.query(Notification).filter_by(user_id=self.id, is_read=False).count()

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    def __repr__(self):
        return f'<Category {self.name}>'

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    image_path = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('posts', lazy=True))
    category = db.relationship('Category', backref=db.backref('posts', lazy=True))
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='post', lazy='select', cascade='all, delete-orphan')
    flags = db.relationship('Flag', backref='post', lazy=True, cascade='all, delete-orphan')
    @property
    def score(self):
        return sum(v.value for v in self.votes) if self.votes else 0

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    flags = db.relationship('Flag', backref='comment', lazy=True, cascade='all, delete-orphan')

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    value = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_vote'),)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))
    post = db.relationship('Post', backref=db.backref('notifications', lazy=True))
    comment = db.relationship('Comment')

class Flag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    reason = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('flags', lazy=True))
    __table_args__ = (db.CheckConstraint('post_id IS NOT NULL OR comment_id IS NOT NULL', name='flag_target'),)  # One or the other
    def __repr__(self):
        return f'<Flag {self.reason} by User {self.user_id}>'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Config for uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Templates
ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Admin Dashboard</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
        .flagged-item { border: 1px solid #ccc; margin: 10px 0; padding: 10px; border-radius: 4px; }
        form { display: inline; margin: 5px; }
        button { padding: 4px 8px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .back-link { margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Admin Dashboard</h1>
    <a href="/" class="back-link">← Back to Feed</a>
    
    <h2>Flagged Posts</h2>
    {% for flag, post in flagged_posts %}
    <div class="flagged-item">
        <h3>{{ post.title }}</h3>
        <p>Flagged by {{ flag.user.username }}: {{ flag.reason }}</p>
        <small>{{ flag.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
        <form method="POST" action="/admin/delete/post/{{ post.id }}">
            <button type="submit">Delete Post</button>
        </form>
    </div>
    {% endfor %}
    
    <h2>Flagged Comments</h2>
    {% for flag, comment in flagged_comments %}
    <div class="flagged-item">
        <p>{{ comment.text }}</p>
        <p>Flagged by {{ flag.user.username }}: {{ flag.reason }}</p>
        <small>{{ flag.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
        <form method="POST" action="/admin/delete/comment/{{ comment.id }}">
            <button type="submit">Delete Comment</button>
        </form>
    </div>
    {% endfor %}
    
    {% if not flagged_posts and not flagged_comments %}
    <p>No flagged items yet.</p>
    {% endif %}
</body>
</html>
'''

PROFILE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Profile - {{ user.username }}</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
        .bio { background: #f9f9f9; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .stats { background: #e7f3ff; padding: 10px; border-radius: 4px; }
        .post { border: 1px solid #ccc; margin: 10px 0; padding: 10px; }
        .vote-score { background: #4caf50; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; margin-left: 10px; }
        .vote-btn { padding: 4px 8px; margin: 0 2px; border: none; border-radius: 4px; cursor: pointer; }
        .up-btn { background: #4caf50; color: white; }
        .down-btn { background: #f44336; color: white; }
        .comment { margin-left: 20px; padding: 5px; background: #f9f9f9; border-left: 3px solid #ccc; }
        form { margin: 20px 0; }
        input[type="text"], textarea, button { display: block; margin: 5px 0; padding: 8px; width: 100%; max-width: 400px; box-sizing: border-box; }
        .back-link { margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Profile: {{ user.username }}</h1>
    <a href="/" class="back-link">← Back to Feed</a>
    <div class="stats">
        <strong>Karma: {{ user.karma }}</strong> | Posts: {{ user.posts|length }} | Joined: {{ user.id }}  <!-- ID as placeholder for join date -->
    </div>
    {% if user.bio %}
    <div class="bio">{{ user.bio }}</div>
    {% endif %}
    {% if current_user.username == user.username %}
    <form method="POST" action="/profile/{{ user.username }}/edit">
        <textarea name="bio" placeholder="Update your bio..." rows="3">{{ user.bio or '' }}</textarea>
        <button type="submit">Update Bio</button>
    </form>
    {% endif %}
    
    <h2>Posts by {{ user.username }}</h2>
    {% for post in posts %}
    <div class="post" id="post-{{ post.id }}">
        <h3>{{ post.title }} <small>in <span class="category">{{ post.category.name }}</span></small></h3>
        <span class="vote-score" id="score-{{ post.id }}">{{ post.score }}</span>
        <button type="button" class="vote-btn up-btn" onclick="vote(event, {{ post.id }}, 1)">↑</button>
        <button type="button" class="vote-btn down-btn" onclick="vote(event, {{ post.id }}, -1)">↓</button>
        <small>{{ post.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
        {% if post.image_path %}
        <img src="{{ post.image_path }}" alt="Post image">
        {% endif %}
        {% for comment in post.comments %}
        <div class="comment">{{ comment.text }} <small>by {{ comment.user.username }} - {{ comment.timestamp.strftime('%Y-%m-%d %H:%M') }}</small></div>
        {% endfor %}
    </div>
    {% endfor %}
    
    <script>
        function vote(event, postId, value) {
            event.preventDefault();
            event.stopPropagation();
            const scoreEl = document.getElementById('score-' + postId);
            fetch('/vote/' + postId, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({value: value})
            }).then(response => response.json()).then(data => {
                if (data.success) {
                    scoreEl.textContent = data.score;
                }
            }).catch(err => console.error('Vote error:', err));
        }
    </script>
</body>
</html>
'''

NOTIFICATIONS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Notifications</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
        .notification { border: 1px solid #ccc; margin: 10px 0; padding: 10px; border-radius: 4px; }
        .unread { background: #e7f3ff; }
        .back-link { margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Notifications</h1>
    <a href="/" class="back-link">← Back to Feed</a>
    {% for notif in notifications %}
    <div class="notification {% if not notif.is_read %}unread{% endif %}">
        <p>{{ notif.message }}</p>
        <small>{{ notif.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
    </div>
    {% endfor %}
    {% if not notifications %}
    <p>No notifications yet.</p>
    {% endif %}
</body>
</html>
'''

SINGLE_POST_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ post.title }}</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
        .post { border: 1px solid #ccc; margin: 10px 0; padding: 10px; }
        .vote-score { background: #4caf50; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; margin-left: 10px; }
        .vote-btn { padding: 4px 8px; margin: 0 2px; border: none; border-radius: 4px; cursor: pointer; }
        .up-btn { background: #4caf50; color: white; }
        .down-btn { background: #f44336; color: white; }
        .comment { margin-left: 20px; padding: 5px; background: #f9f9f9; border-left: 3px solid #ccc; }
        .back-link { margin: 10px 0; }
    </style>
</head>
<body>
    <h1>{{ post.title }}</h1>
    <a href="/" class="back-link">← Back to Feed</a>
    <div class="post">
        <h3>{{ post.title }} <small>by {{ post.user.username }} in {{ post.category.name }}</small></h3>
        <span class="vote-score" id="score-{{ post.id }}">{{ post.score }}</span>
        <button type="button" class="vote-btn up-btn" onclick="vote(event, {{ post.id }}, 1)">↑</button>
        <button type="button" class="vote-btn down-btn" onclick="vote(event, {{ post.id }}, -1)">↓</button>
        <small>{{ post.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
        {% if post.image_path %}
        <img src="{{ post.image_path }}" alt="Post image">
        {% endif %}
        <form method="POST" action="/comment/{{ post.id }}">
            <textarea name="comment" placeholder="Add a comment..." rows="2"></textarea>
            <button type="submit">Comment</button>
        </form>
        {% for comment in post.comments %}
        <div class="comment">{{ comment.text }} <small>by {{ comment.user.username }} - {{ comment.timestamp.strftime('%Y-%m-%d %H:%M') }}</small></div>
        {% endfor %}
    </div>
    <script>
        function vote(event, postId, value) {
            event.preventDefault();
            event.stopPropagation();
            const scoreEl = document.getElementById('score-' + postId);
            fetch('/vote/' + postId, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({value: value})
            }).then(response => response.json()).then(data => {
                if (data.success) {
                    scoreEl.textContent = data.score;
                }
            }).catch(err => console.error('Vote error:', err));
        }
    </script>
</body>
</html>
'''

INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Simple Q&A Web App with Notifications</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
        .post { border: 1px solid #ccc; margin: 10px 0; padding: 10px; }
        .post img { max-width: 100%; height: auto; margin: 10px 0; border-radius: 8px; }
        .category { background: #e7f3ff; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
        .vote-score { background: #4caf50; color: white; padding: 2px 6px; border-radius: 4px; font-weight: bold; margin-left: 10px; }
        .vote-btn { padding: 4px 8px; margin: 0 2px; border: none; border-radius: 4px; cursor: pointer; }
        .up-btn { background: #4caf50; color: white; }
        .down-btn { background: #f44336; color: white; }
        .comment { margin-left: 20px; padding: 5px; background: #f9f9f9; border-left: 3px solid #ccc; }
        form { margin: 20px 0; }
        input[type="text"], input[type="email"], input[type="password"], textarea, button, select { display: block; margin: 5px 0; padding: 8px; width: 100%; max-width: 400px; box-sizing: border-box; }
        input[type="file"] { max-width: 400px; }
        .search-form { display: flex; max-width: 400px; margin: 20px 0; }
        .search-form input[type="text"] { flex: 1; margin-right: 10px; }
        .search-form select { flex: 1; margin-right: 10px; }
        .search-form button { flex: 1; }
        .share-btn { background: #1da1f2; color: white; border: none; padding: 5px 10px; cursor: pointer; border-radius: 4px; }
        .share-btn:hover { background: #0d8bd9; }
        .user-info { float: right; color: #666; }
        .logout { background: #dc3545; color: white; border: none; padding: 5px 10px; cursor: pointer; border-radius: 4px; }
        .flash { color: red; }
        .cat-filter { margin: 10px 0; }
        a.username { color: #1da1f2; text-decoration: none; }
        a.username:hover { text-decoration: underline; }
        .search-header { color: #666; font-style: italic; }
        .bell { position: relative; cursor: pointer; margin-left: 10px; }
        .bell-badge { position: absolute; top: -8px; right: -8px; background: #f44336; color: white; border-radius: 50%; padding: 2px 5px; font-size: 0.8em; }
        .flag-form { display: inline; margin-left: 10px; }
        .flag-form input { width: 120px; margin-right: 5px; }
        .flag-form button { padding: 2px 6px; }
    </style>
</head>
<body>
    <h1>Simple Q&A Board with Notifications</h1>
    <div class="user-info">Logged in as {{ current_user.username }} | <button class="logout" onclick="location.href='/logout'">Logout</button>
        <span class="bell" onclick="location.href='/notifications'" title="Notifications">
            🔔
            {% if current_user.unread_notifications > 0 %}
            <span class="bell-badge">{{ current_user.unread_notifications }}</span>
            {% endif %}
        </span>
        {% if current_user.is_admin %}
        | <a href="/admin">Admin</a>
        {% endif %}
    </div>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}
          <div class="flash">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    
    <form method="GET" action="/search" class="search-form">
        <input type="text" name="q" placeholder="Search titles..." value="{{ query or '' }}">
        <select name="cat_id">
            <option value="">All Categories</option>
            {% for cat in categories %}
            <option value="{{ cat.id }}" {% if cat_id == cat.id %}selected{% endif %}>{{ cat.name }}</option>
            {% endfor %}
        </select>
        <button type="submit">Search</button>
    </form>
    
    <form method="POST" action="/" enctype="multipart/form-data">
        <input type="text" name="title" placeholder="Post a question or update..." required>
        <select name="category_id" required>
            <option value="">Select Category</option>
            {% for cat in categories %}
            <option value="{{ cat.id }}">{{ cat.name }}</option>
            {% endfor %}
        </select>
        <input type="file" name="image" accept="image/*">
        <button type="submit">Post with Image</button>
    </form>
    
    <div class="cat-filter">
        Filter by Category: 
        {% for cat in categories %}
        <a href="/category/{{ cat.slug }}" style="margin: 0 5px; color: #1da1f2;">{{ cat.name }}</a>
        {% endfor %}
        | <a href="/">All</a>
    </div>
    
    {% if query %}
    <p class="search-header">Search Results for "{{ query }}" {% if cat_name %}in {{ cat_name }}{% endif %} ({{ posts|length }} results)</p>
    {% endif %}
    
    {% for post in posts %}
    <div class="post" id="post-{{ post.id }}">
        <h3>{{ post.title }} <small>by <a href="/profile/{{ post.user.username }}" class="username">{{ post.user.username }}</a> in <span class="category">{{ post.category.name }}</span></small></h3>
        <span class="vote-score" id="score-{{ post.id }}">{{ post.score }}</span>
        <button type="button" class="vote-btn up-btn" onclick="vote(event, {{ post.id }}, 1)">↑</button>
        <button type="button" class="vote-btn down-btn" onclick="vote(event, {{ post.id }}, -1)">↓</button>
        <small>{{ post.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
        {% if post.image_path %}
        <img src="{{ post.image_path }}" alt="Post image">
        {% endif %}
        <button type="button" class="share-btn" onclick="sharePost({{ post.id }})">Share</button>
        <form method="POST" action="/flag/post/{{ post.id }}" class="flag-form">
            <input type="text" name="reason" placeholder="Flag reason...">
            <button type="submit">Flag</button>
        </form>
        
        <form method="POST" action="/comment/{{ post.id }}">
            <textarea name="comment" placeholder="Add a comment..." rows="2"></textarea>
            <button type="submit">Comment</button>
        </form>
        
        {% for comment in post.comments %}
        <div class="comment">{{ comment.text }} <small>by <a href="/profile/{{ comment.user.username }}" class="username">{{ comment.user.username }}</a> - {{ comment.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
            <form method="POST" action="/flag/comment/{{ comment.id }}" class="flag-form">
                <input type="text" name="reason" placeholder="Flag reason...">
                <button type="submit">Flag</button>
            </form>
        </div>
        {% endfor %}
    </div>
    {% endfor %}
    
    {% if query and posts|length == 0 %}
    <p>No results found for "{{ query }}". Try a different search!</p>
    {% endif %}
    
    <script>
        function vote(event, postId, value) {
            event.preventDefault();
            event.stopPropagation();
            const scoreEl = document.getElementById('score-' + postId);
            fetch('/vote/' + postId, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({value: value})
            }).then(response => response.json()).then(data => {
                if (data.success) {
                    scoreEl.textContent = data.score;
                }
            }).catch(err => console.error('Vote error:', err));
        }
        function sharePost(postId) {
            const url = window.location.origin + '/post/' + postId;
            if (navigator.share) {
                navigator.share({
                    title: 'Check this post!',
                    url: url
                });
            } else {
                prompt('Copy this link to share:', url);
            }
        }
    </script>
</body>
</html>
'''

# Init DB and sample data (added is_admin to admin, sample flag)
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
    if not db.session.query(User).filter_by(username='admin').first():
        admin_user = User(username='admin', email='admin@example.com', password_hash=generate_password_hash('password'), bio='Admin user - building cool apps!', is_admin=True)
        db.session.add(admin_user)
        db.session.commit()
    else:
        admin_user = db.session.query(User).filter_by(username='admin').first()
        admin_user.is_admin = True
        admin_user.bio = 'Admin user - building cool apps!'
        db.session.commit()
    
    # Seed demo if not exists
    if not db.session.query(User).filter_by(username='demo').first():
        demo_user = User(username='demo', email='demo@example.com', password_hash=generate_password_hash('demopass'), bio='Demo user - testing features!')
        db.session.add(demo_user)
        db.session.commit()
    else:
        demo_user = db.session.query(User).filter_by(username='demo').first()
        demo_user.bio = 'Demo user - testing features!'
        db.session.commit()
    
    # Seed sample posts if < 3 (unchanged)
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
    
    # Seed sample votes (unchanged)
    if db.session.query(Vote).filter_by(post_id=1).count() == 0:
        post1 = db.session.get(Post, 1)
        post3 = db.session.get(Post, 3)
        db.session.add(Vote(user_id=admin_user.id, post_id=post1.id, value=1))
        db.session.add(Vote(user_id=demo_user.id, post_id=post1.id, value=1))
        db.session.add(Vote(user_id=demo_user.id, post_id=post3.id, value=-1))
        db.session.commit()
    
    # Seed sample notifications (unchanged)
    if Notification.query.count() == 0:
        post1 = db.session.get(Post, 1)
        post3 = db.session.get(Post, 3)
        comment1 = db.session.get(Comment, 1)
        comment3 = db.session.get(Comment, 3)
        db.session.add(Notification(user_id=post1.user_id, post_id=post1.id, comment_id=comment1.id, message=f"New comment by {demo_user.username} on your post '{post1.title}'"))
        db.session.add(Notification(user_id=post3.user_id, post_id=post3.id, comment_id=comment3.id, message=f"New comment by {demo_user.username} on your post '{post3.title}'"))
        db.session.commit()
    
    # Seed sample flag (for admin dashboard)
    if Flag.query.count() == 0:
        post2 = db.session.get(Post, 2)
        db.session.add(Flag(user_id=demo_user.id, post_id=post2.id, reason="Spam or off-topic"))
        db.session.commit()
    
    print("Seeding complete!")

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.session.query(User).filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials!')
    return '''
    <!DOCTYPE html>
    <html><head><title>Login</title></head><body>
    <h1>Login</h1>
    <form method="POST">
        <input type="text" name="username" placeholder="Username" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button type="submit">Login</button>
    </form>
    <p><a href="/register">Register</a></p>
    </body></html>
    '''

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if db.session.query(User).filter_by(username=username).first():
            flash('Username taken!')
            return redirect(url_for('register'))
        if db.session.query(User).filter_by(email=email).first():
            flash('Email taken!')
            return redirect(url_for('register'))
        user = User(username=username, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash('Registered! Please login.')
        return redirect(url_for('login'))
    return '''
    <!DOCTYPE html>
    <html><head><title>Register</title></head><body>
    <h1>Register</h1>
    <form method="POST">
        <input type="text" name="username" placeholder="Username" required><br>
        <input type="email" name="email" placeholder="Email" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button type="submit">Register</button>
    </form>
    <p><a href="/login">Login</a></p>
    </body></html>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category_id = request.form.get('category_id', type=int)
        image_path = None
        
        if 'image' in request.files:
            file = request.files['image']
            if file.filename and allowed_file(file.filename):
                filename = secure_filename(f'post_{Post.query.count()}_{file.filename}')
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_path = f"/uploads/{filename}"
        
        if title and category_id:
            post = Post(title=title, image_path=image_path, user_id=current_user.id, category_id=category_id)
            db.session.add(post)
            db.session.commit()
    
    posts = Post.query.options(joinedload(Post.votes)).order_by(Post.timestamp.desc()).all()
    categories = Category.query.all()
    return render_template_string(INDEX_TEMPLATE, posts=posts, categories=categories, query=None, cat_id=None, cat_name=None)

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    cat_id = request.args.get('cat_id', type=int)
    categories = Category.query.all()
    
    q = Post.query
    if query:
        q = q.filter(Post.title.ilike(f'%{query}%'))
    if cat_id:
        q = q.filter_by(category_id=cat_id)
    posts = q.options(joinedload(Post.votes)).order_by(Post.timestamp.desc()).all()
    
    cat_name = Category.query.get(cat_id).name if cat_id else None
    return render_template_string(INDEX_TEMPLATE, posts=posts, categories=categories, query=query, cat_id=cat_id, cat_name=cat_name)

@app.route('/category/<slug>')
@login_required
def category(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    posts = Post.query.filter_by(category_id=cat.id).options(joinedload(Post.votes)).order_by(Post.timestamp.desc()).all()
    categories = Category.query.all()
    return render_template_string(INDEX_TEMPLATE, posts=posts, categories=categories, query=None, cat_id=cat.id, cat_name=cat.name)

@app.route('/profile/<username>')
@login_required
def profile(username):
    user = db.session.query(User).filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=user.id).options(joinedload(Post.comments), joinedload(Post.votes)).all()
    return render_template_string(PROFILE_TEMPLATE, user=user, posts=posts)

@app.route('/profile/<username>/edit', methods=['POST'])
@login_required
def edit_profile(username):
    if current_user.username != username:
        flash('Unauthorized!')
        return redirect(url_for('profile', username=username))
    user = db.session.query(User).filter_by(username=username).first_or_404()
    user.bio = request.form.get('bio', '').strip()
    db.session.commit()
    flash('Bio updated!')
    return redirect(url_for('profile', username=username))

@app.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return render_template_string(NOTIFICATIONS_TEMPLATE, notifications=notifs)

@app.route('/vote/<int:post_id>', methods=['POST'])
@login_required
def vote(post_id):
    data = request.get_json()
    value = data.get('value')
    vote = db.session.query(Vote).filter_by(user_id=current_user.id, post_id=post_id).first()
    if vote:
        if vote.value == value:
            db.session.delete(vote)
            score = -value
        else:
            vote.value = value
            score = 2 * value
    else:
        vote = Vote(user_id=current_user.id, post_id=post_id, value=value)
        db.session.add(vote)
        score = value
    db.session.commit()
    post = db.session.get(Post, post_id)
    return jsonify({'success': True, 'score': post.score})

@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment(post_id):
    text = request.form.get('comment', '').strip()
    if text:
        comment = Comment(text=text, user_id=current_user.id, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        # Create notification
        post = db.session.get(Post, post_id)
        if post.user_id != current_user.id:
            notif = Notification(user_id=post.user_id, post_id=post_id, comment_id=comment.id, message=f"New comment by {current_user.username} on your post '{post.title}'")
            db.session.add(notif)
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>')
@login_required
def single_post(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        flash('Post not found!')
        return redirect(url_for('index'))
    post.comments = post.comments  # Load comments
    return render_template_string(SINGLE_POST_TEMPLATE, post=post)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Admin access required!')
        return redirect(url_for('index'))
    
    flagged_posts = db.session.query(Flag, Post).join(Post).filter(Flag.post_id.isnot(None)).all()
    flagged_comments = db.session.query(Flag, Comment).join(Comment).filter(Flag.comment_id.isnot(None)).all()
    return render_template_string(ADMIN_TEMPLATE, flagged_posts=flagged_posts, flagged_comments=flagged_comments)

@app.route('/flag/post/<int:post_id>', methods=['POST'])
@login_required
def flag_post(post_id):
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Reason required!')
        return redirect(url_for('index'))
    
    post = db.session.get(Post, post_id)
    if not post:
        flash('Post not found!')
        return redirect(url_for('index'))
    
    flag = Flag(user_id=current_user.id, post_id=post.id, reason=reason)
    db.session.add(flag)
    db.session.commit()
    flash('Post flagged for review!')
    return redirect(url_for('index'))

@app.route('/flag/comment/<int:comment_id>', methods=['POST'])
@login_required
def flag_comment(comment_id):
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Reason required!')
        return redirect(url_for('index'))
    
    comment = db.session.get(Comment, comment_id)
    if not comment:
        flash('Comment not found!')
        return redirect(url_for('index'))
    
    flag = Flag(user_id=current_user.id, comment_id=comment.id, reason=reason)
    db.session.add(flag)
    db.session.commit()
    flash('Comment flagged for review!')
    return redirect(url_for('index'))

@app.route('/admin/delete/post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    if not current_user.is_admin:
        flash('Admin access required!')
        return redirect(url_for('admin_dashboard'))
    
    post = db.session.get(Post, post_id)
    if not post:
        flash('Post not found!')
        return redirect(url_for('admin_dashboard'))
    
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted!')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    if not current_user.is_admin:
        flash('Admin access required!')
        return redirect(url_for('admin_dashboard'))
    
    comment = db.session.get(Comment, comment_id)
    if not comment:
        flash('Comment not found!')
        return redirect(url_for('admin_dashboard'))
    
    db.session.delete(comment)
    db.session.commit()
    flash('Comment deleted!')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)