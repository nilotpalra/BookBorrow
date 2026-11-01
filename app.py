import datetime as dt
import re
import secrets
import string
from pathlib import Path

import pandas as pd
import streamlit as st
from supabase import Client, create_client

st.set_page_config(page_title="BookBorrow", page_icon=":material/menu_book:", layout="wide")


@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])


try:
    supabase = get_supabase()
except Exception:
    st.error(
        "Cannot connect to Supabase. Add your project URL and anon key to "
        "`.streamlit/secrets.toml` (see `secrets.toml.example`) and restart the app.",
        icon=":material/cloud_off:",
    )
    st.stop()


# ---------------- Per-flat login ----------------
# User ID is the flat number, e.g. "4-Lavender-1C"; the password is derived
# from it as "<block#>-<unit>-<suffix>", e.g. "4-1C-drmLibrary@26".
def check_login(user_id: str, password: str) -> str | None:
    """Return the kids-table row id for the flat if login succeeds, else None."""
    auth = st.secrets.get("auth", {})
    suffix = auth.get("password_suffix", "drmLibrary@26")
    m = re.fullmatch(r"(\d+)-([A-Za-z]+)-([A-Za-z0-9]+)", user_id.strip())
    if not m:
        return None
    block_no, block_name, unit = m.groups()
    if password != f"{block_no}-{unit}-{suffix}":
        return None
    # the flat must actually exist in the kids table
    res = (
        supabase.table("kids")
        .select("id")
        .eq("apartment_no", f"{block_no}-{block_name} {unit}")
        .limit(1)
        .execute()
    )
    return res.data[0]["id"] if res.data else None


def render_login() -> None:
    if st.session_state.get("logged_in"):
        st.success(f"Signed in as **{st.session_state['flat']}**", icon=":material/check_circle:")
        if st.button("Sign out", icon=":material/logout:", use_container_width=True):
            for key in ("logged_in", "flat", "kid_id", "pending_loan"):
                st.session_state.pop(key, None)
            st.rerun()
        return
    with st.form("login_form"):
        user_id = st.text_input("User ID (your flat, e.g. 4-Lavender-1C)", icon=":material/apartment:")
        password = st.text_input("Password", type="password", icon=":material/lock:")
        if st.form_submit_button("Sign in", icon=":material/login:", use_container_width=True):
            kid_id = check_login(user_id, password) if user_id else None
            if kid_id:
                st.session_state["logged_in"] = True
                st.session_state["flat"] = user_id.strip()
                st.session_state["kid_id"] = kid_id
                st.rerun()
            else:
                st.error("Incorrect user ID or password.", icon=":material/error:")


def require_login() -> bool:
    if not st.session_state.get("logged_in"):
        st.info(
            "This action changes the library. Please sign in from the sidebar.",
            icon=":material/lock:",
        )
        return False
    return True


def load_kids() -> list[dict]:
    res = supabase.table("kids").select("id, name, apartment_no").order("apartment_no").execute()
    return res.data


def load_books() -> list[dict]:
    res = (
        supabase.table("books")
        .select("id, title, author, status, borrowed_by, loan_date, borrow_code, owner_id")
        .order("title")
        .execute()
    )
    return res.data


def new_handover_code() -> str:
    # 6 chars, no easily-confused 0/O or 1/I/L — simple but not guessable
    alphabet = string.ascii_uppercase.replace("O", "").replace("I", "").replace("L", "") + "23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


def reserve_book(book_id: str, kid_id: str, loan_date: dt.date, code: str) -> None:
    supabase.table("books").update(
        {
            "status": "Reserved",
            "borrowed_by": kid_id,
            "loan_date": loan_date.isoformat(),
            "borrow_code": code,
        }
    ).eq("id", book_id).execute()


def confirm_borrow(book_id: str) -> None:
    supabase.table("books").update({"status": "Borrowed", "borrow_code": None}).eq(
        "id", book_id
    ).execute()


