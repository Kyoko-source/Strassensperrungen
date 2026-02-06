import streamlit as st
import folium
from folium.raster_layers import ImageOverlay
from streamlit_folium import st_folium
from PIL import Image
import pandas as pd

st.set_page_config(layout="wide")
st.title("DRK Reken – Digitale Einsatzkarte")

IMAGE_PATH = "karte.jpg"

PIN_TYPES = {
    "RTW (Rot)": "red",
    "KTW (Orange)": "orange",
    "EVT Fußtrupp (Blau)": "blue",
    "Sonstiges (Schwarz)": "black",
}

if "pins" not in st.session_state:
    st.session_state.pins = []

st.sidebar.header("Neuen Pin setzen")
pin_type = st.sidebar.radio("Pin-Typ", list(PIN_TYPES.keys()))
pin_name = st.sidebar.text_input("Name (z.B. RTW Heiden)", value="")

if st.sidebar.button("Alle Pins löschen", use_container_width=True):
    st.session_state.pins = []
    st.rerun()

# Bild laden (Seitenverhältnis)
img = Image.open(IMAGE_PATH)
w, h = img.size

# Koordinatenraum fürs Bild: Breite=100, Höhe skaliert
H = 100 * (h / w)
bounds = [[0, 0], [H, 100]]

# Karte ohne Tiles
m = folium.Map(
    location=[H / 2, 50],
    zoom_start=1,
    crs="Simple",
    tiles=None,
    zoom_control=False,   # optional: Zoom-Buttons aus
)

# Hintergrundbild
ImageOverlay(
    image=IMAGE_PATH,
    bounds=bounds,
    opacity=1.0,
    interactive=True,
    zindex=1
).add_to(m)

m.fit_bounds(bounds)

# Karte "festnageln" (kaum beweglich)
m.options["dragging"] = False
m.options["scrollWheelZoom"] = False
m.options["doubleClickZoom"] = False
m.options["touchZoom"] = False
m.options["boxZoom"] = False
m.options["keyboard"] = False
m.options["zoomSnap"] = 0

# Optional: Nicht rausziehen können
m.options["maxBounds"] = bounds
m.options["maxBoundsViscosity"] = 1.0

# Pins rendern (DRAGGABLE!)
for p in st.session_state.pins:
    folium.Marker(
        location=[p["y"], p["x"]],
        popup=p["name"],
        tooltip=p["name"],
        draggable=True,  # <<< DAS macht die Pins ziehbar
        icon=folium.Icon(color=p["color"])
    ).add_to(m)

# Anzeigen
res = st_folium(m, height=750, use_container_width=True)

# Klick -> Pin hinzufügen
if res and res.get("last_clicked"):
    x = float(res["last_clicked"]["lng"])
    y = float(res["last_clicked"]["lat"])
    st.session_state.pins.append({
        "x": x,
        "y": y,
        "name": pin_name.strip() if pin_name.strip() else pin_type,
        "color": PIN_TYPES[pin_type],
    })
    st.rerun()

st.subheader("Pins (Liste)")
st.dataframe(pd.DataFrame(st.session_state.pins), use_container_width=True)
