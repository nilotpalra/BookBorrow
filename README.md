# BookBorrow

A community book-lending app for Dream Residency Manor.
Built with **Streamlit** (UI) and **Supabase** (PostgreSQL database).

## Screens

1. **Catalogue** — browse available books (no sign-in needed).
2. **Add Books** — type or paste books into a table; they're owned by your flat.
3. **Borrow** — pick a book from *another* flat (you can't borrow your own);
   first-timers add their name. Reserving shows a 6-character handover code.
4. **Return** — bring back a book your flat borrowed. Starting a return shows a
   6-character return code; the book stays on loan until the owner confirms.
5. **My Books** — the lender enters the borrower's handover code here (in their
   own account) to complete the borrowing, enters the return code to confirm a
   book is back, and tracks their flat's books.

Changing the library (adding books, borrowing, returning, setting names) needs a
per-flat login: the user ID is your flat number (e.g. `4-Lavender-1C`) and the
password is `<block#>-<unit>-<suffix>` (e.g. `4-1C-drmLibrary@26`). The shared
`password_suffix` lives under `[auth]` in `.streamlit/secrets.toml`. It's a
simple gate, not real security.

## Setup

### 1. Create the database

1. Create a free project at [supabase.com](https://supabase.com).
2. Open **SQL Editor → New query**, paste the contents of [schema.sql](schema.sql), and **Run**.
   It creates the `kids` and `books` tables (with a foreign key from
   `books.borrowed_by` → `kids.id`) plus a few sample rows you can delete.

   To seed one `kids` row per flat from the member CSV (name left `NULL` until
   the child registers), run `python setup_kids.py` — it wipes existing
   kids/books data first.

### 2. Add your credentials

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in
your **Project URL** and **anon public key** from
*Supabase → Project Settings → Data API / API Keys*.

```toml
[supabase]
url = "https://your-project-ref.supabase.co"
key = "your-anon-public-key"

[auth]
password_suffix = "change-me"   # per-flat login: password is "<block#>-<unit>-<suffix>"
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
| `books` | `id` (uuid, PK), `title`, `author`, `status` (`Available`/`Reserved`/`Borrowed`/`Returning`), `borrowed_by` (FK → `kids.id`, `ON DELETE SET NULL`), `owner_id` (FK → `kids.id`, `ON DELETE SET NULL`), `loan_date`, `borrow_code` (handover code for both borrowing and returning), `created_at` |
