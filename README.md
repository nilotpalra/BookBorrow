# 🏠📚 BookBorrow

A tiny, kid-friendly book-borrowing app for the apartment building.
Built with **Streamlit** (UI) and **Supabase** (PostgreSQL database).

## Screens

1. **📚 Available Books** — browse everything on the shelf.
2. **🎒 Borrow a Book** — a kid picks their name and a book, and it's theirs.
3. **🔁 Return a Book** — bring a book back to the shelf.

Kids and books can be added from the sidebar (➕).

## Setup

### 1. Create the database

1. Create a free project at [supabase.com](https://supabase.com).
2. Open **SQL Editor → New query**, paste the contents of [schema.sql](schema.sql), and **Run**.
   It creates the `kids` and `books` tables (with a foreign key from
   `books.borrowed_by` → `kids.id`) plus a few sample rows you can delete.

### 2. Add your credentials

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in
your **Project URL** and **anon public key** from
*Supabase → Project Settings → Data API / API Keys*.

```toml
[supabase]
url = "https://your-project-ref.supabase.co"
key = "your-anon-public-key"
```

### 3. Install and run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The app opens at http://localhost:8501 — share it on the apartment Wi-Fi with
`streamlit run app.py --server.address 0.0.0.0`.

## Schema

| Table  | Columns |
|--------|---------|
| `kids`  | `id` (uuid, PK), `name`, `apartment_no`, `created_at` |
| `books` | `id` (uuid, PK), `title`, `author`, `status` (`Available`/`Borrowed`), `borrowed_by` (FK → `kids.id`, `ON DELETE SET NULL`), `loan_date`, `created_at` |
