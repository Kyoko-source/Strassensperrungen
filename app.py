import streamlit as st
import folium
from folium.raster_layers import ImageOverlay
from streamlit_folium import st_folium
from PIL import Image
import pandas as pd
from datetime import datetime
import re

# -----------------------------
# Page config + CSS
# -----------------------------
st.set_page_config(layout="wide", page_title="DRK Reken – Einsatzkarte")

st.markdown(
"""
<style>
/* GLOBAL */
html, body, [class*="css"] {
    color: #111111;
    font-size: 16px;
}

/* INPUT FIX */
input, textarea, select {
    color: #0f172a !important;
    background-color: #ffffff !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b1220 0%, #0f1a2e 100%);
}
section[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* Buttons */
.stButton button {
    border-radius: 12px;
    border: 1px solid #cbd5e1;
    padding: 0.6rem 0.9rem;
    font-weight: 600;
    background-color: #f8fafc;
    color: #0f172a;
}

/* Cards */
.card {
    border-radius: 14px;
    padding: 14px 16px;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.card-title { font-size: 0.9rem; color: #475569; }
.card-value { font-size: 1.4rem; font-weight: 700; color: #0f172a; }
.muted { color: #475569; }

/* Pills */
.pill {
    display:inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.85rem;
    color: white;
}
.pill-red { background:#dc2626; }
.pill-orange { background:#f97316; }
.pill-blue { background:#2563eb; }
.pill-black { background:#111827; }

/* Warning */
.warn {
    border-left: 4px solid #dc2626;
    padding: 10px 12px;
    border-radius: 10px;
    background: #fee2e2;
    color: #7f1d1d;
}

/* Tables */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #cbd5e1;
}
thead tr th {
    background-color: #e2e8f0 !important;
    color: #0f172a !important;
}
tbody tr td {
    color: #0f172a !important;
}
</style>
""",
unsafe_allow_html=True
)

# -----------------------------
# Title
# -----------------------------
st.title("🚑 DRK Reken – Digitale Einsatzkarte")

# -----------------------------
# Settings
# -----------------------------
IMAGE_PATH = "karte.jpg"

PIN_TYPES = {
    "RTW (Rot)": "red",
    "KTW (Orange)": "orange",
    "EVT Fußtrupp (Blau)": "blue",
    "Sonstiges (Schwarz)": "black",
}

# -----------------------------
# State
# -----------------------------
if "pins" not in st.session_state:
    st.session_state.pins = []
if "next_pin_id" not in st.session_state:
    st.session_state.next_pin_id = 1
if "selected_pin_id" not in st.session_state:
    st.session_state.selected_pin_id = None

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.header("Neuen Pin setzen")
pin_type = st.sidebar.radio("Pin-Typ", list(PIN_TYPES.keys()))
pin_name = st.sidebar.text_input("Name", placeholder="z.B. RTW Heiden")

if st.sidebar.button("Alle Pins löschen"):
    st.session_state.pins = []
    st.session_state.next_pin_id = 1
    st.session_state.selected_pin_id = None
    st.rerun()

# -----------------------------
# Image / Bounds
# -----------------------------
img = Image.open(IMAGE_PATH)
w, h = img.size
H = 100 * (h / w)
bounds = [[0,0],[H,100]]

# -----------------------------
# Build Map
# -----------------------------
def build_map():
    m = folium.Map(
        location=[H/2,50],
        zoom_start=1,
        crs="Simple",
        tiles=None,
        zoom_control=False
    )

    ImageOverlay(IMAGE_PATH, bounds=bounds).add_to(m)
    m.fit_bounds(bounds)

    m.options["dragging"]=False
    m.options["scrollWheelZoom"]=False
    m.options["doubleClickZoom"]=False

    for p in st.session_state.pins:
        html = f"""
        <b>ID:</b> {p['id']}<br>
        <b>Typ:</b> {p['type']}<br>
        <b>Name:</b> {p['name']}<br>
        <b>Zeit:</b> {p['time']}
        """
        folium.Marker(
            [p["y"],p["x"]],
            popup=html,
            tooltip=f"{p['id']}: {p['name']}",
            icon=folium.Icon(color=p["color"])
        ).add_to(m)

    return m

# -----------------------------
# Map Display
# -----------------------------
m = build_map()
res = st_folium(m, height=750, use_container_width=True)

# Add Pin
if res and res.get("last_clicked"):
    x = float(res["last_clicked"]["lng"])
    y = float(res["last_clicked"]["lat"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    st.session_state.pins.append({
        "id": st.session_state.next_pin_id,
        "x":x,
        "y":y,
        "name": pin_name if pin_name else pin_type,
        "type": pin_type,
        "color": PIN_TYPES[pin_type],
        "time": now
    })

    st.session_state.selected_pin_id = st.session_state.next_pin_id
    st.session_state.next_pin_id += 1
    st.rerun()

# Select by marker click
if res:
    txt = res.get("last_object_clicked_popup")
    if isinstance(txt,str):
        m_id = re.search(r"ID:</b>\s*(\d+)",txt)
        if m_id:
            st.session_state.selected_pin_id = int(m_id.group(1))

# -----------------------------
# Pin Details
# -----------------------------
st.subheader("📌 Pins")

if st.session_state.pins:
    ids=[p["id"] for p in st.session_state.pins]
    if st.session_state.selected_pin_id not in ids:
        st.session_state.selected_pin_id=ids[0]

    sel = st.selectbox("Pin auswählen",ids,index=ids.index(st.session_state.selected_pin_id))
    pin = next(p for p in st.session_state.pins if p["id"]==sel)

    st.markdown(f"""
    <div class="card">
    <div class="card-value">ID {pin["id"]} – {pin["type"]}</div>
    <div class="muted">
    Name: {pin["name"]}<br>
    Zeit: {pin["time"]}<br>
    x={pin["x"]:.2f} | y={pin["y"]:.2f}
    </div>
    </div>
    """,unsafe_allow_html=True)

    pin["name"]=st.text_input("Name ändern",pin["name"])
    new_type=st.selectbox("Typ ändern",list(PIN_TYPES.keys()),
                index=list(PIN_TYPES.keys()).index(pin["type"]))
    pin["type"]=new_type
    pin["color"]=PIN_TYPES[new_type]

    st.markdown('<div class="warn">Pin löschen nummeriert alle Pins neu</div>',unsafe_allow_html=True)

    if st.button("🗑️ Diesen Pin löschen"):
        st.session_state.pins=[p for p in st.session_state.pins if p["id"]!=sel]
        i=1
        for p in st.session_state.pins:
            p["id"]=i
            i+=1
        st.session_state.next_pin_id=i
        st.session_state.selected_pin_id=None
        st.rerun()

    df=pd.DataFrame(st.session_state.pins)
    df=df[["id","type","name","time","x","y"]]
    df.columns=["ID","Typ","Name","Zeit","x","y"]
    st.dataframe(df,use_container_width=True)
else:
    st.info("Noch keine Pins gesetzt.")
