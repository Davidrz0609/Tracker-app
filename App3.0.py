import math as m
import streamlit as st
import pandas as pd
import json
import os
from datetime import date, datetime
from streamlit_autorefresh import st_autorefresh



# -------------------------------------------
# ------- APP CONFIG + STATE INITIALIZATION --
# -------------------------------------------
st.set_page_config(page_title="Tito's Depot Help Center", layout="wide", page_icon="🛒")

REQUESTS_FILE = "requests.json"
COMMENTS_FILE = "comments.json"
UPLOADS_DIR = "uploads"

# Ensure the uploads directory exists
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Example users (username: password)
VALID_USERS = {
    "Andres": "123",
    "Marcela": "123",
    "Tito": "123",
    "Luz": "123",
    "David": "123",
    "John": "123",
    "Sabrina": "123",
    "Bodega": "123", 
    "Carolina" : "123",   
    "Facturacion" : "123"
}

# Helper: Colored Status Badge
def format_status_badge(status):
    status = status.upper()
    color_map = {
        "IN TRANSIT": "#f39c12",
        "READY": "#2ecc71",
        "COMPLETE": "#3498db",
        "ORDERED": "#9b59b6",
        "CANCELLED": "#e74c3c",
        "IMPRIMIR":             "#f1c40f",
        "IMPRESA":              "#27ae60",
        "SEPARAR Y CONFIRMAR":  "#1abc9c",
        "RECIBIDO / PROCESANDO":"#2980b9",
        "PENDIENTE":            "#95a5a6",
        "SEPARADO - PENDIENTE": "#d35400",
        "RETURNED/CANCELLED":   "#c0392b"

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

# Persistence Helpers

def load_data():
    # Load requests
    if os.path.exists(REQUESTS_FILE) and os.path.getsize(REQUESTS_FILE) > 0:
        try:
            with open(REQUESTS_FILE, "r") as f:
                st.session_state.requests = json.load(f)
        except json.JSONDecodeError:
            st.session_state.requests = []
    else:
        st.session_state.requests = []

    # Load comments safely
    if os.path.exists(COMMENTS_FILE) and os.path.getsize(COMMENTS_FILE) > 0:
        try:
            with open(COMMENTS_FILE, "r") as f:
                st.session_state.comments = json.load(f)
        except json.JSONDecodeError:
            st.session_state.comments = {}
    else:
        st.session_state.comments = {}


def save_data():
    with open(REQUESTS_FILE, "w") as f:
        json.dump(st.session_state.requests, f, indent=2)
    with open(COMMENTS_FILE, "w") as f:
        json.dump(st.session_state.comments, f, indent=2)


def add_request(data):
    idx = len(st.session_state.requests)
    st.session_state.requests.append(data)
    st.session_state.comments[str(idx)] = []
    save_data()


def add_comment(index, author, text="", attachment=None):
    key = str(index)
    if key not in st.session_state.comments:
        st.session_state.comments[key] = []
    comment_entry = {
        "author": author,
        "text": text,
        "when": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    if attachment:
        comment_entry["attachment"] = attachment
    st.session_state.comments[key].append(comment_entry)
    save_data()


def delete_request(index):
    if 0 <= index < len(st.session_state.requests):
        st.session_state.requests.pop(index)
        st.session_state.comments.pop(str(index), None)
        # Re-index
        st.session_state.comments = {str(i): st.session_state.comments.get(str(i), [])
                                     for i in range(len(st.session_state.requests))}
        save_data()
        st.success("🗑️ Request deleted successfully.")
        st.session_state.page = "requests"
        st.rerun()


def go_to(page):
    st.session_state.page = page
    st.rerun()

# Initialize session state keys
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
    st.markdown("# 🔒 Please Log In")
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




# ──────────────────────────────────────────────────────────────────────
# ---------------- HOME PAGE (with locked Summary & Requerimientos) ----
# ──────────────────────────────────────────────────────────────────────

# ── Who’s allowed to view the Summary page?
SUMMARY_ALLOWED = {"Andres", "David", "Tito", "Luz"}

# ── Who’s NOT allowed to view Requerimientos Clientes?
REQS_DENIED = {"Bodega"}

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

    # Logout button
    with st.container():
        if st.button("🚪 Log Out", key="home_logout"):
            st.session_state.authenticated = False
            st.session_state.user_name = ""
            st.session_state.page = "login"
            st.rerun()

    st.markdown("# 🏠 Welcome to the Help Center")
    st.markdown(f"Logged in as: **{st.session_state.user_name}**")
    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

    # ── Three buttons on Home ────────────────────────────────
    col1, col2, col3 = st.columns(3)

    # — Requerimientos Clientes (locked for Bodega) —
    with col1:
        if st.session_state.user_name not in REQS_DENIED:
            if st.button(
                "📝 View Requerimientos Clientes",
                use_container_width=True,
                key="home_view_reqs"
            ):
                st.session_state.page = "req_list"
                st.rerun()
        else:
            st.button(
                "🔒 View Requerimientos Clientes",
                disabled=True,
                use_container_width=True,
                key="home_view_reqs_locked"
            )
            st.caption("You don’t have access to this page.")

    # — All Orders (open to everyone) —
    with col2:
        if st.button(
            "📋 View All Purchase/Sales Orders",
            use_container_width=True,
            key="home_view_orders"
        ):
            st.session_state.page = "requests"
            st.rerun()

    # — Summary (locked except for SUMMARY_ALLOWED) —
    with col3:
        if st.session_state.user_name in SUMMARY_ALLOWED:
            if st.button(
                "📊 Summary",
                use_container_width=True,
                key="home_summary"
            ):
                st.session_state.page = "summary"
                st.rerun()
        else:
            st.button(
                "🔒 Summary",
                disabled=True,
                use_container_width=True,
                key="home_summary_locked"
            )
            st.caption("You don’t have access to this page.")



#####

elif st.session_state.page == "summary":
    import pandas as pd
    import plotly.express as px
    from datetime import date

    # ──────────────────────────────────────────────────────────────────────
    # Helpers & Config
    # ──────────────────────────────────────────────────────────────────────
    status_colors = {
        "IN TRANSIT":           "#f39c12",
        "READY":                "#2ecc71",
        "COMPLETE":             "#3498db",
        "ORDERED":              "#9b59b6",
        "CANCELLED":            "#e74c3c",
        "IMPRIMIR":             "#f1c40f",
        "IMPRESA":              "#27ae60",
        "SEPARAR Y CONFIRMAR":  "#1abc9c",
        "RECIBIDO / PROCESANDO": "#2980b9",
        "PENDIENTE":            "#95a5a6",
        "SEPARADO - PENDIENTE": "#d35400",
        "RETURNED/CANCELLED":   "#c0392b"
    }

    def pick_qty(row):
        if pd.notna(row.get('Qty')):
            return row['Qty']
        for col in ("Quantity", "Items"):
            v = row.get(col)
            if isinstance(v, list) and v:
                return v[0]
            if pd.notna(v):
                return v
        return None

    def flatten(v):
        return v[0] if isinstance(v, list) and v else v

    def badge(s):
        color = status_colors.get(s, "#95a5a6")
        return (
            f"<span style='background-color:{color}; "
            f"color:white; padding:2px 6px; border-radius:4px'>{s}</span>"
        )

    # ──────────────────────────────────────────────────────────────────────
    # Load & Pre-Check Data
    # ──────────────────────────────────────────────────────────────────────
    load_data()
    raw = pd.DataFrame(st.session_state.requests)

    if raw.empty or "Type" not in raw.columns:
        st.info("No Purchase Orders or Sales Orders to summarize yet.")
        st.button("⬅ Back to Home", on_click=lambda: go_to("home"))
        st.stop()

    # Only keep POs (💲) and SOs (🛒)
    df = raw[raw["Type"].isin(["💲", "🛒"])].copy()
    if df.empty:
        st.info("No Purchase Orders or Sales Orders to summarize yet.")
        st.button("⬅ Back to Home", on_click=lambda: go_to("home"))
        st.stop()

    # ──────────────────────────────────────────────────────────────────────
    # Clean & Enrich
    # ──────────────────────────────────────────────────────────────────────
    df["Status"]   = df["Status"].astype(str).str.strip().str.upper()          # <<< uppercase all statuses
    df["Date"]     = pd.to_datetime(df["Date"], errors="coerce")
    df["ETA Date"] = pd.to_datetime(df["ETA Date"], errors="coerce")
    df["Ref#"]     = df.apply(
        lambda r: r["Invoice"] if r["Type"] == "💲" else r["Order#"],
        axis=1
    )

    today          = pd.Timestamp(date.today())
    overdue_mask   = (df["ETA Date"] < today) & ~df["Status"].isin(["READY", "CANCELLED"])
    due_today_mask = (df["ETA Date"] == today) & (df["Status"] != "CANCELLED")

    # ──────────────────────────────────────────────────────────────────────
    # 1. Key Metrics Row
    # ──────────────────────────────────────────────────────────────────────
    st.subheader("📊 Summary")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Requests",   len(df))
    k2.metric("Active Requests",  df[~df["Status"].isin(["COMPLETE", "CANCELLED"])].shape[0])
    k3.metric("Overdue Requests", df[overdue_mask].shape[0])
    k4.metric("Due Today",        df[due_today_mask].shape[0])
    st.markdown("---")

    # ──────────────────────────────────────────────────────────────────────
    # 2. Status Distribution Pie
    # ──────────────────────────────────────────────────────────────────────
    count_df = (
        df["Status"]
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Count")
    )

    # ──────────────────────────────────────────────────────────────────────
    # 3. Layout: Pie (left) + Tables (right)
    # ──────────────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Status Distribution Pie")
        fig = px.pie(
            count_df,
            names="Status",
            values="Count",
            color="Status",
            color_discrete_map=status_colors,
        )
        fig.update_traces(textinfo="label+value", textposition="inside")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Due Today
        st.subheader("Due Today")
        due_today = df[due_today_mask].copy()
        if not due_today.empty:
            due_today["Qty"]         = due_today.apply(pick_qty, axis=1)
            due_today["Description"] = due_today["Description"].apply(flatten)
            disp_today = due_today[
                ["Type", "Ref#", "Description", "Qty", "Encargado", "Status"]
            ].copy()
            disp_today["Status"] = disp_today["Status"].apply(badge)
            st.markdown(
                disp_today.to_html(index=False, escape=False),
                unsafe_allow_html=True
            )
        else:
            st.info("No POs/SOs due today.")
        st.markdown("---")

        # Overdue
        st.subheader("Overdue")
        od = df[overdue_mask].copy()
        if not od.empty:
            od["Qty"]         = od.apply(pick_qty, axis=1)
            od["Description"] = od["Description"].apply(flatten)
            disp_od = od[
                ["Type", "Ref#", "Description", "Qty", "Encargado", "Status"]
            ].copy()
            disp_od["Status"] = disp_od["Status"].apply(badge)
            st.markdown(
                disp_od.to_html(index=False, escape=False),
                unsafe_allow_html=True
            )
        else:
            st.info("No overdue POs/SOs.")
            st.markdown("---")

    st.button("⬅ Back to Home", on_click=lambda: go_to("home"))

####

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from streamlit_autorefresh import st_autorefresh

# Assume helper functions are defined elsewhere in your app:
# add_request(data), load_data(), save_data(), delete_request(idx), go_to(page_name), format_status_badge(status)

if st.session_state.page == "requests":
    user = st.session_state.user_name

    # ─── DEFINE GROUPS ─────────────────────────────────────────────
    SALES_CREATORS    = {"Andres", "Tito", "Luz", "David", "John", "Sabrina", "Carolina"}
    TABLE_ONLY        = {"John", "Sabrina", "Carolina"}
    BODEGA            = {"Bodega", "Andres", "Tito", "Luz", "David"}
    PURCHASE_CREATORS = {"Andres", "Tito", "Luz", "David"}

    # ─── STATE FOR OVERLAYS ───────────────────────────────────────
    if "show_new_po" not in st.session_state:
        st.session_state.show_new_po = False
    if "show_new_so" not in st.session_state:
        st.session_state.show_new_so = False

    # ─── PURCHASE ORDER OVERLAY ─────────────────────────────────
    @st.dialog("💲 New Purchase Order", width="large")
    def purchase_order_dialog():
        if "purchase_item_rows" not in st.session_state:
            st.session_state.purchase_item_rows = 1
        st.session_state.purchase_item_rows = max(1, st.session_state.purchase_item_rows)

        st.markdown("""
        <style>
        .stTextInput > div > div > input,
        .stSelectbox > div, .stDateInput > div {
            background-color: #f7f9fc !important;
            border-radius: 12px !important;
            padding: 0.4rem !important;
            border: 1px solid #dfe6ec !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Header fields
        c1, c2 = st.columns(2)
        with c1:
            po_number    = st.text_input("Purchase Order#", placeholder="e.g. 12345")
            status_po    = st.selectbox("Status *", [" ", "COMPLETE", "READY", "CANCELLED", "IN TRANSIT"])
            encargado_po = st.selectbox("Encargado *", [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"])
        with c2:
            order_number = st.text_input("Tracking# (optional)", placeholder="e.g. TRK-45678")
            proveedor     = st.text_input("Proveedor", placeholder="e.g. Amazon")
            pago          = st.selectbox("Método de Pago", [" ", "Wire", "Cheque", "Credito", "Efectivo"])

        # Items + Cost per row
        st.markdown("### 🧾 Items to Order")
        descs, qtys, costs = [], [], []
        for i in range(st.session_state.purchase_item_rows):
            c_desc, c_qty, c_cost = st.columns([3, 2, 1])
            descs.append(c_desc.text_input(f"Description #{i+1}", key=f"po_desc_{i}"))
            qtys.append(c_qty.text_input(f"Quantity #{i+1}", key=f"po_qty_{i}"))
            costs.append(c_cost.text_input(f"Cost #{i+1}", placeholder="e.g. 1500", key=f"po_cost_{i}"))

        # Add/Remove rows
        ca2, cb2 = st.columns([1,1])
        with ca2:
            if st.button("➕ Add another item", key="add_purchase"):
                st.session_state.purchase_item_rows += 1
        with cb2:
            if st.session_state.purchase_item_rows > 1 and st.button("❌ Remove last item", key="remove_purchase"):
                st.session_state.purchase_item_rows -= 1

        # Shipping
        st.markdown("### 🚚 Shipping Information")
        c3, c4 = st.columns(2)
        with c3:
            order_date = st.date_input("Order Date", value=date.today())
        with c4:
            eta_date   = st.date_input("ETA Date")
        shipping_method = st.selectbox("Shipping Method", [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"])

        # Submit/Cancel
        col_submit, col_cancel = st.columns([2,1])
        with col_submit:
            if st.button("✅ Submit Purchase Request", use_container_width=True):
                # Clean inputs
                clean_descs = [d.strip() for d in descs if d.strip()]
                clean_qtys, clean_costs = [], []
                for q in qtys:
                    q = q.strip()
                    if q:
                        try:
                            clean_qtys.append(int(float(q)))
                        except:
                            clean_qtys.append(q)
                for c in costs:
                    c = c.strip()
                    if c:
                        try:
                            clean_costs.append(float(c))
                        except:
                            clean_costs.append(c)

                # Validate
                if not clean_descs or not clean_qtys or not clean_costs or status_po == " " or encargado_po == " ":
                    st.error("❗ Complete required fields.")
                else:
                    add_request({
                        "Type":"💲",
                        "Invoice": po_number,
                        "Order#": order_number,
                        "Date": str(order_date),
                        "Status": status_po,
                        "Shipping Method": shipping_method,
                        "ETA Date": str(eta_date),
                        "Description": clean_descs,
                        "Quantity": clean_qtys,
                        "Cost": clean_costs,
                        "Proveedor": proveedor,
                        "Encargado": encargado_po,
                        "Pago": pago
                    })
                    st.success("✅ Purchase request submitted.")
                    st.session_state.purchase_item_rows = 1
                    st.session_state.show_new_po       = False
                    st.rerun()
        with col_cancel:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_new_po = False
                st.rerun()

    # ─── SALES ORDER OVERLAY ───────────────────────────────────
    @st.dialog("🛒 New Sales Order", width="large")
    def sales_order_dialog():
        if "invoice_item_rows" not in st.session_state:
            st.session_state.invoice_item_rows = 1
        st.session_state.invoice_item_rows = max(1, st.session_state.invoice_item_rows)

        st.markdown(
            """
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

        d1, d2 = st.columns(2)
        with d1:
            order_number_so = st.text_input("Ref# (optional)", placeholder="e.g. SO-2025-001", key="so_ref")
            status_so       = st.selectbox("Status *", [" ", "COMPLETE", "READY", "CANCELLED", "IN TRANSIT"], key="so_status")
            encargado_so    = st.selectbox("Encargado *", [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"], key="so_encargado")
        with d2:
            tracking_so = st.text_input("Tracking# (optional)", placeholder="e.g. TRK45678", key="so_track")
            cliente     = st.text_input("Cliente", placeholder="e.g. TechCorp LLC", key="so_cliente")
            pago_so     = st.selectbox("Método de Pago", [" ", "Wire", "Cheque", "Credito", "Efectivo"], key="so_pago")

        st.markdown("### 🧾 Items to Invoice")
        ds, qs, prices = [], [], []
        for i in range(st.session_state.invoice_item_rows):
            sa, sb, sc = st.columns([3, 2, 1])
            ds.append(sa.text_input(f"Description #{i+1}", key=f"so_desc_{i}"))
            qs.append(sb.text_input(f"Quantity #{i+1}", key=f"so_qty_{i}"))
            prices.append(sc.text_input(f"Sale Price #{i+1}", placeholder="e.g. 2000", key=f"so_price_{i}"))

        sa2, sb2 = st.columns([1,1])
        with sa2:
            if st.button("➕ Add another item", key="add_invoice"):
                st.session_state.invoice_item_rows += 1
        with sb2:
            if st.session_state.invoice_item_rows > 1 and st.button("❌ Remove last item", key="remove_invoice"):
                st.session_state.invoice_item_rows -= 1

        st.markdown("### 🚚 Shipping Information")
        s1, s2 = st.columns(2)
        with s1:
            so_date = st.date_input("Order Date", value=date.today(), key="so_date")
        with s2:
            so_eta  = st.date_input("ETA Date", key="so_eta")
        so_ship = st.selectbox("Shipping Method", [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"], key="so_shipping")

        cs1, cs2 = st.columns([2,1])
        with cs1:
            if st.button("✅ Submit Sales Order", use_container_width=True):
                clean_ds = [d.strip() for d in ds if d.strip()]
                clean_qs, clean_prices = [], []
                for q in qs:
                    q = q.strip()
                    if q:
                        try:
                            clean_qs.append(int(float(q)))
                        except:
                            clean_qs.append(q)
                for p in prices:
                    p = p.strip()
                    if p:
                        try:
                            clean_prices.append(float(p))
                        except:
                            clean_prices.append(p)

                if not clean_ds or not clean_qs or not clean_prices or status_so == " " or encargado_so == " ":
                    st.error("❗ Complete required fields.")
                else:
                    add_request({
                        "Type":"🛒",
                        "Order#": order_number_so,
                        "Invoice": tracking_so,
                        "Date": str(so_date),
                        "Status": status_so,
                        "Shipping Method": so_ship,
                        "ETA Date": str(so_eta),
                        "Description": clean_ds,
                        "Quantity": clean_qs,
                        "Sale Price": clean_prices,
                        "Cliente": cliente,
                        "Encargado": encargado_so,
                        "Pago": pago_so
                    })
                    st.success("✅ Sales order submitted.")
                    st.session_state.invoice_item_rows = 1
                    st.session_state.show_new_so    = False
                    st.rerun()
        with cs2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_new_so = False
                st.rerun()

    # ─── HEADER + AUTO-REFRESH ─────────────────────────────────
    st.markdown("# 📋 All Purchase/Sales Orders")
    st.markdown("---")
    _ = st_autorefresh(interval=1000, limit=None, key="requests_refresh")
    load_data()

    # ─── FIRE OVERLAYS IF REQUESTED ─────────────────────────
    if st.session_state.show_new_po:
        purchase_order_dialog()
    if st.session_state.show_new_so:
        sales_order_dialog()

    # ─── FILTERS ───────────────────────────────────────────
    col1, col2, col3 = st.columns([3,2,2])
    with col1:
        search_term = st.text_input("Search", placeholder="Search requests…")
    with col2:
        status_filter = st.selectbox(
            "Status", ["All","Imprimir","Impresa","Separar y Confirmar","Recibido / Procesando","Pendiente","Separado - Pendiente","COMPLETE","READY","CANCELLED","IN TRANSIT"]
        )
    with col3:
        type_filter = st.selectbox("Request type", ["All","💲 Purchase","🛒 Sales"])

    # ─── ACCESS-BASED BASE LIST ─────────────────────────────
    all_requests = st.session_state.requests
    if user in BODEGA:
        base_requests = all_requests
    else:
        base_requests = [r for r in all_requests if r.get("Type") == "🛒"]

    # ─── BUILD & SORT FILTERED LIST ────────────────────────
    filtered_requests = [
        r for r in base_requests
        if r.get("Type") != "📑"
           and search_term.lower() in json.dumps(r).lower()
           and (status_filter == "All" or r.get("Status","").upper() == status_filter)
           and (type_filter   == "All" or r.get("Type") == type_filter.split()[0])
    ]
    def parse_eta(r):
        try:
            return datetime.strptime(r["ETA Date"], "%Y-%m-%d").date()
        except:
            return date.max
    filtered_requests = sorted(filtered_requests, key=parse_eta)

    # ─── EXPORT + NEW BUTTONS ─────────────────────────────
    col_exp, col_po, col_so = st.columns([3,1,1])
    with col_exp:
        csv_data = pd.DataFrame([...]).to_csv(index=False).encode("utf-8")  # existing export logic
        st.download_button("📥 Export Filtered Requests to CSV", csv_data, "requests_export.csv", "text/csv", use_container_width=True)

    # ─── NEW PURCHASE/SALES ORDER BUTTONS ─────────────────
    with col_po:
        if user in PURCHASE_CREATORS:
            if st.button("💲 New Purchase Order", use_container_width=True):
                st.session_state.show_new_po = True
                st.rerun()
        else:
            st.button("💲 New Purchase Order", disabled=True, use_container_width=True)
    with col_so:
        if user in SALES_CREATORS:
            if st.button("🛒 New Sales Order", use_container_width=True):
                st.session_state.show_new_so = True
                st.rerun()
        else:
            st.button("🛒 New Sales Order", disabled=True, use_container_width=True)

    # ─── DISPLAY TABLE ───────────────────────────────────
    if filtered_requests:
        st.markdown("""
        <style>
        .header-row { font-weight:bold; font-size:18px; padding:0.5rem 0; }
        .type-icon  { font-size:18px; }
        .unread-badge { background-color:#2ecc71; color:#fff; padding:4px 8px; border-radius:12px; display:inline-block; }
        .overdue-icon { color:#e74c3c; font-weight:600; font-size:14px; margin-left:6px; vertical-align:middle; }
        </style>
        """, unsafe_allow_html=True)

        today = date.today()
        allowed_users = {"Andres", "Luz", "Tito", "David"}

        def render_table(requests_list):
            # Determine columns
            if user in allowed_users:
                widths = [1,1,2,2,1,2,2,2,2,2,2,1]
                headers = ["","Type","Ref#","Description","Qty","Cost/Sales Price","Status","Ordered Date","ETA Date","Shipping Method","Encargado",""]
            else:
                widths = [1,1,2,3,1,2,2,2,2,2,1]
                headers = ["","Type","Ref#","Description","Qty","Status","Ordered Date","ETA Date","Shipping Method","Encargado",""]

            # Header
            cols_hdr = st.columns(widths)
            for c,h in zip(cols_hdr, headers):
                c.markdown(f"<div class='header-row'>{h}</div>", unsafe_allow_html=True)

            for req in requests_list:
                idx = st.session_state.requests.index(req)
                cols = st.columns(widths)

                # Unread badge
                comments_list = st.session_state.comments.get(str(idx), [])
                for c in comments_list:
                    c.setdefault("read_by", [])
                unread_cnt = sum(1 for c in comments_list if user not in c["read_by"] and c.get("author") != user)
                cols[0].markdown(f"<span class='unread-badge'>💬{unread_cnt}</span>" if unread_cnt>0 else "", unsafe_allow_html=True)

                # Type icon
                cols[1].markdown(f"<span class='type-icon'>{req['Type']}</span>", unsafe_allow_html=True)
                # Ref#/Invoice
                cols[2].write(req.get("Invoice","") if req["Type"]=="💲" else req.get("Order#",""))
                # Description
                desc = req.get("Description",[])
                cols[3].write(", ".join(desc) if isinstance(desc,list) else desc)
                # Quantity
                qty = req.get("Quantity",[])
                cols[4].write(", ".join(map(str,qty)) if isinstance(qty,list) else qty)

                # Cost/Sales Price if allowed
                if user in allowed_users:
                    raw_list = req.get("Cost",[]) if req["Type"]=="💲" else req.get("Sale Price",[])
                    formatted = []
                    for v in raw_list:
                        try:
                            iv = int(float(v))
                            formatted.append(f"${iv}")
                        except:
                            formatted.append(str(v))
                    cols[5].write(", ".join(formatted))
                    status_idx = 6
                else:
                    status_idx = 5

                # Status + overdue
                stt = req.get("Status","").upper()
                eta = req.get("ETA Date","")
                try:
                    ed = datetime.strptime(eta, "%Y-%m-%d").date()
                except:
                    ed = None
                badge_html = format_status_badge(stt)
                if ed and ed < today and stt not in ("READY","CANCELLED"):
                    badge_html += "<abbr title='Overdue'><span class='overdue-icon'>⚠️</span></abbr>"
                cols[status_idx].markdown(badge_html, unsafe_allow_html=True)

                # Dates, shipping, encargado
                cols[status_idx+1].write(req.get("Date",""))
                cols[status_idx+2].write(eta)
                cols[status_idx+3].write(req.get("Shipping Method",""))
                cols[status_idx+4].write(req.get("Encargado",""))

                # Actions
                action_idx = len(widths)-1
                with cols[action_idx]:
                    a1, a2 = st.columns([1,1])
                    if a1.button("🔍", key=f"view_{idx}"):
                        for c in comments_list:
                            if c.get("author") != user and user not in c["read_by"]:
                                c["read_by"].append(user)
                        save_data()
                        st.session_state.selected_request = idx
                        go_to("detail")
                    if a2.button("❌", key=f"delete_{idx}"):
                        delete_request(idx)

        # Render tables
        if user == "Bodega":
            po_requests = [r for r in filtered_requests if r["Type"] == "💲"]
            so_requests = [r for r in filtered_requests if r["Type"] == "🛒"]
            st.subheader("📦 Purchase Orders")
            render_table(po_requests) if po_requests else st.warning("No matching purchase requests found.")
            st.markdown("---")
            st.subheader("🛒 Sales Orders")
            render_table(so_requests) if so_requests else st.warning("No matching sales requests found.")
        else:
            render_table(filtered_requests)
    else:
        st.warning("No matching requests found.")

    # ─── BACK TO HOME ─────────────────────────────────────────
    if st.button("⬅ Back to Home"):
        go_to("home") 

####
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import os
from datetime import datetime, date

# Assume these helper functions are defined elsewhere in your app:
# add_comment(index, author, text, attachment)
# save_data()
# delete_request(index)
# go_to(page_name)

UPLOADS_DIR = "uploads"  # path to your uploads directory

# -------------------------------------------
# ---------- REQUEST DETAILS PAGE -----------
# -------------------------------------------
if st.session_state.page == "detail":
    # Auto‑refresh comments every second
    _ = st_autorefresh(
        interval=1000,
        limit=None,
        key=f"detail_comments_refresh_{st.session_state.selected_request}"
    )

    # Validate selection
    index = st.session_state.selected_request
    if index is None or index >= len(st.session_state.requests):
        st.error("Invalid request selected.")
        st.stop()

    request = st.session_state.requests[index]
    updated_fields = {}
    is_purchase = (request.get("Type") == "💲")

    # Should Bodega see prices?
    hide_prices = (st.session_state.user_name == "Bodega")

    # ─────────── SIDEBAR ───────────
    with st.sidebar:
        st.markdown("### 📄 Order Information")

        # Ref# / Order#
        order_number_val = request.get("Order#", "")
        order_number = st.text_input("Ref#", order_number_val, key="detail_Order#")
        if order_number != order_number_val:
            updated_fields["Order#"] = order_number

        # Status
        status_opts = [
            " ", "Imprimir", "Impresa", "Separar y Confirmar",
            "Recibido / Procesando", "Pendiente", "Separado - Pendiente",
            "Ready", "Complete", "Returned/Cancelled"
        ]
        curr_status = request.get("Status", " ")
        if curr_status not in status_opts:
            curr_status = " "
        status = st.selectbox(
            "Status", status_opts,
            index=status_opts.index(curr_status),
            key="detail_Status"
        )
        if status != curr_status:
            updated_fields["Status"] = status

        # Tracking# / Invoice
        invoice_val = request.get("Invoice", "")
        invoice = st.text_input("Tracking#", invoice_val, key="detail_Invoice")
        if invoice != invoice_val:
            updated_fields["Invoice"] = invoice

        # Proveedor vs Cliente
        partner_label = "Proveedor" if is_purchase else "Cliente"
        partner_val = request.get(partner_label, "")
        partner = st.text_input(partner_label, partner_val, key=f"detail_{partner_label}")
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
        
        # ─── 🧾 Items (Description / Qty / Price) ─────────────────
        st.markdown("### 🧾 Items")
        descs = request.get("Description", [])
        qtys  = request.get("Quantity", [])
        # cost vs sale price field name
        price_key = "Cost" if is_purchase else "Sale Price"
        prices = request.get(price_key, [])

        new_descs, new_qtys, new_prices = [], [], []
        for i, (d, q, p) in enumerate(zip(descs, qtys, prices)):
            c1, c2, c3 = st.columns([3, 1, 1])
            new_d = c1.text_input(f"Description #{i+1}", d, key=f"detail_desc_{i}")
            new_q = c2.text_input(f"Qty #{i+1}", q, key=f"detail_qty_{i}")
            
            # hide price input for Bodega
            if hide_prices:
                c3.markdown("**—**")
                new_p = p
            else:
                new_p = c3.text_input(f"{price_key} #{i+1}", p, key=f"detail_price_{i}")

            new_descs.append(new_d)
            new_qtys.append(new_q)
            new_prices.append(new_p)

        # detect changes to the items arrays
        if new_descs != descs:
            updated_fields["Description"] = new_descs
        if new_qtys != qtys:
            # convert back to ints where possible
            try:
                updated_fields["Quantity"] = [int(x) for x in new_qtys]
            except:
                updated_fields["Quantity"] = new_qtys
        if new_prices != prices:
            # convert back to floats where possible
            try:
                updated_fields[price_key] = [float(x) for x in new_prices]
            except:
                updated_fields[price_key] = new_prices

        st.markdown("### 🚚 Shipping Information")

        # Order Date
        date_val = request.get("Date", str(date.today()))
        order_date = st.date_input(
            "Order Date",
            value=pd.to_datetime(date_val),
            key="detail_Date"
        )
        if str(order_date) != date_val:
            updated_fields["Date"] = str(order_date)

        # ETA Date
        eta_val = request.get("ETA Date", str(date.today()))
        eta_date = st.date_input(
            "ETA Date",
            value=pd.to_datetime(eta_val),
            key="detail_ETA"
        )
        if str(eta_date) != eta_val:
            updated_fields["ETA Date"] = str(eta_date)

        # Shipping Method
        ship_val = request.get("Shipping Method", " ")
        shipping_method = st.selectbox(
            "Shipping Method",
            [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"],
            index=[" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"].index(ship_val),
            key="detail_Shipping"
        )
        if shipping_method != ship_val:
            updated_fields["Shipping Method"] = shipping_method

        st.markdown("---")
        # Save / Delete / Back
        if updated_fields and st.button("💾 Save Changes", use_container_width=True):
            request.update(updated_fields)
            st.session_state.requests[index] = request
            save_data()
            st.success("✅ Changes saved.")
            st.rerun()

        if st.button("🗑️ Delete Request", use_container_width=True):
            delete_request(index)

        if st.button("⬅ Back to All Requests", use_container_width=True):
            go_to("requests")

    # ─────────── MAIN AREA: COMMENTS ───────────
    st.markdown("## 💬 Comments")
    col_l, col_center, col_r = st.columns([1, 6, 1])
    with col_center:
        # inject CSS for chat bubbles layout
        st.markdown("""
            <style>
                .chat-author-in    { font-size:12px; color:#555; margin:4px 0 0 5px; clear:both; }
                .chat-author-out   { font-size:12px; color:#888; margin:4px 5px 0 0; clear:both; text-align:right; }
                .chat-bubble       { padding:8px 12px; border-radius:16px; max-width:60%; margin:2px 0; clear:both; word-wrap:break-word; }
                .chat-timestamp    { font-size:10px; color:#888; margin:2px 0 8px; clear:both; }
                .chat-attachment   { background:#DDEEFF; color:#003366; padding:8px 12px; border-radius:8px; float:left; max-width:60%; margin:4px 0; clear:both; word-wrap:break-word; }
                .attachment-link   { color:#003366; text-decoration:none; font-weight:600; }
                .clearfix          { clear:both; }
            </style>
        """, unsafe_allow_html=True)

        existing_comments = st.session_state.comments.get(str(index), [])
        # build author→color mapping
        authors = []
        for c in existing_comments:
            if c["author"] not in authors:
                authors.append(c["author"])
        base_colors = ["#D1E8FF", "#FFD1DC", "#DFFFD6", "#FFFACD", "#E0E0E0"]
        color_map = {a: base_colors[i % len(base_colors)] for i, a in enumerate(authors)}

        for comment in existing_comments:
            author = comment["author"]
            text = comment.get("text", "")
            when = comment.get("when", "")
            attachment = comment.get("attachment", None)
            align = "right" if author == st.session_state.user_name else "left"
            cls = "out" if author == st.session_state.user_name else "in"

            # author label
            st.markdown(
                f'<div class="chat-author-{cls}" style="text-align:{align};">{author}</div>',
                unsafe_allow_html=True
            )

            # attachment
            if attachment:
                file_path = os.path.join(UPLOADS_DIR, attachment)
                st.markdown(
                    f'<div class="chat-attachment" style="float:{align};">'
                    f'📎 <a href="/{file_path}" class="attachment-link" download>{attachment}</a>'
                    f'</div>'
                    f'<div class="chat-timestamp" style="text-align:{align};">{when}</div>'
                    f'<div class="clearfix"></div>',
                    unsafe_allow_html=True
                )

            # text bubble
            if text:
                bg = color_map.get(author, "#EDEDED")
                text_color = "#FFF" if cls == "out" else "#000"
                st.markdown(
                    f'<div class="chat-bubble" style="background:{bg}; color:{text_color}; float:{align};">{text}</div>'
                    f'<div class="chat-timestamp" style="text-align:{align};">{when}</div>'
                    f'<div class="clearfix"></div>',
                    unsafe_allow_html=True
                )

        st.markdown("---")

        # Send on Enter callback
        def send_on_enter():
            msg = st.session_state[text_key].strip()
            if msg:
                add_comment(index, st.session_state.user_name, msg)
                st.session_state[text_key] = ""
                st.rerun()

        # text input that submits on Enter
        text_key = f"new_msg_{index}"
        st.text_input(
            "Type your message here…",
            key=text_key,
            on_change=send_on_enter,
            placeholder="Press enter to send"
        )

        # File uploader button
        uploaded_file = st.file_uploader(
            "Attach PDF, PNG or XLSX:",
            type=["pdf", "png", "xlsx"],
            key=f"fileuploader_{index}"
        )
        _, cu = st.columns([1, 1])
        with cu:
            if st.button("Upload File", key=f"upload_file_{index}") and uploaded_file:
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                fn = f"{index}_{ts}_{uploaded_file.name}"
                with open(os.path.join(UPLOADS_DIR, fn), "wb") as f:
                    f.write(uploaded_file.getbuffer())
                add_comment(index, st.session_state.user_name, "", attachment=fn)
                st.success(f"Uploaded: {uploaded_file.name}")
                st.rerun()




####

elif st.session_state.page == "req_list":
    import streamlit as st
    import pandas as pd
    import json
    from datetime import datetime, date
    from streamlit_autorefresh import st_autorefresh

    # ─── Helper functions assumed defined elsewhere:
    # add_request(request_dict)
    # save_data()
    # delete_request(index)
    # load_data()

    # ─── PERSIST DIALOG STATE ─────────────────────────────────────
    if "show_new_req" not in st.session_state:
        st.session_state.show_new_req = False

    # ─── OVERLAY: NEW REQ FORM ─────────────────────────────────────
    @st.dialog(" 📄 Nuevo Requerimiento", width="large")
    def new_req_dialog():
        st.markdown("""
        <style>
            h1,h2,h3,label { font-size:34px!important; }
            .stTextInput>label,
            .stDateInput>label,
            .stSelectbox>label { font-size:24px!important; }
            .stTextInput input,
            .stDateInput input,
            .stSelectbox .css-1n76uvr { font-size:18px!important; }
            button { font-size:18px!important; }
        </style>
        """, unsafe_allow_html=True)

        if "req_item_count" not in st.session_state:
            st.session_state.req_item_count = 1

        c_add, c_rem = st.columns([1,1])
        if c_add.button("➕ Add Item", key="req_add_item"):
            st.session_state.req_item_count += 1
            st.rerun()
        if c_rem.button("➖ Remove Item", key="req_remove_item") and st.session_state.req_item_count > 1:
            st.session_state.req_item_count -= 1
            st.rerun()

        items = []
        for i in range(st.session_state.req_item_count):
            c1, c2, c3 = st.columns([3,2,1])
            desc   = c1.text_input("Description", key=f"req_desc_{i}")
            target = c2.text_input("Target Price", key=f"req_target_{i}")
            qty_in = c3.text_input("QTY",           key=f"req_qty_{i}")
            try:
                qty = int(qty_in) if qty_in != "" else ""
            except:
                qty = qty_in
            items.append({
                "Description": desc,
                "Target Price": target,
                "QTY": qty
            })

        col_v, col_c, col_dt, col_st = st.columns([2,2,2,2])
        vendedores  = [" ", "John","Andres","Luz","Tito","Marcela","Carolina","Sabrina"]
        compradores = [" ", "David","Andres","Thea","Tito","Luz"]
        sel_v = col_v.selectbox("Vendedor",   vendedores,   key="req_vendedor")
        sel_c = col_c.selectbox("Comprador",  compradores,  key="req_comprador")
        dt    = col_dt.date_input("Date", value=date.today(), key="req_fecha")
        stt   = col_st.selectbox(
            "Status",
            ["OPEN", "PURCHASE TEAM REVIEW", "SALES TEAM REVIEW", "CLOSED W", "CLOSED L"],
            key="req_status"
        )

        send_col, cancel_col = st.columns([2,1])
        with send_col:
            if st.button("✅ Enviar Requerimiento", key="req_submit", use_container_width=True):
                cleaned = [it for it in items if it["Description"].strip()]
                if not cleaned or sel_c == " ":
                    st.error("❗ Completa al menos una descripción y el campo Comprador.")
                else:
                    add_request({
                        "Type": "📑",
                        "Items": cleaned,
                        "Vendedor Encargado": sel_v,
                        "Comprador Encargado": sel_c,
                        "Fecha": str(dt),
                        "Status": stt
                    })
                    new_idx = len(st.session_state.requests) - 1
                    st.session_state.comments[str(new_idx)] = []
                    save_data()
                    st.success("✅ Requerimiento enviado.")
                    st.session_state.req_item_count = 1
                    st.session_state.show_new_req = False
                    st.rerun()
        with cancel_col:
            if st.button("❌ Cancel", key="req_cancel", use_container_width=True):
                st.session_state.show_new_req = False
                st.rerun()

    # ─── MAIN LIST UI ────────────────────────────────────────────────
    st.markdown("# 📝 Requerimientos Clientes")
    st.markdown("<hr>", unsafe_allow_html=True)
    _ = st_autorefresh(interval=1000, limit=None, key="req_list_refresh")

    load_data()

    col1, col2 = st.columns([3,1])
    search_term   = col1.text_input("Search",    placeholder="Search requirements...")
    status_filter = col2.selectbox(
        "Status",
        ["All", "OPEN", "PURCHASE TEAM REVIEW", "SALES TEAM REVIEW", "CLOSED W", "CLOSED L"],
        key="req_list_status"
    )

    def parse_fecha(r):
        try:
            return datetime.strptime(r.get("Fecha",""), "%Y-%m-%d").date()
        except:
            return date.max

    # Define status ordering so CLOSED always at bottom
    status_order = {
        "OPEN": 0,
        "PURCHASE TEAM REVIEW": 1,
        "SALES TEAM REVIEW": 2,
        "CLOSED W": 3,
        "CLOSED L": 4
    }

    # Filter and sort
    reqs = [
        r for r in st.session_state.requests
        if r.get("Type")=="📑"
           and (search_term.lower() in str(r).lower())
           and (status_filter=="All" or r.get("Status","OPEN")==status_filter)
    ]
    reqs = sorted(
        reqs,
        key=lambda r: (status_order.get(r.get("Status","OPEN"), 0), parse_fecha(r))
    )

    flat = []
    for r in reqs:
        for itm in r.get("Items", []):
            flat.append({
                "Type":         r["Type"],
                "Description":  itm["Description"],
                "Target Price": itm["Target Price"],
                "Qty":          itm["QTY"],
                "Vendedor":     r.get("Vendedor Encargado",""),
                "Comprador":    r.get("Comprador Encargado",""),
                "Status":       r.get("Status","OPEN"),
                "Date":         r.get("Fecha",""),
                "_req_obj":     r
            })

    df_export = pd.DataFrame([
        {k:v for k,v in row.items() if not k.startswith("_")}
        for row in flat
    ])

    col_export, col_new, col_all = st.columns([3,1,1])
    with col_export:
        st.download_button(
            "📥 Export Filtered Requests to CSV",
            df_export.to_csv(index=False).encode("utf-8"),
            "req_requests.csv","text/csv",
            use_container_width=True
        )
    with col_new:
        if st.button("➕ New Requirement", key="nav_new_req", use_container_width=True):
            st.session_state.show_new_req = True
            st.rerun()
    with col_all:
        if st.button("📋 All Purchase/Sales Orders", key="nav_all_req", use_container_width=True):
            st.session_state.page = "requests"
            st.rerun()

    if st.session_state.show_new_req:
        new_req_dialog()

    if reqs:
        # ─── Table styling & headers ───────────────────
        st.markdown("""
        <style>
          .header-row            { font-weight:bold; font-size:18px; padding:0.5rem 0; }
          .type-icon             { font-size:20px; }
          .status-open           { background-color:#2ecc71; color:#fff; padding:4px 8px; border-radius:12px; display:inline-block; }
          .status-purchase-review{ background-color:#007BFF; color:#fff; padding:4px 8px; border-radius:12px; display:inline-block; }
          .status-sales-review   { background-color:#FD7E14; color:#fff; padding:4px 8px; border-radius:12px; display:inline-block; }
          .status-closed         { background-color:#e74c3c; color:#fff; padding:4px 8px; border-radius:12px; display:inline-block; }
        </style>
        """, unsafe_allow_html=True)

        hdr_cols = st.columns([0.5,0.5,2,1,1,1,1,1.5,1,1])
        headers  = ["","Type","Description","Target Price","Qty","Vendedor","Comprador","Status","Date",""]
        for c,h in zip(hdr_cols, headers):
            c.markdown(f"<div class='header-row'>{h}</div>", unsafe_allow_html=True)

        user = st.session_state.user_name
        for i, row in enumerate(flat):
            cols = st.columns([0.5,0.5,2,1,1,1,1,1.5,1,1])
            idx  = st.session_state.requests.index(row["_req_obj"])

            # compute unread comment count
            comments_list = st.session_state.comments.get(str(idx), [])
            unread_cnt = sum(
                1 for c in comments_list
                  if c.get("author","") != user
                     and user not in c.get("read_by", [])
            )
            cols[0].markdown(
                f"<span class='status-open'>💬{unread_cnt}</span>" if unread_cnt>0 else "",
                unsafe_allow_html=True
            )

            # render row cells
            cols[1].markdown(f"<span class='type-icon'>{row['Type']}</span>", unsafe_allow_html=True)
            cols[2].write(row['Description'])
            cols[3].write(f"${row['Target Price']}")
            cols[4].write(str(row['Qty']))
            cols[5].write(row['Vendedor'])
            cols[6].write(row['Comprador'])

            status = row['Status']
            if status == "OPEN":
                html = "<span class='status-open'>OPEN</span>"
            elif status == "PURCHASE TEAM REVIEW":
                html = "<span class='status-purchase-review'>PURCHASE TEAM REVIEW</span>"
            elif status == "SALES TEAM REVIEW":
                html = "<span class='status-sales-review'>SALES TEAM REVIEW</span>"
            elif status in ["CLOSED W", "CLOSED L"]:
                html = f"<span class='status-closed'>{status}</span>"
            else:
                html = status
            cols[7].markdown(html, unsafe_allow_html=True)

            cols[8].write(row['Date'])

            # action buttons
            with cols[9]:
                a1, a2 = st.columns([1,1])
                if a1.button("🔍", key=f"view_{i}", use_container_width=True):
                    for c in comments_list:
                        if c.get("author","") != user:
                            c.setdefault("read_by", [])
                            if user not in c["read_by"]:
                                c["read_by"].append(user)
                    save_data()
                    st.session_state.selected_request = idx
                    st.session_state.page = "req_detail"
                    st.rerun()

                if a2.button("❌", key=f"del_{i}", use_container_width=True):
                    delete_request(idx)
                    st.rerun()
    else:
        st.info("No hay requerimientos que coincidan.")

    st.markdown("---")
    if st.button("⬅ Back to Home", key="req_list_back"):
        st.session_state.page = "home"
        st.rerun()


########## 

elif st.session_state.page == "req_detail":
    import os
    import pandas as pd
    from datetime import date, datetime
    from streamlit_autorefresh import st_autorefresh

    # ─── Callback for submitting comments on Enter ─────────────────
    def _submit_comment(idx, key):
        new_msg = st.session_state[key].strip()
        if new_msg:
            add_comment(idx, st.session_state.user_name, new_msg)
            st.session_state[key] = ""
            st.rerun()

    # ─── Auto‐refresh every second ─────────────────────────────────
    _ = st_autorefresh(interval=1000, limit=None, key="requests_refresh")
    load_data()

    idx     = st.session_state.selected_request
    request = st.session_state.requests[idx]
    updated = {}

    UPLOADS_DIR = "uploads"  # make sure this exists

    # ─── Sidebar styling & header ────────────────────────────────
    st.markdown("""
    <style>
      [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { font-size:24px!important; }
      [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { font-size:16px!important; }
      button { font-size:16px!important; }
    </style>
    """, unsafe_allow_html=True)
    st.sidebar.markdown("### 📄 Requerimientos Clientes Details")

    # ─── STATUS ────────────────────────────────────────────────────
    original_status = request.get("Status", "OPEN")
    status_map = {"CLOSED": "CLOSED W"}
    current_status = status_map.get(original_status, original_status)
    status_options = ["OPEN", "PURCHASE TEAM REVIEW", "SALES TEAM REVIEW", "CLOSED W", "CLOSED L"]
    status = st.sidebar.selectbox("Status", status_options,
                                 index=status_options.index(current_status) if current_status in status_options else 0,
                                 key="req_detail_status")
    if status != original_status:
        updated["Status"] = status

    # ─── CLOSE L REASON ────────────────────────────────────────────
    if status == "CLOSED L":
        reason_default = request.get("Close L Reason", "")
        reason = st.sidebar.text_area("Reason for Closure (L)", value=reason_default, key="req_detail_reason_l")
        if reason != reason_default:
            updated["Close L Reason"] = reason

    # ─── ITEMS ─────────────────────────────────────────────────────
    items = request.get("Items", [])
    if "items_count" not in st.session_state:
        st.session_state["items_count"] = max(1, len(items))
    st.sidebar.markdown("### 📋 Items")
    ca, cr = st.sidebar.columns([1, 1])
    if ca.button("➕ Add Item", key="req_detail_add"):
        st.session_state["items_count"] += 1
    if cr.button("➖ Remove Item", key="req_detail_remove") and st.session_state["items_count"] > 1:
        st.session_state["items_count"] -= 1

    new_items = []
    for i in range(st.session_state["items_count"]):
        c1, c2, c3 = st.sidebar.columns([3, 2, 1])
        dv = items[i] if i < len(items) else {"Description": "", "Target Price": "", "QTY": ""}
        desc = c1.text_input("Description", value=dv["Description"], key=f"req_detail_desc_{i}")
        targ = c2.text_input("Target Price", value=dv["Target Price"], key=f"req_detail_target_{i}")
        qty_in = c3.text_input("QTY", value=str(dv["QTY"]), key=f"req_detail_qty_{i}")
        try:
            qty = int(qty_in) if qty_in != "" else ""
        except:
            qty = qty_in
        new_items.append({"Description": desc, "Target Price": targ, "QTY": qty})
    if new_items != items:
        updated["Items"] = new_items

    # ─── VENDEDOR & COMPRADOR ──────────────────────────────────────
    vendedores = [" ", "John", "Andres", "Luz", "Tito", "Marcela", "Carolina", "Sabrina"]
    compradores = [" ", "David", "Andres", "Thea", "Tito", "Luz"]
    cv, cc = st.sidebar.columns(2)
    vend0 = request.get("Vendedor Encargado", " ")
    comp0 = request.get("Comprador Encargado", " ")
    sel_v = cv.selectbox("Vendedor", vendedores,
                         index=vendedores.index(vend0) if vend0 in vendedores else 0,
                         key="req_detail_vendedor")
    sel_c = cc.selectbox("Comprador", compradores,
                         index=compradores.index(comp0) if comp0 in compradores else 0,
                         key="req_detail_comprador")
    if sel_v != vend0:
        updated["Vendedor Encargado"] = sel_v
    if sel_c != comp0:
        updated["Comprador Encargado"] = sel_c

    # ─── DATE ───────────────────────────────────────────────────────
    dt0 = request.get("Fecha", str(date.today()))
    dt = st.sidebar.date_input("Date", value=pd.to_datetime(dt0), key="req_detail_date")
    if str(dt) != dt0:
        updated["Fecha"] = str(dt)

    # ─── SAVE / DELETE / BACK ──────────────────────────────────────
    cs, cd, cb = st.sidebar.columns(3, gap="small")
    with cs:
        if updated and st.button("💾 Save", key="req_detail_save", use_container_width=True):
            if "Items" in updated:
                st.session_state["items_count"] = len(updated["Items"])
            request.update(updated)
            st.session_state.requests[idx] = request
            save_data()
            st.sidebar.success("✅ Saved")
    with cd:
        if st.button("🗑️ Delete", key="req_detail_delete", use_container_width=True):
            delete_request(idx)
    with cb:
        if st.button("⬅ Back", key="req_detail_back", use_container_width=True):
            st.session_state.page = "req_list"
            st.rerun()
    st.sidebar.markdown("---")

    # ─── MAIN AREA: COMMENTS ───────────────────────────────────────
    st.markdown("## 💬 Comments")
    col_l, col_center, col_r = st.columns([1, 6, 1])
    with col_center:
        st.markdown("""
        <style>
          .chat-author-in    { font-size:12px; color:#555; margin:4px 0 0 5px; clear:both; }
          .chat-author-out   { font-size:12px; color:#333; margin:4px 5px 0 0; clear:both; text-align:right; }
          .chat-bubble       { padding:8px 12px; border-radius:16px; max-width:60%; margin:2px 0; word-wrap:break-word; clear:both; }
          .chat-timestamp    { font-size:10px; color:#888; margin:2px 0 8px; }
          .chat-attachment   { background:#DDEEFF; color:#003366; padding:8px 12px; border-radius:8px; float:left; max-width:60%; margin:4px 0; clear:both; word-wrap:break-word; }
          .attachment-link   { color:#003366; text-decoration:none; font-weight:600; }
        </style>
        """, unsafe_allow_html=True)
        existing_comments = st.session_state.comments.get(str(idx), [])
        authors = []
        for c in existing_comments:
            if c["author"] not in authors:
                authors.append(c["author"])
        base_colors = ["#D1E8FF","#FFD1DC","#DFFFD6","#FFFACD","#E0E0E0"]
        color_map = {a: base_colors[i % len(base_colors)] for i,a in enumerate(authors)}
        for comment in existing_comments:
            author = comment["author"]
            text = comment.get("text", "")
            when = comment.get("when", "")
            attachment = comment.get("attachment", None)
            file_path = os.path.join(UPLOADS_DIR, attachment) if attachment else None
            bg = color_map.get(author, "#EDEDED")
            align = "right" if author == st.session_state.user_name else "left"
            float_dir = align
            cls = 'out' if author == st.session_state.user_name else 'in'
            # author label
            st.markdown(f'<div class="chat-author-{cls}" style="text-align:{align};">{author}</div>', unsafe_allow_html=True)
            if attachment:
                link_html = f'<a href="/{file_path}" class="attachment-link" download>{attachment}</a>'
                st.markdown(
                    f'<div class="chat-attachment" style="float:{float_dir};">📎 {link_html}</div>'
                    f'<div class="chat-timestamp" style="text-align:{align};">{when}</div>'
                    f'<div style="clear:both;"></div>',
                    unsafe_allow_html=True
                )
            if text:
                st.markdown(
                    f'<div class="chat-bubble" style="background:{bg}; float:{float_dir};">{text}</div>'
                    f'<div class="chat-timestamp" style="text-align:{align};">{when}</div>'
                    f'<div style="clear:both;"></div>',
                    unsafe_allow_html=True
                )
        st.markdown("---")
        text_key = f"new_msg_{idx}"
        st.text_input("Type your message here…", key=text_key, on_change=_submit_comment, args=(idx, text_key), placeholder="Press enter to send")
        uploaded_file = st.file_uploader("Attach PDF, PNG or XLSX:", type=["pdf","png","xlsx"], key=f"fileuploader_{idx}")
        _, cu = st.columns([1,1])
        with cu:
            if st.button("Upload File", key=f"upload_file_{idx}") and uploaded_file:
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                fn = f"{idx}_{ts}_{uploaded_file.name}"
                with open(os.path.join(UPLOADS_DIR, fn), "wb") as f:
                    f.write(uploaded_file.getbuffer())
                add_comment(idx, st.session_state.user_name, "", attachment=fn)
                st.success(f"Uploaded: {uploaded_file.name}")
                st.rerun()
    if "show_new_po" not in st.session_state: st.session_state.show_new_po=False
    if "show_new_so" not in st.session_state: st.session_state.show_new_so=False
    # ... rest unchanged ...

    # ... rest of your overlays and quick actions unchanged ...


    # ─── Quiénes pueden crear PO (igual que home) ───────────────
    PURCHASE_ALLOWED = {"Tito", "Andres", "Luz", "David"}

    # ─── PURCHASE ORDER OVERLAY ───────────────────────────────────
    @st.dialog("💲 New Purchase Order", width="large")
    def purchase_order_dialog():
        # ensure we have at least one row
        if "purchase_item_rows" not in st.session_state:
            st.session_state.purchase_item_rows = 1
        st.session_state.purchase_item_rows = max(1, st.session_state.purchase_item_rows)

        st.markdown("""
        <style>
        .stTextInput > div > div > input,
        .stSelectbox > div, .stDateInput > div {
            background-color: #f7f9fc !important;
            border-radius: 12px !important;
            padding: 0.4rem !important;
            border: 1px solid #dfe6ec !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Header fields
        c1, c2 = st.columns(2)
        with c1:
            po_number    = st.text_input("Purchase Order#", value="", placeholder="e.g. 12345")
            status_po    = st.selectbox("Status *", [" ", "COMPLETE", "READY", "CANCELLED", "IN TRANSIT"])
            encargado_po = st.selectbox("Encargado *", [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"])
        with c2:
            order_number = st.text_input("Tracking# (optional)", value="", placeholder="e.g. TRK-45678")
            proveedor     = st.text_input("Proveedor", value="", placeholder="e.g. Amazon")
            pago          = st.selectbox("Método de Pago", [" ", "Wire", "Cheque", "Credito", "Efectivo"])

        # Items + Cost per row
        st.markdown("### 🧾 Items to Order")
        descs, qtys, costs = [], [], []
        for i in range(st.session_state.purchase_item_rows):
            c_desc, c_qty, c_cost = st.columns([3, 2, 1])
            descs.append(c_desc.text_input(f"Description #{i+1}", key=f"po_desc_{i}"))
            qtys.append(c_qty.text_input(f"Quantity #{i+1}", key=f"po_qty_{i}"))
            costs.append(c_cost.text_input(f"Cost #{i+1}", placeholder="e.g. 1500", key=f"po_cost_{i}"))

        # Add/Remove rows
        ca2, cb2 = st.columns([1,1])
        with ca2:
            if st.button("➕ Add another item", key="add_purchase"):
                st.session_state.purchase_item_rows += 1
        with cb2:
            if st.session_state.purchase_item_rows > 1 and st.button("❌ Remove last item", key="remove_purchase"):
                st.session_state.purchase_item_rows -= 1

        # Shipping
        st.markdown("### 🚚 Shipping Information")
        c3, c4 = st.columns(2)
        with c3:
            order_date = st.date_input("Order Date", value=date.today())
        with c4:
            eta_date   = st.date_input("ETA Date")
        shipping_method = st.selectbox("Shipping Method", [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"])

        # Submit/Cancel
        col_submit, col_cancel = st.columns([2,1])
        with col_submit:
            if st.button("✅ Submit Purchase Request", use_container_width=True):
                # Clean inputs
                clean_descs = [d.strip() for d in descs if d.strip()]
                clean_qtys  = []
                for q in qtys:
                    q = q.strip()
                    if q:
                        try:
                            clean_qtys.append(int(float(q)))
                        except:
                            clean_qtys.append(q)
                clean_costs = []
                for c in costs:
                    c = c.strip()
                    if c:
                        try:
                            clean_costs.append(float(c))
                        except:
                            clean_costs.append(c)

                # Validate
                if not clean_descs or not clean_qtys or not clean_costs or status_po == " " or encargado_po == " ":
                    st.error("❗ Complete required fields.")
                else:
                    add_request({
                        "Type":"💲",
                        "Invoice": po_number,
                        "Order#": order_number,
                        "Date": str(order_date),
                        "Status": status_po,
                        "Shipping Method": shipping_method,
                        "ETA Date": str(eta_date),
                        "Description": clean_descs,
                        "Quantity": clean_qtys,
                        "Cost": clean_costs,
                        "Proveedor": proveedor,
                        "Encargado": encargado_po,
                        "Pago": pago
                    })
                    st.success("✅ Purchase request submitted.")
                    st.session_state.purchase_item_rows = 1
                    st.session_state.show_new_po       = False
                    st.rerun()
        with col_cancel:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_new_po = False
                st.rerun()

    # ─── SALES ORDER OVERLAY ───────────────────────────────────────
    @st.dialog("🛒 New Sales Order", width="large")
    def sales_order_dialog():
        # ensure we have at least one row
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

        # Header fields
        d1, d2 = st.columns(2)
        with d1:
            order_number_so = st.text_input("Ref# (optional)", value="", placeholder="e.g. SO-2025-001")
            status_so       = st.selectbox("Status *", [" ", "COMPLETE", "READY", "CANCELLED", "IN TRANSIT"])
            encargado_so    = st.selectbox("Encargado *", [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"])
        with d2:
            tracking_so = st.text_input("Tracking# (optional)", value="", placeholder="e.g. TRK45678")
            cliente     = st.text_input("Cliente", value="", placeholder="e.g. TechCorp LLC")
            pago_so     = st.selectbox("Método de Pago", [" ", "Wire", "Cheque", "Credito", "Efectivo"])

        # Items + Sale Price per row
        st.markdown("### 🧾 Items to Invoice")
        ds, qs, prices = [], [], []
        for i in range(st.session_state.invoice_item_rows):
            sa, sb, sc = st.columns([3, 2, 1])
            ds.append(sa.text_input(f"Description #{i+1}", key=f"so_desc_{i}"))
            qs.append(sb.text_input(f"Quantity #{i+1}", key=f"so_qty_{i}"))
            prices.append(sc.text_input(f"Sale Price #{i+1}", placeholder="e.g. 2000", key=f"so_price_{i}"))

        # Add/Remove rows
        sa2, sb2 = st.columns([1,1])
        with sa2:
            if st.button("➕ Add another item", key="add_invoice"):
                st.session_state.invoice_item_rows += 1
        with sb2:
            if st.session_state.invoice_item_rows > 1 and st.button("❌ Remove last item", key="remove_invoice"):
                st.session_state.invoice_item_rows -= 1

        # Shipping
        st.markdown("### 🚚 Shipping Information")
        s1, s2 , s3= st.columns(3)
        with s1:
            so_date = st.date_input("Order Date", value=date.today())
        with s2:
            so_eta  = st.date_input("ETA Date")
        so_ship = st.selectbox("Shipping Method", [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"])

        # Submit/Cancel
        cs1, cs2 = st.columns([2,1])
        with cs1:
            if st.button("✅ Submit Sales Order", use_container_width=True):
                # Clean inputs
                clean_ds = [d.strip() for d in ds if d.strip()]
                clean_qs = []
                for q in qs:
                    q = q.strip()
                    if q:
                        try:
                            clean_qs.append(int(float(q)))
                        except:
                            clean_qs.append(q)
                clean_prices = []
                for p in prices:
                    p = p.strip()
                    if p:
                        try:
                            clean_prices.append(float(p))
                        except:
                            clean_prices.append(p)

                # Validate
                if not clean_ds or not clean_qs or not clean_prices or status_so == " " or encargado_so == " ":
                    st.error("❗ Complete required fields.")
                else:
                    add_request({
                        "Type":"🛒",
                        "Order#": order_number_so,
                        "Invoice": tracking_so,
                        "Date": str(so_date),
                        "Status": status_so,
                        "Shipping Method": so_ship,
                        "ETA Date": str(so_eta),
                        "Description": clean_ds,
                        "Quantity": clean_qs,
                        "Sale Price": clean_prices,
                        "Cliente": cliente,
                        "Encargado": encargado_so,
                        "Pago": pago_so
                    })
                    st.success("✅ Sales order submitted.")
                    st.session_state.invoice_item_rows = 1
                    st.session_state.show_new_so    = False
                    st.rerun()
        with cs2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_new_so = False
                st.rerun()

    # ─── QUICK ACTIONS ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📝 Quick Actions")
    col_all, col_po, col_so = st.columns(3)
    user = st.session_state.user_name

    # — All Requests —
    with col_all:
        if st.button("📋 All Requests", use_container_width=True):
            st.session_state.page = "requests"
            st.rerun()

    # — New Purchase Order —
    with col_po:
        if user in PURCHASE_ALLOWED:
            if st.button("💲 New Purchase Order", use_container_width=True):
                st.session_state.show_new_po = True
                st.rerun()
        else:
            st.button("🔒 New Purchase Order", disabled=True, use_container_width=True)
            st.caption("No tienes permiso para crear órdenes de compra.")

    # — New Sales Order —
    with col_so:
        if st.button("🛒 New Sales Order", use_container_width=True):
            st.session_state.show_new_so = True
            st.rerun()

    # Show overlays
    if st.session_state.show_new_po:
        purchase_order_dialog()
    if st.session_state.show_new_so:
        sales_order_dialog()

