# 💰 Alchemy — Expense Report Generator

A full-stack personal finance web app built with Flask, SQLite, and Bootstrap 5.
Created by **Francis Njoroge** — njorogefrancis.dev@gmail.com

---

## 🚀 Quick Start

```bash
# 1. Unzip and enter the project
unzip expense_app_final.zip
cd expense_app

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python app.py
```

Open **http://127.0.0.1:5000** — you'll land on the registration page.
Create your account and start tracking immediately. No demo data, no setup scripts needed.

---

## ✨ Features

### 🔐 Authentication
- Register, login, logout
- bcrypt password hashing
- Session management (8-hour sessions)
- Profile page — update username, email, or password

### 💸 Expense Management
- Add, edit, delete expenses
- Fields: date, category, description, amount (KSh)
- Filter by category, sort by date or amount
- Paginated list view (15 per page)
- **Quick Add** panel directly on the dashboard

### 📥 Import & Export
- **Import CSV** — bulk upload expenses from a spreadsheet
  - Drag & drop or file picker
  - Accepts: `date, category, description, amount` columns
  - Date formats: `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`
  - Auto-creates unknown categories
  - Download a sample CSV template from the import page
- **Export CSV** — download filtered expenses from the Reports page

### 🎯 Budgets
- Set monthly spending limits per category
- Visual progress bars (green → yellow → red)
- Over-budget and near-limit alerts on the dashboard
- Navigate between months with arrow controls

### 📊 Dashboard
- Greeting based on time of day
- 4 KPI cards: Total Spent, This Month, Entries, Avg Expense
- Monthly bar chart (Chart.js)
- Category doughnut chart
- Budget progress for the current month
- Recent 10 transactions
- Quick Add form

### 📈 Analytics
- 12-month spending trend line chart
- Day-of-week spending heatmap
- 30-day cumulative spending curve
- All-time category horizontal bar chart
- Top 10 biggest single expenses
- Week-over-week % change
- Spending streak (consecutive days with activity)

### 📋 Reports
- Filter by custom date range
- Quick presets: This Month, Last Month, Last 90 Days, This Year
- Summary stats: total, count, average, highest expense
- Category breakdown with progress bars
- Full transaction table
- Export to CSV

### 🌙 Dark Mode
- Toggle in the top navbar
- Preference saved in browser (localStorage)

---

## 🗂 Project Structure

```
expense_app/
├── app.py              ← Application factory + entry point
├── config.py           ← Dev / Prod / Test configuration
├── models.py           ← SQLAlchemy models: User, Category, Expense, Budget
├── requirements.txt
├── routes/
│   ├── auth.py         ← Register, Login, Logout, Profile
│   ├── dashboard.py    ← Main dashboard with charts & budget alerts
│   ├── expenses.py     ← CRUD, CSV import, sample download
│   ├── reports.py      ← Date-range reports + CSV export
│   ├── budget.py       ← Monthly budget management
│   └── analytics.py    ← Deep spending analytics
├── templates/
│   ├── base.html
│   ├── auth/           ← login, register, profile
│   ├── dashboard/      ← index
│   ├── expenses/       ← list, form, import, categories
│   ├── reports/        ← index
│   ├── budget/         ← index
│   └── analytics/      ← index
└── static/
    ├── css/app.css     ← Full custom design system + dark mode
    └── js/app.js       ← Dark mode toggle, password strength, helpers
```

---

## 🗃 Database Schema

```
users
  id, username (unique), email (unique), password_hash, created_at

categories
  id, name (unique)

expenses
  id, user_id (FK→users), category_id (FK→categories),
  description, amount (DECIMAL 10,2), date, created_at, updated_at

budgets
  id, user_id (FK→users), category_id (FK→categories),
  amount, month, year, created_at
  UNIQUE (user_id, category_id, month, year)
```

The database (`expense_tracker.db`) and default categories are created automatically on first run.

**Default categories seeded on startup:**
Food & Dining, Transportation, Housing & Utilities, Healthcare,
Entertainment, Shopping, Education, Travel, Personal Care, Miscellaneous

---

## 📥 CSV Import Format

Your CSV file must include these 4 columns (header row required, column order doesn't matter):

| Column | Format | Example |
|---|---|---|
| `date` | YYYY-MM-DD or DD/MM/YYYY | `2025-03-15` |
| `category` | Any text | `Food & Dining` |
| `description` | Any text (max 255 chars) | `Naivas groceries` |
| `amount` | Plain number | `3850.00` |

- Currency symbols (`KSh`, `$`) are stripped automatically
- Unknown categories are created on import
- Rows with invalid dates or amounts are skipped
- Download a ready-to-fill template from **Expenses → Import CSV**

---

## 🔒 Security

| Measure | Implementation |
|---|---|
| Password hashing | bcrypt via Werkzeug |
| CSRF protection | Flask-WTF on all POST forms |
| SQL injection | SQLAlchemy ORM (no raw SQL) |
| Ownership checks | Users can only access their own data |
| Session hardening | HttpOnly cookies, SameSite=Lax |
| Input validation | Server-side on every form |

---

## ⚙️ Configuration

All settings live in `config.py`. Override via environment variables for production:

```bash
export SECRET_KEY="your-random-secret-key-here"
export FLASK_ENV="production"
```

| Setting | Default |
|---|---|
| `SECRET_KEY` | `dev-secret-change-in-production` |
| `SQLALCHEMY_DATABASE_URI` | `sqlite:///expense_tracker.db` |
| `PERMANENT_SESSION_LIFETIME` | 8 hours |

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| Flask | 3.0+ | Web framework |
| Flask-SQLAlchemy | 3.1+ | ORM integration |
| Flask-Login | 0.6+ | Session management |
| Flask-WTF | 1.2+ | CSRF protection |
| Werkzeug | 3.0+ | Password hashing |
| SQLAlchemy | 2.0+ | Database ORM |

Frontend (via CDN — no build step):
- Bootstrap 5.3
- Bootstrap Icons 1.11
- Chart.js 4.4
- Google Fonts: Sora + DM Mono
