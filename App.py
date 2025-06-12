import streamlit as st
import pandas as pd
import json
import os
from datetime import date, datetime
from streamlit_autorefresh import st_autorefresh
import pdfplumber
from PIL import Image

# -------------------------------------------
# ------- APP CONFIG + STATE INITIALIZATION --
# -------------------------------------------
st.set_page_config(
    page_title="Tito's Depot Help Center",
    layout="wide",
    page_icon="🛒"
)

REQUESTS_FILE = "requests.json"
COMMENTS_FILE = "comments.json"
UPLOADS_DIR = "uploads"

# Ensure the uploads directory exists
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

# Example users (username: password). Replace or expand as needed.
VALID_USERS = {
    "andres": "2002",
    "marcela": "2002",
    "tito": "2002",
    "caro": "2002",
    "john": "2002",
    "thea": "2002",
    "luz": "2002",
    "david": "2002",
    "caro": "2002"
}

# --- Helper: Colored Status Badge ---
def format_status_badge(status):
    status = status.upper()
    color_map = {
        "PENDING": "#f39c12",
        "READY": "#2ecc71",
        "IN TRANSIT": "#3498db",
        "ORDERED": "#9b59b6",
        "INCOMPLETE": "#e67e22",
        "CANCELLED": "#e74c3c",
    }
    color = color_map.get(status, "#7f8c8d")
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

# --- Persistence Helpers ---
import os, json

REQUESTS_FILE = "requests.json"
COMMENTS_FILE = "comments.json"

def load_data():
    # ─────────── LOAD requests.json ───────────
    if os.path.exists(REQUESTS_FILE):
        try:
            with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
                contents = f.read().strip()
                if contents:
                    st.session_state.requests = json.loads(contents)
                else:
                    # file exists but is empty → start with empty list
                    st.session_state.requests = []
        except json.JSONDecodeError:
            # requests.json is malformed → overwrite with empty list
            st.session_state.requests = []
    else:
        # file doesn’t exist → initialize and create it
        st.session_state.requests = []
        with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

    # ─────────── LOAD comments.json ───────────
    if os.path.exists(COMMENTS_FILE):
        try:
            with open(COMMENTS_FILE, "r", encoding="utf-8") as f:
                contents = f.read().strip()
                if contents:
                    st.session_state.comments = json.loads(contents)
                else:
                    st.session_state.comments = {}
        except json.JSONDecodeError:
            st.session_state.comments = {}
    else:
        st.session_state.comments = {}
        with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

def save_data():
    with open(REQUESTS_FILE, "w") as f:
        json.dump(st.session_state.requests, f)
    with open(COMMENTS_FILE, "w") as f:
        json.dump(st.session_state.comments, f)

def add_request(data):
    index = len(st.session_state.requests)
    st.session_state.requests.append(data)
    # Initialize an empty comment list for this new request
    st.session_state.comments[str(index)] = []
    save_data()

