"""
routes/expenses.py — Expense CRUD blueprint.
Handles: list, add, edit, delete expenses and manage categories.
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, Response
from flask_login import login_required, current_user
from models import db, Expense, Category

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_amount(raw: str):
    """Return Decimal or None if invalid."""
    try:
        val = Decimal(raw.replace(",", "").strip())
        if val <= 0:
            return None
        return val
    except (InvalidOperation, AttributeError):
        return None


def _validate_expense(form):
    """Validate expense form fields; return (errors, data_dict)."""
    errors = []

    description = form.get("description", "").strip()
    raw_amount  = form.get("amount", "")
    raw_date    = form.get("date", "")
    category_id = form.get("category_id", "")

    if not description or len(description) > 255:
        errors.append("Description is required (max 255 chars).")

    amount = _parse_amount(raw_amount)
    if amount is None:
        errors.append("Amount must be a positive number.")

    try:
        exp_date = date.fromisoformat(raw_date)
        if exp_date > date.today():
            errors.append("Date cannot be in the future.")
    except (ValueError, TypeError):
        errors.append("Invalid date format.")
        exp_date = None

    if not category_id or not db.session.get(Category, category_id):
        errors.append("Please select a valid category.")

    data = {
        "description": description,
        "amount":      amount,
        "date":        exp_date,
        "category_id": int(category_id) if category_id else None,
    }
    return errors, data


# ── List expenses ──────────────────────────────────────────────────────────────

@expenses_bp.route("/")
@login_required
def list_expenses():
    """Paginated list of all user expenses with optional filters."""
    page     = request.args.get("page", 1, type=int)
    cat_id   = request.args.get("category_id", "", type=str)
    sort     = request.args.get("sort", "date_desc")

    query = Expense.query.filter_by(user_id=current_user.id)

    if cat_id:
        query = query.filter_by(category_id=cat_id)

    sort_map = {
        "date_desc":   Expense.date.desc(),
        "date_asc":    Expense.date.asc(),
        "amount_desc": Expense.amount.desc(),
        "amount_asc":  Expense.amount.asc(),
    }
    query = query.order_by(sort_map.get(sort, Expense.date.desc()))

    pagination = query.paginate(page=page, per_page=15, error_out=False)
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "expenses/list.html",
        pagination=pagination,
        expenses=pagination.items,
        categories=categories,
        selected_cat=cat_id,
        sort=sort,
    )


# ── Add expense ────────────────────────────────────────────────────────────────

@expenses_bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add a new expense."""
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        errors, data = _validate_expense(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("expenses/form.html",
                                   categories=categories,
                                   form=request.form,
                                   action="Add")

        expense = Expense(
            user_id     = current_user.id,
            description = data["description"],
            amount      = data["amount"],
            date        = data["date"],
            category_id = data["category_id"],
        )
        db.session.add(expense)
        db.session.commit()
        flash("Expense added successfully!", "success")
        return redirect(url_for("expenses.list_expenses"))

    # Pre-fill date with today
    form_defaults = {"date": date.today().isoformat()}
    return render_template("expenses/form.html",
                           categories=categories,
                           form=form_defaults,
                           action="Add")


# ── Edit expense ───────────────────────────────────────────────────────────────

@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit(expense_id):
    """Edit an existing expense (owner-only)."""
    expense = db.get_or_404(Expense, expense_id)
    if expense.user_id != current_user.id:
        abort(403)

    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        errors, data = _validate_expense(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("expenses/form.html",
                                   categories=categories,
                                   form=request.form,
                                   action="Edit",
                                   expense=expense)

        expense.description = data["description"]
        expense.amount      = data["amount"]
        expense.date        = data["date"]
        expense.category_id = data["category_id"]
        db.session.commit()
        flash("Expense updated.", "success")
        return redirect(url_for("expenses.list_expenses"))

    # Pre-fill form with existing data
    form_defaults = {
        "description": expense.description,
        "amount":      str(expense.amount),
        "date":        expense.date.isoformat(),
        "category_id": str(expense.category_id),
    }
    return render_template("expenses/form.html",
                           categories=categories,
                           form=form_defaults,
                           action="Edit",
                           expense=expense)


# ── Delete expense ─────────────────────────────────────────────────────────────

@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete(expense_id):
    """Delete an expense (owner-only, POST only for CSRF safety)."""
    expense = db.get_or_404(Expense, expense_id)
    if expense.user_id != current_user.id:
        abort(403)

    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.", "warning")
    return redirect(url_for("expenses.list_expenses"))


# ── Category management ────────────────────────────────────────────────────────

@expenses_bp.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    """Add new custom categories."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name or len(name) > 60:
            flash("Category name must be 1–60 characters.", "danger")
        elif Category.query.filter_by(name=name).first():
            flash("That category already exists.", "warning")
        else:
            db.session.add(Category(name=name))
            db.session.commit()
            flash(f'Category "{name}" added.', "success")
        return redirect(url_for("expenses.categories"))

    all_cats = Category.query.order_by(Category.name).all()
    return render_template("expenses/categories.html", categories=all_cats)


# ── CSV Import ────────────────────────────────────────────────────────────────

import csv
import io

ALLOWED_EXTENSIONS = {"csv"}

def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@expenses_bp.route("/import", methods=["GET", "POST"])
@login_required
def import_csv():
    """
    Import expenses from a CSV file.
    Expected columns (in any order, case-insensitive):
      date, category, description, amount
    Date format: YYYY-MM-DD  (or DD/MM/YYYY  or DD-MM-YYYY)
    Amount: plain number, e.g. 1500 or 1500.50  (no currency symbols)
    """
    categories = Category.query.order_by(Category.name).all()
    cat_map    = {c.name.lower(): c for c in categories}   # name → Category

    if request.method == "POST":
        file = request.files.get("csv_file")

        if not file or file.filename == "":
            flash("Please choose a CSV file to upload.", "danger")
            return redirect(url_for("expenses.import_csv"))

        if not _allowed_file(file.filename):
            flash("Only .csv files are supported.", "danger")
            return redirect(url_for("expenses.import_csv"))

        # Read file into memory
        try:
            stream  = io.StringIO(file.read().decode("utf-8-sig"))  # handle BOM
        except UnicodeDecodeError:
            flash("Could not read file — make sure it is saved as UTF-8.", "danger")
            return redirect(url_for("expenses.import_csv"))

        reader = csv.DictReader(stream)

        # Normalise header names (strip spaces, lowercase)
        if reader.fieldnames is None:
            flash("CSV file appears to be empty.", "danger")
            return redirect(url_for("expenses.import_csv"))

        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]

        required = {"date", "category", "description", "amount"}
        missing  = required - set(reader.fieldnames)
        if missing:
            flash(f"Missing required columns: {', '.join(sorted(missing))}. "
                  f"Expected: date, category, description, amount", "danger")
            return redirect(url_for("expenses.import_csv"))

        imported  = 0
        skipped   = 0
        new_cats  = []
        rows_to_add = []

        for i, row in enumerate(reader, start=2):   # row 1 = header
            # ── Parse date ────────────────────────────────────────────────────
            raw_date = row.get("date", "").strip()
            exp_date = None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
                try:
                    from datetime import datetime as _dt
                    exp_date = _dt.strptime(raw_date, fmt).date()
                    break
                except ValueError:
                    continue
            if exp_date is None:
                skipped += 1
                continue
            if exp_date > date.today():
                skipped += 1
                continue

            # ── Parse amount ──────────────────────────────────────────────────
            raw_amount = row.get("amount", "").strip().replace(",", "").lstrip("KSh").lstrip("$").strip()
            amount = _parse_amount(raw_amount)
            if amount is None:
                skipped += 1
                continue

            # ── Parse description ─────────────────────────────────────────────
            description = row.get("description", "").strip()[:255]
            if not description:
                skipped += 1
                continue

            # ── Resolve / auto-create category ────────────────────────────────
            cat_name = row.get("category", "").strip()
            cat_key  = cat_name.lower()
            if cat_key not in cat_map:
                # Auto-create unknown categories
                new_cat = Category(name=cat_name if cat_name else "Imported")
                db.session.add(new_cat)
                db.session.flush()   # get the new id immediately
                cat_map[cat_key] = new_cat
                new_cats.append(cat_name or "Imported")

            rows_to_add.append(Expense(
                user_id     = current_user.id,
                category_id = cat_map[cat_key].id,
                description = description,
                amount      = amount,
                date        = exp_date,
            ))
            imported += 1

        # ── Commit all at once ────────────────────────────────────────────────
        if rows_to_add:
            db.session.add_all(rows_to_add)
            db.session.commit()

        msg = f"Successfully imported {imported} expense(s)."
        if skipped:
            msg += f" {skipped} row(s) were skipped (invalid data)."
        if new_cats:
            msg += f" New categories created: {', '.join(set(new_cats))}."

        flash(msg, "success" if imported else "warning")
        return redirect(url_for("expenses.list_expenses"))

    # GET — show import form
    return render_template("expenses/import.html", categories=categories)


@expenses_bp.route("/import/sample")
@login_required
def sample_csv():
    """Serve a downloadable sample CSV template."""
    sample = (
        "date,category,description,amount\n"
        "2025-03-01,Food & Dining,Naivas groceries,3850.00\n"
        "2025-03-05,Transportation,Uber to JKIA,1800.00\n"
        "2025-03-10,Housing & Utilities,Kenya Power bill,2300.00\n"
        "2025-03-15,Entertainment,Netflix subscription,1100.00\n"
        "2025-03-20,Shopping,Zara Garden City,7500.00\n"
    )
    return Response(
        sample,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sample_expenses.csv"},
    )
