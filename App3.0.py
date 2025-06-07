import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import date, datetime
from streamlit_autorefresh import st_autorefresh
from datetime import datetime as _dt

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

# Example users (username: password)
VALID_USERS = {
    "andres": "2002",
    "marcela": "2002",
    "tito": "2002",
    "caro": "2002",
    "john": "2002",
    "thea": "2002",
    "luz": "2002",
    "david": "2002",
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
def load_data():
    # requests.json
    if os.path.exists(REQUESTS_FILE):
        try:
            with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
                contents = f.read().strip()
                st.session_state.requests = json.loads(contents) if contents else []
        except json.JSONDecodeError:
            st.session_state.requests = []
    else:
        st.session_state.requests = []
        with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

    # comments.json
    if os.path.exists(COMMENTS_FILE):
        try:
            with open(COMMENTS_FILE, "r", encoding="utf-8") as f:
                contents = f.read().strip()
                st.session_state.comments = json.loads(contents) if contents else {}
        except json.JSONDecodeError:
            st.session_state.comments = {}
    else:
        st.session_state.comments = {}
        with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

def save_data():
    with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.requests, f)
    with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.comments, f)

def add_request(data):
    idx = len(st.session_state.requests)
    st.session_state.requests.append(data)
    st.session_state.comments[str(idx)] = []
    save_data()

def add_comment(index, author, text="", attachment=None):
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
        # Re-index comments
        st.session_state.comments = {
            str(i): st.session_state.comments.get(str(i), [])
            for i in range(len(st.session_state.requests))
        }
        st.session_state.selected_request = None
        save_data()
        st.success("🗑️ Request deleted.")
        go_to("requests")

def go_to(page):
    st.session_state.page = page
    st.rerun()

# Initialize session state
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
            st.error("❌ Invalid credentials.")
    st.stop()

# -------------------------------------------
# ---------------- HOME PAGE ----------------
# -------------------------------------------
if st.session_state.page == "home":
    st.markdown("""<style>
        html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
        h1,h2,h3,h4 { color:#003366; font-weight:700; margin-bottom:0.5rem; }
        .logout-button { position:absolute; top:10px; right:10px; }
        div.stButton>button { background:#fff !important; border:1px solid #ccc !important; border-radius:10px; padding:0.6rem 1.2rem; font-weight:600; font-size:16px; color:#333; }
        div.stButton>button:hover { background:#f1f1f1 !important; border-color:#999 !important; }
    </style>""", unsafe_allow_html=True)

    if st.button("🚪 Log Out", key="logout"):
        st.session_state.authenticated = False
        st.session_state.user_name = ""
        st.session_state.page = "login"
        st.rerun()

    st.markdown("## 🏠 Welcome to the Help Center")
    st.markdown(f"Logged in as: **{st.session_state.user_name}**")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💲 Purchase Request", use_container_width=True):
            go_to("purchase")
    with c2:
        if st.button("🛒 Sales Order Request", use_container_width=True):
            go_to("sales_order")

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("📋 View All Requests", use_container_width=True):
        go_to("requests")

