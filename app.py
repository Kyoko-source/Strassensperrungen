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
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px; }
h1, h2, h3 { letter-spacing: -0.02em; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0b1220 0%, #0f1a2e 100%); }
section[data-testid="stSidebar"] * { color: #e9eefc !important; }
.stButton button { border-radius: 14px; border: 1px solid rgba(255,255,255,0.12); padding: 0.62rem 0.9rem; font-weight: 600; }
.stButton button:hover { border-color: rgba(255,255,255,0.22); transform: translateY(-1px); }

.card { border-radius: 18px; padding: 14px 16px;
background: linear-gradient(135deg, rgba(13,110,253,0.08), rgba(110,66,193,0.08));
border: 1px solid rgba(15, 23, 42, 0.12); box-shadow: 0 10px 30px rgba(2, 6, 23, 0.06); }

.card-title { font-size: 0.9rem; opacity: 0.72; margin-bottom: 6px; }
.card-value { font-size: 1.35rem; font-weight: 750; }
.muted { opacity: 0.72; }

.pill { display:inline-block; padding: 6px 10px; border-radius: 999px; font-weight: 650; font-size: 0.85rem; }
.pill-red { background: rgba(220,53,69,0.12); color: #b42318; border: 1px solid rgba(220,53,69,0.25); }
.pill-orange { background: rgba(253,126,20,0.12); color: #b54708; border: 1px solid rgba(253,126,20,0.25); }
.pill-blue { background: rgba(13,110,253,0.12); color: #175cd3; border: 1px solid rgba(13,110,253,0.25); }
.pill-black { background: rgba(33,37,41,0.10); color: #111827; border: 1px solid rgba(33,37,41,0.18); }

.warn { border-left: 4px solid #dc3545; padding: 10px 12px; border-radius: 12px; background: rgba(220,53,69,0.06); }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid rgba(15, 23, 42, 0.10); }

/* >>> NUR FARBE GEÄNDERT <<< */
section[data-testid="stSidebar"] input {
    background-color: #dbeafe !important;
    color: #0f172a !important;
}

section[data-testid="stSidebar"] .stButton button {
    background-color: #2563eb !important;
    color: white !important;
    border: 1px solid #1e40af !important;
}

section[data-testid="stSidebar"] .stButton button:hover {
    background-color: #1e40af !important;
}
/* >>> ENDE <<< */

</style>
""",
unsafe_allow_html=True
)

# -----------------------------
# Title
# -----------------------------
st.title("🚑 DRK Reken – Digitale Einsatzkarte")
st.caption("Pins setzen, benennen, auswählen, einzeln löschen – mit Zeitstempel & automatischer Neu-Nummerierung.")

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

def color_to_pill(color: str) -> str:
    return {
        "red": "pill-red",
        "orange": "pill-orange",
        "blue": "pill-blue",
        "black": "pill-black"
    }.get(color, "pill-black")

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
st.sidebar.markdown("## 🧷 Pin-Steuerung")
fullscreen = st.sidebar.toggle("🖥️ Karte Vollbild", value=False)

pin_type = st.sidebar.radio("Pin-Typ", list(PIN_TYPES.keys()))
pin_name = st.sidebar.text_input("Name", value="", placeholder="z.B. RTW Heiden")

pill_class = color_to_pill(PIN_TYPES[pin_type])
st.sidebar.markdown(
    f"""<div class="card" style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.10);">
    <div class="card-title">Aktuelle Auswahl</div>
    <div class="card-value"><span class="pill {pill_class}">{pin_type}</span></div>
    <div class="muted" style="margin-top:8px;">Karte anklicken → Pin wird gesetzt.</div>
    </div>""",
    unsafe_allow_html=True
)

st.sidebar.divider()
if st.sidebar.button("🧹 Alles löschen", use_container_width=True):
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
bounds = [[0, 0], [H, 100]]

# -----------------------------
# Map Builder
# -----------------------------
def build_map():
    m = folium.Map(location=[H/2,50], zoom_start=1, crs="Simple", tiles=None)
    ImageOverlay(image=IMAGE_PATH, bounds=bounds).add_to(m)
    m.fit_bounds(bounds)
    m.options["dragging"] = False
    m.options["scrollWheelZoom"] = False
    m.options["doubleClickZoom"] = False

    for p in st.session_state.pins:
        folium.Marker(
            [p["y"], p["x"]],
            popup=f"<b>ID:</b> {p['id']}<br><b>Name:</b> {p['name']}",
            tooltip=f"{p['id']}: {p['name']}",
            icon=folium.Icon(color=p["color"])
        ).add_to(m)
    return m

# -----------------------------
# Show Map
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
        "x": x,
        "y": y,
        "name": pin_name if pin_name else pin_type,
        "type": pin_type,
        "color": PIN_TYPES[pin_type],
        "created_at": now
    })

    st.session_state.selected_pin_id = st.session_state.next_pin_id
    st.session_state.next_pin_id += 1
    st.rerun()

# -----------------------------
# Pin List + Delete
# -----------------------------
st.subheader("📌 Pins")

if st.session_state.pins:
    ids = [p["id"] for p in st.session_state.pins]
    sel = st.selectbox("Pin auswählen", ids)
    pin = next(p for p in st.session_state.pins if p["id"] == sel)

    st.write(f"**ID:** {pin['id']}")
    st.write(f"**Name:** {pin['name']}")
    st.write(f"**Zeit:** {pin['created_at']}")

    if st.button("🗑️ Diesen Pin löschen"):
        st.session_state.pins = [p for p in st.session_state.pins if p["id"] != sel]
        i = 1
        for p in st.session_state.pins:
            p["id"] = i
            i += 1
        st.session_state.next_pin_id = i
        st.rerun()

    df = pd.DataFrame(st.session_state.pins)
    st.dataframe(df, use_container_width=True)
else:
    st.info("Noch keine Pins gesetzt.")
