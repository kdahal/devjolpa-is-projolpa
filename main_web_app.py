from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production!

# Config for uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Simple User class
class User(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash

# In-memory users: Now keyed by ID (int) for easy lookup
users = {}  # {user_id: User}
sample_user = User(1, 'admin', 'admin@example.com', generate_password_hash('password'))
users[1] = sample_user  # Pre-create test user

@login_manager.user_loader
def load_user(user_id):
    return users.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# In-memory storage: posts now include 'user_id'
posts = []

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        image_path = None
        
        if 'image' in request.files:
            file = request.files['image']
            if file.filename and allowed_file(file.filename):
                filename = secure_filename(f'post_{len(posts)}_{file.filename}')
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_path = f"/uploads/{filename}"
        
        if title:
            posts.append({
                'id': len(posts),
                'title': title,
                'image_path': image_path,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'user_id': current_user.id,
                'comments': []
            })
    
    # HTML template (now looks up users by ID)
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Simple Q&A Web App with Logins</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
            .post { border: 1px solid #ccc; margin: 10px 0; padding: 10px; }
            .post img { max-width: 100%; height: auto; margin: 10px 0; border-radius: 8px; }
            .comment { margin-left: 20px; padding: 5px; background: #f9f9f9; border-left: 3px solid #ccc; }
            form { margin: 20px 0; }
            input[type="text"], input[type="email"], input[type="password"], textarea, button { display: block; margin: 5px 0; padding: 8px; width: 100%; max-width: 400px; box-sizing: border-box; }
            input[type="file"] { max-width: 400px; }
            .share-btn { background: #1da1f2; color: white; border: none; padding: 5px 10px; cursor: pointer; border-radius: 4px; }
            .share-btn:hover { background: #0d8bd9; }
            .user-info { float: right; color: #666; }
            .logout { background: #dc3545; color: white; border: none; padding: 5px 10px; cursor: pointer; border-radius: 4px; }
            .flash { color: red; }
        </style>
    </head>
    <body>
        <h1>Simple Q&A Board with Images</h1>
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
            <input type="file" name="image" accept="image/*">
            <button type="submit">Post with Image</button>
        </form>
        
        {% for post in posts %}
        <div class="post" id="post-{{ post.id }}">
            <h3>{{ post.title }} <small>by {{ users[post.user_id].username }}</small></h3>
            <small>{{ post.timestamp }}</small>
            {% if post.image_path %}
            <img src="{{ post.image_path }}" alt="Post image">
            {% endif %}
            <button class="share-btn" onclick="sharePost({{ post.id }})">Share</button>
            
            <form method="POST" action="/comment/{{ post.id }}">
                <textarea name="comment" placeholder="Add a comment..." rows="2"></textarea>
                <button type="submit">Comment</button>
            </form>
            
            {% for comment in post.comments %}
            <div class="comment">{{ comment.text }} <small>by {{ users[comment.user_id].username }} - {{ comment.timestamp }}</small></div>
            {% endfor %}
        </div>
        {% endfor %}
        
        <script>
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
    return render_template_string(html, posts=posts, users=users)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password')
        
        # Check if username exists (iterate since keyed by ID)
        if any(u.username == username for u in users.values()) or not all([username, email, password]):
            flash('Username taken or invalid input!')
            return redirect(url_for('register'))
        
        user_id = len(users) + 1
        password_hash = generate_password_hash(password)
        new_user = User(user_id, username, email, password_hash)
        users[user_id] = new_user  # Key by ID
        flash('Registered! Please log in.')
        return redirect(url_for('login'))
    
    # Simple register HTML
    html = '''
    <!DOCTYPE html>
    <html><head><title>Register</title></head><body>
    <h1>Register</h1>
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
        
        # Find user by username
        target_user = next((u for u in users.values() if u.username == username), None)
        if target_user and check_password_hash(target_user.password_hash, password):
            login_user(target_user)
            return redirect(url_for('index'))
        flash('Invalid credentials!')
    
    # Simple login HTML (with flashes)
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
    if comment_text and 0 <= post_id < len(posts):
        posts[post_id]['comments'].append({
            'text': comment_text,
            'user_id': current_user.id,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
        })
    return index()

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)  # debug=False for prod
