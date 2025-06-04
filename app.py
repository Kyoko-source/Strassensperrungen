import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Straßensperrungen 🚧", layout="wide")

st.title("🚧 Aktuelle Straßensperrungen und Umleitungen")
st.markdown("Region: Südlohn, Oeding, Borken, Vreden, Ahaus, Bocholt")

# Größere Bounding Box für mehr Daten
bbox = (51.85, 6.60, 52.00, 7.00)

query = f"""
[out:json][timeout:25];
(
  way["highway"]["access"="no"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
  way["highway"="construction"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
  way["traffic_sign"="detour"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
  way["barrier"="blocked"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
  way["access"="no"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
);
out body;
>;
out skel qt;
"""

response = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})
if response.status_code != 200:
    st.error("Fehler beim Laden der Sperrungen.")
    st.stop()

data = response.json()

nodes = {}
for el in data['elements']:
    if el['type'] == 'node':
        nodes[el['id']] = (el['lat'], el['lon'])

filter_option = st.radio("Anzeigen von:", ("Alle", "Nur Sperrungen", "Nur Umleitungen"))

m = folium.Map(location=[51.93, 6.8], zoom_start=11)

def get_info(tags):
    if tags.get("traffic_sign") == "detour":
        return "Umleitung", "orange"
    elif tags.get("highway") == "construction":
        return "Baustelle", "red"
    elif tags.get("barrier") == "blocked":
        return "Sperrung (Barriere)", "darkred"
    elif tags.get("access") == "no":
        return "Sperrung", "red"
    else:
        return None, None

# Orte als Filter
erlaubte_orte = {"Südlohn", "Oeding", "Borken", "Bocholt", "Vreden", "Ahaus"}

sperrungen_pro_ort = {ort: [] for ort in erlaubte_orte}

debug_wege = []

for el in data['elements']:
    if el['type'] == 'way':
        tags = el.get("tags", {})
        typ, farbe = get_info(tags)

        if typ is None:
            continue

        if filter_option == "Nur Sperrungen" and "Umleitung" in typ:
            continue
        if filter_option == "Nur Umleitungen" and typ != "Umleitung":
            continue

        ort = tags.get("addr:city") or tags.get("place") or "Unbekannter Ort"

        coords = [nodes[nid] for nid in el['nodes'] if nid in nodes]
        if coords:
            folium.PolyLine(coords, color=farbe, weight=5, tooltip=typ).add_to(m)

            strasse = tags.get("name") or "Straßenname unbekannt"
            beschreibung = tags.get("description", "")
            text = f"**{typ}** — {strasse}"
            if beschreibung:
                text += f"\n\n{beschreibung}"

            if ort in erlaubte_orte:
                sperrungen_pro_ort[ort].append(text)

            debug_wege.append({
                "id": el.get("id"),
                "typ": typ,
                "ort": ort,
                "strasse": strasse,
                "beschreibung": beschreibung,
                "tags": tags
            })

st.markdown("## 📋 Aktuelle Sperrungen und Umleitungen nach Ort")
keine_sperrungen_gefunden = True
for ort, sperrungen in sperrungen_pro_ort.items():
    if sperrungen:
        keine_sperrungen_gefunden = False
        with st.expander(f"📍 {ort} ({len(sperrungen)})"):
            for eintrag in sperrungen:
                st.markdown(f"- {eintrag}")

if keine_sperrungen_gefunden:
    st.info("Keine aktuellen Sperrungen oder Umleitungen gefunden.")

st.markdown("## 🗺️ Karte der Sperrungen und Umleitungen")
st_folium(m, width=1000, height=600)

with st.expander("🛠️ Debug: Alle gefundenen Wege (inkl. Ort & Tags)"):
    st.write(f"Anzahl Wege insgesamt: {len(debug_wege)}")
    for weg in debug_wege:
        st.markdown(f"**ID:** {weg['id']} — **Typ:** {weg['typ']} — **Ort:** {weg['ort']} — **Straße:** {weg['strasse']}")
        st.write("Tags:", weg['tags'])

st.markdown("---")
st.caption("Datenquelle: OpenStreetMap via Overpass API. Aktualität kann variieren.")
