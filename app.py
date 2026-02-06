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
/* Layout breathing room */
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px; }

/* Headline */
h1, h2, h3 { letter-spacing: -0.02em; }

/* Sidebar look */
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0b1220 0%, #0f1a2e 100%); }
section[data-testid="stSidebar"] * { color: #e9eefc !important; }
section[data-testid="stSidebar"] .stRadio label, 
section[data-testid="stSidebar"] .stTextInput label,
section[data-testid="stSidebar"] .stButton button { color: #e9eefc !important; }

/* Buttons */
.stButton button {
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.12);
  padding: 0.62rem 0.9rem;
  font-weight: 600;
}
.stButton button:hover { border-color: rgba(255,255,255,0.22); transform: translateY(-1px); }

/* Card components */
.card {
  border-radius: 18px;
  padding: 14px 16px;
  background: linear-gradient(135deg, rgba(13,110,253,0.08), rgba(110,66,193,0.08));
  border: 1px solid rgba(15, 23, 42, 0.12);
  box-shadow: 0 10px 30px rgba(2, 6, 23, 0.06);
}
.card-title { font-size: 0.9rem; opacity: 0.72; margin-bottom: 6px; }
.card-value { font-size: 1.35rem; font-weight: 750; }
.muted { opacity: 0.72; }

/* Pin pill */
.pill { display:inline-block; padding: 6px 10px; border-radius: 999px; font-weight: 650; font-size: 0.85rem; }
.pill-red { background: rgba(220,53,69,0.12); color: #b42318; border: 1px solid rgba(220,53,69,0.25); }
.pill-orange { background: rgba(253,126,20,0.12); color: #b54708; border: 1px solid rgba(253,126,20,0.25); }
.pill-blue { background: rgba(13,110,253,0.12); color: #175cd3; border: 1px solid rgba(13,110,253,0.25); }
.pill-black { background: rgba(33,37,41,0.10); color: #111827; border: 1px solid rgba(33,37,41,0.18); }

/* Delete button hint */
.warn {
  border-left: 4px solid #dc3545;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(220,53,69,0.06);
}

/* Table tweaks */
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid rgba(15, 23, 42, 0.10); }
</style>
""",
    unsafe_allow_html=True,
)

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

pin_type = st.sidebar.radio("Pin-Typ", list(PIN_TYPES.keys()))
pin_name = st.sidebar.text_input("Name", value="", placeholder="z.B. RTW Heiden")

# Nice type indicator
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

colS1, colS2 = st.sidebar.columns(2)
if colS1.button("🧹 Alles löschen", use_container_width=True):
    st.session_state.pins = []
    st.session_state.next_pin_id = 1
    st.session_state.selected_pin_id = None
    st.rerun()

# -----------------------------
# KPIs
# -----------------------------
total = len(st.session_state.pins)
last_pin = st.session_state.pins[-1] if total else None

k1, k2, k3 = st.columns(3)
k1.markdown(f"""<div class="card">
  <div class="card-title">Pins gesamt</div>
  <div class="card-value">{total}</div>
  <div class="muted">Aktueller Stand</div>
</div>""", unsafe_allow_html=True)

k2.markdown(f"""<div class="card">
  <div class="card-title">Letzter Pin</div>
  <div class="card-value">{("ID " + str(last_pin["id"])) if last_pin else "—"}</div>
  <div class="muted">{last_pin["created_at"] if last_pin else "Noch keiner gesetzt"}</div>
</div>""", unsafe_allow_html=True)

k3.markdown(f"""<div class="card">
  <div class="card-title">Auswahl</div>
  <div class="card-value">{("ID " + str(st.session_state.selected_pin_id)) if st.session_state.selected_pin_id else "—"}</div>
  <div class="muted">Klick auf Marker oder Auswahl rechts</div>
</div>""", unsafe_allow_html=True)

st.write("")

# -----------------------------
# Image / Bounds
# -----------------------------
img = Image.open(IMAGE_PATH)
w, h = img.size

H = 100 * (h / w)
bounds = [[0, 0], [H, 100]]

# -----------------------------
# Layout
# -----------------------------
left, right = st.columns([3.2, 1.3], gap="large")

with left:
    st.subheader("🗺️ Karte")
    st.caption("Klick auf die Karte setzt einen Pin. Marker anklicken → Details rechts. (Drag ist optisch möglich, aber Position wird nicht zuverlässig gespeichert.)")

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

    # Karte fixieren
    m.options["dragging"] = False
    m.options["scrollWheelZoom"] = False
    m.options["doubleClickZoom"] = False
    m.options["touchZoom"] = False
    m.options["boxZoom"] = False
    m.options["keyboard"] = False
    m.options["zoomSnap"] = 0
    m.options["maxBounds"] = bounds
    m.options["maxBoundsViscosity"] = 1.0

    # Pins rendern
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
            draggable=True,  # optisch; Speicherung der Drag-Position nicht zuverlässig
            icon=folium.Icon(color=p["color"])
        ).add_to(m)

    res = st_folium(m, height=760, use_container_width=True)

    # Klick auf Karte -> neuen Pin hinzufügen
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

    # Klick auf Marker -> Pin auswählen (wenn streamlit-folium es liefert)
    clicked_popup = None
    if res:
        clicked_popup = res.get("last_object_clicked_popup") or res.get("last_object_clicked_tooltip")

    if isinstance(clicked_popup, str):
        m_id = re.search(r"ID:\s*</b>\s*(\d+)|ID:\s*(\d+)", clicked_popup)
        if m_id:
            pid = int(m_id.group(1) or m_id.group(2))
            st.session_state.selected_pin_id = pid

with right:
    st.subheader("📌 Pin-Details")

    if not st.session_state.pins:
        st.info("Noch keine Pins gesetzt.")
    else:
        ids = [p["id"] for p in st.session_state.pins]
        if st.session_state.selected_pin_id not in ids:
            st.session_state.selected_pin_id = ids[0]

        sel = st.selectbox("Pin auswählen", ids, index=ids.index(st.session_state.selected_pin_id))
        st.session_state.selected_pin_id = sel

        pin = next(p for p in st.session_state.pins if p["id"] == sel)

        pill = f'<span class="pill {color_to_pill(pin["color"])}">{pin["type"]}</span>'
        st.markdown(
            f"""<div class="card">
            <div class="card-title">Ausgewählter Pin</div>
            <div class="card-value">ID {pin["id"]} &nbsp; {pill}</div>
            <div class="muted" style="margin-top:10px;">
              <b>Name:</b> {pin["name"]}<br>
              <b>Zeit:</b> {pin["created_at"]}<br>
              <b>Koordinaten:</b> x={pin["x"]:.2f}, y={pin["y"]:.2f}
            </div>
            </div>""",
            unsafe_allow_html=True
        )

        st.write("")
        st.markdown("### ✏️ Bearbeiten")
        pin["name"] = st.text_input("Name ändern", value=pin["name"])
        new_type = st.selectbox("Typ ändern", list(PIN_TYPES.keys()), index=list(PIN_TYPES.keys()).index(pin["type"]))
        pin["type"] = new_type
        pin["color"] = PIN_TYPES[new_type]

        # Delete + renumber
        st.write("")
        st.markdown('<div class="warn"><b>Achtung:</b> Löschen nummeriert alle Pins neu (1,2,3...).</div>', unsafe_allow_html=True)
        if st.button("🗑️ Diesen Pin löschen", use_container_width=True):
            st.session_state.pins = [p for p in st.session_state.pins if p["id"] != sel]

            # Neu durchnummerieren
            new_id = 1
            for p in st.session_state.pins:
                p["id"] = new_id
                new_id += 1

            st.session_state.next_pin_id = new_id
            st.session_state.selected_pin_id = None
            st.rerun()

st.divider()
st.subheader("📋 Pin-Liste")

if st.session_state.pins:
    df = pd.DataFrame(st.session_state.pins)
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
