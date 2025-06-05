import streamlit as st
import pandas as pd
import json
import os
from datetime import date, datetime
from streamlit_autorefresh import st_autorefresh

# --------------------------------------------------------------------------------
# --- App Configuration ----------------------------------------------------------
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="Tito's Depot Help Center",
    layout="wide",
    page_icon="🛒"
)

# --------------------------------------------------------------------------------
# --- File Paths -----------------------------------------------------------------
# --------------------------------------------------------------------------------
EXCEL_FILE    = "requests2.0.xlsx"   # <— This will live on your local drive
COMMENTS_FILE = "comments.json"

# --------------------------------------------------------------------------------
# --- Helper: Colored Status Badge -----------------------------------------------
# --------------------------------------------------------------------------------
def format_status_badge(status: str) -> str:
    """
    Given a status string (e.g. "PENDING", "READY", etc.), returns
    a small HTML snippet that displays that status in a colored pill.
    """
    status = status.upper()
    color_map = {
        "PENDING": "#f39c12",
        "READY": "#2ecc71",
        "IN TRANSIT": "#3498db",
        "ORDERED": "#9b59b6",
        "INCOMPLETE": "#e67e22",
        "CANCELLED": "#e74c3c",
    }
    color = color_map.get(status, "#7f8c8d")  # default gray
    return f"""
    <span style="
        background-color: {color};
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 600;
        display: inline-block;
    ">{status}</span>
    """

# --------------------------------------------------------------------------------
# --- Utility: Sort Requests by ETA Date -----------------------------------------
# --------------------------------------------------------------------------------
def sort_requests_by_eta(requests_list: list) -> list:
    """
    Given a list of request‐dicts, each containing an "ETA Date" key
    (formatted as "YYYY-MM-DD"), return a new list sorted by ETA ascending.
    Invalid or missing dates are sent to the end.
    """
    def parse_eta(req):
        try:
            return datetime.strptime(req.get("ETA Date", "9999-12-31"), "%Y-%m-%d")
        except Exception:
            return datetime(9999, 12, 31)

    return sorted(requests_list, key=parse_eta)

# --------------------------------------------------------------------------------
# --- Persistence (Excel-backed) -------------------------------------------------
# --------------------------------------------------------------------------------
def load_data():
    """
    1. Reads requests from EXCEL_FILE (if it exists) into st.session_state.requests.
       We expect these columns (exactly in Excel):
         - Type
         - Order#
         - Invoice
         - Date
         - Status
         - Shipping Method
         - ETA Date
         - Description   (JSON‐encoded text)
         - Quantity      (JSON‐encoded text)
         - Proveedor     (only for Purchase orders)
         - Cliente       (only for Sales orders)
         - Encargado
         - Pago

       Description and Quantity columns are read in as plain strings; if they look like
       "["something", "something"]", we JSON‐decode them back into Python lists.

    2. Reads comments from COMMENTS_FILE (if it exists) into st.session_state.comments.

    If either file does not exist, we simply initialize that portion of session_state to empty.
    """
    # ―――――――――――――――――――――――――――――――――――――――――――――――――――――
    # 1) Load the Excel of requests
    # ―――――――――――――――――――――――――――――――――――――――――――――――――――――
    st.session_state.requests = []  # always reset before populating

    if os.path.exists(EXCEL_FILE):
        try:
            # Read entire sheet into a DataFrame, forcing Description & Quantity as strings
            df = pd.read_excel(
                EXCEL_FILE,
                dtype={"Description": str, "Quantity": str},
                sheet_name=0
            )
        except Exception as e:
            st.error(f"❗ Error reading '{EXCEL_FILE}': {e}")
            return

        if not df.empty:
            # small helper: if a cell looks like JSON, JSON‐decode it; otherwise return [].
            def parse_list(cell_value):
                if isinstance(cell_value, str):
                    cell_value = cell_value.strip()
                    if cell_value.startswith("[") or cell_value.startswith("{"):
                        try:
                            return json.loads(cell_value)
                        except Exception:
                            return []
                return []

            for _idx, row in df.iterrows():
                parsed_description = parse_list(row.get("Description", "")) 
                parsed_quantity    = parse_list(row.get("Quantity", ""))

                req = {
                    "Type":             row.get("Type", "")             or "",
                    "Order#":           row.get("Order#", "")           or "",
                    "Invoice":          row.get("Invoice", "")          or "",
                    "Date":             row.get("Date", "")             or "",
                    "Status":           row.get("Status", "")           or "",
                    "Shipping Method":  row.get("Shipping Method", "")  or "",
                    "ETA Date":         row.get("ETA Date", "")         or "",
                    "Description":      parsed_description,
                    "Quantity":         parsed_quantity,
                    "Proveedor":        row.get("Proveedor", "") if "Proveedor" in row else "", 
                    "Cliente":          row.get("Cliente", "")   if "Cliente"   in row else "",
                    "Encargado":        row.get("Encargado", "")        or "",
                    "Pago":             row.get("Pago", "")             or "",
                }
                st.session_state.requests.append(req)
    else:
        # Excel file doesn’t exist→ start with empty list
        st.session_state.requests = []

    # ―――――――――――――――――――――――――――――――――――――――――――――――――――――
    # 2) Load comments from JSON (if it exists)
    # ―――――――――――――――――――――――――――――――――――――――――――――――――――――
    if os.path.exists(COMMENTS_FILE):
        try:
            with open(COMMENTS_FILE, "r") as f:
                st.session_state.comments = json.load(f)
        except Exception:
            st.session_state.comments = {}
    else:
        st.session_state.comments = {}

