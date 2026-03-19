"""
routes/budget.py — Budget management blueprint.
Set monthly spending limits per category, track progress.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func
from models import db, Budget, Category, Expense

budget_bp = Blueprint("budget", __name__, url_prefix="/budgets")


def _get_month_year():
    """Parse month/year from request args, defaulting to current month."""
    today = date.today()
    try:
        month = int(request.args.get("month", today.month))
        year  = int(request.args.get("year",  today.year))
        if not (1 <= month <= 12):
            month = today.month
    except ValueError:
        month, year = today.month, today.year
    return month, year


@budget_bp.route("/", methods=["GET"])
@login_required
def index():
    """Show budgets for selected month with progress bars."""
    month, year = _get_month_year()
    today = date.today()

    # All budgets for this user/month/year
    budgets = (
        Budget.query
        .filter_by(user_id=current_user.id, month=month, year=year)
        .join(Category)
        .order_by(Category.name)
        .all()
    )

    # Actual spending per category this month
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    spending_rows = (
        db.session.query(Expense.category_id, func.sum(Expense.amount))
        .filter(
            Expense.user_id == current_user.id,
            Expense.date >= start,
            Expense.date < end,
        )
        .group_by(Expense.category_id)
        .all()
    )
    spending_map = {row[0]: float(row[1]) for row in spending_rows}

    # Build rich budget items
    budget_items = []
    total_budget = 0
    total_spent  = 0
    for b in budgets:
        spent   = spending_map.get(b.category_id, 0)
        limit   = b.amount_float()
        pct     = min((spent / limit * 100) if limit > 0 else 0, 100)
        over    = spent > limit
        total_budget += limit
        total_spent  += spent
        budget_items.append({
            "budget":   b,
            "spent":    spent,
            "limit":    limit,
            "pct":      round(pct, 1),
            "over":     over,
            "remaining": max(limit - spent, 0),
        })

    # Month navigation helpers
    prev_month = month - 1 if month > 1 else 12
    prev_year  = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year  = year if month < 12 else year + 1

    categories = Category.query.order_by(Category.name).all()
    month_name = date(year, month, 1).strftime("%B %Y")

    return render_template(
        "budget/index.html",
        budget_items=budget_items,
        categories=categories,
        month=month, year=year,
        month_name=month_name,
        prev_month=prev_month, prev_year=prev_year,
        next_month=next_month, next_year=next_year,
        total_budget=total_budget,
        total_spent=total_spent,
        is_current=(month == today.month and year == today.year),
    )


@budget_bp.route("/set", methods=["POST"])
@login_required
def set_budget():
    """Create or update a budget entry."""
    try:
        category_id = int(request.form.get("category_id", 0))
        amount      = Decimal(request.form.get("amount", "0").replace(",", ""))
        month       = int(request.form.get("month", date.today().month))
        year        = int(request.form.get("year",  date.today().year))
    except (ValueError, InvalidOperation):
        flash("Invalid budget values.", "danger")
        return redirect(url_for("budget.index"))

    if amount <= 0:
        flash("Budget amount must be positive.", "danger")
        return redirect(url_for("budget.index", month=month, year=year))

    if not db.session.get(Category, category_id):
        flash("Invalid category.", "danger")
        return redirect(url_for("budget.index", month=month, year=year))

    existing = Budget.query.filter_by(
        user_id=current_user.id,
        category_id=category_id,
        month=month, year=year
    ).first()

    if existing:
        existing.amount = amount
        flash("Budget updated.", "success")
    else:
        db.session.add(Budget(
            user_id=current_user.id,
            category_id=category_id,
            amount=amount,
            month=month,
            year=year,
        ))
        flash("Budget set!", "success")

    db.session.commit()
    return redirect(url_for("budget.index", month=month, year=year))


@budget_bp.route("/<int:budget_id>/delete", methods=["POST"])
@login_required
def delete(budget_id):
    """Delete a budget entry."""
    b = db.get_or_404(Budget, budget_id)
    if b.user_id != current_user.id:
        flash("Not allowed.", "danger")
        return redirect(url_for("budget.index"))
    month, year = b.month, b.year
    db.session.delete(b)
    db.session.commit()
    flash("Budget removed.", "warning")
    return redirect(url_for("budget.index", month=month, year=year))
