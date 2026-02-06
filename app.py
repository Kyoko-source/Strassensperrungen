import json
from dataclasses import dataclass, asdict
from typing import List

import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# =========================
# KONFIG
# =========================
IMAGE_PATH = "karte.jpg"   # <- muss exakt so heißen wie im Repo

GRID_COLS = list("ABCDEFGH")
GRID_ROWS = [1, 2, 3, 4]   # 1 = oben, 4 = unten

PIN_TYPES = {
    "RTW (Rot)": "#ff0000",
    "KTW (Orange)": "#ff8c00",
    "EVT Fußtrupp (Blau)": "#0066ff",
    "Sonstiges (Schwarz)": "#000000",
}

# =========================
# DATENMODELL
# =========================
@dataclass
class Pin:
    id: int
    x: float
    y: float
    color: str
    name: str = ""


def xy_to_grid(x: float, y: float, w: int, h: int) -> str:
    """Teilt das Bild in 8 Spalten (A-H) und 4 Zeilen (1-4), 1 ist oben."""
    col_idx = int((x / w) * len(GRID_COLS))
    row_idx = int((y / h) * len(GRID_ROWS))

    col_idx = max(0, min(col_idx, len(GRID_COLS) - 1))
    row_idx = max(0, min(row_idx, len(GRID_ROWS) - 1))

    return f"{GRID_COLS[col_idx]}{GRID_ROWS[row_idx]}"


# =========================
# STREAMLIT SETUP
# =========================
st.set_page_config(layout="wide")
st.title("DRK Reken – Digitale Einsatzkarte (Pins setzen & benennen)")

# Session State
if "pins" not in st.session_state:
    st.session_state.pins: List[Pin] = []
if "next_id" not in st.session_state:
    st.session_state.next_id = 1

# =========================
# SIDEBAR
# =========================
st.sidebar.header("Pin-Auswahl")
pin_type = st.sidebar.radio("Pin-Typ", list(PIN_TYPES.keys()))
pin_color = PIN_TYPES[pin_type]

if st.sidebar.button("Alle Pins löschen", use_container_width=True):
    st.session_state.pins = []
    st.session_state.next_id = 1
    # Canvas-Session zurücksetzen
    if "canvas" in st.session_state:
        del st.session_state["canvas"]
    st.rerun()

st.sidebar.divider()
st.sidebar.caption("Tipp: Pins setzen = auf Karte klicken. Pins verschieben = Pin anfassen & ziehen.")

# =========================
# BILD LADEN
# =========================
img = Image.open(IMAGE_PATH).convert("RGB")
w, h = img.size

# =========================
# LAYOUT
# =========================
left, right = st.columns([3.2, 1.3], gap="large")

with left:
    st.subheader("Karte")

    # Canvas: Hintergrundbild + Kreise als Pins
    canvas_result = st_canvas(
        background_image=img,
        drawing_mode="circle",
        fill_color=pin_color,
        stroke_color=pin_color,
        stroke_width=2,
        width=w,
        height=h,
        update_streamlit=True,
        key="canvas",
        display_toolbar=True,
    )

    # Canvas-Objekte lesen
    objects = []
    if canvas_result.json_data and "objects" in canvas_result.json_data:
        objects = canvas_result.json_data["objects"]

    # =========================
    # PIN-SYNC
    # =========================
    # Wir bauen aus Canvas-Objekten Pins. Namen behalten wir über Index-Zuordnung.
    new_pins: List[Pin] = []

    for obj in objects:
        if obj.get("type") != "circle":
            continue

        r = float(obj.get("radius", 8))
        x = float(obj.get("left", 0) + r)
        y = float(obj.get("top", 0) + r)
        color = obj.get("fill") or "#000000"
        new_pins.append(Pin(id=0, x=x, y=y, color=color, name=""))

    # IDs & Namen vom alten Zustand übernehmen (solange Reihenfolge gleich bleibt)
    for i, p in enumerate(new_pins):
        if i < len(st.session_state.pins):
            p.id = st.session_state.pins[i].id
            p.name = st.session_state.pins[i].name
        else:
            p.id = st.session_state.next_id
            st.session_state.next_id += 1

    st.session_state.pins = new_pins

with right:
    st.subheader("Pins")
    if len(st.session_state.pins) == 0:
        st.info("Noch keine Pins gesetzt.")
    else:
        # Tabelle
        rows = []
        for p in st.session_state.pins:
            grid = xy_to_grid(p.x, p.y, w, h)

            # Farbcode zurück zu Typ (optional)
            typ = "Unbekannt"
            for k, v in PIN_TYPES.items():
                if (p.color or "").lower().startswith(v.lower()):
                    typ = k
                    break

            rows.append({
                "ID": p.id,
                "Raster": grid,
                "Farbe": p.color,
                "Name": p.name,
            })

        df = pd.DataFrame(rows)
        st.dataframe(df[["ID", "Raster", "Name"]], use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("### Namen vergeben / ändern")
        for p in st.session_state.pins:
            grid = xy_to_grid(p.x, p.y, w, h)
            p.name = st.text_input(f"#{p.id} @ {grid}", value=p.name, key=f"name_{p.id}")

        st.divider()
        export = json.dumps([asdict(p) for p in st.session_state.pins], ensure_ascii=False, indent=2)
        st.download_button(
            "Export JSON",
            data=export.encode("utf-8"),
            file_name="pins.json",
            mime="application/json",
            use_container_width=True,
        )
        st.download_button(
            "Export CSV",
            data=pd.DataFrame([{
                "id": p.id,
                "name": p.name,
                "grid": xy_to_grid(p.x, p.y, w, h),
                "x": round(p.x, 1),
                "y": round(p.y, 1),
                "color": p.color
            } for p in st.session_state.pins]).to_csv(index=False).encode("utf-8"),
            file_name="pins.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.caption("Hinweis: Raster A–H / 1–4 wird aktuell gleichmäßig über das Bild verteilt.")