def save_data():
    """
    1. Take st.session_state.requests (a list of dicts) and write it back to EXCEL_FILE,
       JSON‐encoding the 'Description' and 'Quantity' fields so they fit in a single cell.
    2. Take st.session_state.comments (a dict of string→listofcomments) and write it to COMMENTS_FILE.
    """
    records = []
    for req in st.session_state.requests:
        record = {
            "Type":            req.get("Type", ""),
            "Order#":          req.get("Order#", ""),
            "Invoice":         req.get("Invoice", ""),
            "Date":            req.get("Date", ""),
            "Status":          req.get("Status", ""),
            "Shipping Method": req.get("Shipping Method", ""),
            "ETA Date":        req.get("ETA Date", ""),
            # JSON‐encode the list fields into a string cell
            "Description":     json.dumps(req.get("Description", [])),
            "Quantity":        json.dumps(req.get("Quantity", [])),
            # Only fill Proveedor if it's a Purchase, else blank
            "Proveedor":       req.get("Proveedor", "") if req.get("Type") == "💲" else "",
            # Only fill Cliente if it's a Sales, else blank
            "Cliente":         req.get("Cliente", "") if req.get("Type") == "🛒" else "",
            "Encargado":       req.get("Encargado", ""),
            "Pago":            req.get("Pago", ""),
        }
        records.append(record)

    # Build DataFrame and to_excel
    df = pd.DataFrame(records)
    try:
        df.to_excel(EXCEL_FILE, index=False)
    except Exception as e:
        st.error(f"❗ Error writing to '{EXCEL_FILE}': {e}")

    # Write comments JSON
    try:
        with open(COMMENTS_FILE, "w") as f:
            json.dump(st.session_state.comments, f, indent=2)
    except Exception as e:
        st.error(f"❗ Error writing to '{COMMENTS_FILE}': {e}")

# --------------------------------------------------------------------------------
# --- Navigation + Session State Initialization ---------------------------------
# --------------------------------------------------------------------------------
if "requests" not in st.session_state:
    st.session_state.requests = []
if "comments" not in st.session_state:
    st.session_state.comments = {}

# If we have not yet loaded anything, load from disk now
if not st.session_state.requests or not st.session_state.comments:
    load_data()

if "page" not in st.session_state:
    st.session_state.page = "home"
if "selected_request" not in st.session_state:
    st.session_state.selected_request = None

def go_to(page_name: str):
    st.session_state.page = page_name
    st.rerun()

def add_request(data: dict):
    """
    Append a new request to st.session_state.requests,
    ensure there is a comments list for it, and immediately save to disk.
    """
    index = len(st.session_state.requests)
    st.session_state.requests.append(data)
    st.session_state.comments[str(index)] = []
    save_data()

def add_comment(index: int, author: str, text: str):
    """
    Add a comment under st.session_state.comments[index], then save.
    """
    key = str(index)
    if key not in st.session_state.comments:
        st.session_state.comments[key] = []
    st.session_state.comments[key].append({"author": author, "text": text})
    save_data()