def cancel_reservation(book_id: str) -> None:
    supabase.table("books").update(
        {"status": "Available", "borrowed_by": None, "loan_date": None, "borrow_code": None}
    ).eq("id", book_id).execute()


def initiate_return(book_id: str, code: str) -> None:
    supabase.table("books").update({"status": "Returning", "borrow_code": code}).eq(
        "id", book_id
    ).execute()


def confirm_return(book_id: str) -> None:
    supabase.table("books").update(
        {"status": "Available", "borrowed_by": None, "loan_date": None, "borrow_code": None}
    ).eq("id", book_id).execute()


def cancel_return(book_id: str) -> None:
    supabase.table("books").update({"status": "Borrowed", "borrow_code": None}).eq(
        "id", book_id
    ).execute()


def set_kid_name(kid_id: str, name: str) -> None:
    supabase.table("kids").update({"name": name}).eq("id", kid_id).execute()


def add_books(rows: list[dict]) -> None:
    supabase.table("books").insert(rows).execute()


def flat_of(kid_id: str | None) -> str:
    return kid_names.get(kid_id, {}).get("apartment_no", "?") if kid_id else "?"


def name_of(kid_id: str | None) -> str:
    return kid_names.get(kid_id, {}).get("name") or "?" if kid_id else "?"


kids = load_kids()
books = load_books()
kid_names = {k["id"]: k for k in kids}
available = [b for b in books if b["status"] == "Available"]
reserved = [b for b in books if b["status"] == "Reserved"]
borrowed = [b for b in books if b["status"] == "Borrowed"]
returning = [b for b in books if b["status"] == "Returning"]
my_kid = next((k for k in kids if k["id"] == st.session_state.get("kid_id")), None)

st.title("BookBorrow")
st.caption("Dream Residency Manor community library")
st.image(str(Path(__file__).parent / "AppImage.png"), width=600)

# ---------------- Sidebar: login & name registration ----------------
with st.sidebar:
    st.header("Account", divider=True)
    render_login()

    if st.session_state.get("logged_in") and my_kid:
        st.divider()
        with st.expander("Resident name", icon=":material/person:"):
            st.caption(f"Flat **{my_kid['apartment_no']}**")
            with st.form("set_name_form", clear_on_submit=True):
                new_name = st.text_input("Name", value=my_kid["name"] or "")
                if st.form_submit_button("Save", icon=":material/save:", use_container_width=True):
                    if new_name.strip():
                        set_kid_name(my_kid["id"], new_name.strip())
                        st.success("Name saved.", icon=":material/check_circle:")
                        st.rerun()
                    else:
                        st.warning("Please enter a name.", icon=":material/warning:")

    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Books", len(books), icon=":material/menu_book:")
    c2.metric("Flats", len(kids), icon=":material/apartment:")

# ---------------- Main screens ----------------
tab_browse, tab_add, tab_borrow, tab_return, tab_mine = st.tabs(
    [
        ":material/menu_book: Catalogue",
        ":material/library_add: Add Books",
        ":material/bookmark_add: Borrow",
        ":material/assignment_return: Return",
        ":material/shelves: My Books",
    ]
)

# Screen 1: view all available books
with tab_browse:
    st.header("Available books")
    if not available:
        st.info("No books are available at the moment.", icon=":material/info:")
    else:
        cols = st.columns(3)
        for i, book in enumerate(available):
            with cols[i % 3]:
                with st.container(border=True):
                    st.subheader(book["title"])
                    st.write(book["author"] or "Unknown author")
                    st.caption(f"Contributed by flat {flat_of(book.get('owner_id'))}")

