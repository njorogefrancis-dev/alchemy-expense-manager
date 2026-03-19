"""
routes/auth.py — Authentication blueprint.
Handles: register, login, logout, profile.
"""

import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Expense
from sqlalchemy import func
from datetime import date

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _validate_registration(username, email, password, confirm):
    errors = []
    if not username or len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    if not EMAIL_RE.match(email):
        errors.append("Enter a valid email address.")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if password != confirm:
        errors.append("Passwords do not match.")
    return errors


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        errors = _validate_registration(username, email, password, confirm)

        if not errors:
            if User.query.filter_by(username=username).first():
                errors.append("Username is already taken.")
            if User.query.filter_by(email=email).first():
                errors.append("Email is already registered.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html", username=username, email=email)

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password   = request.form.get("password", "")
        remember   = bool(request.form.get("remember"))

        user = (User.query.filter_by(username=identifier).first() or
                User.query.filter_by(email=identifier).first())

        if user and user.check_password(password):
            login_user(user, remember=remember)
            session.permanent = True
            next_page = request.args.get("next")
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(next_page or url_for("dashboard.index"))

        flash("Invalid credentials. Please try again.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """User profile — change display name, email, or password."""
    today = date.today()

    total_expenses = current_user.expenses.count()
    total_spent = db.session.query(func.sum(Expense.amount))\
        .filter_by(user_id=current_user.id).scalar() or 0
    this_month = current_user.expenses.filter(
        Expense.date >= today.replace(day=1)
    ).count()
    member_since = current_user.created_at.strftime("%B %Y")

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_info":
            new_username = request.form.get("username", "").strip()
            new_email    = request.form.get("email", "").strip().lower()

            if len(new_username) < 3:
                flash("Username must be at least 3 characters.", "danger")
            elif new_username != current_user.username and User.query.filter_by(username=new_username).first():
                flash("Username already taken.", "danger")
            elif not EMAIL_RE.match(new_email):
                flash("Invalid email address.", "danger")
            elif new_email != current_user.email and User.query.filter_by(email=new_email).first():
                flash("Email already in use.", "danger")
            else:
                current_user.username = new_username
                current_user.email    = new_email
                db.session.commit()
                flash("Profile updated successfully.", "success")

        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw     = request.form.get("new_password", "")
            confirm_pw = request.form.get("confirm_password", "")

            if not current_user.check_password(current_pw):
                flash("Current password is incorrect.", "danger")
            elif len(new_pw) < 8:
                flash("New password must be at least 8 characters.", "danger")
            elif new_pw != confirm_pw:
                flash("New passwords do not match.", "danger")
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash("Password changed successfully.", "success")

        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html",
                           total_expenses=total_expenses,
                           total_spent=float(total_spent),
                           this_month=this_month,
                           member_since=member_since)
