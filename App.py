import streamlit as st
import pandas as pd
import json
import os
import shutil
from datetime import datetime, date
import re
from streamlit_autorefresh import st_autorefresh

# --- App Config ---
st.set_page_config(page_title="Tito's Depot Help Center", layout="wide", page_icon="🛒")

# --- File Paths ---
REQUESTS_FILE = "requests.json"
COMMENTS_FILE = "comments.json"
ATTACHMENTS_DIR = "attachments"

# Ensure attachments directory exists
if not os.path.exists(ATTACHMENTS_DIR):
    os.makedirs(ATTACHMENTS_DIR)

# --- Helper: Colored Status Badge ---
def format_status_badge(status):
    status = status.upper()
    color_map = {
        "PENDING": "#f39c12",         # Orange
        "READY": "#2ecc71",            # Green
        "IN TRANSIT": "#3498db",       # Light Blue
        "ORDERED": "#9b59b6",          # Purple
        "INCOMPLETE": "#e67e22",       # Dark Orange
        "CANCELLED": "#e74c3c",        # Red
    }
    color = color_map.get(status, "#7f8c8d")  # Default: Gray
    return f"""
    <span style="background-color: {color};
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 600;
        display: inline-block;">{status}</span>
    """

# --- Persistence ---
def load_data():
    if os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, "r") as f:
            st.session_state.requests = json.load(f)
    else:
        st.session_state.requests = []

    if os.path.exists(COMMENTS_FILE):
        with open(COMMENTS_FILE, "r") as f:
            st.session_state.comments = json.load(f)
    else:
        st.session_state.comments = {}

    # Ensure each request has StatusHistory and Attachments fields
    for idx, req in enumerate(st.session_state.requests):
        if "StatusHistory" not in req:
            req["StatusHistory"] = [{"status": req.get("Status", ""), "when": req.get("Date", str(date.today()))}]
        if "Attachments" not in req:
            req["Attachments"] = []

    save_data()  # Save additions if any were missing


def save_data():
    with open(REQUESTS_FILE, "w") as f:
        json.dump(st.session_state.requests, f)
    with open(COMMENTS_FILE, "w") as f:
        json.dump(st.session_state.comments, f)

# --- Navigation + State ---
if "page" not in st.session_state:
    st.session_state.page = "home"
if "requests" not in st.session_state or "comments" not in st.session_state:
    load_data()
if "selected_request" not in st.session_state:
    st.session_state.selected_request = None
if "bulk_select" not in st.session_state:
    st.session_state.bulk_select = []  # For bulk status update


def go_to(page):
    st.session_state.page = page
    st.rerun()

# When adding a new request, include StatusHistory and Attachments

def add_request(data):
    data["StatusHistory"] = [{"status": data.get("Status", ""), "when": str(datetime.now())}]
    data["Attachments"] = []
    index = len(st.session_state.requests)
    st.session_state.requests.append(data)
    st.session_state.comments[str(index)] = []
    save_data()


def add_comment(index, author, text):
    key = str(index)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = {"author": author, "text": text, "when": timestamp}
    if key not in st.session_state.comments:
        st.session_state.comments[key] = []
    st.session_state.comments[key].append(entry)
    save_data()


def delete_request(index):
    if 0 <= index < len(st.session_state.requests):
        # Also delete any attachment files
        for fname in st.session_state.requests[index].get("Attachments", []):
            fpath = os.path.join(ATTACHMENTS_DIR, fname)
            if os.path.exists(fpath):
                os.remove(fpath)
        st.session_state.requests.pop(index)
        st.session_state.comments.pop(str(index), None)
        # Re-index comments
        st.session_state.comments = {
            str(i): st.session_state.comments.get(str(i), [])
            for i in range(len(st.session_state.requests))
        }
        st.session_state.selected_request = None
        save_data()
        st.success("🗑️ Request deleted successfully.")
        go_to("requests")

# --- Home Page ---
if st.session_state.page == "home":
    # --- Global Styling ---
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

    # --- Section Header ---
    st.markdown("## 🏠 Welcome to the Help Center")
    st.markdown("### What can we help you with today?")

    # --- Main Navigation ---
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💲 Purchase Request", use_container_width=True):
                go_to("purchase")
        with col2:
            if st.button("🛒 Sales Order Request", use_container_width=True):
                go_to("sales_order")

    # --- Divider ---
    st.markdown("<hr style='margin: 2rem 0;'>", unsafe_allow_html=True)

    # --- All Requests ---
    with st.container():
        if st.button("📋 View All Requests", use_container_width=True):
            go_to("requests")

