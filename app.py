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
    "RTW": {"leaflet_color": "red"},
    "KTW": {"leaflet_color": "orange"},
    "EVT (Fußtrupp)": {"leaflet_color": "blue"},
    "Sonstiges": {"leaflet_color": "black"},
}

# -----------------------------
# State
# -----------------------------
if "pins" not in st.session_state:
    # pin: {id, type, num, name, x, y}
    st.session_state.pins = []

if "next_id" not in st.session_state:
    st.session_state.next_id = 1

if "type_counters" not in st.session_state:
    # separate Zähler je Typ
    st.session_state.type_counters = {k: 1 for k in PIN_TYPES.keys()}

if "last_click" not in st.session_state:
    st.session_state.last_click = None  # {"lat":..,"lng":..}

# -----------------------------
# Sidebar: Setzen / Speichern
# -----------------------------
st.sidebar.header("Neuen Pin setzen")
selected_type = st.sidebar.radio("Typ", list(PIN_TYPES.keys()))
name_input = st.sidebar.text_input("Name (optional)", value="")

st.sidebar.caption("Karte anklicken → dann unten auf „Pin setzen“ drücken.")
st.sidebar.divider()

colA, colB = st.sidebar.columns(2)
if colA.button("Alle Pins löschen", use_container_width=True):
    st.session_state.pins = []
    st.session_state.next_id = 1
    st.session_state.type_counters = {k: 1 for k in PIN_TYPES.keys()}
    st.session_state.last_click = None
    st.rerun()

# Export / Import (damit es nach Neustart wieder da ist)
export_obj = {
    "pins": st.session_state.pins,
    "next_id": st.session_state.next_id,
    "type_counters": st.session_state.type_counters,
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
        tc = data.get("type_counters", {k: 1 for k in PIN_TYPES.keys()})
        # fehlende Typen ergänzen
        for k in PIN_TYPES.keys():
            tc.setdefault(k, 1)
        st.session_state.type_counters = tc
        st.sidebar.success("Import OK.")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Import fehlgeschlagen: {e}")

# -----------------------------
# Bild + Koordinatenraum
# -----------------------------
img = Image.open(IMAGE_PATH)
img_w, img_h = img.size

# Koordinatenraum: X = 0..100 (Breite), Y skaliert proportional (H)
W = 100.0
H = 100.0 * (img_h / img_w)
bounds = [[0, 0], [H, W]]  # [[y_min, x_min], [y_max, x_max]]

# -----------------------------
# Layout
# -----------------------------
left, right = st.columns([3.2, 1.3], gap="large")

with left:
    # Karte ohne Weltkarte
    m = folium.Map(
        location=[H / 2, W / 2],
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

    m.fit_bounds(bounds)

    # Karte möglichst „starr“
    m.options["dragging"] = False
    m.options["scrollWheelZoom"] = False
    m.options["doubleClickZoom"] = False
    m.options["touchZoom"] = False
    m.options["boxZoom"] = False
    m.options["keyboard"] = False
    m.options["maxBounds"] = bounds
    m.options["maxBoundsViscosity"] = 1.0

    # Pins zeichnen (Label = Typ + Nummer)
    for p in st.session_state.pins:
        label = f"{p['type']} {p['num']}"
        popup = f"{label}<br>{p.get('name','')}".strip()
        folium.Marker(
            location=[p["y"], p["x"]],
            popup=popup,
            tooltip=label,
            icon=folium.Icon(color=PIN_TYPES[p["type"]]["leaflet_color"])
        ).add_to(m)

    st.caption("1) Klick auf die Karte (Position wählen)  2) Dann „Pin setzen“ drücken.  |  Verschieben: rechts Pin wählen → neue Stelle klicken → verschieben.")
    res = st_folium(m, height=780, use_container_width=True)

    if res and res.get("last_clicked"):
        st.session_state.last_click = res["last_clicked"]  # {"lat":.., "lng":..}

    # Button zum Setzen
    set_disabled = st.session_state.last_click is None
    if st.button("📍 Pin setzen (an letzter Klick-Position)", disabled=set_disabled, use_container_width=True):
        x = float(st.session_state.last_click["lng"])
        y = float(st.session_state.last_click["lat"])

        num = int(st.session_state.type_counters[selected_type])
        st.session_state.type_counters[selected_type] = num + 1

        st.session_state.pins.append({
            "id": st.session_state.next_id,
            "type": selected_type,
            "num": num,
            "name": name_input.strip(),
            "x": x,
            "y": y,
        })
        st.session_state.next_id += 1
        st.rerun()

with right:
    st.subheader("Pins verwalten")

    if st.session_state.last_click:
        st.caption(f"Letzter Klick: x={st.session_state.last_click['lng']:.2f}, y={st.session_state.last_click['lat']:.2f}")
    else:
        st.caption("Noch kein Klick auf der Karte.")

    if not st.session_state.pins:
        st.info("Noch keine Pins gesetzt.")
    else:
        # Auswahl
        options = [
            f"ID {p['id']} – {p['type']} {p['num']} – {p.get('name','')}".strip(" –")
            for p in st.session_state.pins
        ]
        idx = st.selectbox("Pin auswählen", range(len(options)), format_func=lambda i: options[i])
        pin = st.session_state.pins[idx]

        st.divider()
        st.markdown("### Bearbeiten")

        pin["name"] = st.text_input("Name", value=pin.get("name", ""))

        # Typwechsel optional (Nummer bleibt wie sie ist; wenn du willst, kann ich es auch neu nummerieren)
        new_type = st.selectbox("Typ", list(PIN_TYPES.keys()), index=list(PIN_TYPES.keys()).index(pin["type"]))
        pin["type"] = new_type

        pin["x"] = st.number_input("x (0..100)", value=float(pin["x"]), min_value=0.0, max_value=W, step=0.1)
        pin["y"] = st.number_input(f"y (0..{H:.2f})", value=float(pin["y"]), min_value=0.0, max_value=H, step=0.1)

        col1, col2 = st.columns(2)
        if col1.button("➡️ Auf letzten Klick verschieben", use_container_width=True, disabled=st.session_state.last_click is None):
            pin["x"] = float(st.session_state.last_click["lng"])
            pin["y"] = float(st.session_state.last_click["lat"])
            st.rerun()

        if col2.button("🗑️ Löschen", use_container_width=True):
            st.session_state.pins.pop(idx)
            st.rerun()

        st.divider()
        st.markdown("### Liste (mit x/y)")
        rows = []
        for p in st.session_state.pins:
            rows.append({
                "Typ": p["type"],
                "Nr": p["num"],
                "Name": p.get("name", ""),
                "x": round(p["x"], 2),
                "y": round(p["y"], 2),
                "ID": p["id"],
            })
        df = pd.DataFrame(rows).sort_values(["Typ", "Nr", "ID"])
        st.dataframe(df, use_container_width=True, hide_index=True)
