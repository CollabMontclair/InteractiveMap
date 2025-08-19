import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import random

# Function to add jitter to coordinates
def add_jitter(val, scale=0.001):
    return val + random.uniform(-scale, scale)

# Extract unique values helper function
def extract_unique(series):
    items = set()
    for entry in series.dropna():
        for item in entry.split(','):
            items.add(item.strip())
    return sorted(items)

# Load data
@st.cache_data
def load_data():
    df = pd.read_excel('Activities_cleaned.xlsx')
    df['lat_jittered'] = df['primary_site_lat'].apply(add_jitter)
    df['long_jittered'] = df['primary_site_long'].apply(add_jitter)
    return df

final_df = load_data()

# Extract filter options
faculty_list = extract_unique(final_df['faculty_partners'])
focus_area_list = extract_unique(final_df['focus_cleaned'])
activity_list = sorted(final_df['activity_name'].dropna().unique())
campus_partner_list = extract_unique(final_df['campus_partners'])

# Initialize session state for filters and tile if not present
if 'faculty_selected' not in st.session_state:
    st.session_state.faculty_selected = 'All'
if 'focus_selected' not in st.session_state:
    st.session_state.focus_selected = 'All'
if 'activity_selected' not in st.session_state:
    st.session_state.activity_selected = 'All'
if 'campus_selected' not in st.session_state:
    st.session_state.campus_selected = 'All'
if 'selected_tile' not in st.session_state:
    st.session_state.selected_tile = 'OpenStreetMap'

# Reset filters callback function
def reset_filters():
    st.session_state.faculty_selected = 'All'
    st.session_state.focus_selected = 'All'
    st.session_state.activity_selected = 'All'
    st.session_state.campus_selected = 'All'
    st.session_state.selected_tile = 'OpenStreetMap'

st.title("Interactive Map of Activities")
st.markdown("**- Count Shows Number of Activity locations**")

tile_options = {
    'OpenStreetMap': 'OpenStreetMap',
    'CartoDB Positron': 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    'CartoDB Dark Matter': 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    'Esri Satellite': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
}
tile_attribution = {
    'OpenStreetMap': '© OpenStreetMap contributors',
    'CartoDB Positron': '© OpenStreetMap contributors, © CARTO',
    'CartoDB Dark Matter': '© OpenStreetMap contributors, © CARTO',
    'Esri Satellite': 'Tiles © Esri, Maxar, Earthstar Geographics, and the GIS User Community'
}

# Sidebar filters bound to session_state keys
selected_faculty = st.sidebar.selectbox('Faculty:', ['All'] + faculty_list, key='faculty_selected')
selected_focus = st.sidebar.selectbox('Focus Area:', ['All'] + focus_area_list, key='focus_selected')
selected_activity = st.sidebar.selectbox('Activity:', ['All'] + activity_list, key='activity_selected')
selected_campus = st.sidebar.selectbox('Campus Partner:', ['All'] + campus_partner_list, key='campus_selected')
selected_tile = st.sidebar.selectbox('Map Style:', list(tile_options.keys()), key='selected_tile')

# Reset Filters button
st.sidebar.button("Reset Filters", on_click=reset_filters)

# Filter data function
def row_matches(row):
    faculty_names = [x.strip() for x in str(row['faculty_partners']).split(',')] if pd.notna(row['faculty_partners']) else []
    campus_names = [x.strip() for x in str(row['campus_partners']).split(',')] if pd.notna(row['campus_partners']) else []
    focus_cleaned_str = str(row['focus_cleaned']).lower() if pd.notna(row['focus_cleaned']) else ''

    faculty_match = (st.session_state.faculty_selected == 'All' or st.session_state.faculty_selected in faculty_names)
    focus_match = (st.session_state.focus_selected == 'All' or st.session_state.focus_selected.lower() in focus_cleaned_str)
    activity_match = (st.session_state.activity_selected == 'All' or st.session_state.activity_selected == row['activity_name'])
    campus_match = (st.session_state.campus_selected == 'All' or st.session_state.campus_selected in campus_names)

    return faculty_match and focus_match and activity_match and campus_match

filtered_df = final_df[final_df.apply(row_matches, axis=1)]

# Create map with selected tiles
m = folium.Map(
    location=[40.86468, -74.19692],
    zoom_start=9,
    control_scale=True,
    tiles=None
)

folium.TileLayer(
    tiles=tile_options[st.session_state.selected_tile],
    attr=tile_attribution[st.session_state.selected_tile],
    name=st.session_state.selected_tile,
    control=False
).add_to(m)

marker_cluster = MarkerCluster().add_to(m)

# Add markers
for _, row in filtered_df.iterrows():
    faculty_display = row['faculty_partners'] if pd.notna(row['faculty_partners']) else 'N/A'

    popup_html = f"""
    <div style="width: 300px; font-size: 13px;">
    <b>Activity: </b> <a href="{row['activity_url']}" target="_blank">{row['activity_name']}</a><br>
    <b>Faculty/Staff: </b> {faculty_display}<br>
    <b>Campus Partners:</b> {row['campus_partners']}<br>
    <b>Community Partners: </b> {row['community_organizations']}<br>
    <b>Primary Contact: </b> <a href="mailto:{row['primary_contact_email']}">{row['primary_contact_email']}</a>
    </div>
    """

    folium.CircleMarker(
        location=[row['lat_jittered'], row['long_jittered']],
        radius=7,
        color='red',
        fill=True,
        fill_opacity=0.8,
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=row['activity_name']
    ).add_to(marker_cluster)

# Display map
st_folium(m, width=700, height=500)
