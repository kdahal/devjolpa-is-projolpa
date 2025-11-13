# Simple Flask Q&A Web App with Notifications

A lightweight Q&A forum built with Flask, featuring user auth, posts, comments, voting, categories, profiles, notifications, and admin flagging/deletion.

## Features
- User registration/login/logout
- Post creation with images
- Comments and real-time voting
- Category filtering and search
- User profiles with karma and bio
- Notifications for comments
- Admin dashboard for flagged content
- Image uploads

## Quick Start
1. Clone the repo: `git clone <your-repo-url>`
2. Install deps: `pip install -r requirements.txt`
3. Copy env: `cp .env.example .env` and edit `SECRET_KEY`
4. Run: `python app.py`
5. Open http://localhost:5000
6. Demo login: admin/password or demo/demopass

## Deployment
- Render/Heroku: Set `SECRET_KEY` env var.
- SQLite DB auto-creates; for prod, use PostgreSQL.

## Structure
- `app.py`: Main entry point
- `config.py`: App config
- `models.py`: SQLAlchemy models
- `utils.py`: Helper functions
- `templates.py`: Inline Jinja templates
- `auth.py`: Auth routes
- `routes.py`: Main routes
- `admin.py`: Admin routes

Built on November 12, 2025.
