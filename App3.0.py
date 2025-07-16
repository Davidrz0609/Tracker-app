import streamlit as st
import pandas as pd
from datetime import datetime

# ---- Sample data stores ----
if 'requirements' not in st.session_state:
    st.session_state.requirements = []
if 'purchase_orders' not in st.session_state:
    st.session_state.purchase_orders = []
if 'sales_orders' not in st.session_state:
    st.session_state.sales_orders = []

# ---- Sidebar Navigation ----
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", [
    "📋 Requerimientos",
    "📦 Purchase Orders",
    "🧾 Sales Orders",
    "📊 Dashboard"
])

# ---- Helper functions ----
def status_color(status):
    colors = {
        'Pending': '🟡',
        'Confirmed': '🟢',
        'Cancelled': '🔴'
    }
    return colors.get(status, '') + ' ' + status

# ---- Requerimientos Page ----
if page == "📋 Requerimientos":
    st.title("Requerimientos")

    # Chat-style form
    with st.expander("📝 Nuevo Requerimiento"):
        description = st.text_area("Descripción del requerimiento")
        vendor_options = st.multiselect("Vendors interesados", ["Vendor A", "Vendor B", "Vendor C"])
        if st.button("Crear Requerimiento"):
            st.session_state.requirements.append({
                "id": len(st.session_state.requirements)+1,
                "description": description,
                "vendors": vendor_options,
                "status": "Pending",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            st.success("Requerimiento creado")

    # Display all requests
    st.subheader("Todos los Requerimientos")
    if st.session_state.requirements:
        df = pd.DataFrame(st.session_state.requirements)
        df['status'] = df['status'].apply(status_color)
        st.dataframe(df)
    else:
        st.info("No hay requerimientos todavía.")

# ---- Purchase Orders Page ----
elif page == "📦 Purchase Orders":
    st.title("📦 Purchase Orders")

    with st.expander("➕ Crear Purchase Order"):
        po_detail = st.text_input("Detalle del PO")
        if st.button("Guardar PO"):
            st.session_state.purchase_orders.append({
                "id": len(st.session_state.purchase_orders)+1,
                "detail": po_detail,
                "created": datetime.now().strftime("%Y-%m-%d")
            })
            st.success("PO creado")

    st.subheader("Lista de Purchase Orders")
    if st.session_state.purchase_orders:
        st.dataframe(pd.DataFrame(st.session_state.purchase_orders))
    else:
        st.info("No hay POs registrados.")

# ---- Sales Orders Page ----
elif page == "🧾 Sales Orders":
    st.title("🧾 Sales Orders")

    with st.expander("➕ Crear Sales Order"):
        so_detail = st.text_input("Detalle del SO")
        if st.button("Guardar SO"):
            st.session_state.sales_orders.append({
                "id": len(st.session_state.sales_orders)+1,
                "detail": so_detail,
                "created": datetime.now().strftime("%Y-%m-%d")
            })
            st.success("SO creado")

    st.subheader("Lista de Sales Orders")
    if st.session_state.sales_orders:
        st.dataframe(pd.DataFrame(st.session_state.sales_orders))
    else:
        st.info("No hay SO registrados.")

# ---- Dashboard Page ----
elif page == "📊 Dashboard":
    st.title("📊 Resumen General")

    st.metric("Requerimientos Totales", len(st.session_state.requirements))
    st.metric("Purchase Orders", len(st.session_state.purchase_orders))
    st.metric("Sales Orders", len(st.session_state.sales_orders))

    pending = sum(1 for r in st.session_state.requirements if r['status'] == "Pending")
    confirmed = sum(1 for r in st.session_state.requirements if r['status'] == "Confirmed")
    cancelled = sum(1 for r in st.session_state.requirements if r['status'] == "Cancelled")

    st.write("### Estado de Requerimientos")
    st.write(f"🟡 Pendientes: {pending}")
    st.write(f"🟢 Confirmados: {confirmed}")
    st.write(f"🔴 Cancelados: {cancelled}")
