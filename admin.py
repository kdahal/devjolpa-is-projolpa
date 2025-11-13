from flask import request, redirect, url_for, flash, render_template_string
from flask_login import login_required, current_user
from models import db, Flag, Post, Comment
from templates import ADMIN_TEMPLATE

def admin_routes(app):
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
