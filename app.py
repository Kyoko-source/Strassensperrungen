import json
import math
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

import pandas as pd
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# -----------------------------
# Konfiguration: Raster (A–H, 1–4)
# -----------------------------
GRID_COLS = list("ABCDEFGH")
GRID_ROWS = [1, 2, 3, 4]  # oben->unten oder unten->oben? wir nehmen oben=1

PIN_TYPES = {
    "RTW (Rot)":   {"color": "#ff0000", "abbr": "RTW"},
    "KTW (Orange)": {"color": "#ff8c00", "abbr": "KTW"},
    "EVT Fußtrupp (Blau)": {"color": "#0066ff", "abbr": "EVT"},
    "Sonstiges (Schwarz)": {"color": "#000000", "abbr": "SON"},
}

@dataclass
class Pin:
    id: int
    x: float
    y: float
    pin_type: str
    name: str = ""

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def xy_to_grid(x, y, img_w, img_h, pad_left, pad_right, pad_top, pad_bottom):
    """Rechnet Canvas-Koordinate in Rasterfeld um."""
    # Nutzbarer Bereich (ohne Pads)
    usable_w = max(1, img_w - pad_left - pad_right)
    usable_h = max(1, img_h - pad_top - pad_bottom)

    # In nutzbaren Bereich umrechnen
    ux = (x - pad_left) / usable_w
    uy = (y - pad_top) / usable_h
    ux = clamp(ux, 0, 0.999999)
    uy = clamp(uy, 0, 0.999999)

    col_idx = int(ux * len(GRID_COLS))
    row_idx = int(uy * len(GRID_ROWS))

    col = GRID_COLS[col_idx]
    row = GRID_ROWS[row_idx]
    return f"{col}{row}"

def pins_to_df(pins: List[Pin], img_w, img_h, pads):
    rows = []
    for p in pins:
        grid = xy_to_grid(p.x, p.y, img_w, img_h, *pads)
        rows.append({
            "ID": p.id,
            "Typ": p.pin_type,
            "Name": p.name,
            "Raster": grid,
            "x": round(p.x, 1),
            "y": round(p.y, 1),
        })
    return pd.DataFrame(rows)

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(layout="wide")
st.title("DRK Reken – Digitale Einsatzkarte (Pins setzen & benennen)")

# Bild laden
IMG_PATH = "karte.png"  # <- falls dein Bild anders heißt, hier ändern
img = Image.open(IMG_PATH)
img_w, img_h = img.size

# Session State
if "pins" not in st.session_state:
    st.session_state.pins = []  # List[Pin]
if "next_id" not in st.session_state:
    st.session_state.next_id = 1

# Sidebar: Pin-Auswahl + Raster-Feintuning
st.sidebar.header("Pin-Auswahl")
selected_type = st.sidebar.radio("Pin-Typ", list(PIN_TYPES.keys()))
selected_color = PIN_TYPES[selected_type]["color"]

st.sidebar.divider()
st.sidebar.header("Raster-Feintuning (optional)")
st.sidebar.caption("Falls A-H / 1-4 nicht perfekt passt: Ränder anpassen.")
pad_left = st.sidebar.slider("Rand links (px)", 0, int(img_w * 0.3), 0)
pad_right = st.sidebar.slider("Rand rechts (px)", 0, int(img_w * 0.3), 0)
pad_top = st.sidebar.slider("Rand oben (px)", 0, int(img_h * 0.3), 0)
pad_bottom = st.sidebar.slider("Rand unten (px)", 0, int(img_h * 0.3), 0)
pads = (pad_left, pad_right, pad_top, pad_bottom)

st.sidebar.divider()
st.sidebar.header("Daten")
colA, colB = st.sidebar.columns(2)
if colA.button("Alle Pins löschen", use_container_width=True):
    st.session_state.pins = []
    st.session_state.next_id = 1
    st.rerun()

# Export/Import
export_obj = {
    "image": IMG_PATH,
    "pins": [asdict(p) for p in st.session_state.pins],
    "next_id": st.session_state.next_id,
    "pads": {"left": pad_left, "right": pad_right, "top": pad_top, "bottom": pad_bottom},
}
export_json = json.dumps(export_obj, ensure_ascii=False, indent=2)
st.sidebar.download_button(
    "Export JSON",
    data=export_json.encode("utf-8"),
    file_name="einsatzkarte_pins.json",
    mime="application/json",
    use_container_width=True
)

