import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import requests
import pandas as pd
from shapely.geometry import shape, Point, Polygon, MultiPolygon

# --- Load NJ counties ---
@st.cache_data
def load_nj_boundary():
    url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    geojson_data = requests.get(url).json()
    nj_features = [f for f in geojson_data['features'] if f['properties']['STATE'] == '34']
    nj_polygons = [shape(f['geometry']) for f in nj_features]
    boundary = MultiPolygon(nj_polygons)
    return geojson_data, nj_features, boundary

geojson_data, nj_features, nj_boundary = load_nj_boundary()
minx, miny, maxx, maxy = nj_boundary.bounds
center_lat = (miny + maxy) / 2
center_lon = (minx + maxx) / 2

# --- Load your dataset ---
@st.cache_data
def load_data():
    return pd.read_excel("Acitivities_cleaned.xlsx")

final_df = load_data()

# --- Helper to extract unique items from comma-separated strings ---
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

# --- Sidebar Filters ---
st.sidebar.title("Filter Activities")

selected_faculty = st.sidebar.selectbox("Faculty Partner", ["All"] + faculty_list)
selected_focus_areas = st.sidebar.multiselect("Focus Areas", focus_area_list)
selected_activity = st.sidebar.selectbox("Activity Name", ["All"] + activity_list)
selected_campus = st.sidebar.selectbox("Campus Partner", ["All"] + campus_partner_list)

# --- Filter Logic ---
filtered_points = []

for _, row in final_df.iterrows():
    if pd.isna(row['lat_jittered']) or pd.isna(row['long_jittered']):
        continue
    point = Point(row['long_jittered'], row['lat_jittered'])
    if not nj_boundary.contains(point):
        continue

    faculty_names = [f.strip() for f in str(row['faculty_partners']).split(',')] if pd.notna(row['faculty_partners']) else []
    focus_values = [f.strip() for f in str(row['focus_cleaned']).split(',')] if pd.notna(row['focus_cleaned']) else []
    campus_names = [c.strip() for c in str(row['campus_partners']).split(',')] if pd.notna(row['campus_partners']) else []

    if ((selected_faculty == 'All' or selected_faculty in faculty_names) and
        (not selected_focus_areas or all(f in focus_values for f in selected_focus_areas)) and
        (selected_activity == 'All' or selected_activity == row['activity_name']) and
        (selected_campus == 'All' or selected_campus in campus_names)):
        filtered_points.append((point, row))

total_markers = len(filtered_points)

# --- Count markers per county ---
county_marker_counts = {f['properties']['NAME']: 0 for f in nj_features}
for point, _ in filtered_points:
    for feature in nj_features:
        geom = shape(feature['geometry'])
        if geom.contains(point):
            county_marker_counts[feature['properties']['NAME']] += 1
            break

# --- Build Folium Map ---
m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles=None)

folium.TileLayer(
    tiles='https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png',
    attr='© OpenStreetMap contributors, © CARTO',
    name='CartoDB Positron No Labels',
    control=False
).add_to(m)

m.fit_bounds([[miny, minx], [maxy, maxx]])
m.options['maxBounds'] = [[miny, minx], [maxy, maxx]]

# --- Add NJ County Borders ---
folium.GeoJson(
    {"type": "FeatureCollection", "features": nj_features},
    style_function=lambda x: {
        "fillColor": "#ffffff00",
        "color": "blue",
        "weight": 2,
    }
).add_to(m)

# --- Add County Labels with Percentages ---
for feature in nj_features:
    county_name = feature['properties']['NAME']
    geom = shape(feature['geometry'])
    centroid = geom.centroid
    count = county_marker_counts[county_name]
    percentage = (count / total_markers * 100) if total_markers > 0 else 0
    if percentage > 0:
        label_html = f"""
        <div style="font-size: 12px; font-weight: bold; color: blue;">
            {county_name}<br>
            <span style="font-weight: normal; color: black;">{percentage:.1f}%</span>
        </div>
        """
        folium.Marker(
            location=[centroid.y, centroid.x],
            icon=folium.DivIcon(html=label_html)
        ).add_to(m)

# --- Mask Area Outside NJ ---
world = Polygon([(-180, -90), (-180, 90), (180, 90), (180, -90)])
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

# --- Add Marker Cluster ---
marker_cluster = MarkerCluster().add_to(m)

# --- Add Markers ---
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

# --- Display Final Map ---
st.title("New Jersey Collaboratory Activities Map")
st.markdown("This interactive map shows campus and community engagement activities across NJ.")
st_folium(m, width=1100, height=600)
