from flask import request, redirect, url_for, flash, render_template_string
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

LOGIN_TEMPLATE = '''
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

REGISTER_TEMPLATE = '''
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

def register_routes(app):
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
        return render_template_string(LOGIN_TEMPLATE)

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
        return render_template_string(REGISTER_TEMPLATE)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))
