"""
models.py — SQLAlchemy ORM models for Expense Report Generator.
Defines Users, Categories, and Expenses tables with relationships.
"""

from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ──────────────────────────────────────────────────────────────────────────────
# User Model
# ──────────────────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    """
    Represents a registered user.
    UserMixin provides: is_authenticated, is_active, is_anonymous, get_id()
    """
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # One-to-many: a user owns many expenses
    expenses = db.relationship("Expense", backref="owner", lazy="dynamic",
                               cascade="all, delete-orphan")

    # ── Password helpers ──────────────────────────────────────────────────────
    def set_password(self, plaintext: str) -> None:
        """Hash and store a password (bcrypt via werkzeug)."""
        self.password_hash = generate_password_hash(plaintext)

    def check_password(self, plaintext: str) -> bool:
        """Return True if plaintext matches the stored hash."""
        return check_password_hash(self.password_hash, plaintext)

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"


# ──────────────────────────────────────────────────────────────────────────────
# Category Model
# ──────────────────────────────────────────────────────────────────────────────
class Category(db.Model):
    """
    Expense categories (e.g. Food, Travel, Utilities).
    Global — shared across all users.  Seeded on first run.
    """
    __tablename__ = "categories"

    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)

    # One-to-many: a category can appear on many expenses
    expenses = db.relationship("Expense", backref="category", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Category {self.name!r}>"


# ──────────────────────────────────────────────────────────────────────────────
# Expense Model
# ──────────────────────────────────────────────────────────────────────────────
class Expense(db.Model):
    """
    A single expense entry belonging to a user.
    Links to a Category via FK; soft-validation done at the route level.
    """
    __tablename__ = "expenses"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount      = db.Column(db.Numeric(10, 2), nullable=False)
    date        = db.Column(db.Date, nullable=False, default=date.today)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def amount_float(self) -> float:
        """Return amount as a plain Python float (safe for JSON / templates)."""
        return float(self.amount)

    def to_dict(self) -> dict:
        """Serialize expense to a dictionary (useful for CSV/JSON export)."""
        return {
            "id":          self.id,
            "date":        self.date.strftime("%Y-%m-%d"),
            "category":    self.category.name if self.category else "—",
            "description": self.description,
            "amount":      self.amount_float(),
        }

    def __repr__(self) -> str:
        return f"<Expense {self.id} ${self.amount}>"


# ──────────────────────────────────────────────────────────────────────────────
# Default seed data
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_CATEGORIES = [
    "Food & Dining",
    "Transportation",
    "Housing & Utilities",
    "Healthcare",
    "Entertainment",
    "Shopping",
    "Education",
    "Travel",
    "Personal Care",
    "Miscellaneous",
]


def seed_categories() -> None:
    """Insert default categories if the table is empty."""
    if Category.query.count() == 0:
        for name in DEFAULT_CATEGORIES:
            db.session.add(Category(name=name))
        db.session.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Budget Model
# ──────────────────────────────────────────────────────────────────────────────
class Budget(db.Model):
    """
    Monthly spending limit per category per user.
    e.g. user 1 wants to spend max KSh 5,000 on Food in March 2025.
    """
    __tablename__ = "budgets"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    amount      = db.Column(db.Numeric(10, 2), nullable=False)
    month       = db.Column(db.Integer, nullable=False)   # 1-12
    year        = db.Column(db.Integer, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    category = db.relationship("Category")

    __table_args__ = (
        db.UniqueConstraint("user_id", "category_id", "month", "year",
                            name="uq_budget_user_cat_month"),
    )

    def amount_float(self) -> float:
        return float(self.amount)

    def __repr__(self):
        return f"<Budget {self.category_id} {self.month}/{self.year} {self.amount}>"