def add_comment(index, author, text="", attachment=None):
    """
    Add a comment to the request at `index`. If `attachment` is provided,
    it should be the filename (inside UPLOADS_DIR) of the uploaded file.
    """
    key = str(index)
    if key not in st.session_state.comments:
        st.session_state.comments[key] = []
    entry = {
        "author": author,
        "text": text,
        "when": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    if attachment:
        entry["attachment"] = attachment
    st.session_state.comments[key].append(entry)
    save_data()

def delete_request(index):
    if 0 <= index < len(st.session_state.requests):
        st.session_state.requests.pop(index)
        st.session_state.comments.pop(str(index), None)
        # Re-index comments so their keys remain 0..(N-1)
        st.session_state.comments = {
            str(i): st.session_state.comments.get(str(i), [])
            for i in range(len(st.session_state.requests))
        }
        st.session_state.selected_request = None
        save_data()
        st.success("🗑️ Request deleted successfully.")
        go_to("requests")

def go_to(page):
    st.session_state.page = page
    st.rerun()

# Initialize session_state keys if missing
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "page" not in st.session_state:
    st.session_state.page = "login"
if "requests" not in st.session_state or "comments" not in st.session_state:
    load_data()
if "selected_request" not in st.session_state:
    st.session_state.selected_request = None

# -------------------------------------------
# ---------------- LOGIN PAGE ----------------
# -------------------------------------------
if not st.session_state.authenticated:
    st.markdown("## 🔒 Please Log In")
    st.write("Enter your username and password to continue.")
    username_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")
    if st.button("🔑 Log In"):
        if username_input in VALID_USERS and VALID_USERS[username_input] == password_input:
            st.session_state.authenticated = True
            st.session_state.user_name = username_input
            st.session_state.page = "home"
            st.success(f"Welcome, **{username_input}**!")
            st.rerun()
        else:
            st.error("❌ Invalid username or password.")
    st.stop()

# -------------------------------------------
# ------------- AUTHENTICATED ---------------
# -------------------------------------------

# -------------------------------------------
# ---------------- HOME PAGE ----------------
# -------------------------------------------
if st.session_state.page == "home":
    # Global styling
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
    .logout-button {
        position: absolute;
        top: 10px;
        right: 10px;
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

    # Log Out button
    with st.container():
        if st.button("🚪 Log Out", key="logout"):
            st.session_state.authenticated = False
            st.session_state.user_name = ""
            st.session_state.page = "login"
            st.rerun()

    st.markdown("## 🏠 Welcome to the Help Center")
    st.markdown(f"Logged in as: **{st.session_state.user_name}**")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💲 Purchase Request", use_container_width=True):
                go_to("purchase")
        with col2:
            if st.button("🛒 Sales Order Request", use_container_width=True):
                go_to("sales_order")

    st.markdown("<hr style='margin: 2rem 0;'>", unsafe_allow_html=True)

    if st.button("📋 View All Requests", use_container_width=True):
        go_to("requests")

# -------------------------------------------
# -------------- PURCHASE PAGE  -------------
# -------------------------------------------
elif st.session_state.page == "purchase":
    st.markdown("## 💲 Purchase Request Form")
    st.markdown(
        f"Logged in as: **{st.session_state.user_name}**",
        unsafe_allow_html=True
    )
    st.markdown("<hr>", unsafe_allow_html=True)

    if "purchase_item_rows" not in st.session_state:
        st.session_state.purchase_item_rows = 1
    st.session_state.purchase_item_rows = max(1, st.session_state.purchase_item_rows)

    # Styling for inputs
    st.markdown("""
    <style>
    .stTextInput > div > div > input,
    .stSelectbox > div, .stDateInput > div {
        background-color: #f7f9fc !important;
        border-radius: 8px !important;
        padding: 0.4rem !important;
        border: 1px solid #dfe6ec !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📄 Order Information")
    col1, col2 = st.columns(2)
    with col1:
        po_number = st.text_input(
            "Purchase Order#",
            value="",
            placeholder="e.g. 12345"
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
        order_number = st.text_input(
            "Tracking# (optional)",
            value="",
            placeholder="e.g. TRK-45678"
        )
        proveedor = st.text_input(
            "Proveedor",
            value="",
            placeholder="e.g. Amazon"
        )
        pago = st.selectbox(
            "Método de Pago",
            [" ", "Wire", "Cheque", "Credito", "Efectivo"]
        )

    st.markdown("### 🧾 Items to Order")
    descriptions = []
    quantities = []
    for i in range(st.session_state.purchase_item_rows):
        colA, colB = st.columns(2)
        descriptions.append(
            colA.text_input(f"Description #{i+1}", value="", key=f"po_desc_{i}")
        )
        quantities.append(
            colB.text_input(f"Quantity #{i+1}", value="", key=f"po_qty_{i}")
        )

    col_add, col_remove = st.columns([1, 1])
    with col_add:
        if st.button("➕ Add another item", key="add_purchase"):
            st.session_state.purchase_item_rows += 1
    with col_remove:
        if (st.session_state.purchase_item_rows > 1 and
            st.button("❌ Remove last item", key="remove_purchase")):
            st.session_state.purchase_item_rows -= 1

    st.markdown("### 🚚 Shipping Information")
    col3, col4 = st.columns(2)
    with col3:
        order_date = st.date_input("Order Date", value=date.today())
    with col4:
        eta_date = st.date_input("ETA Date")
    shipping_method = st.selectbox(
        "Shipping Method",
        [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"]
    )

    st.markdown("---")
    col_submit, col_back = st.columns([2, 1])
    with col_submit:
        if st.button("✅ Submit Purchase Request", use_container_width=True):
            cleaned_descriptions = [d.strip() for d in descriptions if d.strip()]
            cleaned_quantities = []
            for q in quantities:
                q = q.strip()
                if q:
                    try:
                        cleaned_quantities.append(int(float(q)))
                    except ValueError:
                        cleaned_quantities.append(q)

            if (not cleaned_descriptions or
                not cleaned_quantities or
                status.strip() == " " or
                encargado.strip() == " "):
                st.error("❗ Please complete required fields: Status, Encargado, and at least one item.")
            else:
                add_request({
                    "Type": "💲",
                    "Order#": order_number,     # Tracking goes here
                    "Invoice": po_number,       # PO goes here
                    "Date": str(order_date),
                    "Status": status,
                    "Shipping Method": shipping_method,
                    "ETA Date": str(eta_date),
                    "Description": cleaned_descriptions,
                    "Quantity": cleaned_quantities,
                    "Proveedor": proveedor,
                    "Encargado": encargado,
                    "Pago": pago
                })
                st.success("✅ Purchase request submitted.")
                st.session_state.purchase_item_rows = 1
                go_to("home")

    with col_back:
        if st.button("⬅ Back to Home", use_container_width=True):
            go_to("home")

# -------------------------------------------
# --------- SALES ORDER REQUEST PAGE --------
# -------------------------------------------
elif st.session_state.page == "sales_order":
    st.markdown("## 🛒 Sales Order Request Form")
    st.markdown(
        f"Logged in as: **{st.session_state.user_name}**",
        unsafe_allow_html=True
    )
    st.markdown("<hr>", unsafe_allow_html=True)

    if "invoice_item_rows" not in st.session_state:
        st.session_state.invoice_item_rows = 1
    st.session_state.invoice_item_rows = max(1, st.session_state.invoice_item_rows)

    st.markdown("""
    <style>
    .stTextInput > div > div > input,
    .stSelectbox > div, .stDateInput > div {
        background-color: #f7f9fc !important;
        border-radius: 8px !important;
        padding: 0.4rem !important;
        border: 1px solid #dfe6ec !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📄 Order Information")
    col1, col2 = st.columns(2)
    with col1:
        order_number = st.text_input("Ref# (optional)", value="", placeholder="e.g. SO-2025-001")
        status = st.selectbox(
            "Status *",
            [" ", "PENDING", "ORDERED", "READY", "CANCELLED", "IN TRANSIT", "INCOMPLETE"]
        )
        encargado = st.selectbox(
            "Encargado *",
            [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"]
        )
    with col2:
        sales_order_number = st.text_input("Tracking# (optional)", value="", placeholder="e.g. TRK45678")
        cliente = st.text_input("Cliente", value="", placeholder="e.g. TechCorp LLC")
        pago = st.selectbox("Método de Pago", [" ", "Wire", "Cheque", "Credito", "Efectivo"])

    st.markdown("### 🧾 Items to Invoice")
    descriptions = []
    quantities = []
    for i in range(st.session_state.invoice_item_rows):
        colA, colB = st.columns(2)
        descriptions.append(
            colA.text_input(f"Description #{i+1}", value="", key=f"so_desc_{i}")
        )
        quantities.append(
            colB.text_input(f"Quantity #{i+1}", value="", key=f"so_qty_{i}")
        )

    col_add, col_remove = st.columns([1, 1])
    with col_add:
        if st.button("➕ Add another item", key="add_invoice"):
            st.session_state.invoice_item_rows += 1
    with col_remove:
        if (st.session_state.invoice_item_rows > 1 and
            st.button("❌ Remove last item", key="remove_invoice")):
            st.session_state.invoice_item_rows -= 1

    st.markdown("### 🚚 Shipping Information")
    col3, col4 = st.columns(2)
    with col3:
        order_date = st.date_input("Order Date", value=date.today())
    with col4:
        eta_date = st.date_input("ETA Date")
    shipping_method = st.selectbox("Shipping Method", [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"])

    st.markdown("---")
    col_submit, col_back = st.columns([2, 1])
    with col_submit:
        if st.button("✅ Submit Sales Order", use_container_width=True):
            cleaned_descriptions = [d.strip() for d in descriptions if d.strip()]
            cleaned_quantities = []
            for q in quantities:
                q = q.strip()
                if q:
                    try:
                        cleaned_quantities.append(int(float(q)))
                    except ValueError:
                        cleaned_quantities.append(q)

            if (not cleaned_descriptions or
                not cleaned_quantities or
                status.strip() == " " or
                encargado.strip() == " "):
                st.error("❗ Please complete required fields: Status, Encargado, and at least one item.")
            else:
                add_request({
                    "Type": "🛒",
                    "Order#": order_number,             # Sales order#
                    "Invoice": sales_order_number,       # Tracking
                    "Date": str(order_date),
                    "Status": status,
                    "Shipping Method": shipping_method,
                    "ETA Date": str(eta_date),
                    "Description": cleaned_descriptions,
                    "Quantity": cleaned_quantities,
                    "Cliente": cliente,
                    "Encargado": encargado,
                    "Pago": pago
                })
                st.success("✅ Sales order submitted.")
                st.session_state.invoice_item_rows = 1
                go_to("home")

    with col_back:
        if st.button("⬅ Back to Home", use_container_width=True):
            go_to("home")

# -------------------------------------------
# -------- ALL REQUESTS / EXPORT PAGE -------
# -------------------------------------------
elif st.session_state.page == "requests":
    st.markdown(f"## 📋 All Requests   |   Logged in as: **{st.session_state.user_name}**")
    st.markdown("<hr>", unsafe_allow_html=True)

    # Auto‐refresh & reload
    _ = st_autorefresh(interval=1000, limit=None, key="requests_refresh")
    load_data()

    # ─────────── Filters ───────────
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

    # Build filtered list
    filtered_requests = []
    for req in st.session_state.requests:
        matches_search = search_term.lower() in json.dumps(req).lower()
        matches_status = (status_filter == "All") or (req.get("Status", "").upper() == status_filter)
        matches_type = (type_filter == "All" or req.get("Type") == type_filter.split()[0])
        if matches_search and matches_status and matches_type:
            filtered_requests.append(req)

    # Helper to sort by ETA
    from datetime import datetime as _dt
    def parse_eta(req):
        eta_str = req.get("ETA Date", "")
        try:
            return _dt.strptime(eta_str, "%Y-%m-%d").date()
        except:
            return date.max

    filtered_requests = sorted(filtered_requests, key=parse_eta)

    if filtered_requests:
        # --- CSV Export button ---
        flattened = []
        for req in filtered_requests:
            flat_req = {}
            flat_req["Type"] = req.get("Type", "")
            if req.get("Type") == "💲":
                flat_req["Order#"] = req.get("Invoice", "")
                flat_req["Tracking Number"] = req.get("Order#", "")
            else:
                flat_req["Order#"] = req.get("Order#", "")
                flat_req["Tracking Number"] = req.get("Invoice", "")
            for k, v in req.items():
                key_lower = k.lower()
                if key_lower in ("order#", "invoice", "attachments", "statushistory", "comments", "commentshistory", "type"):
                    continue
                flat_req[k] = ";".join(str(x) for x in v) if isinstance(v, list) else v
            flattened.append(flat_req)

        df_export = pd.DataFrame(flattened)
        csv_data = df_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Filtered Requests to CSV",
            data=csv_data,
            file_name="requests_export.csv",
            mime="text/csv"
        )

        # --- Table styling ---
        st.markdown("""
        <style>
        .header-row {
            font-weight: bold;
            font-size: 18px;
            padding: 0.5rem 0;
        }
        .overdue-icon {
            color: #e74c3c;
            font-weight: 600;
            font-size: 14px;
            margin-left: 6px;
            vertical-align: middle;
        }
        .type-icon {
            font-size: 18px;
        }
        </style>
        """, unsafe_allow_html=True)

        # ─────────── Table header (11 columns) ───────────
        header_cols = st.columns([1, 2, 3, 1, 2, 2, 2, 2, 2, 1, 1])
        headers = [
            "Type", "Ref#", "Description", "Qty", "Status",
            "Ordered Date", "ETA Date", "Shipping Method", "Encargado",
            "",  # view
            ""   # delete
        ]
        for col, header in zip(header_cols, headers):
            col.markdown(f"<div class='header-row'>{header}</div>", unsafe_allow_html=True)

        today = date.today()
        for i, req in enumerate(filtered_requests):
            with st.container():
                cols = st.columns([1, 2, 3, 1, 2, 2, 2, 2, 2, 1, 1])

                # 1) Type
                cols[0].markdown(
                    f"<span class='type-icon'>{req.get('Type','')}</span>",
                    unsafe_allow_html=True
                )

                # 2) Ref#
                ref_val = req.get("Invoice","") if req.get("Type")=="💲" else req.get("Order#","")
                cols[1].write(ref_val)

                # 3) Description
                desc = req.get("Description",[])
                cols[2].write(", ".join(desc) if isinstance(desc,list) else desc)

                # 4) Qty
                qty = req.get("Quantity",[])
                cols[3].write(", ".join(str(x) for x in qty) if isinstance(qty,list) else qty)

                # 5) Status + overdue icon
                status_val = req.get("Status","").upper()
                eta_str = req.get("ETA Date","")
                try:
                    eta_date = _dt.strptime(eta_str, "%Y-%m-%d").date()
                except:
                    eta_date = None
                is_overdue = eta_date and eta_date < today and status_val not in ("READY","CANCELLED")
                status_html = format_status_badge(status_val)
                if is_overdue:
                    status_html += "<abbr title='Overdue'><span class='overdue-icon'>⚠️</span></abbr>"
                cols[4].markdown(status_html, unsafe_allow_html=True)

                # 6) Ordered Date
                cols[5].write(req.get("Date",""))

                # 7) ETA Date
                cols[6].write(eta_str)

                # 8) Shipping Method
                cols[7].write(req.get("Shipping Method",""))

                # 9) Encargado
                cols[8].write(req.get("Encargado",""))

                # 10) View button
                if cols[9].button("🔍", key=f"view_{i}"):
                    full_index = st.session_state.requests.index(req)
                    st.session_state.selected_request = full_index
                    go_to("detail")

                # 11) Delete button
                if cols[10].button("❌", key=f"delete_{i}"):
                    full_index = st.session_state.requests.index(req)
                    delete_request(full_index)

    else:
        st.warning("No matching requests found.")

    if st.button("⬅ Back to Home"):
        go_to("home")

# -------------------------------------------
# ---------- REQUEST DETAILS PAGE -----------
# -------------------------------------------
elif st.session_state.page == "detail":
    # ─────────────────────────────────────────────────────────────────────
    #  “Request Details” PAGE (WhatsApp‐style chat + auto‐refresh)
    #  + inline image/PDF previews, Enter‐to‐send, file uploads, download
    # ─────────────────────────────────────────────────────────────────────

    # 1) Auto‐refresh every 1 second
    _ = st_autorefresh(interval=1000, limit=None, key=f"refresh_{st.session_state.selected_request}")

    # 2) Reload shared data
    load_data()

    # Header
    st.markdown("## 📂 Request Details")
    st.markdown(f"Logged in as: **{st.session_state.user_name}**", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # Validate index
    index = st.session_state.selected_request
    if index is None or index >= len(st.session_state.requests):
        st.error("Invalid request selected.")
        st.stop()

    request = st.session_state.requests[index]
    updated_fields = {}
    is_purchase = (request.get("Type") == "💲")

    # ──────────── ORDER INFORMATION ────────────
    with st.container():
        st.markdown("### 📄 Order Information")
        col1, col2 = st.columns(2)

        with col1:
            # Ref# / Order#
            prev = request.get("Order#", "")
            v = st.text_input("Ref#", value=prev, key="detail_Order#")
            if v != prev: updated_fields["Order#"] = v

            # Items list
            descs = request.get("Description", [])
            qtys  = request.get("Quantity", [])
            rows = max(len(descs), len(qtys), 1)
            st.markdown("#### 📋 Items")
            new_descs, new_qtys = [], []
            for i in range(rows):
                d_prev = descs[i] if i < len(descs) else ""
                q_prev = qtys[i]  if i < len(qtys)  else ""
                c1, c2 = st.columns(2)
                d = c1.text_input(f"Description #{i+1}", value=d_prev, key=f"detail_desc_{i}").strip()
                q_raw = c2.text_input(f"Quantity #{i+1}", value=str(q_prev), key=f"detail_qty_{i}").strip()
                try:
                    q = int(float(q_raw)) if q_raw else ""
                except:
                    q = q_raw
                new_descs.append(d)
                new_qtys.append(q)
            if new_descs != descs: updated_fields["Description"] = new_descs
            if new_qtys != qtys:   updated_fields["Quantity"]    = new_qtys

            # Status
            opts = [" ", "PENDING", "ORDERED", "READY", "CANCELLED", "IN TRANSIT", "INCOMPLETE"]
            curr = request.get("Status", " ")
            if curr not in opts: curr = " "
            s = st.selectbox("Status", opts, index=opts.index(curr), key="detail_Status")
            if s != curr: updated_fields["Status"] = s

        with col2:
            # Tracking# / Invoice field
            inv_prev = request.get("Invoice", "")
            inv = st.text_input("Tracking#", value=inv_prev, key="detail_Invoice")
            if inv != inv_prev: updated_fields["Invoice"] = inv

            # Proveedor / Cliente
            label = "Proveedor" if is_purchase else "Cliente"
            p_prev = request.get(label, "")
            p = st.text_input(label, value=p_prev, key=f"detail_{label}")
            if p != p_prev: updated_fields[label] = p

            # Pago
            pago_prev = request.get("Pago", " ")
            pago = st.selectbox("Método de Pago", [" ", "Wire", "Cheque", "Credito", "Efectivo"],
                                index=[" ", "Wire", "Cheque", "Credito", "Efectivo"].index(pago_prev),
                                key="detail_Pago")
            if pago != pago_prev: updated_fields["Pago"] = pago

            # Encargado
            enc_prev = request.get("Encargado", " ")
            enc = st.selectbox("Encargado", [" ", "Andres","Tito","Luz","David","Marcela","John","Carolina","Thea"],
                               index=[" ", "Andres","Tito","Luz","David","Marcela","John","Carolina","Thea"].index(enc_prev),
                               key="detail_Encargado")
            if enc != enc_prev: updated_fields["Encargado"] = enc

    # ──────────── SHIPPING INFORMATION ────────────
    with st.container():
        st.markdown("### 🚚 Shipping Information")
        c3, c4 = st.columns(2)
        # Order Date
        d_prev = request.get("Date", str(date.today()))
        d_new  = c3.date_input("Order Date", value=pd.to_datetime(d_prev), key="detail_Date")
        if str(d_new) != d_prev: updated_fields["Date"] = str(d_new)
        # ETA Date
        e_prev = request.get("ETA Date", str(date.today()))
        e_new  = c4.date_input("ETA Date", value=pd.to_datetime(e_prev), key="detail_ETA")
        if str(e_new) != e_prev: updated_fields["ETA Date"] = str(e_new)
        # Shipping Method
        sm_prev = request.get("Shipping Method", " ")
        sm = st.selectbox("Shipping Method", [" ","Nivel 1 PU","Nivel 3 PU","Nivel 3 DEL"],
                          index=[" ","Nivel 1 PU","Nivel 3 PU","Nivel 3 DEL"].index(sm_prev),
                          key="detail_Shipping")
        if sm != sm_prev: updated_fields["Shipping Method"] = sm

    # ──────────── ACTION BUTTONS ────────────
    st.markdown("---")
    bs, bd, bb = st.columns([2,1,1])
    with bs:
        if updated_fields and st.button("💾 Save Changes", use_container_width=True):
            request.update(updated_fields)
            st.session_state.requests[index] = request
            save_data()
            st.success("✅ Changes saved.")
            st.rerun()
    with bd:
        if st.button("🗑️ Delete Request", use_container_width=True):
            delete_request(index)
    with bb:
        if st.button("⬅ Back to All Requests", use_container_width=True):
            go_to("requests")

    # ─────────────────────────────────────────────────────────────────────
    #  COMMENTS SECTION (chat bubbles, inline previews, download, Enter/send)
    # ─────────────────────────────────────────────────────────────────────

    # Inject CSS for bubbles, attachments, timestamps
    st.markdown("""
    <style>
      .chat-container{padding:8px;background:#fff;border-radius:8px;}
      .chat-author-in{font-size:12px;font-weight:600;color:#555;margin:4px 0 2px 5px;text-align:left;clear:both;}
      .chat-author-out{font-size:12px;font-weight:600;color:#25D366;margin:4px 5px 2px 0;text-align:right;clear:both;}
      .chat-bubble-in,.chat-bubble-out{padding:10px 14px;border-radius:20px;margin:4px 0;max-width:60%;line-height:1.4;word-wrap:break-word;box-shadow:0 1px 3px rgba(0,0,0,0.1);position:relative;}
      .chat-bubble-in{background:#F1F0F0;color:#000;float:left;clear:both;}
      .chat-bubble-out{background:#DCF8C6;color:#000;float:right;clear:both;}
      .chat-timestamp{font-size:10px;color:#888;margin-top:2px;}
      .clearfix{clear:both;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 💬 Comments (Chat-Style)")
    l, center, r = st.columns([1,6,1])
    with center:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        existing = st.session_state.comments.get(str(index), [])
        for comment in existing:
            author = comment["author"]
            text   = comment.get("text","")
            when   = comment.get("when","")
            attachment = comment.get("attachment", None)

            # Render attachment preview + download
            if attachment:
                path = os.path.join(UPLOADS_DIR, attachment)
                ext  = os.path.splitext(attachment)[1].lower()

                if ext in (".png",".jpg",".jpeg"):
                    st.image(path, caption=attachment, width=200)
                elif ext == ".pdf":
                    with pdfplumber.open(path) as pdf:
                        page = pdf.pages[0]
                        pil_img = page.to_image(resolution=150).original
                    st.image(pil_img, caption=f"Preview: {attachment}", width=200)

                # download button
                try:
                    with open(path, "rb") as f: data = f.read()
                    st.download_button(
                        label=f"📎 Download {attachment}",
                        data=data,
                        file_name=attachment,
                        mime="application/octet-stream",
                        key=f"dl_{index}_{attachment}"
                    )
                except FileNotFoundError:
                    st.error(f"⚠️ Attachment not found: {attachment}")

            # Render text bubble
            if text:
                if author == st.session_state.user_name:
                    st.markdown(
                        f'<div class="chat-author-out">{author}</div>'
                        f'<div class="chat-bubble-out">{text}</div>'
                        f'<div class="chat-timestamp" style="text-align:right;">{when}</div>'
                        '<div class="clearfix"></div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="chat-author-in">{author}</div>'
                        f'<div class="chat-bubble-in">{text}</div>'
                        f'<div class="chat-timestamp" style="text-align:left;">{when}</div>'
                        '<div class="clearfix"></div>',
                        unsafe_allow_html=True
                    )

        st.markdown('</div>', unsafe_allow_html=True)

        # Input row: ENTER-to-send + file uploader + dummy + upload button
        st.markdown("---")
        def _send_on_enter():
            key = f"new_msg_{index}"
            msg = st.session_state[key]
            if msg.strip():
                add_comment(index, st.session_state.user_name, msg.strip(), attachment=None)
                st.session_state[key] = ""
                st.rerun()

        text_key = f"new_msg_{index}"
        st.text_input("Type your message here…", key=text_key,
                      placeholder="Press Enter to send text",
                      on_change=_send_on_enter)

        uploaded = st.file_uploader(
            "Attach a PDF, PNG or XLSX file (then press Enter to upload)",
            type=["pdf","png","xlsx"], key=f"fileuploader_{index}"
        )
        st.button("", key=f"dummy_{index}")  # invisible dummy

        if st.button("Upload File", key=f"upload_file_{index}"):
            if uploaded is not None:
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                fname = f"{index}_{ts}_{uploaded.name}"
                save_path = os.path.join(UPLOADS_DIR, fname)
                with open(save_path, "wb") as f: f.write(uploaded.getbuffer())
                add_comment(index, st.session_state.user_name, text="", attachment=fname)
                st.success(f"Uploaded: {uploaded.name}")
                st.rerun()
    # End of detail page

