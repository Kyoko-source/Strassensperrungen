import json
from dataclasses import dataclass, asdict
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas
import pandas as pd

# =========================
# Einstellungen
# =========================

IMAGE_PATH = "karte.png"

GRID_COLS = list("ABCDEFGH")
GRID_ROWS = [1, 2, 3, 4]   # 1 = oben

PIN_TYPES = {
    "RTW (Rot)": "#ff0000",
    "KTW (Orange)": "#ff8c00",
    "EVT Fußtrupp (Blau)": "#0066ff",
    "Sonstiges (Schwarz)": "#000000"
}

# =========================

@dataclass
class Pin:
    id: int
    x: float
    y: float
    color: str
    name: str

# =========================

def xy_to_grid(x, y, w, h):
    col = int((x / w) * len(GRID_COLS))
    row = int((y / h) * len(GRID_ROWS))
    col = min(col, len(GRID_COLS)-1)
    row = min(row, len(GRID_ROWS)-1)
    return f"{GRID_COLS[col]}{GRID_ROWS[row]}"

# =========================

st.set_page_config(layout="wide")
st.title("DRK Reken – Digitale Einsatzkarte")

# =========================

if "pins" not in st.session_state:
    st.session_state.pins = []
if "next_id" not in st.session_state:
    st.session_state.next_id = 1

# =========================
# Sidebar
# =========================

st.sidebar.header("Pin Auswahl")
pin_type = st.sidebar.radio("Pin Typ:", list(PIN_TYPES.keys()))
pin_color = PIN_TYPES[pin_type]

if st.sidebar.button("Alle Pins löschen"):
    st.session_state.pins = []
    st.session_state.next_id = 1
    st.rerun()

# =========================
# Bild laden
# =========================

img = Image.open(IMAGE_PATH)
width, height = img.size

# =========================
# Canvas
# =========================

canvas = st_canvas(
    background_image=img,
    fill_color=pin_color,
    stroke_color=pin_color,
    stroke_width=2,
    drawing_mode="circle",
    height=height,
    width=width,
    key="canvas"
)

objects = []
if canvas.json_data:
    objects = canvas.json_data["objects"]

# =========================
# Pins synchronisieren
# =========================

new_pins = []

for obj in objects:
    r = obj["radius"]
    x = obj["left"] + r
    y = obj["top"] + r
    color = obj["fill"]
    new_pins.append(Pin(
        id=0,
        x=x,
        y=y,
        color=color,
        name=""
    ))

# IDs & Namen behalten
for i, p in enumerate(new_pins):
    if i < len(st.session_state.pins):
        p.id = st.session_state.pins[i].id
        p.name = st.session_state.pins[i].name
    else:
        p.id = st.session_state.next_id
        st.session_state.next_id += 1

st.session_state.pins = new_pins

# =========================
# Rechte Seite: Liste
# =========================

st.subheader("Pins & Namen")

table = []

for p in st.session_state.pins:
    grid = xy_to_grid(p.x, p.y, width, height)
    p.name = st.text_input(
        f"#{p.id} @ {grid}",
        value=p.name,
        key=f"name_{p.id}"
    )
    table.append({
        "ID": p.id,
        "Name": p.name,
        "Raster": grid
    })

df = pd.DataFrame(table)
st.dataframe(df, use_container_width=True)

# =========================
# Export
# =========================

export = json.dumps([asdict(p) for p in st.session_state.pins])
st.download_button("Pins exportieren", export, "pins.json")
