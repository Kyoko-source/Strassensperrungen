import streamlit as st
import folium
from folium.raster_layers import ImageOverlay
from streamlit_folium import st_folium
from PIL import Image
import pandas as pd

st.set_page_config(layout="wide")
st.title("DRK Reken – Digitale Einsatzkarte")

IMAGE = "karte.jpg"

PIN_TYPES = {
    "RTW (Rot)": "red",
    "KTW (Orange)": "orange",
    "EVT Fußtrupp (Blau)": "blue",
    "Sonstiges (Schwarz)": "black"
}

# -----------------
if "pins" not in st.session_state:
    st.session_state.pins = []

# -----------------
st.sidebar.header("Neuen Pin setzen")
pin_type = st.sidebar.radio("Pin-Typ", list(PIN_TYPES.keys()))
pin_name = st.sidebar.text_input("Name (z.B. RTW Heiden)")

if st.sidebar.button("Alle Pins löschen"):
    st.session_state.pins = []
    st.rerun()

# -----------------
img = Image.open(IMAGE)
w, h = img.size

m = folium.Map(
    location=[50,50],
    zoom_start=2,
    crs="Simple"
)

ImageOverlay(
    image=IMAGE,
    bounds=[[0,0],[100,100]],
).add_to(m)

for p in st.session_state.pins:
    folium.Marker(
        [p["y"], p["x"]],
        popup=f'{p["name"]}',
        icon=folium.Icon(color=p["color"])
    ).add_to(m)

result = st_folium(m, width=1000, height=700)

if result and result["last_clicked"]:
    x = result["last_clicked"]["lng"]
    y = result["last_clicked"]["lat"]
    st.session_state.pins.append({
        "x": x,
        "y": y,
        "name": pin_name,
        "color": PIN_TYPES[pin_type]
    })
    st.rerun()

# -----------------
st.subheader("Pins")
df = pd.DataFrame(st.session_state.pins)
st.dataframe(df)