# Screen 2: add books in bulk (tabular)
with tab_add:
    st.header("Add books")
    if require_login():
        st.caption("One row per book. Use the + control at the bottom of the table to add rows.")
        editor_version = st.session_state.setdefault("books_editor_version", 0)
        edited = st.data_editor(
            pd.DataFrame([{"title": "", "author": ""}]),
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "title": st.column_config.TextColumn("Title", required=True),
                "author": st.column_config.TextColumn("Author"),
            },
            key=f"books_editor_{editor_version}",
        )
        if st.button("Save books", type="primary", icon=":material/save:", use_container_width=True):
            rows = []
            for _, r in edited.iterrows():
                title = str(r["title"]).strip() if pd.notna(r["title"]) else ""
                author = str(r["author"]).strip() if pd.notna(r["author"]) else ""
                if title:
                    rows.append(
                        {"title": title, "author": author or None, "owner_id": my_kid["id"]}
                    )
            if not rows:
                st.warning("Add at least one title first.", icon=":material/warning:")
            else:
                add_books(rows)
                st.session_state["books_editor_version"] = editor_version + 1
                st.success(f"Added {len(rows)} book(s) to the catalogue.", icon=":material/check_circle:")
                st.rerun()

# Screen 3: borrow a book (two steps: reserve → lender confirms with handover code)
with tab_borrow:
    st.header("Borrow a book")
    if not require_login():
        pass
    elif not my_kid:
        st.warning("Your flat is not registered yet.", icon=":material/warning:")
    else:
        pending = st.session_state.get("pending_loan")
        if pending:
            # Step 2: the lender enters the code in their own login (My Books tab)
            st.subheader(f"Collect “{pending['title']}”")
            st.info(
                "Share this code with the resident handing over the book. They enter it "
                "in their own account, under the **My Books** tab, to complete the borrowing.",
                icon=":material/key:",
            )
            st.code(pending["code"], language=None)
            if st.button("Cancel reservation", icon=":material/cancel:", use_container_width=True):
                cancel_reservation(pending["book_id"])
                st.session_state.pop("pending_loan", None)
                st.rerun()
        else:
            borrowable = [b for b in available if b.get("owner_id") != my_kid["id"]]
            if not borrowable:
                st.info("No books from other flats are available to borrow at the moment.", icon=":material/info:")
            else:
                # Step 1: reserve — generates the handover code for the lender
                st.caption(f"Borrowing for flat **{my_kid['apartment_no']}**")
                with st.form("borrow_form"):
                    name = ""
                    if not my_kid["name"]:
                        name = st.text_input("Your name (first time only)", icon=":material/person:")
                    book = st.selectbox(
                        "Book",
                        borrowable,
                        format_func=lambda b: (
                            f"{b['title']} — {b['author'] or 'Unknown'} "
                            f"(flat {flat_of(b.get('owner_id'))})"
                        ),
                    )
                    loan_date = st.date_input("Loan date", value=dt.date.today())
                    if st.form_submit_button("Reserve book", icon=":material/bookmark_add:", use_container_width=True):
                        if not my_kid["name"] and not name.strip():
                            st.warning("Please enter your name so the lender knows who is borrowing.", icon=":material/warning:")
                        else:
                            if not my_kid["name"]:
                                set_kid_name(my_kid["id"], name.strip())
                                my_kid["name"] = name.strip()
                            code = new_handover_code()
                            reserve_book(book["id"], my_kid["id"], loan_date, code)
                            st.session_state["pending_loan"] = {
                                "book_id": book["id"],
                                "title": book["title"],
                                "code": code,
                            }
                            st.rerun()

# Screen 4: return a book (two steps: initiate → owner confirms with return code)
with tab_return:
    st.header("Return a book")
    if not require_login():
        pass
    else:
        my_borrowed = [b for b in borrowed if b["borrowed_by"] == my_kid["id"]]
        my_returning = [b for b in returning if b["borrowed_by"] == my_kid["id"]]
        if not my_borrowed and not my_returning:
            st.info("Your flat has no books on loan.", icon=":material/info:")
        else:
            for b in my_returning:
                # Step 2: the owner enters the code in their own login (My Books tab)
                st.subheader(f"Return “{b['title']}”")
                st.info(
                    "Share this code with the resident receiving the book. They enter it "
                    "in their own account, under the **My Books** tab, to complete the return.",
                    icon=":material/key:",
                )
                st.code(b["borrow_code"], language=None)
                if st.button("Cancel return", key=f"cancel_return_{b['id']}", icon=":material/cancel:", use_container_width=True):
                    cancel_return(b["id"])
                    st.rerun()
            if my_borrowed:
                # Step 1: initiate the return — generates the handover code for the owner
                with st.form("return_form"):
                    book = st.selectbox(
                        "Book",
                        my_borrowed,
                        format_func=lambda b: (
                            f"{b['title']} — flat {flat_of(b.get('owner_id'))}"
                            + (f", borrowed on {b['loan_date']}" if b["loan_date"] else "")
                        ),
                    )
                    if st.form_submit_button("Return book", icon=":material/assignment_return:", use_container_width=True):
                        initiate_return(book["id"], new_handover_code())
                        st.rerun()

