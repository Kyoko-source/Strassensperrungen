import json
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

GRID_COLS = list("ABCDEFGH")
GRID_ROWS = 4  # 1..4

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def xy_to_raster(x, y, W=100.0, H=100.0, invert_y=False, fmt="3B"):
    """
    x: 0..W, y: 0..H
    fmt:
      - "3B" => row then col
      - "B3" => col then row
    """
    x = clamp(x, 0, W - 1e-9)
    y = clamp(y, 0, H - 1e-9)

    if invert_y:
        y = (H - 1e-9) - y

    col_idx = int(x / (W / len(GRID_COLS)))
    row_idx = int(y / (H / GRID_ROWS))

    col = GRID_COLS[clamp(col_idx, 0, len(GRID_COLS)-1)]
    row = str(clamp(row_idx, 0, GRID_ROWS-1) + 1)

    if fmt == "B3":
        return f"{col}{row}"
    return f"{row}{col}"  # default "3B"

# -----------------------------
# State
# -----------------------------
if "pins" not in st.session_state:
    st.session_state.pins = []  # list of dicts
if "next_id" not in st.session_state:
    st.session_state.next_id = 1
if "last_click" not in st.session_state:
    st.session_state.last_click = None

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.header("Neuen Pin setzen")
pin_type_label = st.sidebar.radio("Pin-Typ", list(PIN_TYPES.keys()))
pin_name = st.sidebar.text_input("Name (z.B. RTW Heiden)", value="")
st.sidebar.divider()

# Raster-Optionen
st.sidebar.header("Raster")
raster_fmt = st.sidebar.radio("Anzeige", ["3B", "B3"], index=0)
invert_y = st.sidebar.checkbox("Raster Y umdrehen (falls 1 unten sein soll)", value=False)

st.sidebar.divider()
col1, col2 = st.sidebar.columns(2)
if col1.button("Alle Pins löschen", use_container_width=True):
    st.session_state.pins = []
    st.session_state.next_id = 1
    st.rerun()

# Export / Import
export_obj = {
    "image": IMAGE_PATH,
    "pins": st.session_state.pins,
    "next_id": st.session_state.next_id,
}
st.sidebar.download_button(
    "Export JSON",
    data=json.dumps(export_obj, ensure_ascii=False, indent=2).encode("utf-8"),
    file_name="einsatzkarte_pins.json",
    mime="application/json",
    use_container_width=True
)

uploaded = st.sidebar.file_uploader("Import JSON", type=["json"])
if uploaded is not None:
    try:
        data = json.load(uploaded)
        st.session_state.pins = data.get("pins", [])
        st.session_state.next_id = int(data.get("next_id", 1))
        st.sidebar.success("Import OK.")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Import fehlgeschlagen: {e}")

# -----------------------------
# Bild laden + Koordinatenraum festlegen
# -----------------------------
img = Image.open(IMAGE_PATH)
img_w, img_h = img.size

# Wir machen den Kartenraum so, dass X = 0..100 und Y proportional skaliert ist.
W = 100.0
H = 100.0 * (img_h / img_w)  # damit das Bild nicht verzerrt wird
bounds = [[0, 0], [H, W]]     # [lat(y), lng(x)]

# -----------------------------
# Layout
# -----------------------------
left, right = st.columns([3.2, 1.3], gap="large")

