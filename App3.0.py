import math as m
import streamlit as st
import pandas as pd
import json
import os
import hashlib
import logging
from datetime import date, datetime
from streamlit_autorefresh import st_autorefresh
import plotly.express as px
from pathlib import Path
import platform

# ========================================
# CONFIGURATION & CONSTANTS
# ========================================

class Config:
    """Centralized configuration"""
    # File paths
    REQUESTS_FILE = "requests.json"
    COMMENTS_FILE = "comments.json"
    UPLOADS_DIR = "uploads"
    
    # User authentication (hashed passwords)
    VALID_USERS = {
        "Andres": hashlib.sha256("123".encode()).hexdigest(),
        "Marcela": hashlib.sha256("123".encode()).hexdigest(),
        "Tito": hashlib.sha256("123".encode()).hexdigest(),
        "Luz": hashlib.sha256("123".encode()).hexdigest(),
        "David": hashlib.sha256("123".encode()).hexdigest(),
        "John": hashlib.sha256("123".encode()).hexdigest(),
        "Sabrina": hashlib.sha256("123".encode()).hexdigest(),
        "Bodega": hashlib.sha256("123".encode()).hexdigest(),
        "Carolina": hashlib.sha256("123".encode()).hexdigest(),
        "Facturacion": hashlib.sha256("123".encode()).hexdigest()
    }
    
    # Access control groups
    SUMMARY_ALLOWED = {"Andres", "David", "Tito", "Luz"}
    SALES_CREATORS = {"Andres", "Tito", "Luz", "David", "John", "Sabrina", "Carolina"}
    PURCHASE_CREATORS = {"Andres", "Tito", "Luz", "David"}
    PRICE_ALLOWED = {"Andres", "Luz", "Tito", "David"}
    BODEGA_USERS = {"Bodega", "Andres", "Tito", "Luz", "David"}
    REQS_DENIED = {"Bodega"}
    
    # Status options
    STATUS_OPTIONS = [
        "IMPRIMIR", "IMPRESA", "SEPARAR Y CONFIRMAR",
        "RECIBIDO / PROCESANDO", "PENDIENTE", 
        "SEPARADO - PENDIENTE", "COMPLETE", "READY", 
        "CANCELLED", "IN TRANSIT", "RETURNED/CANCELLED"
    ]
    
    # Status colors
    STATUS_COLORS = {
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
        "RETURNED/CANCELLED": "#c0392b"
    }
    
    # Auto-refresh settings (optimized)
    REFRESH_INTERVAL = 5000  # 5 seconds instead of 1
    REFRESH_LIMIT = 200      # Limit refreshes

# ========================================
# LOGGING SETUP
# ========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('help_center.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========================================
# UTILITY FUNCTIONS
# ========================================

def hash_password(password):
    """Hash password for secure storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(username, password):
    """Verify user credentials"""
    stored_hash = Config.VALID_USERS.get(username)
    return stored_hash == hash_password(password)

def safe_load_json(filepath, default=None):
    """Safely load JSON with comprehensive error handling"""
    try:
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            return default or []
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Successfully loaded {filepath}")
            return data
    except (json.JSONDecodeError, IOError, OSError) as e:
        logger.error(f"Error loading {filepath}: {e}")
        st.error(f"Error loading data from {filepath}")
        return default or []

def safe_save_json(filepath, data):
    """Safely save JSON with error handling"""
    try:
        # Create backup before saving
        if os.path.exists(filepath):
            backup_path = f"{filepath}.backup"
            os.rename(filepath, backup_path)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully saved {filepath}")
        return True
    except (IOError, OSError) as e:
        logger.error(f"Error saving {filepath}: {e}")
        st.error(f"Error saving data to {filepath}")
        return False

def validate_request_data(request_data):
    """Validate request data before saving"""
    required_fields = ['Type', 'Status', 'Encargado']
    
    for field in required_fields:
        if not request_data.get(field) or request_data[field] == " ":
            raise ValueError(f"Required field '{field}' is missing or empty")
    
    # Validate quantities are numeric where expected
    if 'Quantity' in request_data and isinstance(request_data['Quantity'], list):
        for i, qty in enumerate(request_data['Quantity']):
            if qty != "" and qty is not None:
                try:
                    float(qty)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid quantity at index {i}: {qty}")
    
    # Validate prices are numeric where expected
    price_fields = ['Cost', 'Sale Price']
    for price_field in price_fields:
        if price_field in request_data and isinstance(request_data[price_field], list):
            for i, price in enumerate(request_data[price_field]):
                if price != "" and price is not None:
                    try:
                        float(price)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid {price_field} at index {i}: {price}")
    
    return True

def format_status_badge(status):
    """Create colored status badge"""
    if not status:
        return ""
    
    status = status.upper()
    color = Config.STATUS_COLORS.get(status, "#7f8c8d")
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

def apply_global_styling():
    """Apply consistent styling across the app"""
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
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stDateInput > div > div > input {
        border-radius: 8px !important;
        border: 1px solid #dfe6ec !important;
        padding: 0.5rem !important;
        background-color: #f7f9fc !important;
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
    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
    }
    </style>
    """, unsafe_allow_html=True)

# ========================================
# EXPORT FUNCTIONALITY
# ========================================

def choose_export_dir():
    """Choose appropriate export directory"""
    env = os.environ.get("HELP_CENTER_EXPORT_DIR")
    if env:
        p = Path(env).expanduser()
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass

    if platform.system() == "Darwin":
        mac_path = Path.home() / "Downloads" / "Automation_Project_Titos"
        try:
            mac_path.mkdir(parents=True, exist_ok=True)
            return mac_path
        except Exception:
            pass

    p = Path.cwd() / "exports"
    p.mkdir(parents=True, exist_ok=True)
    return p

EXPORT_DIR = choose_export_dir()
EXPORT_ORDERS_CSV = str(EXPORT_DIR / "orders.csv")
EXPORT_REQUIREMENTS_CSV = str(EXPORT_DIR / "requirements.csv")
EXPORT_COMMENTS_CSV = str(EXPORT_DIR / "comments.csv")
EXPORT_XLSX = str(EXPORT_DIR / "HelpCenter_Snapshot.xlsx")
EXPORT_JSON = str(EXPORT_DIR / "HelpCenter_Snapshot.json")

def export_snapshot_to_disk():
    """Export data to various formats with error handling"""
    try:
        from pathlib import Path
        export_dir = Path(EXPORT_DIR)
        export_dir.mkdir(parents=True, exist_ok=True)

        # Build Orders DataFrame
        orders_rows = []
        for i, r in enumerate(st.session_state.get("requests", []) or []):
            t = r.get("Type")
            if t not in ("💲", "🛒"):
                continue

            descs = r.get("Description") or []
            qtys = r.get("Quantity") or []
            price_key = "Cost" if t == "💲" else "Sale Price"
            prices = r.get(price_key) or []

            n = max(len(descs), len(qtys), len(prices), 1)
            for j in range(n):
                orders_rows.append({
                    "RequestIndex": i,
                    "Type": t,
                    "Ref#": r.get("Invoice","") if t == "💲" else r.get("Order#",""),
                    "Item #": j + 1,
                    "Description": descs[j] if j < len(descs) else "",
                    "Qty": qtys[j] if j < len(qtys) else "",
                    "Price": prices[j] if j < len(prices) else "",
                    "Status": r.get("Status",""),
                    "Ordered Date": r.get("Date",""),
                    "ETA Date": r.get("ETA Date",""),
                    "Shipping Method": r.get("Shipping Method",""),
                    "Encargado": r.get("Encargado",""),
                    "Partner": r.get("Proveedor","") if t == "💲" else r.get("Cliente",""),
                    "Pago": r.get("Pago",""),
                })
        orders_df = pd.DataFrame(orders_rows)

        # Build Requirements DataFrame
        req_rows = []
        for i, r in enumerate(st.session_state.get("requests", []) or []):
            if r.get("Type") != "📑":
                continue
            for j, it in enumerate(r.get("Items", []) or []):
                req_rows.append({
                    "RequestIndex": i,
                    "Item #": j + 1,
                    "Description": it.get("Description",""),
                    "Target Price": it.get("Target Price",""),
                    "Qty": it.get("QTY",""),
                    "Vendedor Encargado": r.get("Vendedor Encargado",""),
                    "Comprador Encargado": r.get("Comprador Encargado",""),
                    "Fecha": r.get("Fecha",""),
                    "Status": r.get("Status","OPEN"),
                })
        req_df = pd.DataFrame(req_rows)

        # Build Comments DataFrame
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
                    "When": c.get("when",""),
                    "Text": c.get("text",""),
                    "Attachment": c.get("attachment",""),
                })
        comments_df = pd.DataFrame(comments_rows)

        # Write CSVs
        orders_df.to_csv(EXPORT_ORDERS_CSV, index=False, encoding="utf-8-sig")
        req_df.to_csv(EXPORT_REQUIREMENTS_CSV, index=False, encoding="utf-8-sig")
        comments_df.to_csv(EXPORT_COMMENTS_CSV, index=False, encoding="utf-8-sig")

        # Write Excel
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
            st.warning(f"Excel file was locked. Saved to {alt.name}")

        # Write JSON snapshot
        snap = {
            "requests": st.session_state.get("requests", []),
            "comments": st.session_state.get("comments", {})
        }
        with open(EXPORT_JSON, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)

        logger.info("Export snapshot completed successfully")
        return True

    except Exception as e:
        logger.error(f"Export failed: {e}")
        st.error(f"Export failed: {str(e)}")
        return False

# ========================================
# DATA MANAGEMENT
# ========================================

def load_data():
    """Load requests and comments with error handling"""
    try:
        # Load requests
        requests = safe_load_json(Config.REQUESTS_FILE, [])
        st.session_state.requests = requests

        # Load comments
        comments = safe_load_json(Config.COMMENTS_FILE, {})
        st.session_state.comments = comments

        # If both are empty, try to restore from backup
        if not requests and not comments:
            if try_restore_from_snapshot():
                st.toast("✅ Data restored from backup", icon="✅")
        
        logger.info(f"Loaded {len(requests)} requests and {len(comments)} comment threads")
        
    except Exception as e:
        logger.error(f"Error in load_data: {e}")
        st.error("Failed to load application data")
        st.session_state.requests = []
        st.session_state.comments = {}

