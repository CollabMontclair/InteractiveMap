import streamlit as st
import folium
import requests
import pandas as pd
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# --- Load NJ counties (FIPS = '34') GeoJSON ---
url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
geojson_data = requests.get(url).json()
nj_features = [f for f in geojson_data['features'] if f['properties']['STATE'] == '34']

nj_polygons = [shape(f['geometry']) for f in nj_features]
nj_boundary = MultiPolygon(nj_polygons)

minx, miny, maxx, maxy = nj_boundary.bounds
center_lat = (miny + maxy) / 2
center_lon = (minx + maxx) / 2

# --- Load actual Excel data from the same directory ---
try:
    final_df = pd.read_excel("Acitivities_cleaned.xlsx")
except Exception as e:
    st.error(f"Error loading Excel file: {e}")
    st.stop()

# --- Helper function to extract unique items from comma-separated strings in a series ---
def extract_unique(series):
    items = set()
    for entry in series.dropna():
        for item in entry.split(','):
            items.add(item.strip())
    return sorted(items)

faculty_list = extract_unique(final_df['faculty_partners'])
focus_area_list = extract_unique(final_df['focus_cleaned'])
activity_list = sorted(final_df['activity_name'].dropna().unique())
campus_partner_list = extract_unique(final_df['campus_partners'])

# --- Streamlit widgets ---
faculty_dropdown = st.selectbox('Faculty:', ['All'] + faculty_list)
focus_area_select = st.multiselect('Focus Areas:', focus_area_list)
activity_dropdown = st.selectbox('Activity:', ['All'] + activity_list)
campus_dropdown = st.selectbox('Campus:', ['All'] + campus_partner_list)

# --- Filter markers ---
filtered_points = []

for _, row in final_df.iterrows():
    point = Point(row['long_jittered'], row['lat_jittered'])
    if not nj_boundary.contains(point):
        continue  # Skip points outside NJ

    faculty_names = [f.strip() for f in str(row['faculty_partners']).split(',')] if pd.notna(row['faculty_partners']) else []
    focus_values = [f.strip() for f in str(row['focus_cleaned']).split(',')] if pd.notna(row['focus_cleaned']) else []
    campus_names = [c.strip() for c in str(row['campus_partners']).split(',')] if pd.notna(row['campus_partners']) else []

    if ((faculty_dropdown == 'All' or faculty_dropdown in faculty_names) and
        (not focus_area_select or all(f in focus_values for f in focus_area_select)) and
        (activity_dropdown == 'All' or activity_dropdown == row['activity_name']) and
        (campus_dropdown == 'All' or campus_dropdown in campus_names)):
        filtered_points.append((point, row))

total_markers = len(filtered_points)

# Count markers per county
county_marker_counts = {f['properties']['NAME']: 0 for f in nj_features}
for point, _ in filtered_points:
    for feature in nj_features:
        county_name = feature['properties']['NAME']
        geom = shape(feature['geometry'])
        if geom.contains(point):
            county_marker_counts[county_name] += 1
            break

# --- Create Folium map ---
m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles=None)

# Add tile layer without labels (clean background)
folium.TileLayer(
    tiles='https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png',
    attr='© OpenStreetMap contributors, © CARTO',
    name='CartoDB Positron No Labels',
    control=False
).add_to(m)

# Add NJ counties borders
folium.GeoJson(
    {
        "type": "FeatureCollection",
        "features": nj_features
    },
    style_function=lambda x: {
        "fillColor": "#ffffff00",  # transparent fill
        "color": "blue",
        "weight": 2,
    }
).add_to(m)

# Add county labels with percentage if percentage > 0
for feature in nj_features:
    county_name = feature['properties']['NAME']
    geom = shape(feature['geometry'])
    centroid = geom.centroid
    count = county_marker_counts.get(county_name, 0)
    percentage = (count / total_markers * 100) if total_markers > 0 else 0
    if percentage > 0:
        label_html = f"""
        <div style="font-size: 12px; font-weight: bold; color: blue;">
            {county_name}<br>
            <span style="font-weight: normal; color: black;">{percentage:.1f}%</span>
        </div>
        """
        folium.map.Marker(
            [centroid.y, centroid.x],
            icon=folium.DivIcon(html=label_html)
        ).add_to(m)

# Mask outside NJ with white polygon
world = Polygon([
    (-180, -90),
    (-180, 90),
    (180, 90),
    (180, -90)
])
holes = [poly.exterior.coords[:] for poly in nj_boundary.geoms]
mask_polygon = Polygon(world.exterior.coords, holes=holes)
folium.GeoJson(
    data=mask_polygon.__geo_interface__,
    style_function=lambda x: {
        'fillColor': 'white',
        'color': 'white',
        'fillOpacity': 1,
        'weight': 0
    }
).add_to(m)

# Add marker cluster for filtered points
marker_cluster = MarkerCluster().add_to(m)

for _, row in filtered_points:
    popup_html = f"""
    <div style="width: 300px; font-size: 13px;">
    <b>Activity:</b> <a href="{row['activity_url']}" target="_blank">{row['activity_name']}</a><br>
    <b>Faculty:</b> {row['faculty_partners']}<br>
    <b>Campus Partners:</b> {row['campus_partners']}<br>
    <b>Community Partners:</b> {row['community_organizations']}<br>
    <b>Contact:</b> <a href="mailto:{row['primary_contact_email']}">{row['primary_contact_email']}</a>
    </div>
    """
    folium.CircleMarker(
        location=[row['lat_jittered'], row['long_jittered']],
        radius=7,
        color='crimson',
        fill=True,
        fill_opacity=0.8,
        popup=popup_html,
        tooltip=row['activity_name']
    ).add_to(marker_cluster)

# Render map in Streamlit
st_data = st_folium(m, width=700, height=600)
