import streamlit as st
import pandas as pd
import json, os, platform
from datetime import date, datetime
from streamlit_autorefresh import st_autorefresh
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# ---------------------- PORTABLE EXPORT CONFIG -----------------------
# ─────────────────────────────────────────────────────────────────────
def choose_export_dir() -> Path:
    # 1) Optional env var (works on Streamlit Cloud)
    env = os.environ.get("HELP_CENTER_EXPORT_DIR")
    if env:
        p = Path(env).expanduser()
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass
    # 2) Local Mac dev
    if platform.system() == "Darwin":
        mac_path = Path.home() / "Downloads" / "Automation_Project_Titos"
        try:
            mac_path.mkdir(parents=True, exist_ok=True)
            return mac_path
        except Exception:
            pass
    # 3) Fallback
    p = Path.cwd() / "exports"
    p.mkdir(parents=True, exist_ok=True)
    return p

EXPORT_DIR = choose_export_dir()
EXPORT_ORDERS_CSV       = str(EXPORT_DIR / "orders.csv")
EXPORT_REQUIREMENTS_CSV = str(EXPORT_DIR / "requirements.csv")
EXPORT_COMMENTS_CSV     = str(EXPORT_DIR / "comments.csv")
EXPORT_XLSX             = str(EXPORT_DIR / "HelpCenter_Snapshot.xlsx")
EXPORT_JSON             = str(EXPORT_DIR / "HelpCenter_Snapshot.json")

# ─────────────────────────────────────────────────────────────────────
# -------------------------- RESTORE HELPERS --------------------------
# ─────────────────────────────────────────────────────────────────────
def rebuild_from_csvs():
    """Fallback: rebuild requests/comments from the exported CSVs."""
    reqs_by_old = {}

    # Orders (PO/SO)
    if os.path.exists(EXPORT_ORDERS_CSV) and os.path.getsize(EXPORT_ORDERS_CSV) > 0:
        odf = pd.read_csv(EXPORT_ORDERS_CSV).fillna("")
        for old_idx, g in odf.groupby("RequestIndex"):
            t    = str(g["Type"].iloc[0])                 # "💲" or "🛒"
            ref  = str(g["Ref#"].iloc[0])
            stat = str(g["Status"].iloc[0])
            dte  = str(g["Ordered Date"].iloc[0])
            eta  = str(g["ETA Date"].iloc[0])
            ship = str(g["Shipping Method"].iloc[0])
            enc  = str(g["Encargado"].iloc[0])
            pago = str(g["Pago"].iloc[0])
            partner = str(g["Partner"].iloc[0])

            descs  = [str(x) for x in g["Description"].tolist()]
            qtys   = [x for x in g["Qty"].tolist()]
            prices = [x for x in g["Price"].tolist()]

            base = {
                "Status": stat, "Date": dte, "ETA Date": eta,
                "Shipping Method": ship, "Encargado": enc, "Pago": pago,
                "Description": descs, "Quantity": qtys,
            }

            if t == "💲":
                req = {**base, "Type": "💲", "Invoice": ref, "Order#": "", "Cost": prices, "Proveedor": partner}
            else:
                req = {**base, "Type": "🛒", "Order#": ref, "Invoice": "", "Sale Price": prices, "Cliente": partner}
            reqs_by_old[int(old_idx)] = req

    # Requirements (📑)
    if os.path.exists(EXPORT_REQUIREMENTS_CSV) and os.path.getsize(EXPORT_REQUIREMENTS_CSV) > 0:
        rdf = pd.read_csv(EXPORT_REQUIREMENTS_CSV).fillna("")
        for old_idx, g in rdf.groupby("RequestIndex"):
            items = []
            for _, row in g.iterrows():
                items.append({
                    "Description": str(row.get("Description","")),
                    "Target Price": str(row.get("Target Price","")),
                    "QTY": row.get("Qty","")
                })
            reqs_by_old[int(old_idx)] = {
                "Type": "📑", "Items": items,
                "Vendedor Encargado": str(g["Vendedor Encargado"].iloc[0]) if "Vendedor Encargado" in g else "",
                "Comprador Encargado": str(g["Comprador Encargado"].iloc[0]) if "Comprador Encargado" in g else "",
                "Fecha": str(g["Fecha"].iloc[0]) if "Fecha" in g else "",
                "Status": str(g["Status"].iloc[0]) if "Status" in g else "OPEN",
            }

    # Comments
    comments_old = {}
    if os.path.exists(EXPORT_COMMENTS_CSV) and os.path.getsize(EXPORT_COMMENTS_CSV) > 0:
        cdf = pd.read_csv(EXPORT_COMMENTS_CSV).fillna("")
        for old_idx, g in cdf.groupby("RequestIndex"):
            lst = []
            for _, row in g.iterrows():
                entry = {
                    "author": str(row.get("Author","")),
                    "when": str(row.get("When","")),
                    "text": str(row.get("Text","")),
                }
                att = str(row.get("Attachment",""))
                if att.strip():
                    entry["attachment"] = att
                lst.append(entry)
            comments_old[int(old_idx)] = lst

    # Reindex requests contiguously and remap comment keys
    sorted_pairs = sorted(reqs_by_old.items())  # [(old_idx, req), ...]
    requests, idx_map = [], {}
    for new_idx, (old_idx, req) in enumerate(sorted_pairs):
        idx_map[old_idx] = new_idx
        requests.append(req)

    comments = {}
    for old_idx, lst in comments_old.items():
        if old_idx in idx_map:
            comments[str(idx_map[old_idx])] = lst

    return requests, comments