# Screen 5: my books — lender confirms handovers, tracks own books
with tab_mine:
    st.header("My books")
    if not require_login():
        pass
    else:
        my_books = [b for b in books if b.get("owner_id") == my_kid["id"]]
        my_reserved = [b for b in my_books if b["status"] == "Reserved"]
        my_returns = [b for b in my_books if b["status"] == "Returning"]
        my_lent = [b for b in my_books if b["status"] == "Borrowed"]
        my_shelf = [b for b in my_books if b["status"] == "Available"]

        if my_reserved:
            st.subheader("Confirm handover")
            for b in my_reserved:
                with st.form(f"confirm_{b['id']}"):
                    st.write(
                        f"**{b['title']}** — {name_of(b['borrowed_by'])} "
                        f"(flat {flat_of(b['borrowed_by'])}) is collecting it"
                    )
                    entered = st.text_input("Handover code", key=f"code_{b['id']}", icon=":material/key:").strip().upper()
                    c1, c2 = st.columns(2)
                    confirm = c1.form_submit_button("Confirm", icon=":material/check:", use_container_width=True)
                    cancel = c2.form_submit_button("Cancel", icon=":material/close:", use_container_width=True)
                if confirm:
                    if entered and entered == (b["borrow_code"] or ""):
                        confirm_borrow(b["id"])
                        st.success(f"“{b['title']}” is now on loan to {name_of(b['borrowed_by'])}.", icon=":material/check_circle:")
                        st.rerun()
                    else:
                        st.error("The code does not match. Please check it with the borrower.", icon=":material/error:")
                elif cancel:
                    cancel_reservation(b["id"])
                    st.rerun()
            st.divider()

        if my_returns:
            st.subheader("Confirm return")
            for b in my_returns:
                with st.form(f"confirm_return_{b['id']}"):
                    st.write(
                        f"**{b['title']}** — {name_of(b['borrowed_by'])} "
                        f"(flat {flat_of(b['borrowed_by'])}) is returning it"
                    )
                    entered = st.text_input("Return code", key=f"rcode_{b['id']}", icon=":material/key:").strip().upper()
                    c1, c2 = st.columns(2)
                    confirm = c1.form_submit_button("Confirm", icon=":material/check:", use_container_width=True)
                    cancel = c2.form_submit_button("Not received", icon=":material/close:", use_container_width=True)
                if confirm:
                    if entered and entered == (b["borrow_code"] or ""):
                        confirm_return(b["id"])
                        st.success(f"“{b['title']}” is back on your shelf.", icon=":material/check_circle:")
                        st.rerun()
                    else:
                        st.error("The code does not match. Please check it with the borrower.", icon=":material/error:")
                elif cancel:
                    cancel_return(b["id"])
                    st.rerun()
            st.divider()

        if my_lent:
            st.subheader("On loan")
            for b in my_lent:
                st.write(
                    f"**{b['title']}** — with {name_of(b['borrowed_by'])} "
                    f"(flat {flat_of(b['borrowed_by'])})"
                    + (f" since {b['loan_date']}" if b["loan_date"] else "")
                )
        if my_shelf:
            st.subheader("Available")
            for b in my_shelf:
                st.write(f"**{b['title']}** — {b['author'] or 'Unknown author'}")
        if not my_books:
            st.info("Your flat has not added any books yet. Use the Add Books tab.", icon=":material/info:")
