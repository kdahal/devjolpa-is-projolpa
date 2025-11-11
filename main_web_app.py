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

# Models (unchanged)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    bio = db.Column(db.String(500))  # New: User bio

    def __repr__(self):
        return f'<User {self.username}>'

    # Karma: Sum of scores from user's posts
    @property
    def karma(self):
        return sum(p.score for p in self.posts) if self.posts else 0

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

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    value = db.Column(db.Integer, nullable=False)  # +1 up, -1 down

    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_vote'),)

    def __repr__(self):
        return f'<Vote {self.value} by User {self.user_id} on Post {self.post_id}>'

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

# Global INDEX_TEMPLATE (added search form)
INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Simple Q&A Web App with Search</title>
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
    </style>
</head>
<body>
    <h1>Simple Q&A Board with Upvotes & Categories</h1>
    <div class="user-info">Logged in as {{ current_user.username }} | <button class="logout" onclick="location.href='/logout'">Logout</button></div>
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
        
        <form method="POST" action="/comment/{{ post.id }}">
            <textarea name="comment" placeholder="Add a comment..." rows="2"></textarea>
            <button type="submit">Comment</button>
        </form>
        
        {% for comment in post.comments %}
        <div class="comment">{{ comment.text }} <small>by <a href="/profile/{{ comment.user.username }}" class="username">{{ comment.user.username }}</a> - {{ comment.timestamp.strftime('%Y-%m-%d %H:%M') }}</small></div>
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
        function sharePost(id) {
            const url = window.location.href + '#post-' + id;
            if (navigator.share) {
                navigator.share({ title: 'Check this post!', url: url });
            } else {
                navigator.clipboard.writeText(url).then(() => {
                    alert('Link copied to clipboard!');
                }).catch(() => {
                    alert('Link: ' + url);
                });
            }
        }
    </script>
</body>
</html>
'''

# Profile Template (unchanged)
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

# Init DB and sample data (unchanged)
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
    
    # Seed admin if not exists
    if not db.session.query(User).filter_by(username='admin').first():
        admin_user = User(username='admin', email='admin@example.com', password_hash=generate_password_hash('password'), bio='Admin user - building cool apps!')
        db.session.add(admin_user)
        db.session.commit()
    else:
        admin_user = db.session.query(User).filter_by(username='admin').first()
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
    
    print("Seeding complete!")

# Routes - Added search
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

@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('q', '').strip()
    cat_id = request.args.get('cat_id', type=int)
    cat_name = None
    
    posts = Post.query.options(joinedload(Post.votes))
    
    if query:
        posts = posts.filter(Post.title.ilike(f'%{query}%'))
    
    if cat_id:
        category = Category.query.get(cat_id)
        if category:
            cat_name = category.name
            posts = posts.filter_by(category_id=cat_id)
    
    posts = posts.order_by(Post.timestamp.desc()).all()
    categories = Category.query.all()
    return render_template_string(INDEX_TEMPLATE, posts=posts, categories=categories, query=query, cat_id=cat_id, cat_name=cat_name)

@app.route('/category/<slug>')
@login_required
def category_filter(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    posts = Post.query.options(joinedload(Post.votes)).filter_by(category_id=category.id).order_by(Post.timestamp.desc()).all()
    categories = Category.query.all()
    return render_template_string(INDEX_TEMPLATE, posts=posts, categories=categories, query=None, cat_id=category.id, cat_name=category.name)

@app.route('/profile/<username>')
def profile(username):
    user = db.session.query(User).filter_by(username=username).first_or_404()
    posts = Post.query.options(joinedload(Post.votes), joinedload(Post.comments)).filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()
    return render_template_string(PROFILE_TEMPLATE, user=user, posts=posts)

@app.route('/profile/<username>/edit', methods=['POST'])
@login_required
def edit_profile(username):
    if current_user.username != username:
        flash('You can only edit your own profile!')
        return redirect(url_for('profile', username=username))
    
    user = db.session.query(User).filter_by(username=username).first()
    bio = request.form.get('bio', '').strip()
    if len(bio) > 500:
        flash('Bio too long (max 500 chars)!')
        return redirect(url_for('profile', username=username))
    
    user.bio = bio
    db.session.commit()
    flash('Bio updated!')
    return redirect(url_for('profile', username=username))

@app.route('/vote/<int:post_id>', methods=['POST'])
@login_required
def vote_post(post_id):
    data = request.get_json()
    vote_value = data.get('value', 0)
    
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({'success': False}), 404
    
    existing_vote = db.session.query(Vote).filter_by(user_id=current_user.id, post_id=post.id).first()
    
    if existing_vote:
        if existing_vote.value == vote_value:
            db.session.delete(existing_vote)
        else:
            existing_vote.value = vote_value
    else:
        new_vote = Vote(user_id=current_user.id, post_id=post.id, value=vote_value)
        db.session.add(new_vote)
    
    db.session.commit()
    
    post = db.session.get(Post, post.id, options=[joinedload(Post.votes)])
    score = post.score
    return jsonify({'success': True, 'score': score})

# Register, login, logout, comment, uploads (unchanged)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password')
        
        if db.session.query(User).filter_by(username=username).first() or not all([username, email, password]):
            flash('Username taken or invalid input!')
            return redirect(url_for('register'))
        
        password_hash = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()
        flash('Registered! Please log in.')
        return redirect(url_for('login'))
    
    html = '''
    <!DOCTYPE html>
    <html><head><title>Register</title></head><body>
    <h1>Register</h1>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}
          <p style="color: red;">{{ message }}</p>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="POST">
        <input type="text" name="username" placeholder="Username" required>
        <input type="email" name="email" placeholder="Email" required>
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit">Register</button>
    </form>
    <a href="/login">Already have an account? Login</a> | <a href="/">Home (guest)</a>
    </body></html>
    '''
    return render_template_string(html)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        user = db.session.query(User).filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials!')
    
    html = '''
    <!DOCTYPE html>
    <html><head><title>Login</title></head><body>
    <h1>Login</h1>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}
          <p style="color: red;">{{ message }}</p>
        {% endfor %}
      {% endif %}
    {% endwith %}
    <form method="POST">
        <input type="text" name="username" placeholder="Username" required>
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
    <a href="/register">No account? Register</a> | <a href="/">Home (guest)</a>
    </body></html>
    '''
    return render_template_string(html)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    comment_text = request.form.get('comment', '').strip()
    post = db.session.get(Post, post_id)
    if comment_text and post:
        comment = Comment(text=comment_text, user_id=current_user.id, post_id=post.id)
        db.session.add(comment)
        db.session.commit()
    return index()

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)