uploaded = st.sidebar.file_uploader("Import JSON", type=["json"])
if uploaded is not None:
    try:
        data = json.load(uploaded)
        loaded_pins = [Pin(**p) for p in data.get("pins", [])]
        st.session_state.pins = loaded_pins
        st.session_state.next_id = int(data.get("next_id", 1))
        st.sidebar.success("Import OK.")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Import fehlgeschlagen: {e}")

# Layout: Karte groß + rechts Liste/Namen
left, right = st.columns([3.2, 1.2], gap="large")

with left:
    st.subheader("Karte")
    st.caption("Klick auf die Karte setzt einen Pin (vom ausgewählten Typ). Pins kannst du danach verschieben.")

    # Canvas: Hintergrundbild + Objekte
    # Wir zeichnen Pins als kleine Kreise. Verschieben ist möglich.
    # Beim Klick setzen wir einen neuen Kreis.
    canvas_result = st_canvas(
        fill_color=selected_color,
        stroke_width=2,
        stroke_color=selected_color,
        background_image=img,
        update_streamlit=True,
        height=img_h,
        width=img_w,
        drawing_mode="circle",
        key="canvas",
        display_toolbar=True,
    )

    # Wenn ein neues Objekt hinzugekommen ist, übernehmen wir es als "Pin"
    # Strategie: Wir nehmen die Canvas-Objekte und syncen sie mit unseren Pins
    objects = canvas_result.json_data["objects"] if canvas_result.json_data else []

    # Build pins from canvas objects (nur circles)
    new_pins: List[Pin] = []
    # Wir versuchen IDs stabil zu halten: index-basiert ist ok für Start, aber besser:
    # -> wir speichern ID in "name" Feld des canvas-objects (nicht super zuverlässig),
    # darum: einfache Sync-Logik: Anzahl passt? sonst neu vergeben.
    existing = st.session_state.pins

    if len(objects) != len(existing):
        # Pins neu aus Objekten bauen (IDs neu)
        new_pins = []
        next_id = 1
        for obj in objects:
            if obj.get("type") != "circle":
                continue
            # center aus left/top + radius
            r = obj.get("radius", 8)
            x = float(obj.get("left", 0) + r)
            y = float(obj.get("top", 0) + r)
            # Typ: Wir merken uns die Fill-Farbe => Typ zuordnen
            fill = (obj.get("fill") or "").lower()
            pin_type = None
            for k, v in PIN_TYPES.items():
                if v["color"].lower() in fill:
                    pin_type = k
                    break
            pin_type = pin_type or "Sonstiges (Schwarz)"
            new_pins.append(Pin(id=next_id, x=x, y=y, pin_type=pin_type, name=""))
            next_id += 1
        st.session_state.pins = new_pins
        st.session_state.next_id = next_id
        st.rerun()
    else:
        # Nur Positionen updaten
        updated = []
        for p, obj in zip(existing, objects):
            r = obj.get("radius", 8)
            x = float(obj.get("left", 0) + r)
            y = float(obj.get("top", 0) + r)

            # Typ anhand Fill aktualisieren (falls jemand die Farbe gewechselt hat)
            fill = (obj.get("fill") or "").lower()
            pin_type = p.pin_type
            for k, v in PIN_TYPES.items():
                if v["color"].lower() in fill:
                    pin_type = k
                    break

            updated.append(Pin(id=p.id, x=x, y=y, pin_type=pin_type, name=p.name))
        st.session_state.pins = updated

with right:
    st.subheader("Pins")
    st.caption("Hier Namen vergeben. Raster (A1–H4) wird automatisch berechnet.")

    if len(st.session_state.pins) == 0:
        st.info("Noch keine Pins gesetzt. Links auf die Karte klicken.")
    else:
        # Tabelle
        df = pins_to_df(st.session_state.pins, img_w, img_h, pads)
        st.dataframe(df[["ID", "Typ", "Name", "Raster"]], use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("### Namen bearbeiten")
        for p in st.session_state.pins:
            grid = xy_to_grid(p.x, p.y, img_w, img_h, *pads)
            label = f"#{p.id} – {p.pin_type} @ {grid}"
            new_name = st.text_input(label, value=p.name, key=f"name_{p.id}")
            p.name = new_name

        # CSV Export
        df2 = pins_to_df(st.session_state.pins, img_w, img_h, pads)
        st.download_button(
            "Export CSV",
            data=df2.to_csv(index=False).encode("utf-8"),
            file_name="einsatzkarte_pins.csv",
            mime="text/csv",
            use_container_width=True
        )