def save_data():
    """Save requests and comments with error handling"""
    try:
        # Validate data before saving
        for i, request in enumerate(st.session_state.requests):
            try:
                validate_request_data(request)
            except ValueError as e:
                logger.warning(f"Request {i} validation warning: {e}")

        # Save files
        if not safe_save_json(Config.REQUESTS_FILE, st.session_state.requests):
            return False
        
        if not safe_save_json(Config.COMMENTS_FILE, st.session_state.comments):
            return False

        # Auto-export
        export_snapshot_to_disk()
        
        logger.info("Data saved successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in save_data: {e}")
        st.error("Failed to save data")
        return False

def add_request(data):
    """Add new request with validation"""
    try:
        validate_request_data(data)
        
        idx = len(st.session_state.requests)
        st.session_state.requests.append(data)
        st.session_state.comments[str(idx)] = []
        
        if save_data():
            logger.info(f"Added new request: {data['Type']} by {st.session_state.user_name}")
            return True
        return False
        
    except ValueError as e:
        st.error(f"Invalid request data: {e}")
        return False
    except Exception as e:
        logger.error(f"Error adding request: {e}")
        st.error("Failed to add request")
        return False

def add_comment(index, author, text="", attachment=None):
    """Add comment with validation"""
    try:
        key = str(index)
        if key not in st.session_state.comments:
            st.session_state.comments[key] = []
        
        comment_entry = {
            "author": author,
            "text": text,
            "when": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "read_by": [author]  # Author automatically marks as read
        }
        
        if attachment:
            comment_entry["attachment"] = attachment
        
        st.session_state.comments[key].append(comment_entry)
        save_data()
        
        logger.info(f"Comment added by {author} to request {index}")
        
    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        st.error("Failed to add comment")

def delete_request(index):
    """Delete request with confirmation"""
    try:
        if 0 <= index < len(st.session_state.requests):
            deleted_request = st.session_state.requests.pop(index)
            st.session_state.comments.pop(str(index), None)
            
            # Re-index comments
            new_comments = {}
            for i in range(len(st.session_state.requests)):
                old_key = str(i if i < index else i + 1)
                if old_key in st.session_state.comments:
                    new_comments[str(i)] = st.session_state.comments[old_key]
            
            st.session_state.comments = new_comments
            
            if save_data():
                logger.info(f"Deleted request {index}: {deleted_request.get('Type', 'Unknown')} by {st.session_state.user_name}")
                st.success("🗑️ Request deleted successfully")
                return True
        return False
        
    except Exception as e:
        logger.error(f"Error deleting request: {e}")
        st.error("Failed to delete request")
        return False

def try_restore_from_snapshot():
    """Restore from JSON snapshot or CSV backup"""
    try:
        # Try JSON snapshot first
        if os.path.exists(EXPORT_JSON) and os.path.getsize(EXPORT_JSON) > 0:
            with open(EXPORT_JSON, "r", encoding="utf-8") as f:
                snap = json.load(f)
            
            st.session_state.requests = snap.get("requests", [])
            st.session_state.comments = snap.get("comments", {})
            
            # Save to primary files
            safe_save_json(Config.REQUESTS_FILE, st.session_state.requests)
            safe_save_json(Config.COMMENTS_FILE, st.session_state.comments)
            
            logger.info("Restored from JSON snapshot")
            return True
            
    except Exception as e:
        logger.error(f"Restore from snapshot failed: {e}")
    
    return False

# ========================================
# NAVIGATION HELPER
# ========================================

def go_to(page):
    """Navigate to page with logging"""
    st.session_state.page = page
    logger.info(f"Navigation: {st.session_state.user_name} -> {page}")
    st.rerun()

# ========================================
# APP CONFIGURATION & INITIALIZATION
# ========================================

st.set_page_config(
    page_title="Tito's Depot Help Center", 
    layout="wide", 
    page_icon="🛒",
    initial_sidebar_state="expanded"
)

