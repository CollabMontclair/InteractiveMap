import streamlit as st
import pandas as pd
import folium
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import requests

# --- Load NJ counties GeoJSON (FIPS = '34') ---
@st.cache_data
def load_nj_boundary():
    url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    geojson_data = requests.get(url).json()
    nj_features = [f for f in geojson_data['features'] if f['properties']['STATE'] == '34']
    nj_polygons = [shape(f['geometry']) for f in nj_features]
    return nj_features, MultiPolygon(nj_polygons)

nj_features, nj_boundary = load_nj_boundary()
center_lat = (nj_boundary.bounds[1] + nj_boundary.bounds[3]) / 2
center_lon = (nj_boundary.bounds[0] + nj_boundary.bounds[2]) / 2

# --- Load Excel data ---
@st.cache_data
def load_data():
    return pd.read_excel("Activities_cleaned.xlsx")

final_df = pd.read_excel("Activities_cleaned")

# --- Extract unique focus areas ---
def get_unique_focus_areas(series):
    focus_set = set()
    for entry in series.dropna():
        focus_set.update([f.strip() for f in entry.split(",")])
    return sorted(focus_set)

focus_areas = get_unique_focus_areas(final_df["focus_cleaned"])

# --- Streamlit UI ---
st.title("NJ Activities Map by Focus Area")
selected_focus_areas = st.multiselect("Select Focus Area(s):", focus_areas)

# --- Filter points ---
filtered_rows = []
for _, row in df.iterrows():
    if not pd.notna(row['lat_jittered']) or not pd.notna(row['long_jittered']):
        continue
    point = Point(row['long_jittered'], row['lat_jittered'])
    if not nj_boundary.contains(point):
        continue

    focus_values = [f.strip() for f in str(row['focus_cleaned']).split(',')] if pd.notna(row['focus_cleaned']) else []
    if not selected_focus_areas or all(f in focus_values for f in selected_focus_areas):
        filtered_rows.append(row)

# --- Map setup ---
m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles=None)
folium.TileLayer(
    tiles='https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png',
    attr='© OpenStreetMap contributors, © CARTO',
    name='CartoDB Positron No Labels',
    control=False
).add_to(m)

folium.GeoJson(
    {"type": "FeatureCollection", "features": nj_features},
    style_function=lambda x: {"fillColor": "#ffffff00", "color": "blue", "weight": 2},
).add_to(m)

marker_cluster = MarkerCluster().add_to(m)

for row in filtered_rows:
    popup = f"""
    <b>Activity:</b> <a href="{row['activity_url']}" target="_blank">{row['activity_name']}</a><br>
    <b>Faculty:</b> {row['faculty_partners']}<br>
    <b>Focus:</b> {row['focus_cleaned']}
    """
    folium.CircleMarker(
        location=[row['lat_jittered'], row['long_jittered']],
        radius=6,
        color='crimson',
        fill=True,
        fill_opacity=0.8,
        popup=popup,
        tooltip=row['activity_name']
    ).add_to(marker_cluster)

st_data = st_folium(m, width=700, height=600)
