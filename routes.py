from flask import request, render_template_string, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from models import db, User, Category, Post, Comment, Vote, Notification, Flag
from utils import allowed_file
from templates import INDEX_TEMPLATE, PROFILE_TEMPLATE, NOTIFICATIONS_TEMPLATE, SINGLE_POST_TEMPLATE
from werkzeug.utils import secure_filename
import os

def main_routes(app):
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
        from mail_utils import send_notification_digest  # Modular import
        
        # Fixed: Send digest FIRST (while still unread)
        send_notification_digest(app)
        
        # Then mark all as read for UI
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
