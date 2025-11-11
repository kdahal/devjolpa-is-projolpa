from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
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

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

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
    votes = db.relationship('Vote', backref='post', lazy=True, cascade='all, delete-orphan')

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

    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_vote'),)  # One vote per user/post

    def __repr__(self):
        return f'<Vote {self.value} by User {self.user_id} on Post {self.post_id}>'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Config for uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Global HTML template for index and category views
INDEX_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Simple Q&A Web App with Upvotes</title>
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
        .share-btn { background: #1da1f2; color: white; border: none; padding: 5px 10px; cursor: pointer; border-radius: 4px; }
        .share-btn:hover { background: #0d8bd9; }
        .user-info { float: right; color: #666; }
        .logout { background: #dc3545; color: white; border: none; padding: 5px 10px; cursor: pointer; border-radius: 4px; }
        .flash { color: red; }
        .cat-filter { margin: 10px 0; }
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
    
    <form method="POST" enctype="multipart/form-data">
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
    
    {% for post in posts %}
    <div class="post" id="post-{{ post.id }}">
        <h3>{{ post.title }} <small>by {{ post.user.username }} in <span class="category">{{ post.category.name }}</span></small></h3>
        <span class="vote-score">{{ post.score }}</span>
        <button class="vote-btn up-btn" onclick="vote({{ post.id }}, 1)">↑</button>
        <button class="vote-btn down-btn" onclick="vote({{ post.id }}, -1)">↓</button>
        <small>{{ post.timestamp.strftime('%Y-%m-%d %H:%M') }}</small>
        {% if post.image_path %}
        <img src="{{ post.image_path }}" alt="Post image">
        {% endif %}
        <button class="share-btn" onclick="sharePost({{ post.id }})">Share</button>
        
        <form method="POST" action="/comment/{{ post.id }}">
            <textarea name="comment" placeholder="Add a comment..." rows="2"></textarea>
            <button type="submit">Comment</button>
        </form>
        
        {% for comment in post.comments %}
        <div class="comment">{{ comment.text }} <small>by {{ comment.user.username }} - {{ comment.timestamp.strftime('%Y-%m-%d %H:%M') }}</small></div>
        {% endfor %}
    </div>
    {% endfor %}
    
    <script>
        function vote(postId, value) {
            fetch('/vote/' + postId, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({value: value})
            }).then(response => response.json()).then(data => {
                if (data.success) {
                    location.reload();  // Refresh to show updated score
                }
            });
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

# Init DB and sample data (runs once)
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
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', email='admin@example.com', password_hash=generate_password_hash('password'))
        db.session.add(admin_user)
        db.session.commit()
    else:
        admin_user = User.query.filter_by(username='admin').first()
    
    # Seed a demo user
    if not User.query.filter_by(username='demo').first():
        demo_user = User(username='demo', email='demo@example.com', password_hash=generate_password_hash('demopass'))
        db.session.add(demo_user)
        db.session.commit()
    else:
        demo_user = User.query.filter_by(username='demo').first()
    
    # Seed sample posts (only if < 3 posts exist; assign categories)
    post_count = Post.query.count()
    if post_count < 3:
        cat_programming = Category.query.filter_by(slug='programming').first()
        cat_ai = Category.query.filter_by(slug='ai').first()
        cat_web_dev = Category.query.filter_by(slug='web-dev').first()
        
        # Post 1: Programming category
        post1 = Post(title="What's the best way to learn Python in 2025?", user_id=admin_user.id, category_id=cat_programming.id)
        db.session.add(post1)
        
        # Post 2: Web Dev category, with placeholder image
        post2 = Post(title="Share your favorite app ideas!", image_path="/uploads/sample_image.jpg", user_id=demo_user.id, category_id=cat_web_dev.id)
        db.session.add(post2)
        
        # Post 3: AI category
        post3 = Post(title="How does AI change web dev?", user_id=admin_user.id, category_id=cat_ai.id)
        db.session.add(post3)
        
        db.session.commit()
        
        # Seed sample comments
        comment1 = Comment(text="Start with freeCodeCamp—it's hands-on!", user_id=demo_user.id, post_id=post1.id)
        comment2 = Comment(text="Agreed! Add some Flask projects too.", user_id=admin_user.id, post_id=post1.id)
        comment3 = Comment(text="Something conversational like this app!", user_id=demo_user.id, post_id=post3.id)
        
        db.session.add_all([comment1, comment2, comment3])
        db.session.commit()
    
    # Seed sample votes (if no votes on post1)
    if Vote.query.filter_by(post_id=1).count() == 0:
        # Upvotes on post1
        Vote(user_id=admin_user.id, post_id=1, value=1)
        Vote(user_id=demo_user.id, post_id=1, value=1)
        db.session.add_all([Vote(user_id=admin_user.id, post_id=1, value=1), Vote(user_id=demo_user.id, post_id=1, value=1)])
        # Downvote on post3 for variety
        db.session.add(Vote(user_id=demo_user.id, post_id=3, value=-1))
        db.session.commit()
    
    print("Seeding complete!")  # For logs; remove in prod

# Add property to Post for score calculation
Post.score = property(lambda p: sum(v.value for v in p.votes) if p.votes else 0)

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
    
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    categories = Category.query.all()
    return render_template_string(INDEX_TEMPLATE, posts=posts, categories=categories)

@app.route('/category/<slug>')
@login_required
def category_filter(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    posts = Post.query.filter_by(category_id=category.id).order_by(Post.timestamp.desc()).all()
    categories = Category.query.all()
    return render_template_string(INDEX_TEMPLATE, posts=posts, categories=categories)

@app.route('/vote/<int:post_id>', methods=['POST'])
@login_required
def vote_post(post_id):
    data = request.get_json()
    vote_value = data.get('value', 0)
    
    post = Post.query.get_or_404(post_id)
    existing_vote = Vote.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    
    if existing_vote:
        if existing_vote.value == vote_value:
            # Unvote
            db.session.delete(existing_vote)
        else:
            # Toggle
            existing_vote.value = vote_value
    else:
        # New vote
        new_vote = Vote(user_id=current_user.id, post_id=post.id, value=vote_value)
        db.session.add(new_vote)
    
    db.session.commit()
    
    score = post.score  # Recalculate
    return {'success': True, 'score': score}

# ... (register, login, logout, comment, uploads routes unchanged from previous)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first() or not all([username, email, password]):
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
        
        user = User.query.filter_by(username=username).first()
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
    post = Post.query.get(post_id)
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