# Ensure directories exist
os.makedirs(Config.UPLOADS_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# Apply global styling
apply_global_styling()

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "page" not in st.session_state:
    st.session_state.page = "login"
if "selected_request" not in st.session_state:
    st.session_state.selected_request = None

# Load data on startup
if "requests" not in st.session_state or "comments" not in st.session_state:
    load_data()

# ========================================
# LOGIN PAGE
# ========================================

if not st.session_state.authenticated:
    st.markdown("# 🔒 Please Log In")
    st.write("Enter your username and password to continue.")
    
    with st.form("login_form"):
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        login_button = st.form_submit_button("🔑 Log In")
        
        if login_button:
            if verify_password(username_input, password_input):
                st.session_state.authenticated = True
                st.session_state.user_name = username_input
                st.session_state.page = "home"
                logger.info(f"User logged in: {username_input}")
                st.success(f"Welcome, **{username_input}**!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")
                logger.warning(f"Failed login attempt: {username_input}")
    
    st.stop()

# ========================================
# HOME PAGE
# ========================================

if st.session_state.page == "home":
    # Logout button in sidebar
    with st.sidebar:
        if st.button("🚪 Log Out"):
            st.session_state.authenticated = False
            st.session_state.user_name = ""
            st.session_state.page = "login"
            logger.info(f"User logged out: {st.session_state.user_name}")
            st.rerun()

    st.markdown("# 🏠 Welcome to the Help Center")
    st.markdown(f"Logged in as: **{st.session_state.user_name}**")
    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

    # Quick stats
    total_requests = len(st.session_state.requests)
    active_requests = len([r for r in st.session_state.requests 
                          if r.get("Status", "").upper() not in ["COMPLETE", "CANCELLED"]])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Requests", total_requests)
    col2.metric("Active Requests", active_requests) 
    col3.metric("My Access Level", "Admin" if st.session_state.user_name in Config.SUMMARY_ALLOWED else "User")

    st.markdown("---")

    # Navigation buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.session_state.user_name not in Config.REQS_DENIED:
            if st.button("📝 View Requerimientos Clientes", use_container_width=True):
                go_to("req_list")
        else:
            st.button("🔒 View Requerimientos Clientes", disabled=True, use_container_width=True)
            st.caption("Access denied for your role")

    with col2:
        if st.button("📋 View All Purchase/Sales Orders", use_container_width=True):
            go_to("requests")

    with col3:
        if st.session_state.user_name in Config.SUMMARY_ALLOWED:
            if st.button("📊 Summary", use_container_width=True):
                go_to("summary")
        else:
            st.button("🔒 Summary", disabled=True, use_container_width=True)
            st.caption("Admin access required")

    # Backup & Restore section
    with st.expander("📦 Backup & Restore"):
        st.caption(f"Export folder: {EXPORT_DIR}")
        
        snap = {
            "requests": st.session_state.get("requests", []),
            "comments": st.session_state.get("comments", {})
        }
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "⬇️ Download Backup (JSON)",
                data=json.dumps(snap, ensure_ascii=False, indent=2),
                file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col2:
            uploaded = st.file_uploader("Restore from backup", type=["json"])
            if uploaded and st.button("🔄 Restore Now"):
                try:
                    data = json.load(uploaded)
                    st.session_state.requests = data.get("requests", [])
                    st.session_state.comments = data.get("comments", {})
                    save_data()
                    st.success("✅ Data restored successfully")
                    logger.info(f"Data restored by {st.session_state.user_name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Restore failed: {e}")
                    logger.error(f"Restore failed: {e}")


#####

elif st.session_state.page == "summary":
    import pandas as pd
    import plotly.express as px
    from datetime import date

    # ──────────────────────────────────────────────────────────────────────
    # Helpers & Config
    # ──────────────────────────────────────────────────────────────────────
    status_colors = {
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
        "RETURNED/CANCELLED": "#c0392b"
    }

    def pick_qty(row):
        """Extract quantity from various possible columns"""
        if pd.notna(row.get('Qty')):
            return row['Qty']
        for col in ("Quantity", "Items"):
            v = row.get(col)
            if isinstance(v, list) and v:
                return v[0]
            if pd.notna(v):
                return v
        return 0

    def flatten(v):
        """Flatten list values to single values"""
        if isinstance(v, list) and v:
            return v[0]
        return v if pd.notna(v) else ""

    def badge(status):
        """Create colored status badge"""
        color = status_colors.get(status, "#95a5a6")
        return f"<span style='background-color:{color}; color:white; padding:2px 6px; border-radius:4px; font-size:12px;'>{status}</span>"

    # ──────────────────────────────────────────────────────────────────────
    # Load & Validate Data
    # ──────────────────────────────────────────────────────────────────────
    load_data()
    
    if 'requests' not in st.session_state or not st.session_state.requests:
        st.info("No data available to summarize.")
        st.button("⬅ Back to Home", on_click=lambda: go_to("home"))
        st.stop()

    raw = pd.DataFrame(st.session_state.requests)

    if raw.empty or "Type" not in raw.columns:
        st.info("No Purchase Orders or Sales Orders to summarize yet.")
        st.button("⬅ Back to Home", on_click=lambda: go_to("home"))
        st.stop()

    # Filter for POs (💲) and SOs (🛒) only
    df = raw[raw["Type"].isin(["💲", "🛒"])].copy()
    if df.empty:
        st.info("No Purchase Orders or Sales Orders to summarize yet.")
        st.button("⬅ Back to Home", on_click=lambda: go_to("home"))
        st.stop()

    # ──────────────────────────────────────────────────────────────────────
    # Data Cleaning & Processing
    # ──────────────────────────────────────────────────────────────────────
    df["Status"] = df["Status"].astype(str).str.strip().str.upper()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["ETA Date"] = pd.to_datetime(df["ETA Date"], errors="coerce")
    
    # Create reference number column
    df["Ref#"] = df.apply(
        lambda r: r.get("Invoice", "") if r["Type"] == "💲" else r.get("Order#", ""),
        axis=1
    )

    # Calculate date-based flags
    today = pd.Timestamp(date.today())
    completed_cancelled = ["COMPLETE", "CANCELLED", "RETURNED/CANCELLED"]
    
    overdue_mask = (
        (df["ETA Date"] < today) & 
        (~df["Status"].isin(completed_cancelled)) &
        (df["ETA Date"].notna())
    )
    
    due_today_mask = (
        (df["ETA Date"] == today.normalize()) & 
        (~df["Status"].isin(["CANCELLED", "RETURNED/CANCELLED"]))
    )

    # ──────────────────────────────────────────────────────────────────────
    # Summary Metrics
    # ──────────────────────────────────────────────────────────────────────
    st.subheader("📊 Summary")
    k1, k2, k3, k4 = st.columns(4)
    
    total_requests = len(df)
    active_requests = len(df[~df["Status"].isin(completed_cancelled)])
    overdue_count = len(df[overdue_mask])
    due_today_count = len(df[due_today_mask])
    
    k1.metric("Total Requests", total_requests)
    k2.metric("Active Requests", active_requests)
    k3.metric("Overdue Requests", overdue_count)
    k4.metric("Due Today", due_today_count)
    
    st.markdown("---")

    # ──────────────────────────────────────────────────────────────────────
    # Charts and Tables
    # ──────────────────────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Status Distribution")
        status_counts = df["Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        
        if not status_counts.empty:
            fig = px.pie(
                status_counts,
                names="Status",
                values="Count",
                color="Status",
                color_discrete_map=status_colors,
            )
            fig.update_traces(textinfo="label+value", textposition="inside")
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data to display")

    with col2:
        # Due Today Table
        st.subheader("Due Today")
        due_today_df = df[due_today_mask].copy()
        
        if not due_today_df.empty:
            # Process data for display
            due_today_df["Qty"] = due_today_df.apply(pick_qty, axis=1)
            due_today_df["Description"] = due_today_df["Description"].apply(flatten)
            
            display_cols = ["Type", "Ref#", "Description", "Qty", "Encargado", "Status"]
            display_df = due_today_df[display_cols].copy()
            display_df["Status"] = display_df["Status"].apply(badge)
            
            st.markdown(
                display_df.to_html(index=False, escape=False),
                unsafe_allow_html=True
            )
        else:
            st.info("No orders due today.")
        
        st.markdown("---")

        # Overdue Table
        st.subheader("Overdue Orders")
        overdue_df = df[overdue_mask].copy()
        
        if not overdue_df.empty:
            # Process data for display
            overdue_df["Qty"] = overdue_df.apply(pick_qty, axis=1)
            overdue_df["Description"] = overdue_df["Description"].apply(flatten)
            
            display_cols = ["Type", "Ref#", "Description", "Qty", "Encargado", "Status"]
            display_df = overdue_df[display_cols].copy()
            display_df["Status"] = display_df["Status"].apply(badge)
            
            st.markdown(
                display_df.to_html(index=False, escape=False),
                unsafe_allow_html=True
            )
        else:
            st.info("No overdue orders.")

    st.markdown("---")
    st.button("⬅ Back to Home", on_click=lambda: go_to("home"))
# ──────────────────────────────────────────────────────────────────────
# ---------------- IMPROVED PURCHASE/SALES ORDERS PAGE ----------------
# ──────────────────────────────────────────────────────────────────────

if st.session_state.page == "requests":
    # ─── CONSTANTS & CONFIGURATION ─────────────────────────────────────
    USER = st.session_state.user_name
    
    ACCESS_GROUPS = {
        'SALES_CREATORS': {"Andres", "Tito", "Luz", "David", "John", "Sabrina", "Carolina"},
        'PURCHASE_CREATORS': {"Andres", "Tito", "Luz", "David"},
        'PRICE_ALLOWED': {"Andres", "Luz", "Tito", "David"},
        'BODEGA': {"Bodega", "Andres", "Tito", "Luz", "David"}
    }
    
    COMMON_OPTIONS = {
        'STATUS': ["COMPLETE", "READY", "CANCELLED", "IN TRANSIT"],
        'ENCARGADOS': ["Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"],
        'PAYMENT_METHODS': ["Wire", "Cheque", "Credito", "Efectivo"],
        'SHIPPING_METHODS': ["Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"]
    }

    # ─── UTILITY FUNCTIONS ─────────────────────────────────────────────
    def has_permission(group):
        return USER in ACCESS_GROUPS.get(group, set())

    def clean_numeric_input(value, data_type=float):
        """Clean and convert numeric inputs"""
        if not value or not str(value).strip():
            return None
        try:
            return data_type(float(value.strip()))
        except ValueError:
            return value.strip()

    def format_list_display(items):
        """Format list items for display"""
        if not items:
            return ""
        return ", ".join(str(item) for item in items if item)

    def format_money_list(amounts):
        """Format monetary amounts for display"""
        if not amounts:
            return ""
        formatted = []
        for amount in (amounts if isinstance(amounts, list) else [amounts]):
            try:
                formatted.append(f"${int(float(amount))}")
            except (ValueError, TypeError):
                formatted.append(str(amount))
        return ", ".join(formatted)

    def validate_required_fields(fields_dict):
        """Validate required form fields"""
        missing = [k for k, v in fields_dict.items() if not v or v == " "]
        return len(missing) == 0, missing

    # ─── SHARED FORM COMPONENTS ────────────────────────────────────────
    def render_item_inputs(prefix, item_count, labels):
        """Render item input rows for both PO and SO forms"""
        items = {label.lower(): [] for label in labels}
        
        for i in range(item_count):
            cols = st.columns([3, 2, 1] if len(labels) == 3 else [4, 2])
            for j, label in enumerate(labels):
                key = f"{prefix}_{label.lower()}_{i}"
                items[label.lower()].append(
                    cols[j].text_input(f"{label} #{i+1}", key=key)
                )
        return items

    def render_item_controls(prefix, session_key, max_items=10):
        """Render add/remove item controls"""
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add Item", key=f"add_{prefix}") and st.session_state[session_key] < max_items:
                st.session_state[session_key] += 1
                st.rerun()
        with col2:
            if st.session_state[session_key] > 1 and st.button("❌ Remove Item", key=f"remove_{prefix}"):
                st.session_state[session_key] -= 1
                st.rerun()

    # ─── ORDER DIALOGS ─────────────────────────────────────────────────
    @st.dialog("💲 New Purchase Order", width="large")
    def purchase_order_dialog():
        st.session_state.setdefault('purchase_item_rows', 1)
        
        # Basic Information
        col1, col2 = st.columns(2)
        with col1:
            po_number = st.text_input("PO Number", placeholder="12345")
            status = st.selectbox("Status *", [" "] + COMMON_OPTIONS['STATUS'])
            encargado = st.selectbox("Encargado *", [" "] + COMMON_OPTIONS['ENCARGADOS'])
        with col2:
            tracking = st.text_input("Tracking#", placeholder="TRK-45678")
            proveedor = st.text_input("Supplier", placeholder="Amazon")
            payment = st.selectbox("Payment Method", [" "] + COMMON_OPTIONS['PAYMENT_METHODS'])

        # Items Section
        st.markdown("### 📦 Items")
        items = render_item_inputs("po", st.session_state.purchase_item_rows, 
                                 ["Description", "Quantity", "Cost"])
        render_item_controls("po", "purchase_item_rows")

        # Shipping Information
        st.markdown("### 🚚 Shipping")
        col3, col4 = st.columns(2)
        with col3:
            order_date = st.date_input("Order Date", value=date.today())
        with col4:
            eta_date = st.date_input("ETA Date")
        shipping = st.selectbox("Shipping Method", [" "] + COMMON_OPTIONS['SHIPPING_METHODS'])

        # Submit/Cancel
        col_submit, col_cancel = st.columns([2, 1])
        with col_submit:
            if st.button("✅ Submit", use_container_width=True):
                # Clean and validate data
                clean_items = {}
                for key, values in items.items():
                    if key == "cost":
                        clean_items[key] = [clean_numeric_input(v) for v in values if v.strip()]
                    elif key == "quantity":
                        clean_items[key] = [clean_numeric_input(v, int) for v in values if v.strip()]
                    else:
                        clean_items[key] = [v.strip() for v in values if v.strip()]

                required_fields = {
                    "Status": status,
                    "Encargado": encargado,
                    "Items": len(clean_items.get('description', []))
                }
                
                valid, missing = validate_required_fields(required_fields)
                if not valid or not all(clean_items.values()):
                    st.error("❗ Please complete all required fields and items.")
                    return

                # Create request
                request_data = {
                    "Type": "💲",
                    "Invoice": po_number,
                    "Order#": tracking,
                    "Date": str(order_date),
                    "Status": status,
                    "Shipping Method": shipping,
                    "ETA Date": str(eta_date),
                    "Description": clean_items['description'],
                    "Quantity": clean_items['quantity'],
                    "Cost": clean_items['cost'],
                    "Proveedor": proveedor,
                    "Encargado": encargado,
                    "Pago": payment
                }
                
                add_request(request_data)
                export_snapshot_to_disk()
                st.success("✅ Purchase order created!")
                st.session_state.purchase_item_rows = 1
                st.rerun()

        with col_cancel:
            if st.button("❌ Cancel", use_container_width=True):
                st.rerun()

    @st.dialog("🛒 New Sales Order", width="large")
    def sales_order_dialog():
        st.session_state.setdefault('sales_item_rows', 1)
        
        # Basic Information
        col1, col2 = st.columns(2)
        with col1:
            ref_number = st.text_input("Reference#", placeholder="SO-2025-001")
            status = st.selectbox("Status *", [" "] + COMMON_OPTIONS['STATUS'])
            encargado = st.selectbox("Encargado *", [" "] + COMMON_OPTIONS['ENCARGADOS'])
        with col2:
            tracking = st.text_input("Tracking#", placeholder="TRK45678")
            cliente = st.text_input("Customer", placeholder="TechCorp LLC")
            payment = st.selectbox("Payment Method", [" "] + COMMON_OPTIONS['PAYMENT_METHODS'])

        # Items Section
        st.markdown("### 🧾 Items")
        items = render_item_inputs("so", st.session_state.sales_item_rows, 
                                 ["Description", "Quantity", "Price"])
        render_item_controls("so", "sales_item_rows")

        # Shipping Information
        st.markdown("### 🚚 Shipping")
        col3, col4 = st.columns(2)
        with col3:
            order_date = st.date_input("Order Date", value=date.today())
        with col4:
            eta_date = st.date_input("ETA Date")
        shipping = st.selectbox("Shipping Method", [" "] + COMMON_OPTIONS['SHIPPING_METHODS'])

        # Submit/Cancel
        col_submit, col_cancel = st.columns([2, 1])
        with col_submit:
            if st.button("✅ Submit", use_container_width=True):
                # Clean and validate data
                clean_items = {}
                for key, values in items.items():
                    if key == "price":
                        clean_items[key] = [clean_numeric_input(v) for v in values if v.strip()]
                    elif key == "quantity":
                        clean_items[key] = [clean_numeric_input(v, int) for v in values if v.strip()]
                    else:
                        clean_items[key] = [v.strip() for v in values if v.strip()]

                required_fields = {
                    "Status": status,
                    "Encargado": encargado,
                    "Items": len(clean_items.get('description', []))
                }
                
                valid, missing = validate_required_fields(required_fields)
                if not valid or not all(clean_items.values()):
                    st.error("❗ Please complete all required fields and items.")
                    return

                # Create request
                request_data = {
                    "Type": "🛒",
                    "Order#": ref_number,
                    "Invoice": tracking,
                    "Date": str(order_date),
                    "Status": status,
                    "Shipping Method": shipping,
                    "ETA Date": str(eta_date),
                    "Description": clean_items['description'],
                    "Quantity": clean_items['quantity'],
                    "Sale Price": clean_items['price'],
                    "Cliente": cliente,
                    "Encargado": encargado,
                    "Pago": payment
                }
                
                add_request(request_data)
                export_snapshot_to_disk()
                st.success("✅ Sales order created!")
                st.session_state.sales_item_rows = 1
                st.rerun()

        with col_cancel:
            if st.button("❌ Cancel", use_container_width=True):
                st.rerun()

    # ─── MAIN PAGE LOGIC ───────────────────────────────────────────────
    st.markdown("# 📋 Purchase & Sales Orders")
    st.markdown("---")
    
    # Auto-refresh and data loading
    st_autorefresh(interval=5000, key="requests_refresh")  # Reduced frequency
    load_data()
    export_snapshot_to_disk()

    # Show dialogs if triggered
    if st.session_state.get("show_new_po"):
        purchase_order_dialog()
    if st.session_state.get("show_new_so"):
        sales_order_dialog()

    # ─── FILTERS ──────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        search_term = st.text_input("🔍 Search", placeholder="Search orders...")
    with col2:
        all_statuses = ["All"] + [s for s in COMMON_OPTIONS['STATUS']] + ["IMPRIMIR", "IMPRESA", "SEPARAR Y CONFIRMAR"]
        status_filter = st.selectbox("Status Filter", all_statuses)
    with col3:
        type_filter = st.selectbox("Type Filter", ["All", "💲 Purchase", "🛒 Sales"])

    # ─── DATA FILTERING ──────────────────────────────────────────────
    # Get base data based on permissions
    all_requests = st.session_state.requests
    if has_permission('BODEGA'):
        base_requests = all_requests
    else:
        base_requests = [r for r in all_requests if r.get("Type") == "🛒"]

    # Apply filters
    filtered_requests = []
    for req in base_requests:
        if req.get("Type") not in {"💲", "🛒"}:
            continue
            
        # Search filter
        if search_term and search_term.lower() not in json.dumps(req).lower():
            continue
            
        # Status filter
        if status_filter != "All" and req.get("Status", "").upper() != status_filter:
            continue
            
        # Type filter
        if type_filter != "All":
            type_emoji = type_filter.split()[0]
            if req.get("Type") != type_emoji:
                continue
                
        filtered_requests.append(req)

    # Sort by ETA date
    def parse_eta(req):
        try:
            return datetime.strptime(req.get("ETA Date", ""), "%Y-%m-%d").date()
        except:
            return date.max

    filtered_requests.sort(key=parse_eta)

    # ─── ACTION BUTTONS ───────────────────────────────────────────────
    col_exp, col_po, col_so = st.columns([3, 1, 1])

    with col_exp:
        # Export functionality
        if filtered_requests:
            export_data = []
            show_prices = has_permission('PRICE_ALLOWED')
            
            for req in filtered_requests:
                is_purchase = req.get("Type") == "💲"
                row = {
                    "Type": req.get("Type", ""),
                    "Reference": req.get("Invoice" if is_purchase else "Order#", ""),
                    "Description": format_list_display(req.get("Description", [])),
                    "Quantity": format_list_display(req.get("Quantity", [])),
                    "Status": req.get("Status", ""),
                    "Order Date": req.get("Date", ""),
                    "ETA Date": req.get("ETA Date", ""),
                    "Shipping": req.get("Shipping Method", ""),
                    "Encargado": req.get("Encargado", ""),
                    "Partner": req.get("Proveedor" if is_purchase else "Cliente", ""),
                    "Payment": req.get("Pago", "")
                }
                
                if show_prices:
                    price_key = "Cost" if is_purchase else "Sale Price"
                    row[price_key] = format_money_list(req.get(price_key, []))
                    
                export_data.append(row)

            df = pd.DataFrame(export_data)
            st.download_button(
                "📥 Export to CSV",
                df.to_csv(index=False).encode("utf-8"),
                "orders_export.csv",
                use_container_width=True
            )

    with col_po:
        if has_permission('PURCHASE_CREATORS'):
            if st.button("💲 New PO", use_container_width=True):
                st.session_state.show_new_po = True
                st.rerun()
        else:
            st.button("🔒 New PO", disabled=True, use_container_width=True)

    with col_so:
        if has_permission('SALES_CREATORS'):
            if st.button("🛒 New SO", use_container_width=True):
                st.session_state.show_new_so = True
                st.rerun()

    # ─── DATA TABLE ──────────────────────────────────────────────────
    if not filtered_requests:
        st.warning("No matching orders found.")
    else:
        st.markdown("""
        <style>
        .order-row { border-bottom: 1px solid #eee; padding: 0.5rem 0; }
        .status-badge { padding: 0.2rem 0.5rem; border-radius: 0.5rem; font-size: 0.8rem; }
        .unread-badge { background: #e74c3c; color: white; padding: 0.2rem 0.5rem; border-radius: 1rem; }
        .overdue { color: #e74c3c; font-weight: bold; }
        </style>
        """, unsafe_allow_html=True)

        show_prices = has_permission('PRICE_ALLOWED')
        today = date.today()

        # Table headers
        if show_prices:
            headers = ["💬", "Type", "Ref#", "Items", "Qty", "Amount", "Status", "Order", "ETA", "Ship", "Owner", "Actions"]
            widths = [0.5, 0.5, 1, 2.5, 1, 1.5, 1.5, 1, 1, 1, 1, 1]
        else:
            headers = ["💬", "Type", "Ref#", "Items", "Qty", "Status", "Order", "ETA", "Ship", "Owner", "Actions"]
            widths = [0.5, 0.5, 1, 3, 1, 1.5, 1, 1, 1, 1, 1]

        cols = st.columns(widths)
        for col, header in zip(cols, headers):
            col.markdown(f"**{header}**")

        # Table rows
        for req in filtered_requests:
            idx = st.session_state.requests.index(req)
            cols = st.columns(widths)

            # Comments indicator
            comments = st.session_state.comments.get(str(idx), [])
            unread_count = sum(1 for c in comments 
                             if USER not in c.get("read_by", []) and c.get("author") != USER)
            if unread_count > 0:
                cols[0].markdown(f"<span class='unread-badge'>{unread_count}</span>", unsafe_allow_html=True)

            # Basic info
            cols[1].write(req.get("Type", ""))
            ref = req.get("Invoice" if req.get("Type") == "💲" else "Order#", "")
            cols[2].write(ref)
            cols[3].write(format_list_display(req.get("Description", [])))
            cols[4].write(format_list_display(req.get("Quantity", [])))

            # Price column (if authorized)
            col_idx = 5
            if show_prices:
                is_purchase = req.get("Type") == "💲"
                amounts = req.get("Cost" if is_purchase else "Sale Price", [])
                cols[5].write(format_money_list(amounts))
                col_idx = 6

            # Status with overdue indicator
            status = req.get("Status", "")
            status_html = format_status_badge(status)
            try:
                eta_date = datetime.strptime(req.get("ETA Date", ""), "%Y-%m-%d").date()
                if eta_date < today and status.upper() not in ("COMPLETE", "CANCELLED"):
                    status_html += " <span class='overdue'>⚠️</span>"
            except:
                pass
            cols[col_idx].markdown(status_html, unsafe_allow_html=True)

            # Remaining columns
            cols[col_idx + 1].write(req.get("Date", ""))
            cols[col_idx + 2].write(req.get("ETA Date", ""))
            cols[col_idx + 3].write(req.get("Shipping Method", ""))
            cols[col_idx + 4].write(req.get("Encargado", ""))

            # Actions
            with cols[-1]:
                col_view, col_del = st.columns(2)
                if col_view.button("👁️", key=f"view_{idx}"):
                    # Mark comments as read
                    for comment in comments:
                        if comment.get("author") != USER and USER not in comment.get("read_by", []):
                            comment["read_by"].append(USER)
                    save_data()
                    st.session_state.selected_request = idx
                    go_to("detail")
                    
                if col_del.button("🗑️", key=f"del_{idx}"):
                    delete_request(idx)
                    export_snapshot_to_disk()
                    st.rerun()

    # ─── NAVIGATION ───────────────────────────────────────────────────
    if st.button("⬅ Back to Home"):
        go_to("home")
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

UPLOADS_DIR = "uploads"

# Constants for better maintainability
STATUS_OPTIONS = [
    " ", "Imprimir", "Impresa", "Separar y Confirmar",
    "Recibido / Procesando", "Pendiente", "Separado - Pendiente",
    "Ready", "Complete", "Returned/Cancelled"
]

PAYMENT_OPTIONS = [" ", "Wire", "Cheque", "Credito", "Efectivo"]
STAFF_OPTIONS = [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"]
SHIPPING_OPTIONS = [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"]
BUBBLE_COLORS = ["#D1E8FF", "#FFD1DC", "#DFFFD6", "#FFFACD", "#E0E0E0"]

# CSS for chat bubbles (defined once)
CHAT_CSS = """
<style>
    .chat-author-in { font-size:12px; color:#555; margin:4px 0 0 5px; clear:both; }
    .chat-author-out { font-size:12px; color:#888; margin:4px 5px 0 0; clear:both; text-align:right; }
    .chat-bubble { padding:8px 12px; border-radius:16px; max-width:60%; margin:2px 0; clear:both; word-wrap:break-word; }
    .chat-timestamp { font-size:10px; color:#888; margin:2px 0 8px; clear:both; }
    .chat-attachment { background:#DDEEFF; color:#003366; padding:8px 12px; border-radius:8px; float:left; max-width:60%; margin:4px 0; clear:both; word-wrap:break-word; }
    .attachment-link { color:#003366; text-decoration:none; font-weight:600; }
    .clearfix { clear:both; }
</style>
"""

def safe_selectbox_index(options, value):
    """Safely get index for selectbox, defaulting to 0 if value not found"""
    try:
        return options.index(value) if value in options else 0
    except (ValueError, TypeError):
        return 0

def safe_date_input(date_string):
    """Safely convert date string to date object"""
    try:
        return pd.to_datetime(date_string).date() if date_string else date.today()
    except (ValueError, TypeError):
        return date.today()

def safe_numeric_conversion(values, conversion_func):
    """Safely convert list of values to numeric types"""
    try:
        return [conversion_func(x) for x in values if x]
    except (ValueError, TypeError):
        return values

def render_sidebar_fields(request, is_purchase, hide_prices):
    """Render all sidebar input fields and return updated fields"""
    updated_fields = {}
    
    st.markdown("### 📄 Order Information")
    
    # Order number
    order_number = st.text_input("Ref#", request.get("Order#", ""), key="detail_Order#")
    if order_number != request.get("Order#", ""):
        updated_fields["Order#"] = order_number
    
    # Status
    current_status = request.get("Status", " ")
    status_index = safe_selectbox_index(STATUS_OPTIONS, current_status)
    status = st.selectbox("Status", STATUS_OPTIONS, index=status_index, key="detail_Status")
    if status != current_status:
        updated_fields["Status"] = status
    
    # Invoice/Tracking
    invoice = st.text_input("Tracking#", request.get("Invoice", ""), key="detail_Invoice")
    if invoice != request.get("Invoice", ""):
        updated_fields["Invoice"] = invoice
    
    # Partner (Proveedor/Cliente)
    partner_label = "Proveedor" if is_purchase else "Cliente"
    partner = st.text_input(partner_label, request.get(partner_label, ""), key=f"detail_{partner_label}")
    if partner != request.get(partner_label, ""):
        updated_fields[partner_label] = partner
    
    # Payment method
    current_pago = request.get("Pago", " ")
    pago_index = safe_selectbox_index(PAYMENT_OPTIONS, current_pago)
    pago = st.selectbox("Método de Pago", PAYMENT_OPTIONS, index=pago_index, key="detail_Pago")
    if pago != current_pago:
        updated_fields["Pago"] = pago
    
    # Staff assignment
    current_encargado = request.get("Encargado", " ")
    encargado_index = safe_selectbox_index(STAFF_OPTIONS, current_encargado)
    encargado = st.selectbox("Encargado", STAFF_OPTIONS, index=encargado_index, key="detail_Encargado")
    if encargado != current_encargado:
        updated_fields["Encargado"] = encargado
    
    return updated_fields

def render_items_section(request, is_purchase, hide_prices):
    """Render items section and return updated fields"""
    updated_fields = {}
    
    st.markdown("### 🧾 Items")
    
    descs = request.get("Description", [])
    qtys = request.get("Quantity", [])
    price_key = "Cost" if is_purchase else "Sale Price"
    prices = request.get(price_key, [])
    
    # Ensure all arrays are same length
    max_len = max(len(descs), len(qtys), len(prices)) if any([descs, qtys, prices]) else 0
    descs.extend([""] * (max_len - len(descs)))
    qtys.extend([""] * (max_len - len(qtys)))
    prices.extend([""] * (max_len - len(prices)))
    
    new_descs, new_qtys, new_prices = [], [], []
    
    for i in range(max_len):
        c1, c2, c3 = st.columns([3, 1, 1])
        
        desc = c1.text_input(f"Description #{i+1}", descs[i], key=f"detail_desc_{i}")
        qty = c2.text_input(f"Qty #{i+1}", str(qtys[i]) if qtys[i] else "", key=f"detail_qty_{i}")
        
        if hide_prices:
            c3.markdown("**—**")
            price = prices[i]
        else:
            price = c3.text_input(f"{price_key} #{i+1}", str(prices[i]) if prices[i] else "", key=f"detail_price_{i}")
        
        new_descs.append(desc)
        new_qtys.append(qty)
        new_prices.append(price)
    
    # Check for changes
    if new_descs != descs:
        updated_fields["Description"] = new_descs
    
    if new_qtys != [str(q) if q else "" for q in qtys]:
        updated_fields["Quantity"] = safe_numeric_conversion(new_qtys, int)
    
    if new_prices != [str(p) if p else "" for p in prices]:
        updated_fields[price_key] = safe_numeric_conversion(new_prices, float)
    
    return updated_fields

def render_shipping_section(request):
    """Render shipping section and return updated fields"""
    updated_fields = {}
    
    st.markdown("### 🚚 Shipping Information")
    
    # Order Date
    current_date = request.get("Date", str(date.today()))
    order_date = st.date_input("Order Date", value=safe_date_input(current_date), key="detail_Date")
    if str(order_date) != current_date:
        updated_fields["Date"] = str(order_date)
    
    # ETA Date
    current_eta = request.get("ETA Date", str(date.today()))
    eta_date = st.date_input("ETA Date", value=safe_date_input(current_eta), key="detail_ETA")
    if str(eta_date) != current_eta:
        updated_fields["ETA Date"] = str(eta_date)
    
    # Shipping Method
    current_shipping = request.get("Shipping Method", " ")
    shipping_index = safe_selectbox_index(SHIPPING_OPTIONS, current_shipping)
    shipping_method = st.selectbox("Shipping Method", SHIPPING_OPTIONS, index=shipping_index, key="detail_Shipping")
    if shipping_method != current_shipping:
        updated_fields["Shipping Method"] = shipping_method
    
    return updated_fields

def get_author_color_map(comments):
    """Generate color mapping for comment authors"""
    authors = []
    for comment in comments:
        author = comment.get("author", "")
        if author and author not in authors:
            authors.append(author)
    
    return {author: BUBBLE_COLORS[i % len(BUBBLE_COLORS)] for i, author in enumerate(authors)}

def render_comment(comment, color_map, current_user):
    """Render a single comment bubble"""
    author = comment.get("author", "")
    text = comment.get("text", "")
    when = comment.get("when", "")
    attachment = comment.get("attachment", None)
    
    is_own_message = (author == current_user)
    align = "right" if is_own_message else "left"
    css_class = "out" if is_own_message else "in"
    
    # Author label
    st.markdown(
        f'<div class="chat-author-{css_class}" style="text-align:{align};">{author}</div>',
        unsafe_allow_html=True
    )
    
    # Attachment
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
    
    # Text bubble
    if text:
        bg_color = color_map.get(author, "#EDEDED")
        text_color = "#FFF" if is_own_message else "#000"
        st.markdown(
            f'<div class="chat-bubble" style="background:{bg_color}; color:{text_color}; float:{align};">{text}</div>'
            f'<div class="chat-timestamp" style="text-align:{align};">{when}</div>'
            f'<div class="clearfix"></div>',
            unsafe_allow_html=True
        )

def handle_file_upload(index, uploaded_file):
    """Handle file upload with proper error handling"""
    if not uploaded_file:
        return False
    
    try:
        # Ensure uploads directory exists
        os.makedirs(UPLOADS_DIR, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{index}_{timestamp}_{uploaded_file.name}"
        file_path = os.path.join(UPLOADS_DIR, filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Add comment with attachment
        add_comment(index, st.session_state.user_name, "", attachment=filename)
        st.success(f"✅ Uploaded: {uploaded_file.name}")
        return True
    except Exception as e:
        st.error(f"❌ Upload failed: {str(e)}")
        return False

# -------------------------------------------
# ---------- REQUEST DETAILS PAGE -----------
# -------------------------------------------

if st.session_state.page == "detail":
    # Validate selection first
    index = st.session_state.selected_request
    if index is None or index >= len(st.session_state.requests):
        st.error("Invalid request selected.")
        st.stop()
    
    # Auto-refresh comments (only if there are existing comments to avoid unnecessary refreshes)
    existing_comments = st.session_state.comments.get(str(index), [])
    if existing_comments:
        st_autorefresh(
            interval=1000,
            limit=None,
            key=f"detail_comments_refresh_{index}"
        )
    
    request = st.session_state.requests[index]
    is_purchase = (request.get("Type") == "💲")
    hide_prices = (st.session_state.user_name == "Bodega")
    
    # ─────────── SIDEBAR ───────────
    with st.sidebar:
        # Collect all updated fields
        sidebar_updates = render_sidebar_fields(request, is_purchase, hide_prices)
        items_updates = render_items_section(request, is_purchase, hide_prices)
        shipping_updates = render_shipping_section(request)
        
        # Combine all updates
        all_updates = {**sidebar_updates, **items_updates, **shipping_updates}
        
        st.markdown("---")
        
        # Action buttons
        if all_updates and st.button("💾 Save Changes", use_container_width=True):
            request.update(all_updates)
            st.session_state.requests[index] = request
            save_data()
            st.success("✅ Changes saved!")
            st.rerun()
        
        if st.button("🗑️ Delete Request", use_container_width=True):
            delete_request(index)
        
        if st.button("⬅ Back to All Requests", use_container_width=True):
            go_to("requests")
    
    # ─────────── MAIN AREA: COMMENTS ───────────
    st.markdown("## 💬 Comments")
    
    col_l, col_center, col_r = st.columns([1, 6, 1])
    with col_center:
        # Inject CSS once
        st.markdown(CHAT_CSS, unsafe_allow_html=True)
        
        # Get comments and color mapping
        color_map = get_author_color_map(existing_comments)
        
        # Render comments
        for comment in existing_comments:
            render_comment(comment, color_map, st.session_state.user_name)
        
        st.markdown("---")
        
        # Message input with enter-to-send
        def send_message():
            text_key = f"new_msg_{index}"
            message = st.session_state.get(text_key, "").strip()
            if message:
                add_comment(index, st.session_state.user_name, message)
                st.session_state[text_key] = ""
                st.rerun()
        
        text_key = f"new_msg_{index}"
        st.text_input(
            "Type your message here…",
            key=text_key,
            on_change=send_message,
            placeholder="Press Enter to send"
        )
        
        # File upload section
        uploaded_file = st.file_uploader(
            "Attach PDF, PNG or XLSX:",
            type=["pdf", "png", "xlsx"],
            key=f"fileuploader_{index}"
        )
        
        if uploaded_file and st.button("📎 Upload File", key=f"upload_file_{index}"):
            if handle_file_upload(index, uploaded_file):
                st.rerun()
####

elif st.session_state.page == "req_list":
    import streamlit as st
    import pandas as pd
    from datetime import datetime, date
    from streamlit_autorefresh import st_autorefresh

    # ─── CONSTANTS ─────────────────────────────────────────────────
    VENDEDORES = [" ", "John", "Andres", "Luz", "Tito", "Marcela", "Carolina", "Sabrina"]
    COMPRADORES = [" ", "David", "Andres", "Thea", "Tito", "Luz"]
    STATUS_OPTIONS = ["OPEN", "PURCHASE TEAM REVIEW", "SALES TEAM REVIEW", "CLOSED W", "CLOSED L"]
    STATUS_ORDER = {
        "OPEN": 0,
        "PURCHASE TEAM REVIEW": 1,
        "SALES TEAM REVIEW": 2,
        "CLOSED W": 3,
        "CLOSED L": 4
    }
    
    # CSS styles - defined once
    DIALOG_CSS = """
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
    """
    
    TABLE_CSS = """
    <style>
      .header-row            { font-weight:bold; font-size:18px; padding:0.5rem 0; }
      .type-icon             { font-size:20px; }
      .status-open           { background-color:#2ecc71; color:#fff; padding:4px 8px; border-radius:12px; display:inline-block; }
      .status-purchase-review{ background-color:#007BFF; color:#fff; padding:4px 8px; border-radius:12px; display:inline-block; }
      .status-sales-review   { background-color:#FD7E14; color:#fff; padding:4px 8px; border-radius:12px; display:inline-block; }
      .status-closed         { background-color:#e74c3c; color:#fff; padding:4px 8px; border-radius:12px; display:inline-block; }
    </style>
    """

    # ─── HELPER FUNCTIONS ─────────────────────────────────────────
    @st.cache_data(ttl=1)  # Cache for 1 second to reduce redundant parsing
    def parse_fecha(fecha_str):
        """Parse date string safely with caching."""
        try:
            return datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return date.max

    def get_status_html(status):
        """Get HTML for status badge."""
        status_classes = {
            "OPEN": "status-open",
            "PURCHASE TEAM REVIEW": "status-purchase-review", 
            "SALES TEAM REVIEW": "status-sales-review",
            "CLOSED W": "status-closed",
            "CLOSED L": "status-closed"
        }
        css_class = status_classes.get(status, "")
        return f"<span class='{css_class}'>{status}</span>" if css_class else status

    def initialize_session_state():
        """Initialize session state variables."""
        if "show_new_req" not in st.session_state:
            st.session_state.show_new_req = False
        if "req_item_count" not in st.session_state:
            st.session_state.req_item_count = 1

    def filter_and_sort_requests(requests, search_term, status_filter):
        """Filter and sort requests efficiently."""
        # Pre-filter requirements (type check first as it's fastest)
        filtered_reqs = []
        search_lower = search_term.lower() if search_term else ""
        
        for req in requests:
            if req.get("Type") != "📑":
                continue
            if status_filter != "All" and req.get("Status", "OPEN") != status_filter:
                continue
            if search_term and search_lower not in str(req).lower():
                continue
            filtered_reqs.append(req)
        
        # Sort by status order and date
        return sorted(
            filtered_reqs,
            key=lambda r: (STATUS_ORDER.get(r.get("Status", "OPEN"), 0), parse_fecha(r.get("Fecha", "")))
        )

    def create_flat_data(requests):
        """Create flattened data structure for display."""
        flat_data = []
        for req in requests:
            items = req.get("Items", [])
            if not items:  # Handle empty items list
                continue
                
            for item in items:
                flat_data.append({
                    "Type": req["Type"],
                    "Description": item.get("Description", ""),
                    "Target Price": item.get("Target Price", ""),
                    "Qty": item.get("QTY", ""),
                    "Vendedor": req.get("Vendedor Encargado", ""),
                    "Comprador": req.get("Comprador Encargado", ""),
                    "Status": req.get("Status", "OPEN"),
                    "Date": req.get("Fecha", ""),
                    "_req_obj": req
                })
        return flat_data

    def count_unread_comments(comments_list, user):
        """Count unread comments for current user."""
        return sum(
            1 for comment in comments_list
            if comment.get("author", "") != user and user not in comment.get("read_by", [])
        )

    # ─── DIALOG COMPONENT ─────────────────────────────────────────
    @st.dialog(" 📄 Nuevo Requerimiento", width="large")
    def new_req_dialog():
        st.markdown(DIALOG_CSS, unsafe_allow_html=True)

        # Item management
        col_add, col_rem = st.columns([1, 1])
        with col_add:
            if st.button("➕ Add Item", key="req_add_item"):
                st.session_state.req_item_count += 1
                st.rerun()
        with col_rem:
            if st.button("➖ Remove Item", key="req_remove_item") and st.session_state.req_item_count > 1:
                st.session_state.req_item_count -= 1
                st.rerun()

        # Dynamic items input
        items = []
        for i in range(st.session_state.req_item_count):
            col1, col2, col3 = st.columns([3, 2, 1])
            desc = col1.text_input("Description", key=f"req_desc_{i}")
            target = col2.text_input("Target Price", key=f"req_target_{i}")
            qty_input = col3.text_input("QTY", key=f"req_qty_{i}")
            
            # Safe quantity parsing
            try:
                qty = int(qty_input) if qty_input.strip() else ""
            except ValueError:
                qty = qty_input
                
            items.append({
                "Description": desc,
                "Target Price": target,
                "QTY": qty
            })

        # Form fields
        col_v, col_c, col_dt, col_st = st.columns([2, 2, 2, 2])
        sel_v = col_v.selectbox("Vendedor", VENDEDORES, key="req_vendedor")
        sel_c = col_c.selectbox("Comprador", COMPRADORES, key="req_comprador")
        dt = col_dt.date_input("Date", value=date.today(), key="req_fecha")
        stt = col_st.selectbox("Status", STATUS_OPTIONS, key="req_status")

        # Action buttons
        col_send, col_cancel = st.columns([2, 1])
        with col_send:
            if st.button("✅ Enviar Requerimiento", key="req_submit", use_container_width=True):
                # Validate and clean items
                cleaned_items = [item for item in items if item["Description"].strip()]
                
                if not cleaned_items or sel_c == " ":
                    st.error("❗ Completa al menos una descripción y el campo Comprador.")
                else:
                    # Add request
                    new_request = {
                        "Type": "📑",
                        "Items": cleaned_items,
                        "Vendedor Encargado": sel_v,
                        "Comprador Encargado": sel_c,
                        "Fecha": str(dt),
                        "Status": stt
                    }
                    add_request(new_request)
                    
                    # Initialize comments for new request
                    new_idx = len(st.session_state.requests) - 1
                    st.session_state.comments[str(new_idx)] = []
                    save_data()
                    
                    # Reset form and close dialog
                    st.success("✅ Requerimiento enviado.")
                    st.session_state.req_item_count = 1
                    st.session_state.show_new_req = False
                    st.rerun()

        with col_cancel:
            if st.button("❌ Cancel", key="req_cancel", use_container_width=True):
                st.session_state.show_new_req = False
                st.rerun()

    # ─── MAIN APPLICATION ─────────────────────────────────────────
    initialize_session_state()
    
    st.markdown("# 📝 Requerimientos Clientes")
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # Auto-refresh with longer interval for better performance
    st_autorefresh(interval=2000, limit=None, key="req_list_refresh")
    
    load_data()

    # Search and filter controls
    col1, col2 = st.columns([3, 1])
    search_term = col1.text_input("Search", placeholder="Search requirements...")
    status_filter = col2.selectbox(
        "Status",
        ["All"] + STATUS_OPTIONS,
        key="req_list_status"
    )

    # Process data
    filtered_requests = filter_and_sort_requests(st.session_state.requests, search_term, status_filter)
    flat_data = create_flat_data(filtered_requests)

    # Export data preparation
    df_export = pd.DataFrame([
        {k: v for k, v in row.items() if not k.startswith("_")}
        for row in flat_data
    ])

    # Action buttons
    col_export, col_new, col_all = st.columns([3, 1, 1])
    with col_export:
        if not df_export.empty:
            st.download_button(
                "📥 Export Filtered Requests to CSV",
                df_export.to_csv(index=False).encode("utf-8"),
                "req_requests.csv",
                "text/csv",
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

    # Show dialog if needed
    if st.session_state.show_new_req:
        new_req_dialog()

    # Display results
    if flat_data:
        st.markdown(TABLE_CSS, unsafe_allow_html=True)

        # Table headers
        header_cols = st.columns([0.5, 0.5, 2, 1, 1, 1, 1, 1.5, 1, 1])
        headers = ["", "Type", "Description", "Target Price", "Qty", "Vendedor", "Comprador", "Status", "Date", ""]
        for col, header in zip(header_cols, headers):
            col.markdown(f"<div class='header-row'>{header}</div>", unsafe_allow_html=True)

        # Table rows
        user = st.session_state.user_name
        for i, row in enumerate(flat_data):
            cols = st.columns([0.5, 0.5, 2, 1, 1, 1, 1, 1.5, 1, 1])
            req_idx = st.session_state.requests.index(row["_req_obj"])

            # Unread comments count
            comments_list = st.session_state.comments.get(str(req_idx), [])
            unread_count = count_unread_comments(comments_list, user)
            
            cols[0].markdown(
                f"<span class='status-open'>💬{unread_count}</span>" if unread_count > 0 else "",
                unsafe_allow_html=True
            )

            # Row data
            cols[1].markdown(f"<span class='type-icon'>{row['Type']}</span>", unsafe_allow_html=True)
            cols[2].write(row['Description'])
            cols[3].write(f"${row['Target Price']}" if row['Target Price'] else "")
            cols[4].write(str(row['Qty']) if row['Qty'] else "")
            cols[5].write(row['Vendedor'])
            cols[6].write(row['Comprador'])
            cols[7].markdown(get_status_html(row['Status']), unsafe_allow_html=True)
            cols[8].write(row['Date'])

            # Action buttons
            with cols[9]:
                btn_col1, btn_col2 = st.columns([1, 1])
                
                if btn_col1.button("🔍", key=f"view_{i}", use_container_width=True):
                    # Mark comments as read
                    for comment in comments_list:
                        if comment.get("author", "") != user:
                            comment.setdefault("read_by", [])
                            if user not in comment["read_by"]:
                                comment["read_by"].append(user)
                    save_data()
                    
                    st.session_state.selected_request = req_idx
                    st.session_state.page = "req_detail"
                    st.rerun()

                if btn_col2.button("❌", key=f"del_{i}", use_container_width=True):
                    delete_request(req_idx)
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

    # ─── Auto‐refresh every 5 seconds instead of 1 for better performance ─────
    _ = st_autorefresh(interval=5000, limit=None, key="requests_refresh")
    load_data()

    idx = st.session_state.selected_request
    request = st.session_state.requests[idx]
    updated = {}

    UPLOADS_DIR = "uploads"  # make sure this exists

    # ─── Cached CSS to avoid repeated rendering ────────────────────
    @st.cache_data
    def get_sidebar_css():
        return """
        <style>
          [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { font-size:24px!important; }
          [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { font-size:16px!important; }
          button { font-size:16px!important; }
        </style>
        """
    
    st.markdown(get_sidebar_css(), unsafe_allow_html=True)
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

    # ─── OPTIMIZED ITEMS MANAGEMENT ────────────────────────────────
    items = request.get("Items", [])
    
    # Initialize items count more efficiently
    if "items_count" not in st.session_state:
        st.session_state["items_count"] = max(1, len(items))
    
    st.sidebar.markdown("### 📋 Items")
    ca, cr = st.sidebar.columns([1, 1])
    
    # Add item with better state management
    if ca.button("➕ Add Item", key="req_detail_add"):
        st.session_state["items_count"] += 1
        st.rerun()
    
    # Remove item with proper bounds checking and state cleanup
    if cr.button("➖ Remove Item", key="req_detail_remove"):
        if st.session_state["items_count"] > 1:
            # Clear the removed item's session state keys to prevent memory leaks
            removed_index = st.session_state["items_count"] - 1
            keys_to_remove = [
                f"req_detail_desc_{removed_index}",
                f"req_detail_target_{removed_index}",
                f"req_detail_qty_{removed_index}"
            ]
            for key in keys_to_remove:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.session_state["items_count"] -= 1
            st.rerun()

    new_items = []
    for i in range(st.session_state["items_count"]):
        c1, c2, c3 = st.sidebar.columns([3, 2, 1])
        
        # Use get() with fallback to avoid index errors
        default_item = items[i] if i < len(items) else {"Description": "", "Target Price": "", "QTY": ""}
        
        desc = c1.text_input("Description", 
                            value=default_item.get("Description", ""), 
                            key=f"req_detail_desc_{i}")
        targ = c2.text_input("Target Price", 
                            value=default_item.get("Target Price", ""), 
                            key=f"req_detail_target_{i}")
        qty_input = c3.text_input("QTY", 
                                 value=str(default_item.get("QTY", "")), 
                                 key=f"req_detail_qty_{i}")
        
        # Improved quantity parsing
        qty = ""
        if qty_input.strip():
            try:
                # Try to parse as integer first, then float
                if qty_input.strip().isdigit():
                    qty = int(qty_input.strip())
                else:
                    qty = float(qty_input.strip())
                    # Convert to int if it's a whole number
                    if qty.is_integer():
                        qty = int(qty)
            except ValueError:
                qty = qty_input.strip()  # Keep as string if parsing fails
        
        new_items.append({
            "Description": desc.strip(),
            "Target Price": targ.strip(),
            "QTY": qty
        })
    
    # Only update if items actually changed
    if new_items != items:
        updated["Items"] = new_items

    # ─── VENDEDOR & COMPRADOR with caching ─────────────────────────
    @st.cache_data
    def get_user_lists():
        return {
            "vendedores": [" ", "John", "Andres", "Luz", "Tito", "Marcela", "Carolina", "Sabrina"],
            "compradores": [" ", "David", "Andres", "Thea", "Tito", "Luz"]
        }
    
    user_lists = get_user_lists()
    vendedores = user_lists["vendedores"]
    compradores = user_lists["compradores"]
    
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

    # ─── DATE with better parsing ───────────────────────────────────
    dt0 = request.get("Fecha", str(date.today()))
    try:
        parsed_date = pd.to_datetime(dt0).date()
    except:
        parsed_date = date.today()
    
    dt = st.sidebar.date_input("Date", value=parsed_date, key="req_detail_date")
    if str(dt) != dt0:
        updated["Fecha"] = str(dt)

    # ─── SAVE / DELETE / BACK with improved feedback ──────────────
    cs, cd, cb = st.sidebar.columns(3, gap="small")
    with cs:
        if updated and st.button("💾 Save", key="req_detail_save", use_container_width=True):
            try:
                if "Items" in updated:
                    st.session_state["items_count"] = len(updated["Items"])
                request.update(updated)
                st.session_state.requests[idx] = request
                save_data()
                st.sidebar.success("✅ Saved")
                # Clear updated dict to prevent repeated saves
                updated.clear()
            except Exception as e:
                st.sidebar.error(f"❌ Error saving: {str(e)}")
    
    with cd:
        if st.button("🗑️ Delete", key="req_detail_delete", use_container_width=True):
            try:
                delete_request(idx)
                st.sidebar.success("✅ Deleted")
            except Exception as e:
                st.sidebar.error(f"❌ Error deleting: {str(e)}")
    
    with cb:
        if st.button("⬅ Back", key="req_detail_back", use_container_width=True):
            # Clean up session state when going back
            keys_to_clean = [key for key in st.session_state.keys() 
                           if key.startswith(('req_detail_', 'new_msg_', 'fileuploader_'))]
            for key in keys_to_clean:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.session_state.page = "req_list"
            st.rerun()
    
    st.sidebar.markdown("---")

    # ─── OPTIMIZED COMMENTS SECTION ────────────────────────────────
    st.markdown("## 💬 Comments")
    col_l, col_center, col_r = st.columns([1, 6, 1])
    with col_center:
        # Cache CSS for comments to avoid repeated rendering
        @st.cache_data
        def get_comments_css():
            return """
            <style>
              .chat-author-in    { font-size:12px; color:#555; margin:4px 0 0 5px; clear:both; }
              .chat-author-out   { font-size:12px; color:#333; margin:4px 5px 0 0; clear:both; text-align:right; }
              .chat-bubble       { padding:8px 12px; border-radius:16px; max-width:60%; margin:2px 0; word-wrap:break-word; clear:both; }
              .chat-timestamp    { font-size:10px; color:#888; margin:2px 0 8px; }
              .chat-attachment   { background:#DDEEFF; color:#003366; padding:8px 12px; border-radius:8px; float:left; max-width:60%; margin:4px 0; clear:both; word-wrap:break-word; }
              .attachment-link   { color:#003366; text-decoration:none; font-weight:600; }
            </style>
            """
        
        st.markdown(get_comments_css(), unsafe_allow_html=True)
        
        existing_comments = st.session_state.comments.get(str(idx), [])
        
        # Optimize color mapping
        if existing_comments:
            authors = list(set(c["author"] for c in existing_comments))  # Remove duplicates efficiently
            base_colors = ["#D1E8FF", "#FFD1DC", "#DFFFD6", "#FFFACD", "#E0E0E0"]
            color_map = {a: base_colors[i % len(base_colors)] for i, a in enumerate(authors)}
            
            for comment in existing_comments:
                author = comment["author"]
                text = comment.get("text", "")
                when = comment.get("when", "")
                attachment = comment.get("attachment", None)
                
                if attachment:
                    file_path = os.path.join(UPLOADS_DIR, attachment)
                
                bg = color_map.get(author, "#EDEDED")
                is_user = author == st.session_state.user_name
                align = "right" if is_user else "left"
                float_dir = align
                cls = 'out' if is_user else 'in'
                
                # Author label
                st.markdown(f'<div class="chat-author-{cls}" style="text-align:{align};">{author}</div>', 
                           unsafe_allow_html=True)
                
                # Attachment
                if attachment and os.path.exists(file_path):
                    link_html = f'<a href="/{file_path}" class="attachment-link" download>{attachment}</a>'
                    st.markdown(
                        f'<div class="chat-attachment" style="float:{float_dir};">📎 {link_html}</div>'
                        f'<div class="chat-timestamp" style="text-align:{align};">{when}</div>'
                        f'<div style="clear:both;"></div>',
                        unsafe_allow_html=True
                    )
                
                # Text message
                if text:
                    st.markdown(
                        f'<div class="chat-bubble" style="background:{bg}; float:{float_dir};">{text}</div>'
                        f'<div class="chat-timestamp" style="text-align:{align};">{when}</div>'
                        f'<div style="clear:both;"></div>',
                        unsafe_allow_html=True
                    )
        
        st.markdown("---")
        
        # Comment input
        text_key = f"new_msg_{idx}"
        st.text_input("Type your message here…", 
                     key=text_key, 
                     on_change=_submit_comment, 
                     args=(idx, text_key), 
                     placeholder="Press enter to send")
        
        # File upload with better error handling
        uploaded_file = st.file_uploader("Attach PDF, PNG or XLSX:", 
                                        type=["pdf", "png", "xlsx"], 
                                        key=f"fileuploader_{idx}")
        
        _, cu = st.columns([1, 1])
        with cu:
            if st.button("Upload File", key=f"upload_file_{idx}") and uploaded_file:
                try:
                    # Ensure uploads directory exists
                    os.makedirs(UPLOADS_DIR, exist_ok=True)
                    
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    fn = f"{idx}_{ts}_{uploaded_file.name}"
                    file_path = os.path.join(UPLOADS_DIR, fn)
                    
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    add_comment(idx, st.session_state.user_name, "", attachment=fn)
                    st.success(f"✅ Uploaded: {uploaded_file.name}")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Upload failed: {str(e)}")

    # ─── Initialize dialog states ──────────────────────────────────
    if "show_new_po" not in st.session_state: 
        st.session_state.show_new_po = False
    if "show_new_so" not in st.session_state: 
        st.session_state.show_new_so = False

    # ─── PURCHASE ALLOWED USERS ────────────────────────────────────
    PURCHASE_ALLOWED = {"Tito", "Andres", "Luz", "David"}

    # ─── OPTIMIZED PURCHASE ORDER OVERLAY ──────────────────────────
    @st.dialog("💲 New Purchase Order", width="large")
    def purchase_order_dialog():
        # Initialize with minimum rows
        if "purchase_item_rows" not in st.session_state:
            st.session_state.purchase_item_rows = 1
        st.session_state.purchase_item_rows = max(1, st.session_state.purchase_item_rows)

        # Cache dialog CSS
        @st.cache_data
        def get_dialog_css():
            return """
            <style>
            .stTextInput > div > div > input,
            .stSelectbox > div, .stDateInput > div {
                background-color: #f7f9fc !important;
                border-radius: 12px !important;
                padding: 0.4rem !important;
                border: 1px solid #dfe6ec !important;
            }
            </style>
            """
        
        st.markdown(get_dialog_css(), unsafe_allow_html=True)

        # Header fields
        c1, c2 = st.columns(2)
        with c1:
            po_number = st.text_input("Purchase Order#", value="", placeholder="e.g. 12345")
            status_po = st.selectbox("Status *", [" ", "COMPLETE", "READY", "CANCELLED", "IN TRANSIT"])
            encargado_po = st.selectbox("Encargado *", [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"])
        with c2:
            order_number = st.text_input("Tracking# (optional)", value="", placeholder="e.g. TRK-45678")
            proveedor = st.text_input("Proveedor", value="", placeholder="e.g. Amazon")
            pago = st.selectbox("Método de Pago", [" ", "Wire", "Cheque", "Credito", "Efectivo"])

        # Items with improved remove functionality
        st.markdown("### 🧾 Items to Order")
        descs, qtys, costs = [], [], []
        for i in range(st.session_state.purchase_item_rows):
            c_desc, c_qty, c_cost = st.columns([3, 2, 1])
            descs.append(c_desc.text_input(f"Description #{i+1}", key=f"po_desc_{i}"))
            qtys.append(c_qty.text_input(f"Quantity #{i+1}", key=f"po_qty_{i}"))
            costs.append(c_cost.text_input(f"Cost #{i+1}", placeholder="e.g. 1500", key=f"po_cost_{i}"))

        # Add/Remove rows with state cleanup
        ca2, cb2 = st.columns([1, 1])
        with ca2:
            if st.button("➕ Add another item", key="add_purchase"):
                st.session_state.purchase_item_rows += 1
                st.rerun()
        with cb2:
            if st.session_state.purchase_item_rows > 1 and st.button("❌ Remove last item", key="remove_purchase"):
                # Clean up the removed item's keys
                removed_index = st.session_state.purchase_item_rows - 1
                keys_to_remove = [f"po_desc_{removed_index}", f"po_qty_{removed_index}", f"po_cost_{removed_index}"]
                for key in keys_to_remove:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.session_state.purchase_item_rows -= 1
                st.rerun()

        # Shipping information
        st.markdown("### 🚚 Shipping Information")
        c3, c4 = st.columns(2)
        with c3:
            order_date = st.date_input("Order Date", value=date.today())
        with c4:
            eta_date = st.date_input("ETA Date")
        shipping_method = st.selectbox("Shipping Method", [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"])

        # Submit/Cancel
        col_submit, col_cancel = st.columns([2, 1])
        with col_submit:
            if st.button("✅ Submit Purchase Request", use_container_width=True):
                # Clean and validate inputs
                clean_descs = [d.strip() for d in descs if d.strip()]
                clean_qtys = []
                for q in qtys:
                    q = q.strip()
                    if q:
                        try:
                            clean_qtys.append(int(float(q)))
                        except:
                            clean_qtys.append(q)
                    else:
                        clean_qtys.append("")
                
                clean_costs = []
                for c in costs:
                    c = c.strip()
                    if c:
                        try:
                            clean_costs.append(float(c))
                        except:
                            clean_costs.append(c)
                    else:
                        clean_costs.append("")

                # Validate required fields
                if not clean_descs or status_po == " " or encargado_po == " ":
                    st.error("❗ Complete required fields: Description, Status, and Encargado.")
                else:
                    try:
                        add_request({
                            "Type": "💲",
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
                        
                        # Reset state
                        st.session_state.purchase_item_rows = 1
                        st.session_state.show_new_po = False
                        
                        # Clean up dialog keys
                        dialog_keys = [key for key in st.session_state.keys() if key.startswith('po_')]
                        for key in dialog_keys:
                            if key in st.session_state:
                                del st.session_state[key]
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to submit: {str(e)}")
                        
        with col_cancel:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_new_po = False
                # Clean up dialog keys
                dialog_keys = [key for key in st.session_state.keys() if key.startswith('po_')]
                for key in dialog_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

    # ─── OPTIMIZED SALES ORDER OVERLAY ─────────────────────────────
    @st.dialog("🛒 New Sales Order", width="large")
    def sales_order_dialog():
        # Initialize with minimum rows
        if "invoice_item_rows" not in st.session_state:
            st.session_state.invoice_item_rows = 1
        st.session_state.invoice_item_rows = max(1, st.session_state.invoice_item_rows)

        st.markdown(get_dialog_css(), unsafe_allow_html=True)

        # Header fields
        d1, d2 = st.columns(2)
        with d1:
            order_number_so = st.text_input("Ref# (optional)", value="", placeholder="e.g. SO-2025-001")
            status_so = st.selectbox("Status *", [" ", "COMPLETE", "READY", "CANCELLED", "IN TRANSIT"])
            encargado_so = st.selectbox("Encargado *", [" ", "Andres", "Tito", "Luz", "David", "Marcela", "John", "Carolina", "Thea"])
        with d2:
            tracking_so = st.text_input("Tracking# (optional)", value="", placeholder="e.g. TRK45678")
            cliente = st.text_input("Cliente", value="", placeholder="e.g. TechCorp LLC")
            pago_so = st.selectbox("Método de Pago", [" ", "Wire", "Cheque", "Credito", "Efectivo"])

        # Items with improved remove functionality
        st.markdown("### 🧾 Items to Invoice")
        ds, qs, prices = [], [], []
        for i in range(st.session_state.invoice_item_rows):
            sa, sb, sc = st.columns([3, 2, 1])
            ds.append(sa.text_input(f"Description #{i+1}", key=f"so_desc_{i}"))
            qs.append(sb.text_input(f"Quantity #{i+1}", key=f"so_qty_{i}"))
            prices.append(sc.text_input(f"Sale Price #{i+1}", placeholder="e.g. 2000", key=f"so_price_{i}"))

        # Add/Remove rows with state cleanup
        sa2, sb2 = st.columns([1, 1])
        with sa2:
            if st.button("➕ Add another item", key="add_invoice"):
                st.session_state.invoice_item_rows += 1
                st.rerun()
        with sb2:
            if st.session_state.invoice_item_rows > 1 and st.button("❌ Remove last item", key="remove_invoice"):
                # Clean up the removed item's keys
                removed_index = st.session_state.invoice_item_rows - 1
                keys_to_remove = [f"so_desc_{removed_index}", f"so_qty_{removed_index}", f"so_price_{removed_index}"]
                for key in keys_to_remove:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.session_state.invoice_item_rows -= 1
                st.rerun()

        # Shipping
        st.markdown("### 🚚 Shipping Information")
        s1, s2, s3 = st.columns(3)
        with s1:
            so_date = st.date_input("Order Date", value=date.today())
        with s2:
            so_eta = st.date_input("ETA Date")
        with s3:
            so_ship = st.selectbox("Shipping Method", [" ", "Nivel 1 PU", "Nivel 3 PU", "Nivel 3 DEL"])

        # Submit/Cancel
        cs1, cs2 = st.columns([2, 1])
        with cs1:
            if st.button("✅ Submit Sales Order", use_container_width=True):
                # Clean and validate inputs
                clean_ds = [d.strip() for d in ds if d.strip()]
                clean_qs = []
                for q in qs:
                    q = q.strip()
                    if q:
                        try:
                            clean_qs.append(int(float(q)))
                        except:
                            clean_qs.append(q)
                    else:
                        clean_qs.append("")
                
                clean_prices = []
                for p in prices:
                    p = p.strip()
                    if p:
                        try:
                            clean_prices.append(float(p))
                        except:
                            clean_prices.append(p)
                    else:
                        clean_prices.append("")

                # Validate required fields
                if not clean_ds or status_so == " " or encargado_so == " ":
                    st.error("❗ Complete required fields: Description, Status, and Encargado.")
                else:
                    try:
                        add_request({
                            "Type": "🛒",
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
                        
                        # Reset state
                        st.session_state.invoice_item_rows = 1
                        st.session_state.show_new_so = False
                        
                        # Clean up dialog keys
                        dialog_keys = [key for key in st.session_state.keys() if key.startswith('so_')]
                        for key in dialog_keys:
                            if key in st.session_state:
                                del st.session_state[key]
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to submit: {str(e)}")
                        
        with cs2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_new_so = False
                # Clean up dialog keys
                dialog_keys = [key for key in st.session_state.keys() if key.startswith('so_')]
                for key in dialog_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

    # ─── QUICK ACTIONS ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📝 Quick Actions")
    col_all, col_po, col_so = st.columns(3)
    user = st.session_state.user_name

    # All Requests
    with col_all:
        if st.button("📋 All Requests", use_container_width=True):
            st.session_state.page = "requests"
            st.rerun()

    # New Purchase Order (with permissions)
    with col_po:
        if user in PURCHASE_ALLOWED:
            if st.button("💲 New Purchase Order", use_container_width=True):
                st.session_state.show_new_po = True
                st.rerun()
        else:
            st.button("🔒 New Purchase Order", disabled=True, use_container_width=True)
            st.caption("No tienes permiso para crear órdenes de compra.")

    # New Sales Order
    with col_so:
        if st.button("🛒 New Sales Order", use_container_width=True):
            st.session_state.show_new_so = True
            st.rerun()

    # Show dialogs
    if st.session_state.show_new_po:
        purchase_order_dialog()
    if st.session_state.show_new_so:
        sales_order_dialog()
