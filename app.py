import streamlit as st
import folium
from folium.raster_layers import ImageOverlay
from streamlit_folium import st_folium
from PIL import Image
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide")
st.title("DRK Reken – Digitale Einsatzkarte")

IMAGE_PATH = "karte.jpg"

PIN_TYPES = {
    "RTW (Rot)": "red",
    "KTW (Orange)": "orange",
    "EVT Fußtrupp (Blau)": "blue",
    "Sonstiges (Schwarz)": "black",
}

# --- State ---
if "pins" not in st.session_state:
    # jeder Pin: {"id": int, "x": float, "y": float, "name": str, "color": str, "type": str, "created_at": str}
    st.session_state.pins = []

if "next_pin_id" not in st.session_state:
    st.session_state.next_pin_id = 1

if "selected_pin_id" not in st.session_state:
    st.session_state.selected_pin_id = None

# --- Sidebar: Neuen Pin setzen ---
st.sidebar.header("Neuen Pin setzen")
pin_type = st.sidebar.radio("Pin-Typ", list(PIN_TYPES.keys()))
pin_name = st.sidebar.text_input("Name (z.B. RTW Heiden)", value="")

if st.sidebar.button("Alle Pins löschen", use_container_width=True):
    st.session_state.pins = []
    st.session_state.next_pin_id = 1
    st.session_state.selected_pin_id = None
    st.rerun()

# --- Bild laden (Seitenverhältnis) ---
img = Image.open(IMAGE_PATH)
w, h = img.size

# Koordinatenraum fürs Bild: Breite=100, Höhe skaliert
H = 100 * (h / w)
bounds = [[0, 0], [H, 100]]

# --- Karte ohne Tiles ---
m = folium.Map(
    location=[H / 2, 50],
    zoom_start=1,
    crs="Simple",
    tiles=None,
    zoom_control=False,
)

ImageOverlay(
    image=IMAGE_PATH,
    bounds=bounds,
    opacity=1.0,
    interactive=True,
    zindex=1
).add_to(m)

m.fit_bounds(bounds)

# Karte "festnageln"
m.options["dragging"] = False
m.options["scrollWheelZoom"] = False
m.options["doubleClickZoom"] = False
m.options["touchZoom"] = False
m.options["boxZoom"] = False
m.options["keyboard"] = False
m.options["zoomSnap"] = 0
m.options["maxBounds"] = bounds
m.options["maxBoundsViscosity"] = 1.0

# --- Pins rendern ---
# Trick: Wir schreiben die ID in den Popup-Text, damit wir sie beim Anklicken wiederfinden können.
for p in st.session_state.pins:
    popup_html = (
        f"<b>ID:</b> {p['id']}<br>"
        f"<b>Typ:</b> {p['type']}<br>"
        f"<b>Name:</b> {p['name']}<br>"
        f"<b>gesetzt:</b> {p['created_at']}<br>"
        f"<b>x/y:</b> {p['x']:.2f}, {p['y']:.2f}"
    )
    folium.Marker(
        location=[p["y"], p["x"]],
        popup=popup_html,
        tooltip=f"{p['id']}: {p['name']}",
        draggable=True,  # Ziehbar (Hinweis: Position wird dadurch NICHT automatisch gespeichert)
        icon=folium.Icon(color=p["color"])
    ).add_to(m)

# --- Anzeigen ---
res = st_folium(m, height=750, use_container_width=True)

# 1) Klick auf Karte -> neuen Pin hinzufügen
if res and res.get("last_clicked"):
    x = float(res["last_clicked"]["lng"])
    y = float(res["last_clicked"]["lat"])
    new_id = st.session_state.next_pin_id
    st.session_state.next_pin_id += 1

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    st.session_state.pins.append({
        "id": new_id,
        "x": x,
        "y": y,
        "name": pin_name.strip() if pin_name.strip() else pin_type,
        "type": pin_type,
        "color": PIN_TYPES[pin_type],
        "created_at": now,
    })
    st.session_state.selected_pin_id = new_id
    st.rerun()

# 2) Klick auf Marker -> Pin auswählen (falls streamlit-folium es liefert)
# Je nach Version heißt das Feld unterschiedlich. Wir versuchen beides.
clicked_popup = None
if res:
    clicked_popup = res.get("last_object_clicked_popup") or res.get("last_object_clicked_tooltip")

# Wenn wir im Popup/Tooltip eine ID finden, übernehmen wir sie als Auswahl.
if isinstance(clicked_popup, str):
    # Suche nach "ID: <zahl>" oder "ID:</b> <zahl>"
    import re
    m_id = re.search(r"ID:\s*</b>\s*(\d+)|ID:\s*(\d+)", clicked_popup)
    if m_id:
        pid = int(m_id.group(1) or m_id.group(2))
        st.session_state.selected_pin_id = pid

st.divider()
st.subheader("Pin-Übersicht / Bearbeiten")

# --- Tabelle mit Pins ---
if st.session_state.pins:
    df = pd.DataFrame(st.session_state.pins)
    # hübsch sortieren
    df = df[["id", "type", "name", "created_at", "x", "y"]].sort_values("id")
    df.rename(columns={
        "id": "ID",
        "type": "Typ",
        "name": "Name",
        "created_at": "Zeitstempel",
        "x": "x",
        "y": "y",
    }, inplace=True)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Noch keine Pins gesetzt.")

# --- Auswahl & Einzel-Löschen ---
if st.session_state.pins:
    ids = [p["id"] for p in st.session_state.pins]
    # Falls nichts ausgewählt: erstes Element
    if st.session_state.selected_pin_id not in ids:
        st.session_state.selected_pin_id = ids[0]

    sel = st.selectbox("Pin auswählen", ids, index=ids.index(st.session_state.selected_pin_id))
    st.session_state.selected_pin_id = sel

    pin = next(p for p in st.session_state.pins if p["id"] == sel)

    st.markdown("### Ausgewählter Pin")
    st.write(f"**ID:** {pin['id']}")
    st.write(f"**Typ:** {pin['type']}")
    st.write(f"**Name:** {pin['name']}")
    st.write(f"**Zeitstempel:** {pin['created_at']}")
    st.write(f"**Koordinaten:** x={pin['x']:.2f}, y={pin['y']:.2f}")

    # Bearbeiten (optional)
    pin["name"] = st.text_input("Name ändern", value=pin["name"])
    new_type = st.selectbox("Typ ändern", list(PIN_TYPES.keys()), index=list(PIN_TYPES.keys()).index(pin["type"]))
    pin["type"] = new_type
    pin["color"] = PIN_TYPES[new_type]

    col1, col2 = st.columns(2)
    if col1.button("🗑️ Diesen Pin löschen", use_container_width=True):
        st.session_state.pins = [p for p in st.session_state.pins if p["id"] != sel]
        st.session_state.selected_pin_id = None
        st.rerun()

    if col2.button("💾 Änderungen übernehmen", use_container_width=True):
        st.rerun()