# -------------------------------------------
# -------------- PURCHASE PAGE  -------------
# -------------------------------------------
elif st.session_state.page == "purchase":
    st.markdown("## 💲 Purchase Request Form")
    st.markdown(f"Logged in as: **{st.session_state.user_name}**", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    if "purchase_item_rows" not in st.session_state:
        st.session_state.purchase_item_rows = 1

    st.markdown("""<style>
        .stTextInput>div>div>input,
        .stSelectbox>div, .stDateInput>div { background:#f7f9fc !important; border-radius:8px !important; padding:0.4rem !important; border:1px solid #dfe6ec !important; }
    </style>""", unsafe_allow_html=True)

    st.markdown("### 📄 Order Information")
    col1, col2 = st.columns(2)
    with col1:
        po_number = st.text_input("Purchase Order#", placeholder="e.g. 12345")
        status = st.selectbox("Status *", [" ", "PENDING", "ORDERED", "READY", "CANCELLED", "IN TRANSIT", "INCOMPLETE"])
        encargado = st.selectbox("Encargado *", [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"])
    with col2:
        order_number = st.text_input("Tracking# (optional)", placeholder="e.g. TRK-45678")
        proveedor = st.text_input("Proveedor", placeholder="e.g. Amazon")
        pago = st.selectbox("Método de Pago", [" ", "Wire", "Cheque", "Credito", "Efectivo"])

    st.markdown("### 🧾 Items to Order")
    descriptions, quantities = [], []
    for i in range(st.session_state.purchase_item_rows):
        cA, cB = st.columns(2)
        descriptions.append(cA.text_input(f"Description #{i+1}", key=f"po_desc_{i}"))
        quantities.append(cB.text_input(f"Quantity #{i+1}", key=f"po_qty_{i}"))

    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add another item", key="add_purchase"):
            st.session_state.purchase_item_rows += 1
    with crem:
        if st.session_state.purchase_item_rows > 1 and st.button("❌ Remove last item", key="remove_purchase"):
            st.session_state.purchase_item_rows -= 1

    st.markdown("### 🚚 Shipping Information")
    c3, c4 = st.columns(2)
    with c3:
        order_date = st.date_input("Order Date", value=date.today())
    with c4:
        eta_date = st.date_input("ETA Date")
    shipping_method = st.selectbox("Shipping Method", [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"])

    st.markdown("---")
    cs, cb = st.columns([2,1])
    with cs:
        if st.button("✅ Submit Purchase Request", use_container_width=True):
            descs = [d.strip() for d in descriptions if d.strip()]
            qtys = []
            for q in quantities:
                q = q.strip()
                if q:
                    try: qtys.append(int(float(q)))
                    except: qtys.append(q)
            if not descs or not qtys or status.strip()==" " or encargado.strip()==" ":
                st.error("❗ Complete required fields.")
            else:
                add_request({
                    "Type": "💲",
                    "Order#": order_number,
                    "Invoice": po_number,
                    "Date": str(order_date),
                    "Status": status,
                    "Shipping Method": shipping_method,
                    "ETA Date": str(eta_date),
                    "Description": descs,
                    "Quantity": qtys,
                    "Proveedor": proveedor,
                    "Encargado": encargado,
                    "Pago": pago
                })
                st.success("✅ Submitted.")
                st.session_state.purchase_item_rows = 1
                go_to("home")
    with cb:
        if st.button("⬅ Back to Home", use_container_width=True):
            go_to("home")

# -------------------------------------------
# --------- SALES ORDER REQUEST PAGE --------
# -------------------------------------------
elif st.session_state.page == "sales_order":
    st.markdown("## 🛒 Sales Order Request Form")
    st.markdown(f"Logged in as: **{st.session_state.user_name}**", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    if "invoice_item_rows" not in st.session_state:
        st.session_state.invoice_item_rows = 1

    st.markdown("""<style>
        .stTextInput>div>div>input,
        .stSelectbox>div, .stDateInput>div { background:#f7f9fc !important; border-radius:8px !important; padding:0.4rem !important; border:1px solid #dfe6ec !important; }
    </style>""", unsafe_allow_html=True)

    st.markdown("### 📄 Order Information")
    c1, c2 = st.columns(2)
    with c1:
        order_number = st.text_input("Ref# (optional)", placeholder="e.g. SO-2025-001")
        status = st.selectbox("Status *", [" ", "PENDING", "ORDERED", "READY", "CANCELLED", "IN TRANSIT", "INCOMPLETE"])
        encargado = st.selectbox("Encargado *", [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"])
    with c2:
        sales_order_number = st.text_input("Tracking# (optional)", placeholder="e.g. TRK45678")
        cliente = st.text_input("Cliente", placeholder="e.g. TechCorp LLC")
        pago = st.selectbox("Método de Pago", [" ", "Wire", "Cheque", "Credito", "Efectivo"])

    st.markdown("### 🧾 Items to Invoice")
    descs, qtys = [], []
    for i in range(st.session_state.invoice_item_rows):
        cA, cB = st.columns(2)
        descs.append(cA.text_input(f"Description #{i+1}", key=f"so_desc_{i}"))
        qtys.append(cB.text_input(f"Quantity #{i+1}", key=f"so_qty_{i}"))

    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add another item", key="add_invoice"):
            st.session_state.invoice_item_rows += 1
    with crem:
        if st.session_state.invoice_item_rows > 1 and st.button("❌ Remove last item", key="remove_invoice"):
            st.session_state.invoice_item_rows -= 1

    st.markdown("### 🚚 Shipping Information")
    c3, c4 = st.columns(2)
    with c3:
        order_date = st.date_input("Order Date", value=date.today())
    with c4:
        eta_date = st.date_input("ETA Date")
    shipping_method = st.selectbox("Shipping Method", [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"])

    st.markdown("---")
    cs, cb = st.columns([2,1])
    with cs:
        if st.button("✅ Submit Sales Order", use_container_width=True):
            descs_clean = [d.strip() for d in descs if d.strip()]
            qtys_clean = []
            for q in qtys:
                q = q.strip()
                if q:
                    try: qtys_clean.append(int(float(q)))
                    except: qtys_clean.append(q)
            if not descs_clean or not qtys_clean or status.strip()==" " or encargado.strip()==" ":
                st.error("❗ Complete required fields.")
            else:
                add_request({
                    "Type": "🛒",
                    "Order#": order_number,
                    "Invoice": sales_order_number,
                    "Date": str(order_date),
                    "Status": status,
                    "Shipping Method": shipping_method,
                    "ETA Date": str(eta_date),
                    "Description": descs_clean,
                    "Quantity": qtys_clean,
                    "Cliente": cliente,
                    "Encargado": encargado,
                    "Pago": pago
                })
                st.success("✅ Submitted.")
                st.session_state.invoice_item_rows = 1
                go_to("home")
    with cb:
        if st.button("⬅ Back to Home", use_container_width=True):
            go_to("home")

# -------------------------------------------
# -------- ALL REQUESTS / IMPORT & EXPORT ----
# -------------------------------------------
elif st.session_state.page == "requests":
    st.markdown(f"## 📋 All Requests   |   Logged in as: **{st.session_state.user_name}**")
    st.markdown("<hr>", unsafe_allow_html=True)

    # Auto‐refresh & reload
    _ = st_autorefresh(interval=1000, limit=None, key="requests_refresh")
    load_data()

    # Filters
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        search_term = st.text_input("Search", placeholder="Search requests…")
    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "PENDING", "IN TRANSIT", "READY", "CANCELLED", "CONFIRMED", "INCOMPLETE"]
        )
    with col3:
        type_filter = st.selectbox("Request type", ["All", "💲 Purchase", "🛒 Sales"])

    # Import CSV
    st.markdown("### ⬆️ Import Requests from CSV")
    upload_csv = st.file_uploader("Choose a requests CSV to import", type=["csv"])
    if upload_csv is not None:
        try:
            df = pd.read_csv(upload_csv)
            cols = [c.strip() for c in df.columns]

            def find(cands):
                return next((c for c in cols if any(c.lower() == d.lower() for d in cands)), None)

            order_col = find(["Order#", "Ref#", "Invoice"])
            track_col = find(["Tracking Number", "Tracking", "Trk"])
            qty_col   = find(["Quantity",   "Qty"])
            desc_col  = find(["Description"])
            date_col  = find(["Date",       "Ordered Date"])
            eta_col   = find(["ETA Date",   "ETA"])
            status_col= find(["Status"])
            ship_col  = find(["Shipping Method", "Ship Method"])
            enc_col   = find(["Encargado"])
            prov_col  = find(["Proveedor", "Client", "Cliente"])
            pago_col  = find(["Pago"])

            missing = [n for n,c in [
                ("order", order_col), ("qty", qty_col),
                ("date", date_col),  ("desc", desc_col),
                ("status", status_col), ("eta", eta_col)
            ] if c is None]
            if missing:
                st.error(f"❌ Missing columns {missing}. Found: {cols}")
            else:
                imported = []
                for _, row in df.iterrows():
                    req = {"Type": row.get("Type","")}
                    is_p = (req["Type"]=="💲")
                    if is_p:
                        req["Invoice"] = row.get(order_col,"")
                        req["Order#"]  = track_col and row.get(track_col,"") or ""
                    else:
                        req["Order#"]  = row.get(order_col,"")
                        req["Invoice"] = track_col and row.get(track_col,"") or ""

                    req["Date"]            = str(row.get(date_col,""))
                    req["ETA Date"]        = str(row.get(eta_col,""))
                    req["Status"]          = row.get(status_col,"")
                    req["Shipping Method"] = row.get(ship_col,"")
                    req["Encargado"]       = row.get(enc_col,"")

                    # Description list
                    desc_str = row.get(desc_col,"")
                    parts = re.split(r";|,", str(desc_str))
                    req["Description"] = [p.strip() for p in parts if p.strip()]

                    # Quantity list
                    qty_str = row.get(qty_col,"")
                    qparts = re.split(r";|,", str(qty_str))
                    qlist = []
                    for q in qparts:
                        q = q.strip()
                        try:    qlist.append(int(float(q)))
                        except: qlist.append(q)
                    req["Quantity"] = qlist

                    if prov_col:
                        if is_p: req["Proveedor"] = row.get(prov_col,"")
                        else:    req["Cliente"]   = row.get(prov_col,"")
                    if pago_col:
                        req["Pago"] = row.get(pago_col,"")

                    imported.append(req)

                st.session_state.requests = imported
                st.session_state.comments = { str(i): [] for i in range(len(imported)) }
                save_data()
                st.success(f"✅ Imported {len(imported)} requests.")
                go_to("requests")

        except Exception as e:
            st.error(f"❌ Failed to import CSV: {e}")

    # Build filtered list
    filtered_requests = []
    for req in st.session_state.requests:
        t = json.dumps(req).lower()
        if (search_term.lower() in t
            and (status_filter=="All" or req.get("Status","").upper()==status_filter)
            and (type_filter=="All" or req.get("Type")==type_filter.split()[0])
        ):
            filtered_requests.append(req)

    # Sort by ETA
    def parse_eta(r):
        try:
            return _dt.strptime(r.get("ETA Date",""), "%Y-%m-%d").date()
        except:
            return date.max
    filtered_requests.sort(key=parse_eta)

    # Export & table
    if filtered_requests:
        flat=[]
        for req in filtered_requests:
            row={"Type":req.get("Type","")}
            if req["Type"]=="💲":
                row["Order#"]=req.get("Invoice","")
                row["Tracking Number"]=req.get("Order#","")
            else:
                row["Order#"]=req.get("Order#","")
                row["Tracking Number"]=req.get("Invoice","")
            for k,v in req.items():
                kl=k.lower()
                if kl in ("order#","invoice","type"): continue
                row[k] = ";".join(str(x) for x in v) if isinstance(v,(list,tuple)) else v
            flat.append(row)

        df_export=pd.DataFrame(flat)
        data_bytes=df_export.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Export Filtered Requests to CSV",
            data=data_bytes,file_name="requests_export.csv",mime="text/csv")

        # (reuse your CSS + rendering loop here)
        # … your existing table-rendering code …

    else:
        st.warning("No matching requests found.")

    if st.button("⬅ Back to Home"):
        go_to("home")

# -------------------------------------------
# ---------- REQUEST DETAILS PAGE -----------
# -------------------------------------------
elif st.session_state.page == "detail":
    # auto-refresh
    _ = st_autorefresh(interval=1000, limit=None, key=f"refresh_{st.session_state.selected_request}")
    load_data()

    st.markdown("## 📂 Request Details")
    st.markdown(f"Logged in as: **{st.session_state.user_name}**", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    idx = st.session_state.selected_request
    if idx is None or idx >= len(st.session_state.requests):
        st.error("Invalid request selected."); st.stop()
    request = st.session_state.requests[idx]
    updated = {}

    is_purchase = (request.get("Type") == "💲")

    # Order Information
    with st.container():
        st.markdown("### 📄 Order Information")
        c1, c2 = st.columns(2)
        with c1:
            ord_val = request.get("Order#","")
            ord_in = st.text_input("Ref#", value=ord_val, key="detail_Order#")
            if ord_in != ord_val: updated["Order#"] = ord_in

            descs = request.get("Description",[])
            qtys  = request.get("Quantity",[])
            nrows = max(len(descs), len(qtys), 1)
            st.markdown("#### 📋 Items")
            new_desc, new_qty = [], []
            for i in range(nrows):
                d_val = descs[i] if i<len(descs) else ""
                q_val = qtys[i]  if i<len(qtys)  else ""
                da, db = st.columns(2)
                d_new = da.text_input(f"Description #{i+1}", value=d_val, key=f"detail_desc_{i}").strip()
                q_new_raw = db.text_input(f"Quantity #{i+1}", value=str(q_val), key=f"detail_qty_{i}").strip()
                try: q_new = int(float(q_new_raw)) if q_new_raw else ""
                except: q_new = q_new_raw
                new_desc.append(d_new); new_qty.append(q_new)
            if new_desc != descs: updated["Description"] = new_desc
            if new_qty  != qtys: updated["Quantity"]    = new_qty

            status_opts = [" ", "PENDING", "ORDERED", "READY", "CANCELLED", "IN TRANSIT", "INCOMPLETE"]
            cur_stat = request.get("Status"," ")
            if cur_stat not in status_opts: cur_stat = " "
            stat_in = st.selectbox("Status", status_opts, index=status_opts.index(cur_stat), key="detail_Status")
            if stat_in != cur_stat: updated["Status"] = stat_in

        with c2:
            inv_val = request.get("Invoice","")
            inv_in = st.text_input("Tracking#", value=inv_val, key="detail_Invoice")
            if inv_in != inv_val: updated["Invoice"] = inv_in

            partner_label = "Proveedor" if is_purchase else "Cliente"
            part_val = request.get(partner_label,"")
            part_in = st.text_input(partner_label, value=part_val, key=f"detail_{partner_label}")
            if part_in != part_val: updated[partner_label] = part_in

            pago_opts = [" ", "Wire", "Cheque", "Credito", "Efectivo"]
            pago_val = request.get("Pago"," ")
            pago_in = st.selectbox("Método de Pago", pago_opts, index=pago_opts.index(pago_val), key="detail_Pago")
            if pago_in != pago_val: updated["Pago"] = pago_in

            enc_opts = [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"]
            enc_val = request.get("Encargado"," ")
            enc_in = st.selectbox("Encargado", enc_opts, index=enc_opts.index(enc_val), key="detail_Encargado")
            if enc_in != enc_val: updated["Encargado"] = enc_in

    # Shipping Information
    with st.container():
        st.markdown("### 🚚 Shipping Information")
        c3, c4 = st.columns(2)
        with c3:
            d_val = request.get("Date", str(date.today()))
            d_in = st.date_input("Order Date", value=pd.to_datetime(d_val), key="detail_Date")
            if str(d_in) != d_val: updated["Date"] = str(d_in)
        with c4:
            eta_val = request.get("ETA Date", str(date.today()))
            eta_in = st.date_input("ETA Date", value=pd.to_datetime(eta_val), key="detail_ETA")
            if str(eta_in) != eta_val: updated["ETA Date"] = str(eta_in)

        ship_opts = [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"]
        ship_val = request.get("Shipping Method"," ")
        ship_in = st.selectbox("Shipping Method", ship_opts, index=ship_opts.index(ship_val), key="detail_Shipping")
        if ship_in != ship_val: updated["Shipping Method"] = ship_in

    # Save / Delete / Back
    st.markdown("---")
    cs, cd, cb = st.columns([2,1,1])
    with cs:
        if updated and st.button("💾 Save Changes", use_container_width=True):
            request.update(updated)
            st.session_state.requests[idx] = request
            save_data()
            st.success("✅ Changes saved.")
            st.rerun()
    with cd:
        if st.button("🗑️ Delete Request", use_container_width=True):
            delete_request(idx)
    with cb:
        if st.button("⬅ Back to All Requests", use_container_width=True):
            go_to("requests")

    # Comments Section
    st.markdown("""
    <style>
      .chat-container { padding:8px; background:#fff; border-radius:8px; }
      .chat-author-in { font-size:12px; font-weight:600; color:#555; margin:4px 0 2px 5px; text-align:left; clear:both; }
      .chat-author-out { font-size:12px; font-weight:600; color:#25D366; margin:4px 5px 2px 0; text-align:right; clear:both; }
      .chat-bubble-in, .chat-bubble-out { padding:10px 14px; border-radius:20px; margin:4px 0; max-width:60%; line-height:1.4; word-wrap:break-word; box-shadow:0 1px 3px rgba(0,0,0,0.1); position:relative; }
      .chat-bubble-in { background:#F1F0F0; color:#000; float:left; clear:both; }
      .chat-bubble-out { background:#DCF8C6; color:#000; float:right; clear:both; }
      .chat-timestamp { font-size:10px; color:#888; margin-top:2px; }
      .chat-attachment { background:#E0F7FA; color:#006064; padding:8px 12px; border-radius:12px; margin:6px 0; max-width:60%; float:left; clear:both; word-wrap:break-word; box-shadow:0 1px 2px rgba(0,0,0,0.08); }
      .clearfix { clear:both; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 💬 Comments (Chat-Style)")
    l, c, r = st.columns([1,6,1])
    with c:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for comment in st.session_state.comments.get(str(idx), []):
            author = comment["author"]
            text    = comment.get("text","")
            when    = comment.get("when","")
            attach  = comment.get("attachment", None)

            if attach:
                path = os.path.join(UPLOADS_DIR, attach)
                try:
                    with open(path,"rb") as f:
                        data = f.read()
                    st.download_button(f"📎 {attach}", data=data, file_name=attach, mime="application/octet-stream", key=f"dl_{idx}_{attach}")
                except FileNotFoundError:
                    st.error(f"⚠️ Attachment not found: {attach}")

            if text:
                if author == st.session_state.user_name:
                    st.markdown(f'<div class="chat-author-out">{author}</div><div class="chat-bubble-out">{text}</div><div class="chat-timestamp" style="text-align:right">{when}</div><div class="clearfix"></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="chat-author-in">{author}</div><div class="chat-bubble-in">{text}</div><div class="chat-timestamp" style="text-align:left">{when}</div><div class="clearfix"></div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")

        def _send_on_enter():
            msg = st.session_state[text_key]
            if msg.strip():
                add_comment(idx, st.session_state.user_name, msg.strip(), None)
                st.session_state[text_key] = ""
                st.rerun()

        text_key = f"new_msg_{idx}"
        st.text_input("Type your message…", key=text_key, on_change=_send_on_enter, placeholder="Press Enter to send")
        uploaded = st.file_uploader("Attach PDF, PNG or XLSX (then press Upload)", type=["pdf","png","xlsx"], key=f"fileuploader_{idx}")
        st.button("", key=f"dummy_{idx}")
        if st.button("Upload File", key=f"upload_file_{idx}"):
            if uploaded:
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                safe = f"{idx}_{ts}_{uploaded.name}"
                save_path = os.path.join(UPLOADS_DIR, safe)
                with open(save_path,"wb") as f: f.write(uploaded.getbuffer())
                add_comment(idx, st.session_state.user_name, "", safe)
                st.success(f"Uploaded: {uploaded.name}")
                st.rerun()