def try_restore_from_snapshot():
    """If local JSONs are empty/missing, restore from snapshot JSON; else from CSVs."""
    if os.path.exists(EXPORT_JSON) and os.path.getsize(EXPORT_JSON) > 0:
        try:
            with open(EXPORT_JSON, "r", encoding="utf-8") as f:
                snap = json.load(f)
            st.session_state.requests = snap.get("requests", [])
            st.session_state.comments = snap.get("comments", {})
            # Write primary JSONs so normal load() works next run
            with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state.requests, f, ensure_ascii=False, indent=2)
            with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(st.session_state.comments, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            st.warning(f"JSON snapshot restore failed: {e}")
    try:
        requests, comments = rebuild_from_csvs()
        if requests:
            st.session_state.requests = requests
            st.session_state.comments = comments
            with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
                json.dump(requests, f, ensure_ascii=False, indent=2)
            with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(comments, f, ensure_ascii=False, indent=2)
            return True
    except Exception as e:
        st.warning(f"CSV restore failed: {e}")
    return False

# ─────────────────────────────────────────────────────────────────────
# ------- APP CONFIG + STATE INITIALIZATION / CONSTANTS ---------------
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Tito's Depot Help Center", layout="wide", page_icon="🛒")

REQUESTS_FILE = "requests.json"
COMMENTS_FILE = "comments.json"
UPLOADS_DIR   = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

VALID_USERS = {
    "Andres": "GreenPhone13!",
    "Marcela": "3539",
    "Tito": "123",
    "Luz": "123",
    "David": "Medellin1()",
    "John": "Jn123*",
    "Sabrina": "Null",
    "Bodega": "bodega",
    "Carolina": "caroxoxo96",
    "Maye": "$Lucia01",
    "Juan": "Emiliano219"
}

def format_status_badge(status: str) -> str:
    status = (status or "").upper()
    color_map = {
        "IN TRANSIT": "#f39c12",
        "READY": "#2ecc71",
        "COMPLETE": "#3498db",
        "ORDERED": "#9b59b6",
        "CANCELLED": "#e74c3c",
        "IMPRIMIR": "#f1c40f",
        "IMPRESA": "#27ae60",
        "SEPARAR Y CONFIRMAR": "#1abc9c",
        "RECIBIDO / PROCESANDO": "#2980b9",
        "PENDIENTE": "#95a5a6",
        "SEPARADO - PENDIENTE": "#d35400",
        "RETURNED/CANCELLED": "#c0392b",
    }
    color = color_map.get(status, "#7f8c8d")
    return (
        f'<span style="background-color:{color};color:#fff;padding:4px 10px;'
        f'border-radius:12px;font-size:13px;font-weight:600;display:inline-block;">{status}</span>'
    )

# ─────────────────────────────────────────────────────────────────────
# ----------------------------- PERSISTENCE ---------------------------
# ─────────────────────────────────────────────────────────────────────
def load_data():
    # requests
    if os.path.exists(REQUESTS_FILE) and os.path.getsize(REQUESTS_FILE) > 0:
        try:
            with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
                st.session_state.requests = json.load(f)
        except json.JSONDecodeError:
            st.session_state.requests = []
    else:
        st.session_state.requests = []
    # comments
    if os.path.exists(COMMENTS_FILE) and os.path.getsize(COMMENTS_FILE) > 0:
        try:
            with open(COMMENTS_FILE, "r", encoding="utf-8") as f:
                st.session_state.comments = json.load(f)
        except json.JSONDecodeError:
            st.session_state.comments = {}
    else:
        st.session_state.comments = {}
    # Auto-restore if both empty
    if not st.session_state.requests and not st.session_state.comments:
        if try_restore_from_snapshot():
            st.toast("Restored data from snapshot ✅", icon="✅")

def export_snapshot_to_disk():
    """Write CSVs + Excel + JSON snapshot of current session state."""
    export_dir = Path(EXPORT_DIR)
    export_dir.mkdir(parents=True, exist_ok=True)

    # Orders (one row per item)
    orders_rows = []
    for i, r in enumerate(st.session_state.get("requests", []) or []):
        t = r.get("Type")
        if t not in ("💲", "🛒"):
            continue
        descs  = r.get("Description") or []
        qtys   = r.get("Quantity") or []
        price_key = "Cost" if t == "💲" else "Sale Price"
        prices = r.get(price_key) or []
        n = max(len(descs), len(qtys), len(prices), 1)
        for j in range(n):
            orders_rows.append({
                "RequestIndex": i,
                "Type": t,
                "Ref#": r.get("Invoice","") if t == "💲" else r.get("Order#",""),
                "Item #": j+1,
                "Description": descs[j] if j < len(descs) else "",
                "Qty":         qtys[j]  if j < len(qtys)  else "",
                "Price":       prices[j] if j < len(prices) else "",
                "Status": r.get("Status",""),
                "Ordered Date": r.get("Date",""),
                "ETA Date": r.get("ETA Date",""),
                "Shipping Method": r.get("Shipping Method",""),
                "Encargado": r.get("Encargado",""),
                "Partner": r.get("Proveedor","") if t == "💲" else r.get("Cliente",""),
                "Pago": r.get("Pago",""),
            })
    orders_df = pd.DataFrame(orders_rows)

    # Requirements (one row per item)
    req_rows = []
    for i, r in enumerate(st.session_state.get("requests", []) or []):
        if r.get("Type") != "📑":
            continue
        for j, it in enumerate(r.get("Items", []) or []):
            req_rows.append({
                "RequestIndex": i,
                "Item #": j+1,
                "Description": it.get("Description",""),
                "Target Price": it.get("Target Price",""),
                "Qty": it.get("QTY",""),
                "Vendedor Encargado":  r.get("Vendedor Encargado",""),
                "Comprador Encargado": r.get("Comprador Encargado",""),
                "Fecha": r.get("Fecha",""),
                "Status": r.get("Status","OPEN"),
            })
    req_df = pd.DataFrame(req_rows)

    # Comments
    comments_rows = []
    for k, comments in (st.session_state.get("comments", {}) or {}).items():
        try:
            k_int = int(k)
        except Exception:
            k_int = k
        for c in comments or []:
            comments_rows.append({
                "RequestIndex": k_int,
                "Author": c.get("author",""),
                "When":   c.get("when",""),
                "Text":   c.get("text",""),
                "Attachment": c.get("attachment",""),
            })
    comments_df = pd.DataFrame(comments_rows)

    orders_df.to_csv(EXPORT_ORDERS_CSV, index=False, encoding="utf-8-sig")
    req_df.to_csv(EXPORT_REQUIREMENTS_CSV, index=False, encoding="utf-8-sig")
    comments_df.to_csv(EXPORT_COMMENTS_CSV, index=False, encoding="utf-8-sig")

    # Excel snapshot (fallback filename if open)
    try:
        with pd.ExcelWriter(EXPORT_XLSX) as xls:
            orders_df.to_excel(xls, index=False, sheet_name="Orders")
            req_df.to_excel(xls, index=False, sheet_name="Requirements")
            comments_df.to_excel(xls, index=False, sheet_name="Comments")
        xlsx_out = EXPORT_XLSX
    except PermissionError:
        alt = export_dir / f"HelpCenter_Snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        with pd.ExcelWriter(str(alt)) as xls:
            orders_df.to_excel(xls, index=False, sheet_name="Orders")
            req_df.to_excel(xls, index=False, sheet_name="Requirements")
            comments_df.to_excel(xls, index=False, sheet_name="Comments")
        xlsx_out = str(alt)
        st.warning(f"Excel is open. Saved snapshot to {alt}.")

    # JSON snapshot
    snap = {"requests": st.session_state.get("requests", []), "comments": st.session_state.get("comments", {})}
    try:
        with open(EXPORT_JSON, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Snapshot JSON not saved: {e}")

    return {"orders_csv": EXPORT_ORDERS_CSV, "requirements_csv": EXPORT_REQUIREMENTS_CSV,
            "comments_csv": EXPORT_COMMENTS_CSV, "xlsx": xlsx_out, "json": EXPORT_JSON}

def save_data():
    with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.requests, f, ensure_ascii=False, indent=2)
    with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.comments, f, ensure_ascii=False, indent=2)
    try:
        export_snapshot_to_disk()
    except Exception as e:
        st.warning(f"Auto-export failed: {e}")

def add_request(data: dict):
    idx = len(st.session_state.requests)
    st.session_state.requests.append(data)
    st.session_state.comments[str(idx)] = []
    save_data()

def add_comment(index: int, author: str, text: str = "", attachment: str | None = None):
    key = str(index)
    st.session_state.comments.setdefault(key, [])
    st.session_state.comments[key].append({
        "author": author,
        "text": text,
        "when": datetime.now().strftime("%Y-%m-%d %H:%M"),
        **({"attachment": attachment} if attachment else {})
    })
    save_data()

def delete_request(index: int):
    if 0 <= index < len(st.session_state.requests):
        st.session_state.requests.pop(index)
        st.session_state.comments.pop(str(index), None)
        # reindex comments to match shifted request indices
        st.session_state.comments = {str(i): st.session_state.comments.get(str(i), []) for i in range(len(st.session_state.requests))}
        save_data()
        st.success("🗑️ Request deleted successfully.")
        st.session_state.page = "requests"
        st.rerun()

def go_to(page: str):
    st.session_state.page = page
    st.rerun()

# ─────────────────────────────────────────────────────────────────────
# -------------------------- SESSION DEFAULTS -------------------------
# ─────────────────────────────────────────────────────────────────────
st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("user_name", "")
st.session_state.setdefault("page", "login")
if "requests" not in st.session_state or "comments" not in st.session_state:
    load_data()
st.session_state.setdefault("selected_request", None)

# ─────────────────────────────────────────────────────────────────────
# ------------------------------- LOGIN -------------------------------
# ─────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────
# -------------- SNAPSHOT GUARD (global, after login) -----------------
# ─────────────────────────────────────────────────────────────────────
def require_snapshot_download(every_seconds: int = 12600, file_basename: str = "HelpCenter_Snapshot.json"):
    """
    Blocks with a modal until the user 1) downloads the JSON and 2) confirms.
    Pops back up every `every_seconds` (default 3h 30m).
    """
    if "snapshot_ack_ts" not in st.session_state:
        st.session_state.snapshot_ack_ts = None
    if "snapshot_dl_clicked" not in st.session_state:
        st.session_state.snapshot_dl_clicked = False

    now  = datetime.now().timestamp()
    last = st.session_state.snapshot_ack_ts
    if last is not None and (now - last) < every_seconds:
        return

    # live snapshot ping (background save)
    try:
        export_snapshot_to_disk()
    except Exception as e:
        st.warning(f"Auto-export failed: {e}")

    @st.dialog("⚠️ Download required", width="large")
    def _guard():
        st.markdown("""
        <style>
          [data-testid="stDialog"] { max-width: 98vw !important; }
          [data-testid="stDialog"] button[aria-label="Close"] { display:none !important; }
        </style>
        """, unsafe_allow_html=True)

        st.write("To keep your data safe, download the live JSON. This prompt will reappear every **3 hours 30 minutes**.")

        left, right = st.columns([1, 1])
        snap = {"requests": st.session_state.get("requests", []), "comments": st.session_state.get("comments", {})}
        with left:
            dl = st.download_button(
                "⬇️ Download live snapshot (JSON)",
                data=json.dumps(snap, ensure_ascii=False, indent=2),
                file_name=file_basename,
                mime="application/json",
                key="force_snapshot_dl_btn",
                use_container_width=True
            )
            if dl:
                st.session_state.snapshot_dl_clicked = True

        with right:
            cont = st.button(
                "✅ I downloaded it — continue",
                disabled=not st.session_state.snapshot_dl_clicked,
                use_container_width=True,
                key="force_snapshot_continue_btn"
            )
            if cont:
                st.session_state.snapshot_ack_ts = now
                st.session_state.snapshot_dl_clicked = False
                st.rerun()

        _ = st_autorefresh(interval=1000, limit=None, key="snapshot_guard_tick")

    _guard()
    st.stop()

