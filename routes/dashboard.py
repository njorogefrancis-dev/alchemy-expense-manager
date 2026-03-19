"""
routes/dashboard.py — Dashboard blueprint.
Shows totals, category breakdown, recent transactions, budget alerts.
"""

from datetime import date, timedelta, datetime
from collections import defaultdict
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from models import db, Expense, Category, Budget

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    today = date.today()
    first_of_month = today.replace(day=1)

    # ── Totals ────────────────────────────────────────────────────────────────
    all_expenses = Expense.query.filter_by(user_id=current_user.id).all()
    total_all  = sum(e.amount_float() for e in all_expenses)

    month_expenses = [e for e in all_expenses if e.date >= first_of_month]
    total_month    = sum(e.amount_float() for e in month_expenses)

    expense_count = len(all_expenses)
    avg_expense   = (total_all / expense_count) if expense_count else 0

    # ── Category breakdown (all time) ─────────────────────────────────────────
    cat_data = (
        db.session.query(Category.name, func.sum(Expense.amount))
        .join(Expense, Expense.category_id == Category.id)
        .filter(Expense.user_id == current_user.id)
        .group_by(Category.name)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )
    category_labels = [r[0] for r in cat_data]
    category_totals = [float(r[1]) for r in cat_data]

    # ── Monthly summary (last 6 months) ───────────────────────────────────────
    monthly = defaultdict(float)
    for e in all_expenses:
        monthly[e.date.strftime("%b %Y")] += e.amount_float()

    from datetime import datetime
    def month_key(item):
        try:
            return datetime.strptime(item[0], "%b %Y")
        except ValueError:
            return datetime.min

    sorted_months = sorted(monthly.items(), key=month_key)[-6:]
    month_labels  = [m[0] for m in sorted_months]
    month_totals  = [round(m[1], 2) for m in sorted_months]

    # ── Recent 10 ─────────────────────────────────────────────────────────────
    recent = (
        Expense.query.filter_by(user_id=current_user.id)
        .order_by(Expense.date.desc(), Expense.created_at.desc())
        .limit(10).all()
    )

    # ── Budget progress (current month) ───────────────────────────────────────
    budgets = (
        Budget.query.filter_by(user_id=current_user.id, month=today.month, year=today.year)
        .join(Category).order_by(Category.name).all()
    )

    spending_map = {}
    for e in month_expenses:
        spending_map[e.category_id] = spending_map.get(e.category_id, 0) + e.amount_float()

    budget_items = []
    for b in budgets:
        spent = spending_map.get(b.category_id, 0)
        limit = b.amount_float()
        pct   = min((spent / limit * 100) if limit > 0 else 0, 100)
        budget_items.append({
            "budget":    b,
            "spent":     spent,
            "limit":     limit,
            "pct":       round(pct, 1),
            "over":      spent > limit,
            "remaining": max(limit - spent, 0),
        })

    # ── Budget alerts ─────────────────────────────────────────────────────────
    budget_alerts = []
    for item in budget_items:
        name = item["budget"].category.name
        if item["over"]:
            budget_alerts.append({
                "type":    "danger",
                "icon":    "exclamation-triangle-fill",
                "message": f"⚠ You have exceeded your {name} budget by KSh {item['spent']-item['limit']:,.2f}!"
            })
        elif item["pct"] >= 90:
            budget_alerts.append({
                "type":    "warning",
                "icon":    "exclamation-circle-fill",
                "message": f"You have used {item['pct']}% of your {name} budget — only KSh {item['remaining']:,.2f} left."
            })

    # ── Categories for quick-add form ──────────────────────────────────────────
    categories = Category.query.order_by(Category.name).all()

    now_hour = datetime.now().hour
    return render_template(
        "dashboard/index.html",
        total_all=total_all,
        total_month=total_month,
        expense_count=expense_count,
        avg_expense=avg_expense,
        category_labels=category_labels,
        category_totals=category_totals,
        month_labels=month_labels,
        month_totals=month_totals,
        recent=recent,
        today=today,
        budget_items=budget_items,
        budget_alerts=budget_alerts,
        categories=categories,
        now_hour=now_hour,
    )
