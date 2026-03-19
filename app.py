"""
app.py — Application factory and entry point for Expense Report Generator.
Run with:  python app.py
"""

import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import ActiveConfig
from models import db, User, seed_categories

# ── Extensions (initialised later in create_app) ──────────────────────────────
login_manager = LoginManager()
csrf          = CSRFProtect()


def create_app(config=None):
    """
    Application factory — creates and configures the Flask app.
    Pass a config object to override the default (useful for testing).
    """
    app = Flask(__name__)
    app.config.from_object(config or ActiveConfig)

    # Ensure export folder exists
    os.makedirs(app.config.get("EXPORT_FOLDER", "static/exports"), exist_ok=True)

    # ── Bind extensions ────────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # ── Flask-Login settings ───────────────────────────────────────────────────
    login_manager.login_view      = "auth.login"
    login_manager.login_message   = "Please log in to access that page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # ── Register blueprints ────────────────────────────────────────────────────
    from routes.auth      import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.expenses  import expenses_bp
    from routes.reports   import reports_bp
    from routes.budget    import budget_bp
    from routes.analytics import analytics_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(analytics_bp)

    # Root redirect — always show register first, then login once account exists
    @app.route("/")
    def root():
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.register"))

    # ── Create tables & seed data ─────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        seed_categories()

    # ── Template filters ───────────────────────────────────────────────────────
    @app.template_filter("currency")
    def currency_filter(value):
        """Format a number as KSh 1,234.56"""
        try:
            return f"KSh {float(value):,.2f}"
        except (ValueError, TypeError):
            return "KSh 0.00"

    @app.template_filter("dateformat")
    def dateformat_filter(value, fmt="%b %d, %Y"):
        """Format a date object."""
        try:
            return value.strftime(fmt)
        except AttributeError:
            return str(value)

    return app


# ── Run ────────────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
