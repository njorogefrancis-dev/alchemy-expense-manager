"""
routes/analytics.py — Deep analytics blueprint.
Trends, day-of-week heatmap, top expenses, spending velocity.
"""

from datetime import date, timedelta
from collections import defaultdict
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from models import db, Expense, Category

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
@login_required
def index():
    today = date.today()

    all_expenses = (
        Expense.query
        .filter_by(user_id=current_user.id)
        .order_by(Expense.date.asc())
        .all()
    )

    if not all_expenses:
        return render_template("analytics/index.html", has_data=False)

    # ── Day-of-week spending heatmap ───────────────────────────────────────────
    dow_totals  = defaultdict(float)
    dow_counts  = defaultdict(int)
    for e in all_expenses:
        dow = e.date.weekday()   # 0=Mon … 6=Sun
        dow_totals[dow] += e.amount_float()
        dow_counts[dow] += 1
    dow_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dow_data   = [round(dow_totals[i], 2) for i in range(7)]

    # ── Last 12 months trend ───────────────────────────────────────────────────
    monthly = defaultdict(float)
    for e in all_expenses:
        key = e.date.strftime("%Y-%m")
        monthly[key] += e.amount_float()
    sorted_months = sorted(monthly.items())[-12:]
    trend_labels  = [m[0] for m in sorted_months]
    trend_values  = [round(m[1], 2) for m in sorted_months]

    # ── Top 10 biggest single expenses ────────────────────────────────────────
    top10 = sorted(all_expenses, key=lambda e: e.amount, reverse=True)[:10]

    # ── Category cumulative (all time) ────────────────────────────────────────
    cat_agg = defaultdict(float)
    for e in all_expenses:
        cat_agg[e.category.name] += e.amount_float()
    cat_sorted = sorted(cat_agg.items(), key=lambda x: x[1], reverse=True)
    cat_labels = [c[0] for c in cat_sorted]
    cat_values = [round(c[1], 2) for c in cat_sorted]

    # ── Daily average (last 30 days) ───────────────────────────────────────────
    thirty_ago = today - timedelta(days=30)
    last30 = [e for e in all_expenses if e.date >= thirty_ago]
    daily_avg_30 = round(sum(e.amount_float() for e in last30) / 30, 2)

    # ── Spending streak: consecutive days with at least one expense ────────────
    expense_dates = sorted({e.date for e in all_expenses}, reverse=True)
    streak = 0
    if expense_dates:
        check = today
        for d in expense_dates:
            if d == check:
                streak += 1
                check -= timedelta(days=1)
            elif d < check:
                break

    # ── Week-over-week change ──────────────────────────────────────────────────
    this_week_start = today - timedelta(days=today.weekday())
    last_week_start = this_week_start - timedelta(days=7)
    this_week_total = sum(e.amount_float() for e in all_expenses
                          if this_week_start <= e.date <= today)
    last_week_total = sum(e.amount_float() for e in all_expenses
                          if last_week_start <= e.date < this_week_start)
    wow_change = 0
    if last_week_total > 0:
        wow_change = round((this_week_total - last_week_total) / last_week_total * 100, 1)

    # ── Cumulative spending line (last 30 days) ────────────────────────────────
    cumulative = []
    cum_labels  = []
    running = 0
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        day_total = sum(e.amount_float() for e in last30 if e.date == d)
        running += day_total
        cumulative.append(round(running, 2))
        cum_labels.append(d.strftime("%b %d"))

    return render_template(
        "analytics/index.html",
        has_data=True,
        dow_labels=dow_labels,
        dow_data=dow_data,
        trend_labels=trend_labels,
        trend_values=trend_values,
        top10=top10,
        cat_labels=cat_labels,
        cat_values=cat_values,
        daily_avg_30=daily_avg_30,
        streak=streak,
        wow_change=wow_change,
        this_week_total=this_week_total,
        last_week_total=last_week_total,
        cum_labels=cum_labels,
        cumulative=cumulative,
        total_expenses=len(all_expenses),
        grand_total=sum(e.amount_float() for e in all_expenses),
    )