def delete_request(index: int):
    """
    Drop a request and its comments, re-index everything, save, and go back to the “All Requests” page.
    """
    if 0 <= index < len(st.session_state.requests):
        st.session_state.requests.pop(index)
        st.session_state.comments.pop(str(index), None)

        # Re-index comments so nothing breaks
        new_comments = {}
        for i, _ in enumerate(st.session_state.requests):
            old_key = str(i if i < index else i + 1)
            new_comments[str(i)] = st.session_state.comments.get(old_key, [])
        st.session_state.comments = new_comments

        st.session_state.selected_request = None
        save_data()
        st.success("🗑️ Request deleted successfully.")
        go_to("requests")

# --------------------------------------------------------------------------------
# --- “Home” Page ----------------------------------------------------------------
# --------------------------------------------------------------------------------
if st.session_state.page == "home":
    # Global CSS
    st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
    }
    h1, h2, h3, h4 {
        color: #003366;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    div.stButton > button {
        background-color: #ffffff !important;
        border: 1px solid #ccc !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        color: #333 !important;
        transition: background-color 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #f1f1f1 !important;
        border-color: #999 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## 🏠 Welcome to the Help Center")
    st.markdown("### What can we help you with today?")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💲 Purchase Request", use_container_width=True):
                go_to("purchase")
        with col2:
            if st.button("🛒 Sales Order Request", use_container_width=True):
                go_to("sales_order")

    st.markdown("<hr style='margin: 2rem 0;'>", unsafe_allow_html=True)

    with st.container():
        if st.button("📋 View All Requests", use_container_width=True):
            go_to("requests")


# --------------------------------------------------------------------------------
# --- Purchase Request Page ------------------------------------------------------
# --------------------------------------------------------------------------------
elif st.session_state.page == "purchase":
    st.markdown("## 💲 Purchase Request Form")

    # Global Styles
    st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
    }
    h1, h2, h3, h4 {
        color: #003366;
        font-weight: 600;
    }
    .stTextInput > div > div > input,
    .stSelectbox > div,
    .stDateInput > div
    {
        background-color: #f7f9fc !important;
        border-radius: 8px !important;
        padding: 0.4rem !important;
        border: 1px solid #dfe6ec !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialize dynamic item-row counter
    if "purchase_item_rows" not in st.session_state:
        st.session_state.purchase_item_rows = 1
    st.session_state.purchase_item_rows = max(1, st.session_state.purchase_item_rows)

    # ── 1) Order Information ────────────────────────────────────────────────────────
    st.markdown("### 📄 Order Information")
    col1, col2 = st.columns(2)

    with col1:
        order_number = st.text_input(
            "Tracking# (optional)",
            value="",
            placeholder="e.g. PO-2025-12345"
        )
        status = st.selectbox(
            "Status *",
            [" ", "PENDING", "ORDERED", "READY", "CANCELLED", "IN TRANSIT", "INCOMPLETE"]
        )
        encargado = st.selectbox(
            "Encargado *",
            [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"]
        )

    with col2:
        po_number  = st.text_input(
            "Purchase Order#",
            value="",
            placeholder="e.g. 12345"
        )
        proveedor  = st.text_input(
            "Proveedor",
            value="",
            placeholder="e.g. Amazon"
        )
        pago = st.selectbox(
            "Método de Pago",
            [" ", "Wire", "Cheque", "Credito", "Efectivo"]
        )

    # ── 2) Item Rows (dynamic) ─────────────────────────────────────────────────────
    st.markdown("### 🧾 Items to Order")
    descriptions = []
    quantities  = []
    for i in range(st.session_state.purchase_item_rows):
        colA, colB = st.columns(2)
        descriptions.append(
            colA.text_input(
                f"Description #{i+1}",
                value="",
                key=f"po_desc_{i}"
            )
        )
        quantities.append(
            colB.text_input(
                f"Quantity #{i+1}",
                value="",
                key=f"po_qty_{i}"
            )
        )

    col_add, col_remove = st.columns([1, 1])
    with col_add:
        if st.button("➕ Add another item", key="add_purchase"):
            st.session_state.purchase_item_rows += 1
    with col_remove:
        if (
            st.session_state.purchase_item_rows > 1
            and st.button("❌ Remove last item", key="remove_purchase")
        ):
            st.session_state.purchase_item_rows -= 1

    # ── 3) Shipping Information ────────────────────────────────────────────────────
    st.markdown("### 🚚 Shipping Information")
    col3, col4 = st.columns(2)
    with col3:
        order_date = st.date_input(
            "Order Date",
            value=date.today()
        )
    with col4:
        eta_date = st.date_input("ETA Date")

    shipping_method = st.selectbox(
        "Shipping Method",
        [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"]
    )

    # ── 4) Submit + Back Buttons ───────────────────────────────────────────────────
    st.markdown("---")
    col_submit, col_back = st.columns([2, 1])
    with col_submit:
        if st.button("✅ Submit Purchase Request", use_container_width=True):
            cleaned_descriptions = [d.strip() for d in descriptions if d.strip()]
            cleaned_quantities   = []
            for q in quantities:
                q = q.strip()
                if q:
                    try:
                        cleaned_quantities.append(int(float(q)))
                    except ValueError:
                        cleaned_quantities.append(q)

            if (
                not cleaned_descriptions
                or not cleaned_quantities
                or status.strip() == " "
                or encargado.strip() == " "
            ):
                st.error("❗ Please complete required fields: Status, Encargado, and at least one item.")
            else:
                add_request({
                    "Type":            "💲", 
                    "Order#":          order_number,
                    "Invoice":         po_number,
                    "Date":            str(order_date),
                    "Status":          status,
                    "Shipping Method": shipping_method,
                    "ETA Date":        str(eta_date),
                    "Description":     cleaned_descriptions,
                    "Quantity":        cleaned_quantities,
                    "Proveedor":       proveedor,
                    "Encargado":       encargado,
                    "Pago":            pago
                })
                st.success("✅ Purchase request submitted.")
                st.session_state.purchase_item_rows = 1
                go_to("home")

    with col_back:
        if st.button("⬅ Back to Home", use_container_width=True):
            go_to("home")


# --------------------------------------------------------------------------------
# --- Sales Order Request Page ---------------------------------------------------
# --------------------------------------------------------------------------------
elif st.session_state.page == "sales_order":
    st.markdown("## 🛒 Sales Order Request Form")

    # Global Styles
    st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
    }
    h1, h2, h3, h4 {
        color: #003366;
        font-weight: 600;
    }
    .stTextInput > div > div > input,
    .stSelectbox > div,
    .stDateInput > div
    {
        background-color: #f7f9fc !important;
        border-radius: 8px !important;
        padding: 0.4rem !important;
        border: 1px solid #dfe6ec !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialize dynamic item‐row counter
    if "invoice_item_rows" not in st.session_state:
        st.session_state.invoice_item_rows = 1
    st.session_state.invoice_item_rows = max(1, st.session_state.invoice_item_rows)

    # ── 1) Order Information ────────────────────────────────────────────────────────
    st.markdown("### 📄 Order Information")
    col1, col2 = st.columns(2)
    with col1:
        order_number = st.text_input(
            "Ref# (optional)",
            value="",
            placeholder="e.g. SO-2025-001"
        )
        status = st.selectbox(
            "Status *",
            [" ", "PENDING", "CONFIRMED", "READY", "CANCELLED", "IN TRANSIT", "INCOMPLETE"]
        )
        encargado = st.selectbox(
            "Encargado *",
            [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"]
        )
    with col2:
        sales_order_number = st.text_input(
            "Tracking# (optional)",
            value="",
            placeholder="e.g. TRK45678"
        )
        cliente = st.text_input(
            "Cliente",
            value="",
            placeholder="e.g. TechCorp LLC"
        )
        pago = st.selectbox(
            "Método de Pago",
            [" ", "Wire", "Cheque", "Credito", "Efectivo"]
        )

    # ── 2) Item Rows (dynamic) ─────────────────────────────────────────────────────
    st.markdown("### 🧾 Items to Invoice")
    descriptions = []
    quantities  = []
    for i in range(st.session_state.invoice_item_rows):
        colA, colB = st.columns(2)
        descriptions.append(
            colA.text_input(
                f"Description #{i+1}",
                value="",
                key=f"so_desc_{i}"
            )
        )
        quantities.append(
            colB.text_input(
                f"Quantity #{i+1}",
                value="",
                key=f"so_qty_{i}"
            )
        )

    col_add, col_remove = st.columns([1, 1])
    with col_add:
        if st.button("➕ Add another item", key="add_invoice"):
            st.session_state.invoice_item_rows += 1
    with col_remove:
        if (
            st.session_state.invoice_item_rows > 1
            and st.button("❌ Remove last item", key="remove_invoice")
        ):
            st.session_state.invoice_item_rows -= 1

    # ── 3) Shipping Information ────────────────────────────────────────────────────
    st.markdown("### 🚚 Shipping Information")
    col3, col4 = st.columns(2)
    with col3:
        order_date = st.date_input(
            "Order Date",
            value=date.today()
        )
    with col4:
        eta_date = st.date_input("ETA Date")

    shipping_method = st.selectbox(
        "Shipping Method",
        [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"]
    )

    # ── 4) Submit + Back Buttons ───────────────────────────────────────────────────
    st.markdown("---")
    col_submit, col_back = st.columns([2, 1])
    with col_submit:
        if st.button("✅ Submit Sales Order", use_container_width=True):
            cleaned_descriptions = [d.strip() for d in descriptions if d.strip()]
            cleaned_quantities   = []
            for q in quantities:
                q = q.strip()
                if q:
                    try:
                        cleaned_quantities.append(int(float(q)))
                    except ValueError:
                        cleaned_quantities.append(q)

            if (
                not cleaned_descriptions
                or not cleaned_quantities
                or status.strip() == " "
                or encargado.strip() == " "
            ):
                st.error("❗ Please complete required fields: Status, Encargado, and at least one item.")
            else:
                add_request({
                    "Type":             "🛒",
                    "Order#":           order_number,
                    "Invoice":          sales_order_number,
                    "Date":             str(order_date),
                    "Status":           status,
                    "Shipping Method":  shipping_method,
                    "ETA Date":         str(eta_date),
                    "Description":      cleaned_descriptions,
                    "Quantity":         cleaned_quantities,
                    "Cliente":          cliente,
                    "Encargado":        encargado,
                    "Pago":             pago
                })
                st.success("✅ Sales order submitted.")
                st.session_state.invoice_item_rows = 1
                go_to("home")

    with col_back:
        if st.button("⬅ Back to Home", use_container_width=True):
            go_to("home")


# --------------------------------------------------------------------------------
# --- All Requests Page (Excel-backed) -------------------------------------------
# --------------------------------------------------------------------------------
elif st.session_state.page == "requests":
    # Auto-refresh every second so that if you externally edited the Excel (or JSON),
    # the app picks up changes immediately.
    _ = st_autorefresh(interval=1000, limit=None, key="requests_refresh")

    # Re-load data from disk (Excel + comments JSON) so we always show the latest
    load_data()

    st.header("📋 All Requests")

    # ── Filters: Search / Status / Type ─────────────────────────────────────────────
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        search_term = st.text_input("Search", placeholder="Search requests...")
    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "PENDING", "IN TRANSIT", "READY", "CANCELLED", "CONFIRMED", "INCOMPLETE"]
        )
    with col3:
        type_filter = st.selectbox(
            "Request type",
            ["All", "💲 Purchase", "🛒 Sales"]
        )

    # ── Filter Logic ───────────────────────────────────────────────────────────────
    filtered_requests = []
    for req in st.session_state.requests:
        matches_search = search_term.lower() in json.dumps(req).lower()
        matches_status = (status_filter == "All") or (req.get("Status", "").upper() == status_filter)
        matches_type   = (type_filter == "All") or (req.get("Type") == type_filter.split()[0])

        if matches_search and matches_status and matches_type:
            filtered_requests.append(req)

    # ── Sort by ETA date ────────────────────────────────────────────────────────────
    filtered_requests = sort_requests_by_eta(filtered_requests)

    if filtered_requests:
        # Table Header Styling
        st.markdown("""
        <style>
        .header-row {
            font-weight: bold;
            font-size: 18px;
            padding: 0.5rem 0;
        }
        </style>
        """, unsafe_allow_html=True)

        # Table Header
        header_cols = st.columns([1, 2, 3, 1, 2, 2, 2, 2, 2, 1])
        headers     = [
            "Type", "Ref#", "Description", "Qty", "Status",
            "Ordered Date", "ETA Date", "Shipping Method", "Encargado", ""
        ]
        for col, head in zip(header_cols, headers):
            col.markdown(f"<div class='header-row'>{head}</div>", unsafe_allow_html=True)

        # Table Rows
        for i, req in enumerate(filtered_requests):
            with st.container():
                cols = st.columns([1, 2, 3, 1, 2, 2, 2, 2, 2, 1])

                # 1) Type (icon)
                cols[0].write(req.get("Type", ""))

                # 2) Ref# (Order# or Invoice)
                ref_val = req.get("Order#", "") or req.get("Invoice", "")
                cols[1].write(ref_val)

                # 3) Description (join list → comma)
                desc_list   = req.get("Description", [])
                desc_display = ", ".join(desc_list) if isinstance(desc_list, list) else str(desc_list)
                cols[2].write(desc_display)

                # 4) Quantity (join list → comma)
                qty_list    = req.get("Quantity", [])
                qty_display = ", ".join([str(q) for q in qty_list]) if isinstance(qty_list, list) else str(qty_list)
                cols[3].write(qty_display)

                # 5) Status badge
                cols[4].markdown(
                    format_status_badge(req.get("Status", "")),
                    unsafe_allow_html=True
                )

                # 6) Ordered Date
                cols[5].write(req.get("Date", ""))

                # 7) ETA Date
                cols[6].write(req.get("ETA Date", ""))

                # 8) Shipping Method
                cols[7].write(req.get("Shipping Method", ""))

                # 9) Encargado
                cols[8].write(req.get("Encargado", ""))

                # 10) “View” button → go to detail page
                if cols[9].button("🔍", key=f"view_{i}"):
                    full_index = st.session_state.requests.index(req)
                    st.session_state.selected_request = full_index
                    go_to("detail")
    else:
        st.warning("No matching requests found.")

    if st.button("⬅ Back to Home"):
        go_to("home")


# --------------------------------------------------------------------------------
# --- Detail Page ----------------------------------------------------------------
# --------------------------------------------------------------------------------
elif st.session_state.page == "detail":
    st.markdown("## 📂 Request Details")
    index = st.session_state.selected_request

    # Global Styles
    st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
    }
    h1, h2, h3, h4 {
        color: #003366;
        font-weight: 600;
    }
    .stTextInput > div > div > input,
    .stSelectbox > div, .stDateInput > div, .stTextArea > div > textarea {
        background-color: #f7f9fc !important;
        border-radius: 8px !important;
        padding: 0.4rem !important;
        border: 1px solid #dfe6ec !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if (index is not None) and (0 <= index < len(st.session_state.requests)):
        request = st.session_state.requests[index]
        updated_fields = {}

        # Determine if Purchase (💲) or Sales (🛒)
        is_purchase = (request.get("Type") == "💲")
        is_sales    = (request.get("Type") == "🛒")

        # ── 1) Order Information ─────────────────────────────────────────────────────
        with st.container():
            st.markdown("### 📄 Order Information")
            col1, col2 = st.columns(2)

            with col1:
                # Ref# / Order#
                order_number_val = request.get("Order#", "")
                order_number = st.text_input(
                    "Ref#",
                    value=order_number_val,
                    key="detail_Order#"
                )
                if order_number != order_number_val:
                    updated_fields["Order#"] = order_number

                # Dynamic rows for Description & Quantity
                desc_list = request.get("Description", [])
                qty_list  = request.get("Quantity", [])
                num_rows  = max(len(desc_list), len(qty_list), 1)

                st.markdown("#### 📋 Items")
                new_descriptions = []
                new_quantities  = []
                for i in range(num_rows):
                    cA, cB = st.columns(2)
                    desc_val = desc_list[i] if i < len(desc_list) else ""
                    qty_val  = qty_list[i]  if i < len(qty_list) else ""
                    new_desc = cA.text_input(
                        f"Description #{i+1}",
                        value=desc_val,
                        key=f"detail_desc_{i}"
                    ).strip()
                    new_qty_raw = cB.text_input(
                        f"Quantity #{i+1}",
                        value=str(qty_val),
                        key=f"detail_qty_{i}"
                    ).strip()
                    try:
                        new_qty = int(float(new_qty_raw)) if new_qty_raw else ""
                    except:
                        new_qty = new_qty_raw
                    new_descriptions.append(new_desc)
                    new_quantities.append(new_qty)

                if new_descriptions != desc_list:
                    updated_fields["Description"] = new_descriptions
                if new_quantities != qty_list:
                    updated_fields["Quantity"] = new_quantities

                # Status
                status_options = [" ", "PENDING", "ORDERED", "READY", "CANCELLED", "IN TRANSIT", "INCOMPLETE"]
                current_status = request.get("Status", " ")
                if current_status not in status_options:
                    current_status = " "
                status = st.selectbox(
                    "Status",
                    status_options,
                    index=status_options.index(current_status),
                    key="detail_Status"
                )
                if status != current_status:
                    updated_fields["Status"] = status

            with col2:
                # Tracking# / Invoice
                invoice_val = request.get("Invoice", "")
                invoice = st.text_input(
                    "Tracking#",
                    value=invoice_val,
                    key="detail_Invoice"
                )
                if invoice != invoice_val:
                    updated_fields["Invoice"] = invoice

                # Proveedor vs Cliente
                partner_label = "Proveedor" if is_purchase else "Cliente"
                partner_val   = request.get(partner_label, "")
                partner = st.text_input(
                    partner_label,
                    value=partner_val,
                    key=f"detail_{partner_label}"
                )
                if partner != partner_val:
                    updated_fields[partner_label] = partner

                # Método de Pago
                pago_val = request.get("Pago", " ")
                pago = st.selectbox(
                    "Método de Pago",
                    [" ", "Wire", "Cheque", "Credito", "Efectivo"],
                    index=[" ", "Wire", "Cheque", "Credito", "Efectivo"].index(pago_val),
                    key="detail_Pago"
                )
                if pago != pago_val:
                    updated_fields["Pago"] = pago

                # Encargado
                encargado_val = request.get("Encargado", " ")
                encargado = st.selectbox(
                    "Encargado",
                    [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"],
                    index=[" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"].index(encargado_val),
                    key="detail_Encargado"
                )
                if encargado != encargado_val:
                    updated_fields["Encargado"] = encargado

        # ── 2) Shipping Information ───────────────────────────────────────────────────
        with st.container():
            st.markdown("### 🚚 Shipping Information")
            col3, col4 = st.columns(2)

            with col3:
                date_val = request.get("Date", str(date.today()))
                order_date = st.date_input(
                    "Order Date",
                    value=pd.to_datetime(date_val),
                    key="detail_Date"
                )
                if str(order_date) != date_val:
                    updated_fields["Date"] = str(order_date)

            with col4:
                eta_val = request.get("ETA Date", str(date.today()))
                eta_date = st.date_input(
                    "ETA Date",
                    value=pd.to_datetime(eta_val),
                    key="detail_ETA"
                )
                if str(eta_date) != eta_val:
                    updated_fields["ETA Date"] = str(eta_date)

            ship_val = request.get("Shipping Method", " ")
            shipping_method = st.selectbox(
                "Shipping Method",
                [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"],
                index=[" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"].index(ship_val),
                key="detail_Shipping"
            )
            if shipping_method != ship_val:
                updated_fields["Shipping Method"] = shipping_method

        # ── 3) Save, Delete, Back Buttons ────────────────────────────────────────────
        st.markdown("---")
        col_save, col_delete, col_back = st.columns([2, 1, 1])

        with col_save:
            if updated_fields and st.button("💾 Save Changes", use_container_width=True):
                # Apply updates to the in‐memory request
                request.update(updated_fields)
                st.session_state.requests[index] = request
                save_data()
                st.success("✅ Changes saved.")
                st.rerun()

        with col_delete:
            if st.button("🗑️ Delete Request", use_container_width=True):
                delete_request(index)

        with col_back:
            if st.button("⬅ Back to All Requests", use_container_width=True):
                go_to("requests")

        # ── 4) Comments Section ─────────────────────────────────────────────────────
        st.markdown("### 💬 Comments")
        for comment in st.session_state.comments.get(str(index), []):
            st.markdown(f"**{comment['author']}**: {comment['text']}")

        new_comment = st.text_area("Add a comment", key="detail_NewComment")
        if st.button("Submit Comment"):
            if new_comment.strip():
                add_comment(index, "User", new_comment.strip())
                st.success("✅ Comment added.")
                st.experimental_rerun()

    else:
        st.error("Invalid request selected.")





