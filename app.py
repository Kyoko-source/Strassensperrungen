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

# Speicher für Pins
if "pins" not in st.session_state:
    st.session_state.pins = []

# Sidebar
st.sidebar.header("Neuen Pin setzen")
pin_type = st.sidebar.radio("Pin-Typ", list(PIN_TYPES.keys()))
pin_name = st.sidebar.text_input("Name (z.B. RTW Heiden)", value="")

if st.sidebar.button("Alle Pins löschen", use_container_width=True):
    st.session_state.pins = []
    st.rerun()

# Bild laden (nur für Seitenverhältnis)
img = Image.open(IMAGE_PATH)
w, h = img.size

# Koordinatenraum für das Bild: X = 0..100, Y = 0..(100*h/w)
# damit das Bild ohne Verzerrung passt
H = 100 * (h / w)
bounds = [[0, 0], [H, 100]]  # [lat, lng] im Simple-CRS

# Karte OHNE Welt-Tiles
m = folium.Map(
    location=[H / 2, 50],
    zoom_start=1,
    crs="Simple",
    tiles=None,          # <- WICHTIG: keine Weltkarte mehr
    zoom_control=True
)

# Bild als Hintergrund
ImageOverlay(
    image=IMAGE_PATH,
    bounds=bounds,
    opacity=1.0,
    interactive=True,
    cross_origin=False,
    zindex=1
).add_to(m)

# Auf das Bild zoomen
m.fit_bounds(bounds)

# Optional: nicht “wegdriften”
m.options["maxBounds"] = bounds
m.options["maxBoundsViscosity"] = 1.0

# Pins rendern
for p in st.session_state.pins:
    folium.Marker(
        location=[p["y"], p["x"]],
        popup=p["name"],
        icon=folium.Icon(color=p["color"])
    ).add_to(m)

# Karte anzeigen (breit)
res = st_folium(m, height=750, use_container_width=True)

# Klick -> neuen Pin hinzufügen
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
df = pd.DataFrame(st.session_state.pins)
st.dataframe(df, use_container_width=True)
