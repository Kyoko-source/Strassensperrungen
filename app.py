import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Straßensperrungen", layout="wide")
st.title("🚧 Aktuelle Straßensperrungen")
st.subheader("Südlohn, Oeding, Borken, Vreden, Ahaus, Bocholt")

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

m = folium.Map(location=[51.93, 6.8], zoom_start=11)
nodes = {}
st.markdown("### 📋 Liste der aktuellen Sperrungen:")

for el in data['elements']:
    if el['type'] == 'node':
        nodes[el['id']] = (el['lat'], el['lon'])

sperrungen = 0
for el in data['elements']:
    if el['type'] == 'way':
        coords = [nodes[nid] for nid in el['nodes'] if nid in nodes]
        if coords:
            farbe = "orange" if el.get("tags", {}).get("traffic_sign") == "detour" else "red"
            tooltip = "Umleitung" if farbe == "orange" else "Sperrung oder Baustelle"
            folium.PolyLine(coords, color=farbe, weight=5, tooltip=tooltip).add_to(m)
            sperrungen += 1
            st.markdown(f"- 🚧 **{tooltip}** mit {len(coords)} Punkten")

if sperrungen == 0:
    st.info("Keine aktuellen Sperrungen oder Baustellen gefunden.")

st.markdown("### 🗺️ Karte der Sperrungen")
st_folium(m, width=1000, height=600)
