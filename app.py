import datetime as dt

import streamlit as st
from supabase import Client, create_client

st.set_page_config(page_title="BookBorrow 🏠📚", page_icon="📚", layout="wide")


@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])


try:
    supabase = get_supabase()
except Exception:
    st.error(
        "🔧 Can't connect to Supabase. Add your project URL and anon key to "
        "`.streamlit/secrets.toml` (see `secrets.toml.example`) and restart the app."
    )
    st.stop()


def load_kids() -> list[dict]:
    res = supabase.table("kids").select("id, name, apartment_no").order("name").execute()
    return res.data


def load_books() -> list[dict]:
    res = (
        supabase.table("books")
        .select("id, title, author, status, borrowed_by, loan_date")
        .order("title")
        .execute()
    )
    return res.data


def borrow_book(book_id: str, kid_id: str, loan_date: dt.date) -> None:
    supabase.table("books").update(
        {"status": "Borrowed", "borrowed_by": kid_id, "loan_date": loan_date.isoformat()}
    ).eq("id", book_id).execute()


def return_book(book_id: str) -> None:
    supabase.table("books").update(
        {"status": "Available", "borrowed_by": None, "loan_date": None}
    ).eq("id", book_id).execute()


kids = load_kids()
books = load_books()
kid_names = {k["id"]: k for k in kids}
available = [b for b in books if b["status"] == "Available"]
borrowed = [b for b in books if b["status"] == "Borrowed"]

st.title("🏠📚 BookBorrow")
st.caption("Our apartment's little library — borrow a book, read it, bring it back!")

# ---------------- Sidebar: add kids & books ----------------
with st.sidebar:
    st.header("➕ Add to the library")

    with st.expander("🧒 Add a kid"):
        with st.form("add_kid_form", clear_on_submit=True):
            kid_name = st.text_input("Name")
            kid_apt = st.text_input("Apartment no.")
            if st.form_submit_button("Add kid", use_container_width=True):
                if kid_name.strip() and kid_apt.strip():
                    supabase.table("kids").insert(
                        {"name": kid_name.strip(), "apartment_no": kid_apt.strip()}
                    ).execute()
                    st.success(f"Welcome, {kid_name.strip()}! 🎈")
                    st.rerun()
                else:
                    st.warning("Please fill in both name and apartment.")

    with st.expander("📖 Add a book"):
        with st.form("add_book_form", clear_on_submit=True):
            book_title = st.text_input("Title")
            book_author = st.text_input("Author")
            if st.form_submit_button("Add book", use_container_width=True):
                if book_title.strip():
                    supabase.table("books").insert(
                        {"title": book_title.strip(), "author": book_author.strip() or None}
                    ).execute()
                    st.success(f"Added “{book_title.strip()}” to the shelf! 📚")
                    st.rerun()
                else:
                    st.warning("A book needs at least a title.")

    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("📚 Books", len(books))
    c2.metric("🧒 Kids", len(kids))

# ---------------- Main screens ----------------
tab_browse, tab_borrow, tab_return = st.tabs(
    ["📚 Available Books", "🎒 Borrow a Book", "🔁 Return a Book"]
)

# Screen 1: view all available books
with tab_browse:
    st.header("Books on the shelf right now")
    if not available:
        st.info("All the books are out on adventures! Check back soon. 🌍")
    else:
        cols = st.columns(3)
        for i, book in enumerate(available):
            with cols[i % 3]:
                with st.container(border=True):
                    st.subheader(f"📖 {book['title']}")
                    st.write(f"✏️ {book['author'] or 'Unknown author'}")
                    st.badge("✅ Available")

# Screen 2: borrow a book
with tab_borrow:
    st.header("Borrow a book")
    if not kids:
        st.warning("No kids registered yet — ask a grown-up to add your name in the sidebar! ⬅️")
    elif not available:
        st.info("No books available to borrow right now. 😢")
    else:
        with st.form("borrow_form"):
            kid = st.selectbox(
                "Who are you? 🧒",
                kids,
                format_func=lambda k: f"{k['name']} (Apt {k['apartment_no']})",
            )
            book = st.selectbox(
                "Pick a book 📖",
                available,
                format_func=lambda b: f"{b['title']} — {b['author'] or 'Unknown'}",
            )
            loan_date = st.date_input("Loan date 📅", value=dt.date.today())
            if st.form_submit_button("Borrow it! 🎉", use_container_width=True):
                borrow_book(book["id"], kid["id"], loan_date)
                st.balloons()
                st.success(f"Enjoy “{book['title']}”, {kid['name']}! Happy reading! 🎈")
                st.rerun()

# Screen 3: return a book
with tab_return:
    st.header("Return a book")
    if not borrowed:
        st.info("Nothing to return — every book is home safe. 🏠")
    else:
        with st.form("return_form"):
            book = st.selectbox(
                "Which book are you bringing back? 📕",
                borrowed,
                format_func=lambda b: (
                    f"{b['title']} — borrowed by "
                    f"{kid_names.get(b['borrowed_by'], {}).get('name', '?')}"
                    + (f" on {b['loan_date']}" if b["loan_date"] else "")
                ),
            )
            if st.form_submit_button("Return it! 🔁", use_container_width=True):
                return_book(book["id"])
                st.balloons()
                st.success(f"Thank you for returning “{book['title']}”! 🌟")
                st.rerun()
