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