# Global guard once (don’t call again inside Home)
if st.session_state.authenticated:
    if st.session_state.page in ("home", "summary"):
        _ = st_autorefresh(interval=10_000, limit=None, key=f"guard_heartbeat_{st.session_state.page}")
    require_snapshot_download(every_seconds=12600)

# ─────────────────────────────────────────────────────────────────────
# -------------------------------- HOME -------------------------------
# ─────────────────────────────────────────────────────────────────────
SUMMARY_ALLOWED = {"Andres", "David", "Juan", "Tito", "Luz"}
REQS_DENIED     = {"Bodega"}

if st.session_state.page == "home":
    _ = st_autorefresh(interval=10_000, limit=None, key="home_heartbeat")

    # Styling
    st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
    h1, h2, h3, h4 { color: #003366; font-weight: 700; margin-bottom: 0.5rem; }
    div.stButton > button {
        background-color: #fff !important; border: 1px solid #ccc !important;
        border-radius: 10px !important; padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important; font-size: 16px !important; color: #333 !important;
        transition: background-color 0.2s ease;
    }
    div.stButton > button:hover { background-color: #f1f1f1 !important; border-color: #999 !important; }
    </style>
    """, unsafe_allow_html=True)

    if st.button("🚪 Log Out", key="home_logout"):
        st.session_state.authenticated = False
        st.session_state.user_name = ""
        st.session_state.page = "login"
        st.rerun()

    st.markdown("# 🏠 Welcome to the Help Center")
    st.markdown(f"Logged in as: **{st.session_state.user_name}**")
    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.session_state.user_name not in REQS_DENIED:
            if st.button("📝 View Requerimientos Clientes", use_container_width=True, key="home_view_reqs"):
                st.session_state.page = "req_list"; st.rerun()
        else:
            st.button("🔒 View Requerimientos Clientes", disabled=True, use_container_width=True, key="home_view_reqs_locked")
            st.caption("You don’t have access to this page.")
    with col2:
        if st.button("📋 View All Purchase/Sales Orders", use_container_width=True, key="home_view_orders"):
            st.session_state.page = "requests"; st.rerun()
    with col3:
        if st.session_state.user_name in SUMMARY_ALLOWED:
            if st.button("📊 Summary", use_container_width=True, key="home_summary"):
                st.session_state.page = "summary"; st.rerun()
        else:
            st.button("🔒 Summary", disabled=True, use_container_width=True, key="home_summary_locked")
            st.caption("You don’t have access to this page.")

    with st.expander("Backup & Restore"):
        st.caption(f"Export folder: {EXPORT_DIR}")
        snap = {"requests": st.session_state.get("requests", []), "comments": st.session_state.get("comments", {})}
        st.download_button(
            "⬇️ Download snapshot (JSON)",
            data=json.dumps(snap, ensure_ascii=False, indent=2),
            file_name="HelpCenter_Snapshot.json",
            mime="application/json",
            key="backup_dl_btn"
        )
        uploaded = st.file_uploader("Restore from snapshot JSON", type=["json"], key="restore_uploader")
        if uploaded and st.button("Restore now", key="restore_now_btn"):
            try:
                data = json.load(uploaded)
                st.session_state.requests = data.get("requests", [])
                st.session_state.comments = data.get("comments", {})
                save_data()
                st.success("Restored from uploaded snapshot ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Restore failed: {e}")

# ─────────────────────────────────────────────────────────────────────
# ------------------------------ SUMMARY ------------------------------
# ─────────────────────────────────────────────────────────────────────
elif st.session_state.page == "summary":
    import plotly.express as px

    status_colors = {
        "IN TRANSIT":"#f39c12","READY":"#2ecc71","COMPLETE":"#3498db","ORDERED":"#9b59b6",
        "CANCELLED":"#e74c3c","IMPRIMIR":"#f1c40f","IMPRESA":"#27ae60","SEPARAR Y CONFIRMAR":"#1abc9c",
        "RECIBIDO / PROCESANDO":"#2980b9","PENDIENTE":"#95a5a6","SEPARADO - PENDIENTE":"#d35400",
        "RETURNED/CANCELLED":"#c0392b"
    }

    def pick_qty(row):
        if pd.notna(row.get('Qty')): return row['Qty']
        for col in ("Quantity", "Items"):
            v = row.get(col)
            if isinstance(v, list) and v: return v[0]
            if pd.notna(v): return v
        return None

    def flatten(v): return v[0] if isinstance(v, list) and v else v

    def badge(s):
        color = status_colors.get(s, "#95a5a6")
        return f"<span style='background:{color};color:#fff;padding:2px 6px;border-radius:4px'>{s}</span>"

    load_data()
    raw = pd.DataFrame(st.session_state.requests)
    if raw.empty or "Type" not in raw.columns:
        st.info("No Purchase Orders or Sales Orders to summarize yet.")
        st.button("⬅ Back to Home", on_click=lambda: go_to("home"))
        st.stop()

    df = raw[raw["Type"].isin(["💲", "🛒"])].copy()
    if df.empty:
        st.info("No Purchase Orders or Sales Orders to summarize yet.")
        st.button("⬅ Back to Home", on_click=lambda: go_to("home"))
        st.stop()

    df["Status"]   = df["Status"].astype(str).str.strip().str.upper()
    df["Date"]     = pd.to_datetime(df["Date"], errors="coerce")
    df["ETA Date"] = pd.to_datetime(df["ETA Date"], errors="coerce")
    df["Ref#"]     = df.apply(lambda r: r["Invoice"] if r["Type"] == "💲" else r["Order#"], axis=1)

    today          = pd.Timestamp(date.today())
    overdue_mask   = (df["ETA Date"] < today) & ~df["Status"].isin(["READY", "CANCELLED"])
    due_today_mask = (df["ETA Date"] == today) & (df["Status"] != "CANCELLED")

    st.subheader("📊 Summary")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Requests",   len(df))
    k2.metric("Active Requests",  df[~df["Status"].isin(["COMPLETE", "CANCELLED"])].shape[0])
    k3.metric("Overdue Requests", df[overdue_mask].shape[0])
    k4.metric("Due Today",        df[due_today_mask].shape[0])
    st.markdown("---")

    count_df = df["Status"].value_counts().rename_axis("Status").reset_index(name="Count")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Status Distribution Pie")
        fig = px.pie(count_df, names="Status", values="Count", color="Status", color_discrete_map=status_colors)
        fig.update_traces(textinfo="label+value", textposition="inside")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Due Today")
        due_today = df[due_today_mask].copy()
        if not due_today.empty:
            due_today["Qty"]         = due_today.apply(pick_qty, axis=1)
            due_today["Description"] = due_today["Description"].apply(flatten)
            disp_today = due_today[["Type","Ref#","Description","Qty","Encargado","Status"]].copy()
            disp_today["Status"] = disp_today["Status"].apply(badge)
            st.markdown(disp_today.to_html(index=False, escape=False), unsafe_allow_html=True)
        else:
            st.info("No POs/SOs due today.")
        st.markdown("---")

        st.subheader("Overdue")
        od = df[overdue_mask].copy()
        if not od.empty:
            od["Qty"]         = od.apply(pick_qty, axis=1)
            od["Description"] = od["Description"].apply(flatten)
            disp_od = od[["Type","Ref#","Description","Qty","Encargado","Status"]].copy()
            disp_od["Status"] = disp_od["Status"].apply(badge)
            st.markdown(disp_od.to_html(index=False, escape=False), unsafe_allow_html=True)
        else:
            st.info("No overdue POs/SOs.")
            st.markdown("---")

    st.button("⬅ Back to Home", on_click=lambda: go_to("home"))

# ─────────────────────────────────────────────────────────────────────
# -------------------- ALL PURCHASE/SALES ORDERS ----------------------
# ─────────────────────────────────────────────────────────────────────
elif st.session_state.page == "requests":
    user = st.session_state.user_name

    SALES_CREATORS    = {"Andres","Tito","Luz","David","John","Sabrina","Carolina","Juan","Marcela","Maye"}
    PURCHASE_CREATORS = {"Andres","Tito","Luz","David","Juan","Maye"}
    PRICE_ALLOWED     = {"Andres","Luz","Tito","David","Juan","Maye"}
    BODEGA            = {"Bodega","Andres","Tito","Luz","David","Juan","Maye"}

    st.session_state.setdefault("show_new_po", False)
    st.session_state.setdefault("show_new_so", False)

    @st.dialog("💲 New Purchase Order", width="large")
    def purchase_order_dialog():
        st.session_state.setdefault("purchase_item_rows", 1)
        st.session_state.purchase_item_rows = max(1, st.session_state.purchase_item_rows)

        st.markdown("""
        <style>.stTextInput > div > div > input,.stSelectbox > div,.stDateInput > div{
        background:#f7f9fc!important;border-radius:12px!important;padding:0.4rem!important;border:1px solid #dfe6ec!important;}
        </style>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            po_number    = st.text_input("Purchase Order#", placeholder="e.g. 12345")
            status_po    = st.selectbox("Status *", [" ", "COMPLETE", "READY", "CANCELLED", "IN TRANSIT"])
            encargado_po = st.selectbox("Encargado *", [" ", "Andres","Tito","Luz","David","Marcela","John","Carolina","Thea","Juan"])
        with c2:
            order_number = st.text_input("Tracking# (optional)", placeholder="e.g. TRK-45678")
            proveedor    = st.text_input("Proveedor", placeholder="e.g. Amazon")
            pago         = st.selectbox("Método de Pago", [" ", "Wire", "Cheque", "Credito", "Efectivo"])

        st.markdown("### 🧾 Items to Order")
        descs, qtys, costs = [], [], []
        for i in range(st.session_state.purchase_item_rows):
            c_desc, c_qty, c_cost = st.columns([3, 2, 1])
            descs.append(c_desc.text_input(f"Description #{i+1}", key=f"po_desc_{i}"))
            qtys.append(c_qty.text_input(f"Quantity #{i+1}", key=f"po_qty_{i}"))
            costs.append(c_cost.text_input(f"Cost #{i+1}", placeholder="e.g. 1500", key=f"po_cost_{i}"))

        ca2, cb2 = st.columns([1,1])
        with ca2:
            if st.button("➕ Add another item", key="add_purchase"):
                st.session_state.purchase_item_rows += 1
        with cb2:
            if st.session_state.purchase_item_rows > 1 and st.button("❌ Remove last item", key="remove_purchase"):
                st.session_state.purchase_item_rows -= 1

        st.markdown("### 🚚 Shipping Information")
        c3, c4 = st.columns(2)
        with c3: order_date = st.date_input("Order Date", value=date.today())
        with c4: eta_date   = st.date_input("ETA Date")
        shipping_method = st.selectbox("Shipping Method", [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"])

        col_submit, col_cancel = st.columns([2,1])
        with col_submit:
            if st.button("✅ Submit Purchase Request", use_container_width=True):
                clean_descs = [d.strip() for d in descs if isinstance(d, str) and d.strip()]
                clean_qtys = []
                for q in qtys:
                    q = (q or "").strip()
                    if q:
                        try: clean_qtys.append(int(float(q)))
                        except: clean_qtys.append(q)
                clean_costs = []
                for c in costs:
                    c = (c or "").strip()
                    if c:
                        try: clean_costs.append(float(c))
                        except: clean_costs.append(c)
                if not clean_descs or not clean_qtys or not clean_costs or status_po == " " or encargado_po == " ":
                    st.error("❗ Complete required fields.")
                else:
                    add_request({
                        "Type":"💲","Invoice": po_number,"Order#": order_number,"Date": str(order_date),
                        "Status": status_po,"Shipping Method": shipping_method,"ETA Date": str(eta_date),
                        "Description": clean_descs,"Quantity": clean_qtys,"Cost": clean_costs,
                        "Proveedor": proveedor,"Encargado": encargado_po,"Pago": pago
                    })
                    try: export_snapshot_to_disk()
                    except Exception as e: st.warning(f"Auto-export failed: {e}")
                    st.success("✅ Purchase request submitted.")
                    st.session_state.purchase_item_rows = 1
                    st.session_state.show_new_po = False
                    st.rerun()
        with col_cancel:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_new_po = False; st.rerun()

    @st.dialog("🛒 New Sales Order", width="large")
    def sales_order_dialog():
        st.session_state.setdefault("invoice_item_rows", 1)
        st.session_state.invoice_item_rows = max(1, st.session_state.invoice_item_rows)

        st.markdown("""
        <style>.stTextInput > div > div > input,.stSelectbox > div,.stDateInput > div{
        background:#f7f9fc!important;border-radius:8px!important;padding:0.4rem!important;border:1px solid #dfe6ec!important;}
        </style>""", unsafe_allow_html=True)

        d1, d2 = st.columns(2)
        with d1:
            order_number_so = st.text_input("Ref# (optional)", placeholder="e.g. SO-2025-001", key="so_ref")
            status_so       = st.selectbox("Status *", [" ", "COMPLETE", "READY", "CANCELLED", "IN TRANSIT"], key="so_status")
            encargado_so    = st.selectbox("Encargado *", [" ", "Andres","Tito","Luz","David","Marcela","John","Carolina","Thea","Juan"], key="so_encargado")
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
        with s1: so_date = st.date_input("Order Date", value=date.today(), key="so_date")
        with s2: so_eta  = st.date_input("ETA Date", key="so_eta")
        so_ship = st.selectbox("Shipping Method", [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"], key="so_shipping")

        cs1, cs2 = st.columns([2,1])
        with cs1:
            if st.button("✅ Submit Sales Order", use_container_width=True):
                clean_ds = [d.strip() for d in ds if isinstance(d, str) and d.strip()]
                clean_qs, clean_prices = [], []
                for q in qs:
                    q = (q or "").strip()
                    if q:
                        try: clean_qs.append(int(float(q)))
                        except: clean_qs.append(q)
                for p in prices:
                    p = (p or "").strip()
                    if p:
                        try: clean_prices.append(float(p))
                        except: clean_prices.append(p)
                if not clean_ds or not clean_qs or not clean_prices or status_so == " " or encargado_so == " ":
                    st.error("❗ Complete required fields.")
                else:
                    add_request({
                        "Type":"🛒","Order#": order_number_so,"Invoice": tracking_so,"Date": str(so_date),
                        "Status": status_so,"Shipping Method": so_ship,"ETA Date": str(so_eta),
                        "Description": clean_ds,"Quantity": clean_qs,"Sale Price": clean_prices,
                        "Cliente": cliente,"Encargado": encargado_so,"Pago": pago_so
                    })
                    try: export_snapshot_to_disk()
                    except Exception as e: st.warning(f"Auto-export failed: {e}")
                    st.success("✅ Sales order submitted.")
                    st.session_state.invoice_item_rows = 1
                    st.session_state.show_new_so = False
                    st.rerun()
        with cs2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_new_so = False; st.rerun()

    # Header + data
    st.markdown("# 📋 All Purchase/Sales Orders")
    st.markdown("---")
    _ = st_autorefresh(interval=10_000, limit=None, key="requests_refresh")
    load_data()

    try: export_snapshot_to_disk()
    except Exception as e: st.warning(f"Auto-export failed: {e}")

    if st.session_state.show_new_po: purchase_order_dialog()
    if st.session_state.show_new_so: sales_order_dialog()

    # Filters
    col1, col2, col3 = st.columns([3,2,2])
    with col1: search_term = st.text_input("Search", placeholder="Search requests…")
    with col2:
        status_options = ["All","IMPRIMIR","IMPRESA","SEPARAR Y CONFIRMAR","RECIBIDO / PROCESANDO","PENDIENTE","SEPARADO - PENDIENTE","COMPLETE","READY","CANCELLED","IN TRANSIT"]
        status_filter = st.selectbox("Status", status_options)
    with col3:
        type_filter = st.selectbox("Request type", ["All","💲 Purchase","🛒 Sales"])

    # Scope
    all_requests = st.session_state.requests
    base_requests = list(enumerate(all_requests)) if user in BODEGA else [(i,r) for i,r in enumerate(all_requests) if r.get("Type")=="🛒"]

    # Apply filters
    def _matches_status(r): return True if status_filter=="All" else (r.get("Status","").upper()==status_filter)
    def _matches_type(r):   return True if type_filter=="All" else (r.get("Type")==type_filter.split()[0])

    filtered_requests = [(i,r) for (i,r) in base_requests
                         if r.get("Type") in {"💲","🛒"}
                         and (search_term.lower() in json.dumps(r).lower())
                         and _matches_status(r) and _matches_type(r)]

    def parse_eta(req_dict):
        try: return datetime.strptime(req_dict.get("ETA Date",""), "%Y-%m-%d").date()
        except: return date.max

    filtered_requests = sorted(filtered_requests, key=lambda pair: parse_eta(pair[1]))

    # Export current view
    col_exp, col_po, col_so = st.columns([3,1,1])
    with col_exp:
        include_prices = (user in PRICE_ALLOWED)
        def _join(v): return ", ".join(map(str, v)) if isinstance(v, list) else ("" if v is None else str(v))
        def _fmt_money_list(lst):
            if not isinstance(lst, list): lst = [lst]
            out = []
            for x in lst:
                try: out.append(f"${int(float(x))}")
                except: out.append(str(x))
            return ", ".join(out)
        rows = []
        for _, r in filtered_requests:
            is_po = (r.get("Type")=="💲")
            row = {
                "Type": r.get("Type",""),
                "Ref#": r.get("Invoice","") if is_po else r.get("Order#",""),
                "Description": _join(r.get("Description", [])),
                "Qty": _join(r.get("Quantity", [])),
                "Status": r.get("Status",""),
                "Ordered Date": r.get("Date",""),
                "ETA Date": r.get("ETA Date",""),
                "Shipping Method": r.get("Shipping Method",""),
                "Encargado": r.get("Encargado",""),
                "Partner": r.get("Proveedor","") if is_po else r.get("Cliente",""),
                "Pago": r.get("Pago",""),
            }
            if include_prices:
                row["Cost" if is_po else "Sale Price"] = _fmt_money_list(r.get("Cost", []) if is_po else r.get("Sale Price", []))
            rows.append(row)
        df_export = pd.DataFrame(rows)
        st.download_button("📥 Export Filtered Requests to CSV",
                           df_export.to_csv(index=False).encode("utf-8"),
                           "requests_export.csv","text/csv", use_container_width=True)

    with col_po:
        if user in PURCHASE_CREATORS:
            if st.button("💲 New Purchase Order", use_container_width=True):
                st.session_state.show_new_po = True; st.rerun()
        else:
            st.button("🔒 New Purchase Order", disabled=True, use_container_width=True)
            st.caption("You don’t have permission to create POs.")
    with col_so:
        if user in SALES_CREATORS:
            if st.button("🛒 New Sales Order", use_container_width=True):
                st.session_state.show_new_so = True; st.rerun()
        else:
            st.button("🛒 New Sales Order", disabled=True, use_container_width=True)

    # Table render with chips for long list cells
    if filtered_requests:
        st.markdown("""
        <style>
          .header-row{font-weight:bold;font-size:18px;padding:0.5rem 0}
          .type-icon{font-size:18px}
          .unread-badge{background:#2ecc71;color:#fff;padding:4px 8px;border-radius:12px;display:inline-block}
          .overdue-icon{color:#e74c3c;font-weight:600;font-size:14px;margin-left:6px;vertical-align:middle}
          .chips{max-width:520px;white-space:normal}
          .chips span{background:#f1f3f5;border-radius:9999px;padding:2px 8px;margin:2px 4px 2px 0;display:inline-block;font-size:13px}
        </style>
        """, unsafe_allow_html=True)

        import html as _html
        def make_chips(val, limit=3):
            if val is None or val == "": return ""
            if not isinstance(val, list): val = [val]
            items = list(map(str, val))
            first, more = items[:limit], max(0, len(items)-limit)
            chips_html = "".join(f"<span>{_html.escape(x)}</span>" for x in first)
            suffix = f"<span>+{more} more</span>" if more else ""
            full_text = ", ".join(items)
            return f"<div class='chips' title='{_html.escape(full_text)}'>{chips_html}{suffix}</div>"

        today = date.today()
        def render_table(pairs_list):
            if user in PRICE_ALLOWED:
                widths = [1.5,1,2,5,2,2,2,2,2,2,2,2]
                headers = ["","Type","Ref#","Description","Qty","Cost/Sales Price","Status","Ordered Date","ETA Date","Shipping Method","Encargado",""]
            else:
                widths = [1.5,1,2,5,2,2,2,2,2,2,2]
                headers = ["","Type","Ref#","Description","Qty","Status","Ordered Date","ETA Date","Shipping Method","Encargado",""]

            cols_hdr = st.columns(widths)
            for c,h in zip(cols_hdr, headers): c.markdown(f"<div class='header-row'>{h}</div>", unsafe_allow_html=True)

            for global_idx, req in pairs_list:
                cols = st.columns(widths)

                comments_list = st.session_state.comments.get(str(global_idx), [])
                for c in comments_list: c.setdefault("read_by", [])
                unread_cnt = sum(1 for c in comments_list if user not in c["read_by"] and c.get("author") != user)
                cols[0].markdown(f"<span class='unread-badge'>💬{unread_cnt}</span>" if unread_cnt>0 else "", unsafe_allow_html=True)

                cols[1].markdown(f"<span class='type-icon'>{req.get('Type','')}</span>", unsafe_allow_html=True)
                cols[2].write(req.get("Invoice","") if req.get("Type")=="💲" else req.get("Order#",""))

                cols[3].markdown(make_chips(req.get("Description", [])), unsafe_allow_html=True)
                cols[4].markdown(make_chips(req.get("Quantity", [])), unsafe_allow_html=True)

                if user in PRICE_ALLOWED:
                    raw_list = req.get("Cost", []) if req.get("Type")=="💲" else req.get("Sale Price", [])
                    if not isinstance(raw_list, list): raw_list = [raw_list]
                    formatted=[]
                    for v in raw_list:
                        try: formatted.append(f"${int(float(v))}")
                        except: formatted.append(str(v))
                    cols[5].markdown(make_chips(formatted), unsafe_allow_html=True)
                    status_idx = 6
                else:
                    status_idx = 5

                stt = (req.get("Status","") or "").upper()
                eta = req.get("ETA Date","")
                try: ed = datetime.strptime(eta, "%Y-%m-%d").date()
                except: ed = None
                badge_html = format_status_badge(stt)
                if ed and ed < today and stt not in ("READY","CANCELLED"):
                    badge_html += "<abbr title='Overdue'><span class='overdue-icon'>⚠️</span></abbr>"
                cols[status_idx].markdown(badge_html, unsafe_allow_html=True)

                cols[status_idx+1].write(req.get("Date",""))
                cols[status_idx+2].write(eta)
                cols[status_idx+3].write(req.get("Shipping Method",""))
                cols[status_idx+4].write(req.get("Encargado",""))

                action_idx = len(widths)-1
                with cols[action_idx]:
                    a1, a2 = st.columns([1,1])
                    if a1.button("🔍", key=f"view_{global_idx}"):
                        for c in comments_list:
                            if c.get("author") != user and user not in c["read_by"]:
                                c["read_by"].append(user)
                        save_data()
                        st.session_state.selected_request = global_idx
                        go_to("detail")
                    if a2.button("❌", key=f"delete_{global_idx}"):
                        delete_request(global_idx)
                        try: export_snapshot_to_disk()
                        except Exception as e: st.warning(f"Auto-export failed: {e}")
                        st.rerun()

        if user == "Bodega":
            po_pairs = [(i, r) for (i, r) in filtered_requests if r.get("Type") == "💲"]
            so_pairs = [(i, r) for (i, r) in filtered_requests if r.get("Type") == "🛒"]
            st.subheader("📦 Purchase Orders")
            render_table(po_pairs) if po_pairs else st.warning("No matching purchase requests found.")
            st.markdown("---")
            st.subheader("🛒 Sales Orders")
            render_table(so_pairs) if so_pairs else st.warning("No matching sales requests found.")
        else:
            render_table(filtered_requests)
    else:
        st.warning("No matching requests found.")

    if st.button("⬅ Back to Home"): go_to("home")

# ─────────────────────────────────────────────────────────────────────
# --------------------------- ORDER DETAILS ---------------------------
# ─────────────────────────────────────────────────────────────────────
elif st.session_state.page == "detail":
    # De-dupe helpers for comments/uploads
    import time
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    def _submit_comment_value(idx: int, value: str) -> bool:
        txt = (value or "").strip()
        if not txt: return False
        guard = st.session_state.setdefault("detail_comment_guard", {})
        now = time.time()
        sig = f"{st.session_state.user_name}|{txt}"
        last = guard.get(str(idx))
        if last and last.get("sig")==sig and (now - last.get("ts",0)) < 3.0:
            return False
        add_comment(idx, st.session_state.user_name, txt)
        guard[str(idx)] = {"sig": sig, "ts": now}
        st.session_state["detail_comment_guard"] = guard
        return True

    def _upload_attachment(idx: int, uploaded_file) -> bool:
        if not uploaded_file: return False
        guard = st.session_state.setdefault("detail_upload_guard", {})
        now = time.time()
        last = guard.get(str(idx))
        if last and last.get("name")==uploaded_file.name and (now - last.get("ts",0)) < 3.0:
            return False
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        fn = f"{idx}_{ts}_{uploaded_file.name}"
        with open(os.path.join(UPLOADS_DIR, fn), "wb") as f:
            f.write(uploaded_file.getbuffer())
        add_comment(idx, st.session_state.user_name, "", attachment=fn)
        guard[str(idx)] = {"name": uploaded_file.name, "ts": now}
        st.session_state["detail_upload_guard"] = guard
        return True

    _ = st_autorefresh(interval=1000, limit=None, key=f"detail_comments_refresh_{st.session_state.selected_request}")
    load_data()

    index = st.session_state.selected_request
    if index is None or index >= len(st.session_state.requests):
        st.error("Invalid request selected."); st.stop()

    request = st.session_state.requests[index]
    updated_fields = {}
    is_purchase = (request.get("Type") == "💲")
    hide_prices = (st.session_state.user_name == "Bodega")

    with st.sidebar:
        st.markdown("### 📄 Order Information")

        order_number_val = request.get("Order#", "")
        order_number = st.text_input("Ref#", order_number_val, key="detail_Order#")
        if order_number != order_number_val: updated_fields["Order#"] = order_number

        status_opts = [" ","Imprimir","Impresa","Separar y Confirmar","Recibido / Procesando","Pendiente","Separado - Pendiente","Ready","Complete","Returned/Cancelled"]
        curr_status = request.get("Status", " "); curr_status = curr_status if curr_status in status_opts else " "
        status = st.selectbox("Status", status_opts, index=status_opts.index(curr_status), key="detail_Status")
        if status != curr_status: updated_fields["Status"] = status

        invoice_val = request.get("Invoice", "")
        invoice = st.text_input("Tracking#", invoice_val, key="detail_Invoice")
        if invoice != invoice_val: updated_fields["Invoice"] = invoice

        partner_label = "Proveedor" if is_purchase else "Cliente"
        partner_val = request.get(partner_label, "")
        partner = st.text_input(partner_label, partner_val, key=f"detail_{partner_label}")
        if partner != partner_val: updated_fields[partner_label] = partner

        pago_val = request.get("Pago", " ")
        pago = st.selectbox("Método de Pago", [" ", "Wire", "Cheque", "Credito", "Efectivo"], index=[" ","Wire","Cheque","Credito","Efectivo"].index(pago_val), key="detail_Pago")
        if pago != pago_val: updated_fields["Pago"] = pago

        encargado_val = request.get("Encargado", " ")
        encargado = st.selectbox("Encargado", [" ","Andres","Tito","Luz","David","Marcela","John","Carolina","Thea","Juan"],
                                 index=[" ","Andres","Tito","Luz","David","Marcela","John","Carolina","Thea","Juan"].index(encargado_val),
                                 key="detail_Encargado")
        if encargado != encargado_val: updated_fields["Encargado"] = encargado

        st.markdown("### 🧾 Items")
        descs = request.get("Description", [])
        qtys  = request.get("Quantity", [])
        price_key = "Cost" if is_purchase else "Sale Price"
        prices = request.get(price_key, [])

        new_descs, new_qtys, new_prices = [], [], []
        for i, (d, q, p) in enumerate(zip(descs, qtys, prices)):
            c1, c2, c3 = st.columns([3, 1, 1])
            new_d = c1.text_input(f"Description #{i+1}", d, key=f"detail_desc_{i}")
            new_q = c2.text_input(f"Qty #{i+1}", q, key=f"detail_qty_{i}")
            if hide_prices: c3.markdown("**—**"); new_p = p
            else: new_p = c3.text_input(f"{price_key} #{i+1}", p, key=f"detail_price_{i}")
            new_descs.append(new_d); new_qtys.append(new_q); new_prices.append(new_p)

        if new_descs != descs: updated_fields["Description"] = new_descs
        if new_qtys != qtys:
            try: updated_fields["Quantity"] = [int(x) for x in new_qtys]
            except: updated_fields["Quantity"] = new_qtys
        if new_prices != prices:
            try: updated_fields[price_key] = [float(x) for x in new_prices]
            except: updated_fields[price_key] = new_prices

        st.markdown("### 🚚 Shipping Information")
        date_val = request.get("Date", str(date.today()))
        order_date = st.date_input("Order Date", value=pd.to_datetime(date_val), key="detail_Date")
        if str(order_date) != date_val: updated_fields["Date"] = str(order_date)

        eta_val = request.get("ETA Date", str(date.today()))
        eta_date = st.date_input("ETA Date", value=pd.to_datetime(eta_val), key="detail_ETA")
        if str(eta_date) != eta_val: updated_fields["ETA Date"] = str(eta_date)

        ship_val = request.get("Shipping Method", " ")
        shipping_method = st.selectbox("Shipping Method", [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"],
                                       index=[" ","Nivel 1 PU","Nivel 3 PU","Nivel 3 DEL"].index(ship_val),
                                       key="detail_Shipping")
        if shipping_method != ship_val: updated_fields["Shipping Method"] = shipping_method

        st.markdown("---")
        if updated_fields and st.button("💾 Save Changes", use_container_width=True):
            request.update(updated_fields); st.session_state.requests[index] = request
            save_data(); st.success("✅ Changes saved."); st.rerun()
        if st.button("🗑️ Delete Request", use_container_width=True): delete_request(index)
        if st.button("⬅ Back to All Requests", use_container_width=True): go_to("requests")

    # Comments
    st.markdown("## 💬 Comments")
    col_l, col_center, col_r = st.columns([1,6,1])
    with col_center:
        st.markdown("""
        <style>
          .chat-author-in{font-size:12px;color:#555;margin:4px 0 0 5px;clear:both}
          .chat-author-out{font-size:12px;color:#888;margin:4px 5px 0 0;clear:both;text-align:right}
          .chat-bubble{padding:8px 12px;border-radius:16px;max-width:60%;margin:2px 0;clear:both;word-wrap:break-word}
          .chat-timestamp{font-size:10px;color:#888;margin:2px 0 8px}
          .chat-attachment{background:#DDEEFF;color:#003366;padding:8px 12px;border-radius:8px;float:left;max-width:60%;margin:4px 0;clear:both;word-wrap:break-word}
          .attachment-link{color:#003366;text-decoration:none;font-weight:600}
          .clearfix{clear:both}
        </style>
        """, unsafe_allow_html=True)

        existing_comments = st.session_state.comments.get(str(index), [])
        authors = []
        for c in existing_comments:
            if c["author"] not in authors: authors.append(c["author"])
        base_colors = ["#D1E8FF","#FFD1DC","#DFFFD6","#FFFACD","#E0E0E0"]
        color_map = {a: base_colors[i % len(base_colors)] for i,a in enumerate(authors)}

        for comment in existing_comments:
            author = comment["author"]; text = comment.get("text",""); when = comment.get("when","")
            attachment = comment.get("attachment")
            align = "right" if author == st.session_state.user_name else "left"
            cls = "out" if author == st.session_state.user_name else "in"
            st.markdown(f'<div class="chat-author-{cls}" style="text-align:{align};">{author}</div>', unsafe_allow_html=True)
            if attachment:
                file_path = os.path.join(UPLOADS_DIR, attachment)
                st.markdown(
                    f'<div class="chat-attachment" style="float:{align};">📎 <a href="/{file_path}" class="attachment-link" download>{attachment}</a></div>'
                    f'<div class="chat-timestamp" style="text-align:{align};">{when}</div><div class="clearfix"></div>', unsafe_allow_html=True
                )
            if text:
                bg = color_map.get(author, "#EDEDED"); text_color = "#FFF" if cls=="out" else "#000"
                st.markdown(
                    f'<div class="chat-bubble" style="background:{bg};color:{text_color};float:{align};">{text}</div>'
                    f'<div class="chat-timestamp" style="text-align:{align};">{when}</div><div class="clearfix"></div>', unsafe_allow_html=True
                )

        st.markdown("---")
        text_key = f"new_msg_{index}"
        with st.form(key=f"detail_comment_form_{index}", clear_on_submit=True):
            msg = st.text_input("Type your message here…", key=text_key, placeholder="Press Enter to send")
            sent = st.form_submit_button("Send")
            if sent and _submit_comment_value(index, msg): st.rerun()

        uploaded_file = st.file_uploader("Attach PDF, PNG or XLSX:", type=["pdf","png","xlsx"], key=f"fileuploader_{index}")
        _, cu = st.columns([1,1])
        with cu:
            if st.button("Upload File", key=f"upload_file_{index}") and uploaded_file:
                if _upload_attachment(index, uploaded_file):
                    st.success(f"Uploaded: {uploaded_file.name}"); st.rerun()

# ─────────────────────────────────────────────────────────────────────
# ----------------------- REQS LIST + DETAIL --------------------------
# ─────────────────────────────────────────────────────────────────────
elif st.session_state.page == "req_list":
    # persist flag & one-shot close
    st.session_state.setdefault("show_new_req", False)
    if st.session_state.pop("req_dialog_just_closed", False):
        st.session_state.show_new_req = False
        st.toast("✅ Requerimiento enviado.")

    @st.dialog(" 📄 Nuevo Requerimiento", width="large")
    def new_req_dialog():
        st.markdown("""
        <style>
          .stTextInput>label,.stDateInput>label,.stSelectbox>label{font-size:24px!important}
          .stTextInput input,.stDateInput input,.stSelectbox .css-1n76uvr{font-size:18px!important}
          button{font-size:18px!important}
        </style>""", unsafe_allow_html=True)

        st.session_state.setdefault("req_item_count", 1)
        c_add, c_rem = st.columns([1,1])
        if c_add.button("➕ Add Item", key="req_add_item"):
            st.session_state.req_item_count += 1; st.rerun()
        if c_rem.button("➖ Remove Item", key="req_remove_item") and st.session_state.req_item_count > 1:
            st.session_state.req_item_count -= 1; st.rerun()

        items = []
        for i in range(st.session_state.req_item_count):
            c1, c2, c3 = st.columns([3,2,1])
            desc   = c1.text_input("Description", key=f"req_desc_{i}")
            target = c2.text_input("Target Price", key=f"req_target_{i}")
            qty_in = c3.text_input("QTY", key=f"req_qty_{i}")
            try: qty = int(qty_in) if qty_in != "" else ""
            except: qty = qty_in
            items.append({"Description": desc, "Target Price": target, "QTY": qty})

        col_v, col_c, col_dt, col_st = st.columns([2,2,2,2])
        vendedores  = [" ","John","Andres","Luz","Tito","Marcela","Carolina","Sabrina","Juan"]
        compradores = [" ","David","Andres","Thea","Tito","Luz","Juan"]
        sel_v = col_v.selectbox("Vendedor", vendedores, key="req_vendedor")
        sel_c = col_c.selectbox("Comprador", compradores, key="req_comprador")
        dt    = col_dt.date_input("Date", value=date.today(), key="req_fecha")
        stt   = col_st.selectbox("Status", ["OPEN","PURCHASE TEAM REVIEW","SALES TEAM REVIEW","CLOSED W","CLOSED L"], key="req_status")

        send_col, cancel_col = st.columns([2,1])
        with send_col:
            if st.button("✅ Enviar Requerimiento", key="req_submit", use_container_width=True):
                cleaned = [it for it in items if (it["Description"] or "").strip()]
                if not cleaned or sel_c == " ":
                    st.error("❗ Completa al menos una descripción y el campo Comprador.")
                else:
                    add_request({"Type":"📑","Items": cleaned,"Vendedor Encargado": sel_v,"Comprador Encargado": sel_c,"Fecha": str(dt),"Status": stt})
                    new_idx = len(st.session_state.requests) - 1
                    st.session_state.comments[str(new_idx)] = []
                    save_data()
                    st.session_state.req_item_count = 1
                    st.session_state.show_new_req = False
                    st.session_state.req_dialog_just_closed = True
                    st.rerun()
        with cancel_col:
            if st.button("❌ Cancel", key="req_cancel", use_container_width=True):
                st.session_state.show_new_req = False; st.rerun()

    st.markdown("# 📝 Requerimientos Clientes")
    st.markdown("<hr>", unsafe_allow_html=True)
    _ = st_autorefresh(interval=1000, limit=None, key="req_list_refresh")
    load_data()

    col1, col2 = st.columns([3,1])
    search_term   = col1.text_input("Search", placeholder="Search requirements...")
    status_filter = col2.selectbox("Status", ["All","OPEN","PURCHASE TEAM REVIEW","SALES TEAM REVIEW","CLOSED W","CLOSED L"], key="req_list_status")

    def parse_fecha(r):
        try: return datetime.strptime(r.get("Fecha",""), "%Y-%m-%d").date()
        except: return date.max

    status_order = {"OPEN":0,"PURCHASE TEAM REVIEW":1,"SALES TEAM REVIEW":2,"CLOSED W":3,"CLOSED L":4}

    reqs = [r for r in st.session_state.requests
            if r.get("Type")=="📑"
            and (search_term.lower() in str(r).lower())
            and (status_filter=="All" or r.get("Status","OPEN")==status_filter)]
    reqs = sorted(reqs, key=lambda r: (status_order.get(r.get("Status","OPEN"), 0), parse_fecha(r)))

    flat = []
    for r in reqs:
        for itm in r.get("Items", []):
            flat.append({
                "Type": r["Type"], "Description": itm["Description"], "Target Price": itm["Target Price"],
                "Qty": itm["QTY"], "Vendedor": r.get("Vendedor Encargado",""), "Comprador": r.get("Comprador Encargado",""),
                "Status": r.get("Status","OPEN"), "Date": r.get("Fecha",""), "_req_obj": r
            })

    df_export = pd.DataFrame([{k:v for k,v in row.items() if not k.startswith("_")} for row in flat])

    col_export, col_new, col_all = st.columns([3,1,1])
    with col_export:
        st.download_button("📥 Export Filtered Requests to CSV",
                           df_export.to_csv(index=False).encode("utf-8"),
                           "req_requests.csv","text/csv", use_container_width=True)
    with col_new:
        if st.button("➕ New Requirement", key="nav_new_req", use_container_width=True):
            st.session_state.show_new_req = True; st.rerun()
    with col_all:
        if st.button("📋 All Purchase/Sales Orders", key="nav_all_req", use_container_width=True):
            st.session_state.page = "requests"; st.rerun()

    if st.session_state.show_new_req: new_req_dialog()

    if reqs:
        st.markdown("""
        <style>
          .header-row{font-weight:bold;font-size:18px;padding:0.5rem 0}
          .type-icon{font-size:20px}
          .status-open{background:#2ecc71;color:#fff;padding:4px 8px;border-radius:12px;display:inline-block}
          .status-purchase-review{background:#007BFF;color:#fff;padding:4px 8px;border-radius:12px;display:inline-block}
          .status-sales-review{background:#FD7E14;color:#fff;padding:4px 8px;border-radius:12px;display:inline-block}
          .status-closed{background:#e74c3c;color:#fff;padding:4px 8px;border-radius:12px;display:inline-block}
        </style>
        """, unsafe_allow_html=True)

        hdr_cols = st.columns([0.5,0.5,2,1,1,1,1,1.5,1,1])
        headers  = ["","Type","Description","Target Price","Qty","Vendedor","Comprador","Status","Date",""]
        for c,h in zip(hdr_cols, headers): c.markdown(f"<div class='header-row'>{h}</div>", unsafe_allow_html=True)

        user = st.session_state.user_name
        for i, row in enumerate(flat):
            cols = st.columns([0.5,0.5,2,1,1,1,1,1.5,1,1])
            idx  = st.session_state.requests.index(row["_req_obj"])

            comments_list = st.session_state.comments.get(str(idx), [])
            unread_cnt = sum(1 for c in comments_list if c.get("author","") != user and user not in c.get("read_by", []))
            cols[0].markdown(f"<span class='status-open'>💬{unread_cnt}</span>" if unread_cnt>0 else "", unsafe_allow_html=True)

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
            elif status in ["CLOSED W","CLOSED L"]:
                html = f"<span class='status-closed'>{status}</span>"
            else:
                html = status
            cols[7].markdown(html, unsafe_allow_html=True)
            cols[8].write(row['Date'])

            with cols[9]:
                a1, a2 = st.columns([1,1])
                if a1.button("🔍", key=f"view_{i}", use_container_width=True):
                    for c in comments_list:
                        if c.get("author","") != user:
                            c.setdefault("read_by", [])
                            if user not in c["read_by"]: c["read_by"].append(user)
                    save_data()
                    st.session_state.selected_request = idx
                    st.session_state.page = "req_detail"
                    st.rerun()
                if a2.button("❌", key=f"del_{i}", use_container_width=True):
                    delete_request(idx); st.rerun()
    else:
        st.info("No hay requerimientos que coincidan.")

    st.markdown("---")
    if st.button("⬅ Back to Home", key="req_list_back"): st.session_state.page = "home"; st.rerun()

elif st.session_state.page == "req_detail":
    # comment/upload de-dupe for req_detail too
    import time
    _ = st_autorefresh(interval=1000, limit=None, key="requests_refresh")
    load_data()

    idx = st.session_state.selected_request
    request = st.session_state.requests[idx]
    updated = {}
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    st.markdown("""
    <style>
      [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { font-size:24px!important; }
      [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { font-size:16px!important; }
      button { font-size:16px!important; }
    </style>
    """, unsafe_allow_html=True)
    st.sidebar.markdown("### 📄 Requerimientos Clientes Details")

    original_status = request.get("Status", "OPEN")
    status_options = ["OPEN","PURCHASE TEAM REVIEW","SALES TEAM REVIEW","CLOSED W","CLOSED L"]
    status = st.sidebar.selectbox("Status", status_options,
                                  index=status_options.index(original_status) if original_status in status_options else 0,
                                  key="req_detail_status")
    if status != original_status: updated["Status"] = status

    if status == "CLOSED L":
        reason_default = request.get("Close L Reason", "")
        reason = st.sidebar.text_area("Reason for Closure (L)", value=reason_default, key="req_detail_reason_l")
        if reason != reason_default: updated["Close L Reason"] = reason

    items = request.get("Items", [])
    st.session_state.setdefault("items_count", max(1, len(items)))
    st.sidebar.markdown("### 📋 Items")
    ca, cr = st.sidebar.columns([1,1])
    if ca.button("➕ Add Item", key="req_detail_add"): st.session_state["items_count"] += 1
    if cr.button("➖ Remove Item", key="req_detail_remove") and st.session_state["items_count"] > 1: st.session_state["items_count"] -= 1

    new_items = []
    for i in range(st.session_state["items_count"]):
        c1, c2, c3 = st.sidebar.columns([3,2,1])
        dv = items[i] if i < len(items) else {"Description": "", "Target Price": "", "QTY": ""}
        desc = c1.text_input("Description", value=dv["Description"], key=f"req_detail_desc_{i}")
        targ = c2.text_input("Target Price", value=dv["Target Price"], key=f"req_detail_target_{i}")
        qty_in = c3.text_input("QTY", value=str(dv["QTY"]), key=f"req_detail_qty_{i}")
        try: qty = int(qty_in) if qty_in != "" else ""
        except: qty = qty_in
        new_items.append({"Description": desc, "Target Price": targ, "QTY": qty})
    if new_items != items: updated["Items"] = new_items

    vendedores = [" ","John","Andres","Luz","Tito","Marcela","Carolina","Sabrina","Juan"]
    compradores = [" ","David","Andres","Thea","Tito","Luz","Juan"]
    cv, cc = st.sidebar.columns(2)
    vend0 = request.get("Vendedor Encargado", " ")
    comp0 = request.get("Comprador Encargado", " ")
    sel_v = cv.selectbox("Vendedor", vendedores, index=vendedores.index(vend0) if vend0 in vendedores else 0, key="req_detail_vendedor")
    sel_c = cc.selectbox("Comprador", compradores, index=compradores.index(comp0) if comp0 in compradores else 0, key="req_detail_comprador")
    if sel_v != vend0: updated["Vendedor Encargado"] = sel_v
    if sel_c != comp0: updated["Comprador Encargado"] = sel_c

    dt0 = request.get("Fecha", str(date.today()))
    dt = st.sidebar.date_input("Date", value=pd.to_datetime(dt0), key="req_detail_date")
    if str(dt) != dt0: updated["Fecha"] = str(dt)

    cs, cd, cb = st.sidebar.columns(3, gap="small")
    with cs:
        if updated and st.button("💾 Save", key="req_detail_save", use_container_width=True):
            if "Items" in updated: st.session_state["items_count"] = len(updated["Items"])
            request.update(updated); st.session_state.requests[idx] = request
            save_data(); st.sidebar.success("✅ Saved")
    with cd:
        if st.button("🗑️ Delete", key="req_detail_delete", use_container_width=True):
            delete_request(idx)
    with cb:
        if st.button("⬅ Back", key="req_detail_back", use_container_width=True):
            st.session_state.page = "req_list"; st.rerun()
    st.sidebar.markdown("---")

    # Comments (de-duped)
    def _submit_comment_value(idx: int, value: str) -> bool:
        txt = (value or "").strip()
        if not txt: return False
        guard = st.session_state.setdefault("comment_guard", {})
        now = time.time()
        sig = f"{st.session_state.user_name}|{txt}"
        last = guard.get(str(idx))
        if last and last.get("sig")==sig and (now - last.get("ts",0)) < 3.0:
            return False
        add_comment(idx, st.session_state.user_name, txt)
        guard[str(idx)] = {"sig": sig, "ts": now}
        st.session_state["comment_guard"] = guard
        return True

    def _upload_attachment(idx: int, uploaded_file) -> bool:
        if not uploaded_file: return False
        guard = st.session_state.setdefault("upload_guard", {})
        now = time.time()
        last = guard.get(str(idx))
        if last and last.get("name")==uploaded_file.name and (now - last.get("ts",0)) < 3.0:
            return False
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        fn = f"{idx}_{ts}_{uploaded_file.name}"
        with open(os.path.join(UPLOADS_DIR, fn), "wb") as f:
            f.write(uploaded_file.getbuffer())
        add_comment(idx, st.session_state.user_name, "", attachment=fn)
        guard[str(idx)] = {"name": uploaded_file.name, "ts": now}
        st.session_state["upload_guard"] = guard
        return True

    st.markdown("## 💬 Comments")
    col_l, col_center, col_r = st.columns([1,6,1])
    with col_center:
        st.markdown("""
        <style>
          .chat-author-in{font-size:12px;color:#555;margin:4px 0 0 5px;clear:both}
          .chat-author-out{font-size:12px;color:#333;margin:4px 5px 0 0;clear:both;text-align:right}
          .chat-bubble{padding:8px 12px;border-radius:16px;max-width:60%;margin:2px 0;word-wrap:break-word;clear:both}
          .chat-timestamp{font-size:10px;color:#888;margin:2px 0 8px}
          .chat-attachment{background:#DDEEFF;color:#003366;padding:8px 12px;border-radius:8px;float:left;max-width:60%;margin:4px 0;clear:both;word-wrap:break-word}
          .attachment-link{color:#003366;text-decoration:none;font-weight:600}
        </style>
        """, unsafe_allow_html=True)

        existing_comments = st.session_state.comments.get(str(idx), [])
        authors = []
        for c in existing_comments:
            if c["author"] not in authors: authors.append(c["author"])
        base_colors = ["#D1E8FF","#FFD1DC","#DFFFD6","#FFFACD","#E0E0E0"]
        color_map = {a: base_colors[i % len(base_colors)] for i,a in enumerate(authors)}

        for comment in existing_comments:
            author = comment["author"]; text = comment.get("text",""); when = comment.get("when","")
            attachment = comment.get("attachment")
            file_path = os.path.join(UPLOADS_DIR, attachment) if attachment else None
            bg = color_map.get(author, "#EDEDED")
            align = "right" if author == st.session_state.user_name else "left"
            float_dir = align
            cls = 'out' if author == st.session_state.user_name else 'in'
            st.markdown(f'<div class="chat-author-{cls}" style="text-align:{align};">{author}</div>', unsafe_allow_html=True)
            if attachment:
                link_html = f'<a href="/{file_path}" class="attachment-link" download>{attachment}</a>'
                st.markdown(
                    f'<div class="chat-attachment" style="float:{float_dir};">📎 {link_html}</div>'
                    f'<div class="chat-timestamp" style="text-align:{align};">{when}</div>'
                    f'<div style="clear:both;"></div>', unsafe_allow_html=True
                )
            if text:
                st.markdown(
                    f'<div class="chat-bubble" style="background:{bg}; float:{float_dir};">{text}</div>'
                    f'<div class="chat-timestamp" style="text-align:{align};">{when}</div>'
                    f'<div style="clear:both;"></div>', unsafe_allow_html=True
                )

        st.markdown("---")
        text_key = f"new_msg_{idx}"
        with st.form(key=f"comment_form_{idx}", clear_on_submit=True):
            msg = st.text_input("Type your message here…", key=text_key, placeholder="Press Enter to send")
            sent = st.form_submit_button("Send")
            if sent and _submit_comment_value(idx, msg): st.rerun()

        uploaded_file = st.file_uploader("Attach PDF, PNG or XLSX:", type=["pdf","png","xlsx"], key=f"fileuploader_{idx}")
        _, cu = st.columns([1,1])
        with cu:
            if st.button("Upload File", key=f"upload_file_{idx}") and uploaded_file:
                if _upload_attachment(idx, uploaded_file):
                    st.success(f"Uploaded: {uploaded_file.name}"); st.rerun()



