import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Straßensperrungen 🚧", layout="wide")

st.title("🚧 Aktuelle Straßensperrungen und Umleitungen")
st.markdown("Region: Südlohn, Oeding, Borken, Vreden, Ahaus, Bocholt")

bbox = (51.89, 6.65, 51.97, 6.95)

query = f"""
[out:json][timeout:25];
(
  way["highway"]["access"="no"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
  way["highway"="construction"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
  way["traffic_sign"="detour"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
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

color_map = {
    "detour": "orange",
    "construction": "red",
    "access_no": "red"
}

def get_info(tags):
    if tags.get("traffic_sign") == "detour":
        return "Umleitung", color_map["detour"]
    elif tags.get("highway") == "construction":
        return "Baustelle", color_map["construction"]
    elif tags.get("highway") and tags.get("access") == "no":
        return "Sperrung", color_map["access_no"]
    else:
        return "Sperrung", "red"

list_sperrungen = []

for el in data['elements']:
    if el['type'] == 'way':
        tags = el.get("tags", {})
        typ, farbe = get_info(tags)

        if filter_option == "Nur Sperrungen" and typ == "Umleitung":
            continue
        if filter_option == "Nur Umleitungen" and typ != "Umleitung":
            continue

        coords = [nodes[nid] for nid in el['nodes'] if nid in nodes]
        if coords:
            folium.PolyLine(coords, color=farbe, weight=5, tooltip=typ).add_to(m)

            # Orts- und Straßenname
            ort = tags.get("addr:city") or tags.get("place") or "Unbekannter Ort"
            strasse = tags.get("name") or "Straßenname unbekannt"

            beschreibung = tags.get("description", "")
            header = f"### 🚧 {typ} in {ort} — {strasse}"
            if beschreibung:
                header += f"\n\n{beschreibung}"

            list_sperrungen.append(header)

st.markdown("### 📋 Liste der aktuellen Sperrungen und Umleitungen")
if list_sperrungen:
    for eintrag in list_sperrungen:
        st.markdown(eintrag)
else:
    st.info("Keine aktuellen Sperrungen oder Umleitungen gefunden.")

st.markdown("### 🗺️ Karte der Sperrungen und Umleitungen")
st_folium(m, width=1000, height=600)

st.markdown("---")
st.caption("Datenquelle: OpenStreetMap via Overpass API. Aktualität kann variieren.")
