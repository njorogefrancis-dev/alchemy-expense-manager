"""
routes/reports.py — Reports blueprint.
Handles: date-range filter, summary display, CSV export.
"""

import csv
import io
from datetime import date, datetime
from flask import (Blueprint, render_template, request, flash,
                   Response, stream_with_context)
from flask_login import login_required, current_user
from sqlalchemy import func
from models import db, Expense, Category

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def _parse_date(raw: str, fallback: date) -> date:
    """Parse ISO date string, return fallback on failure."""
    try:
        return date.fromisoformat(raw)
    except (ValueError, TypeError):
        return fallback


@reports_bp.route("/", methods=["GET"])
@login_required
def index():
    """Report page — filter by date range, show summary."""
    today      = date.today()
    first_month = today.replace(day=1)

    # Date range from query params (default: current month)
    start_date = _parse_date(request.args.get("start_date", ""), first_month)
    end_date   = _parse_date(request.args.get("end_date", ""), today)

    if start_date > end_date:
        flash("Start date must be before end date.", "warning")
        start_date, end_date = first_month, today

    # ── Fetch filtered expenses ────────────────────────────────────────────────
    expenses = (
        Expense.query
        .filter(
            Expense.user_id == current_user.id,
            Expense.date >= start_date,
            Expense.date <= end_date,
        )
        .order_by(Expense.date.desc())
        .all()
    )

    # ── Summary stats ──────────────────────────────────────────────────────────
    total = sum(e.amount_float() for e in expenses)
    count = len(expenses)
    avg   = (total / count) if count else 0

    # Category breakdown
    cat_summary = {}
    for e in expenses:
        cat_name = e.category.name
        cat_summary[cat_name] = cat_summary.get(cat_name, 0) + e.amount_float()
    cat_summary = dict(sorted(cat_summary.items(), key=lambda x: x[1], reverse=True))

    # Highest single expense
    max_expense = max(expenses, key=lambda e: e.amount, default=None)

    return render_template(
        "reports/index.html",
        expenses=expenses,
        start_date=start_date,
        end_date=end_date,
        total=total,
        count=count,
        avg=avg,
        cat_summary=cat_summary,
        max_expense=max_expense,
        cat_labels=list(cat_summary.keys()),
        cat_values=list(cat_summary.values()),
    )


@reports_bp.route("/export/csv")
@login_required
def export_csv():
    """Stream a CSV file for the filtered date range."""
    today      = date.today()
    first_month = today.replace(day=1)

    start_date = _parse_date(request.args.get("start_date", ""), first_month)
    end_date   = _parse_date(request.args.get("end_date", ""), today)

    expenses = (
        Expense.query
        .filter(
            Expense.user_id == current_user.id,
            Expense.date >= start_date,
            Expense.date <= end_date,
        )
        .order_by(Expense.date.asc())
        .all()
    )

    def generate():
        """Yield CSV rows as strings."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["#", "Date", "Category", "Description", "Amount (KSh)"])
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)

        for i, e in enumerate(expenses, 1):
            writer.writerow([
                i,
                e.date.strftime("%Y-%m-%d"),
                e.category.name,
                e.description,
                f"{e.amount_float():.2f}",
            ])
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

        # Footer totals
        writer.writerow([])
        writer.writerow(["", "", "", "TOTAL",
                          f"{sum(e.amount_float() for e in expenses):.2f}"])
        yield output.getvalue()

    filename = (f"expenses_{start_date.isoformat()}_to_{end_date.isoformat()}"
                f"_{current_user.username}.csv")

    return Response(
        stream_with_context(generate()),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