with left:
    # Karte ohne Welt-Tiles
    m = folium.Map(
        location=[H/2, W/2],
        zoom_start=1,
        crs="Simple",
        tiles=None,
        zoom_control=False
    )

    ImageOverlay(
        image=IMAGE_PATH,
        bounds=bounds,
        opacity=1.0,
        interactive=True,
        zindex=1
    ).add_to(m)

    # Auf das Bild zoomen und Karte quasi fixieren
    m.fit_bounds(bounds)
    m.options["dragging"] = False
    m.options["scrollWheelZoom"] = False
    m.options["doubleClickZoom"] = False
    m.options["touchZoom"] = False
    m.options["boxZoom"] = False
    m.options["keyboard"] = False
    m.options["maxBounds"] = bounds
    m.options["maxBoundsViscosity"] = 1.0

    # Pins rendern
    for p in st.session_state.pins:
        folium.Marker(
            location=[p["y"], p["x"]],
            popup=f'{p["name"]} ({p["type"]})',
            tooltip=p["name"],
            icon=folium.Icon(color=p["color"])
        ).add_to(m)

    st.caption("Klick auf die Karte setzt einen Pin. (Zum Verschieben: rechts Pin wählen → neue Stelle klicken → verschieben.)")
    res = st_folium(m, height=780, use_container_width=True)

    # Klick speichern
    if res and res.get("last_clicked"):
        st.session_state.last_click = res["last_clicked"]  # {"lat":..,"lng":..}

    # Wenn geklickt: neuen Pin anlegen
    if st.session_state.last_click and st.button("📍 Pin an letzter Klick-Position setzen", use_container_width=True):
        x = float(st.session_state.last_click["lng"])
        y = float(st.session_state.last_click["lat"])
        st.session_state.pins.append({
            "id": st.session_state.next_id,
            "type": pin_type_label,
            "color": PIN_TYPES[pin_type_label],
            "name": pin_name.strip() if pin_name.strip() else pin_type_label,
            "x": x,
            "y": y,
        })
        st.session_state.next_id += 1
        st.rerun()

with right:
    st.subheader("Pins verwalten")

    if not st.session_state.pins:
        st.info("Noch keine Pins.")
    else:
        # Auswahl für Verschieben
        pin_ids = [p["id"] for p in st.session_state.pins]
        selected_id = st.selectbox("Pin auswählen", pin_ids)

        selected_pin = next(p for p in st.session_state.pins if p["id"] == selected_id)

        # Neue Position = letzter Klick
        if st.session_state.last_click:
            st.caption(f"Letzter Klick: x={st.session_state.last_click['lng']:.2f}, y={st.session_state.last_click['lat']:.2f}")
        else:
            st.caption("Noch kein Klick auf der Karte.")

        if st.button("➡️ Ausgewählten Pin auf letzten Klick verschieben", use_container_width=True) and st.session_state.last_click:
            selected_pin["x"] = float(st.session_state.last_click["lng"])
            selected_pin["y"] = float(st.session_state.last_click["lat"])
            st.rerun()

        st.divider()
        st.subheader("Liste (mit Raster)")

        # Tabelle bauen + Edit-Felder
        rows = []
        for p in st.session_state.pins:
            raster = xy_to_raster(p["x"], p["y"], W=W, H=H, invert_y=invert_y, fmt=raster_fmt)
            rows.append({
                "ID": p["id"],
                "Typ": p["type"],
                "Name": p["name"],
                "Raster": raster,
                "x": round(p["x"], 2),
                "y": round(p["y"], 2),
            })
        df = pd.DataFrame(rows).sort_values("ID")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Pin bearbeiten")
        # Name + Koordinaten editierbar (damit du fein verschieben kannst)
        selected_pin["name"] = st.text_input("Name", value=selected_pin["name"])
        selected_pin["type"] = st.selectbox("Typ", list(PIN_TYPES.keys()), index=list(PIN_TYPES.keys()).index(selected_pin["type"]))
        selected_pin["color"] = PIN_TYPES[selected_pin["type"]]

        selected_pin["x"] = st.number_input("x (0..100)", value=float(selected_pin["x"]), min_value=0.0, max_value=W, step=0.1)
        selected_pin["y"] = st.number_input(f"y (0..{H:.2f})", value=float(selected_pin["y"]), min_value=0.0, max_value=H, step=0.1)

        if st.button("🗑️ Ausgewählten Pin löschen", use_container_width=True):
            st.session_state.pins = [p for p in st.session_state.pins if p["id"] != selected_id]
            st.rerun()