# --- Purchase Request Form ---
elif st.session_state.page == "purchase":
    st.markdown("## 💲 Purchase Request Form")

    # --- Global Styles ---
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
    .stSelectbox > div, .stDateInput > div {
        background-color: #f7f9fc !important;
        border-radius: 8px !important;
        padding: 0.4rem !important;
        border: 1px solid #dfe6ec !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Initialize session‐state containers if not already set ---
    if "purchase_item_rows" not in st.session_state:
        st.session_state.purchase_item_rows = 1
    st.session_state.purchase_item_rows = max(1, st.session_state.purchase_item_rows)

    # --- 1) Order Information ---
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
        po_number = st.text_input(
            "Purchase Order#",
            value="",
            placeholder="e.g. 12345"
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

    # --- 2) Items to Order ---
    st.markdown("### 🧾 Items to Order")
    descriptions = []
    quantities = []

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

    # ───── Add/Remove Item Rows ─────
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

    # --- 3) Shipping Information ---
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

    # --- 4) Submit + Back ---
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

            if (
                not cleaned_descriptions
                or not cleaned_quantities
                or status.strip() == " "
                or encargado.strip() == " "
            ):
                st.error("❗ Please complete required fields: Status, Encargado, and at least one item.")
            else:
                add_request({
                    "Type": "💲",
                    "Order#": order_number,
                    "Invoice": po_number,
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

# --- Sales Order Request Form ---
elif st.session_state.page == "sales_order":
    st.markdown("## 🛒 Sales Order Request Form")

    # --- Global Styles ---
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
    .stSelectbox > div, .stDateInput > div {
        background-color: #f7f9fc !important;
        border-radius: 8px !important;
        padding: 0.4rem !important;
        border: 1px solid #dfe6ec !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Initialize session‐state containers ---
    if "invoice_item_rows" not in st.session_state:
        st.session_state.invoice_item_rows = 1
    st.session_state.invoice_item_rows = max(1, st.session_state.invoice_item_rows)

    # --- 1) Order Information ---
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

    # --- 2) Items to Invoice ---
    st.markdown("### 🧾 Items to Invoice")
    descriptions = []
    quantities = []

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

    # ───── Add/Remove Item Rows ─────
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

    # --- 3) Shipping Information ---
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

    # --- 4) Submit + Back ---
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

            if (
                not cleaned_descriptions
                or not cleaned_quantities
                or status.strip() == " "
                or encargado.strip() == " "
            ):
                st.error("❗ Please complete required fields: Status, Encargado, and at least one item.")
            else:
                add_request({
                    "Type": "🛒",
                    "Order#": order_number,
                    "Invoice": sales_order_number,
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

# --- All Requests Page ---
elif st.session_state.page == "requests":
    # --- Auto-refresh every 5 seconds ---
    _ = st_autorefresh(interval=1000, limit=None, key="requests_refresh")

    # --- Re-load data from disk so we see the latest requests ---
    load_data()

    st.header("📋 All Requests")

    # --- Filters + Bulk Actions ---
    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
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
    with col4:
        # Toggle to show overdue first
        if st.checkbox("Show Overdue First", key="overdue_toggle"):
            show_overdue_first = True
        else:
            show_overdue_first = False

    # --- Filter Logic ---
    filtered_requests = []
    for idx, req in enumerate(st.session_state.requests):
        matches_search = search_term.lower() in json.dumps(req).lower()
        matches_status = (status_filter == "All") or (req.get("Status", "").upper() == status_filter)
        matches_type = (
            type_filter == "All"
            or req.get("Type") == type_filter.split()[0]
        )
        if matches_search and matches_status and matches_type:
            filtered_requests.append((idx, req))

    # --- Compute Overdue Flag ---
    today = date.today()
    display_list = []
    for idx, req in filtered_requests:
        eta_str = req.get("ETA Date", "")
        try:
            eta_date = datetime.strptime(eta_str, "%Y-%m-%d").date()
        except:
            eta_date = None
        status_val = req.get("Status", "").upper()
        is_overdue = eta_date is not None and eta_date < today and status_val not in ("READY", "CANCELLED")
        display_list.append((idx, req, is_overdue))

    # --- Sort by Overdue if toggle, else by ETA date ---
    if show_overdue_first:
        display_list.sort(key=lambda x: (not x[2], x[0]))
    else:
        def parse_eta(req):
            eta_str = req.get("ETA Date", "")
            try:
                return datetime.strptime(eta_str, "%Y-%m-%d").date()
            except:
                return date.max
        display_list.sort(key=lambda x: parse_eta(x[1]))

    # --- Bulk Status Update UI ---
    st.markdown("### Bulk Actions")
    col_b1, col_b2, col_b3 = st.columns([1, 1, 2])
    with col_b1:
        if st.button("Select All Overdue"):
            st.session_state.bulk_select = [idx for idx, _, overdue in display_list if overdue]
    with col_b2:
        if st.button("Clear Selection"):
            st.session_state.bulk_select = []
    with col_b3:
        new_bulk_status = st.selectbox("Set status for selected", [" ", "PENDING", "ORDERED", "READY", "CANCELLED", "IN TRANSIT", "INCOMPLETE"], key="bulk_status")
        if st.button("Update Selected"):
            count = 0
            for idx in st.session_state.bulk_select:
                req = st.session_state.requests[idx]
                old_status = req.get("Status", "")
                if new_bulk_status.strip() and new_bulk_status != old_status:
                    req["Status"] = new_bulk_status
                    # Append to history
                    req["StatusHistory"].append({"status": new_bulk_status, "when": datetime.now().strftime("%Y-%m-%d %H:%M")})
                    count += 1
            if count:
                save_data()
                st.success(f"✅ Updated status for {count} request(s).")
                st.session_state.bulk_select = []
                st.rerun()

    # --- Export Button ---
    # Build DataFrame from filtered_requests
    export_data = []
    for idx, req, _ in display_list:
        row = {
            "Index": idx,
            "Type": req.get("Type", ""),
            "Ref#": req.get("Order#", "") or req.get("Invoice", ""),
            "Description": ", ".join(req.get("Description", [])) if isinstance(req.get("Description", []), list) else req.get("Description", ""),
            "Qty": ", ".join(str(x) for x in req.get("Quantity", [])) if isinstance(req.get("Quantity", []), list) else req.get("Quantity", ""),
            "Status": req.get("Status", ""),
            "Ordered Date": req.get("Date", ""),
            "ETA Date": req.get("ETA Date", ""),
            "Shipping Method": req.get("Shipping Method", ""),
            "Encargado": req.get("Encargado", "")
        }
        export_data.append(row)
    df_export = pd.DataFrame(export_data)
    csv = df_export.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Download CSV", data=csv, file_name="filtered_requests.csv", mime='text/csv')

    # --- Table Header Styling & Display ---
    if display_list:
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

        header_cols = st.columns([0.5, 1, 2, 1, 2, 2, 2, 2, 1, 1])
        headers = ["Select", "Type", "Ref#", "Description", "Qty", "Status", "Ordered Date", "ETA Date", "Encargado", ""]
        for col, header in zip(header_cols, headers):
            col.markdown(f"<div class='header-row'>{header}</div>", unsafe_allow_html=True)

        for idx, req, is_overdue in display_list:
            cols = st.columns([0.5, 1, 2, 1, 2, 2, 2, 2, 1, 1])
            # Bulk select checkbox
            checked = idx in st.session_state.bulk_select
            new_checked = cols[0].checkbox("", value=checked, key=f"select_{idx}")
            if new_checked and idx not in st.session_state.bulk_select:
                st.session_state.bulk_select.append(idx)
            elif not new_checked and idx in st.session_state.bulk_select:
                st.session_state.bulk_select.remove(idx)

            # 1) Type icon
            type_icon = req.get("Type", "")
            cols[1].markdown(f"<span class='type-icon'>{type_icon}</span>", unsafe_allow_html=True)

            # 2) Ref#
            ref_val = req.get("Order#", "") or req.get("Invoice", "")
            cols[2].write(ref_val)

            # 3) Description
            desc_list = req.get("Description", [])
            desc_display = ", ".join(desc_list) if isinstance(desc_list, list) else str(desc_list)
            cols[3].write(desc_display)

            # 4) Qty
            qty_list = req.get("Quantity", [])
            if isinstance(qty_list, list):
                qty_display = ", ".join(str(q) for q in qty_list)
            else:
                qty_display = str(qty_list)
            cols[4].write(qty_display)

            # 5) Status + overdue icon
            status_val = req.get("Status", "").upper()
            status_html = format_status_badge(status_val)
            if is_overdue:
                status_html += "<abbr title='Overdue'><span class='overdue-icon'>⚠️</span></abbr>"
            cols[5].markdown(status_html, unsafe_allow_html=True)

            # 6) Ordered Date
            cols[6].write(req.get("Date", ""))
            # 7) ETA Date
            cols[7].write(req.get("ETA Date", ""))
            # 8) Encargado
            cols[8].write(req.get("Encargado", ""))

            # 9) View button
            if cols[9].button("🔍", key=f"view_{idx}"):
                st.session_state.selected_request = idx
                go_to("detail")
    else:
        st.warning("No matching requests found.")

    if st.button("⬅ Back to Home"):
        go_to("home")

# --- Request Details Page ---
elif st.session_state.page == "detail":
    st.markdown("## 📂 Request Details")
    index = st.session_state.selected_request

    # --- Global Styles ---
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
    .stSelectbox > div, .stDateInput > div > input, .stFileUploader > div {
        background-color: #f7f9fc !important;
        border-radius: 8px !important;
        padding: 0.4rem !important;
        border: 1px solid #dfe6ec !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if index is not None and 0 <= index < len(st.session_state.requests):
        request = st.session_state.requests[index]
        updated_fields = {}

        # Purchase vs Sales flag
        is_purchase = (request.get("Type") == "💲")
        is_sales = (request.get("Type") == "🛒")

        # --- 1) Order Information ---
        with st.container():
            st.markdown("### 📄 Order Information")
            col1, col2 = st.columns(2)

            with col1:
                # Ref#/Order#
                order_number_val = request.get("Order#", "")
                order_number = st.text_input(
                    "Ref# / Tracking#",
                    value=order_number_val,
                    key="detail_Order#"
                )
                if order_number != order_number_val:
                    updated_fields["Order#"] = order_number

                # Items list
                desc_list = request.get("Description", [])
                qty_list = request.get("Quantity", [])
                num_rows = max(len(desc_list), len(qty_list), 1)

                st.markdown("#### 📋 Items")
                new_descriptions = []
                new_quantities = []
                for i in range(num_rows):
                    cA, cB = st.columns(2)
                    desc_val = desc_list[i] if i < len(desc_list) else ""
                    qty_val = qty_list[i] if i < len(qty_list) else ""
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
                status_val = st.selectbox(
                    "Status",
                    status_options,
                    index=status_options.index(current_status),
                    key="detail_Status"
                )
                if status_val != current_status:
                    updated_fields["Status"] = status_val
                    # Append to status history
                    request["StatusHistory"].append({"status": status_val, "when": datetime.now().strftime("%Y-%m-%d %H:%M")})

            with col2:
                # Partner (Proveedor or Cliente)
                partner_label = "Proveedor" if is_purchase else "Cliente"
                partner_val = request.get(partner_label, "")
                partner = st.text_input(
                    partner_label,
                    value=partner_val,
                    key=f"detail_{partner_label}"
                )
                if partner != partner_val:
                    updated_fields[partner_label] = partner

                # Payment
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

        # --- 2) Shipping Information ---
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

        # --- 3) Attachments ---
        st.markdown("### 📎 Attachments")
        existing = request.get("Attachments", [])
        for fname in existing:
            path = os.path.join(ATTACHMENTS_DIR, fname)
            if os.path.exists(path):
                st.markdown(f"- [{fname}](attachments/{fname})")
        new_file = st.file_uploader("Upload a file", key="upload_attachment")
        if new_file is not None:
            save_path = os.path.join(ATTACHMENTS_DIR, new_file.name)
            with open(save_path, "wb") as f:
                f.write(new_file.getbuffer())
            request["Attachments"].append(new_file.name)
            save_data()
            st.success(f"Uploaded {new_file.name}")

        # --- 4) Status History ---
        st.markdown("### 🕘 Status History")
        for hist in request.get("StatusHistory", []):
            st.markdown(f"- `{hist['when']}`: {hist['status']}")

        # --- 5) Save, Delete, Back ---
        st.markdown("---")
        col_save, col_delete, col_back = st.columns([2, 1, 1])
        with col_save:
            if updated_fields and st.button("💾 Save Changes", use_container_width=True):
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

        # --- 6) Comments Section ---
        st.markdown("### 💬 Comments")
        for comment in st.session_state.comments.get(str(index), []):
            st.markdown(f"**{comment['author']}** ({comment['when']}): {comment['text']}")

        new_comment = st.text_area("Add a comment", key="detail_NewComment")
        if st.button("Submit Comment"):
            if new_comment.strip():
                add_comment(index, "User", new_comment.strip())
                st.success("✅ Comment added.")
                st.rerun()
    else:
        st.error("Invalid request selected.")



