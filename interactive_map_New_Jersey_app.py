import streamlit as st
import pandas as pd
import folium
import requests
import random
from shapely.geometry import shape, Point, MultiPolygon, Polygon
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

# Load NJ counties GeoJSON
@st.cache_data
def load_nj_counties():
    url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    geojson = requests.get(url).json()
    nj_features = [f for f in geojson['features'] if f['properties']['STATE'] == '34']
    return nj_features

# Load Excel data
@st.cache_data
def load_data():
    df = pd.read_excel("Activities_cleaned.xlsx", engine="openpyxl")
    df['lat_jittered'] = df['primary_site_lat'].apply(lambda x: x + random.uniform(-0.001, 0.001))
    df['long_jittered'] = df['primary_site_long'].apply(lambda x: x + random.uniform(-0.001, 0.001))
    return df

# Generate joyful colors
@st.cache_data
def joyful_color_palette(n):
    if n == 0:
        return []
    step = max(1, int(360 / n))
    hues = list(range(0, 360, step))
    random.shuffle(hues)
    colors = [f"hsl({h}, 65%, 70%)" for h in hues]
    while len(colors) < n:
        colors.append(f"hsl({random.randint(0,359)}, 65%, 70%)")
    return colors[:n]

def reset_filters():
    st.session_state.faculty_selected = 'All'
    st.session_state.focus_selected = 'All'
    st.session_state.activity_selected = 'All'
    st.session_state.campus_selected = 'All'

def main():
    st.title("Interactive Map of Activities in NJ")
    st.markdown("**-  Count shows number of locations**")

    nj_features = load_nj_counties()
    df = load_data()

    nj_polygons = [shape(f['geometry']) for f in nj_features]
    nj_boundary = MultiPolygon(nj_polygons)
    minx, miny, maxx, maxy = nj_boundary.bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2

    county_names = sorted({f['properties']['NAME'] for f in nj_features})
    county_color_map = dict(zip(county_names, joyful_color_palette(len(county_names))))

    # Filter option lists
    faculty_list = sorted(set(
        x.strip() for vals in df['faculty_partners'].dropna() for x in vals.split(',')
    ))
    focus_area_list = sorted(set(
        x.strip() for vals in df['focus_cleaned'].dropna() for x in vals.split(',')
    ))
    activity_list = sorted(df['activity_name'].dropna().unique())
    campus_partner_list = sorted(set(
        x.strip() for vals in df['campus_partners'].dropna() for x in vals.split(',')
    ))

    # Initialize session state defaults
    for key in ['faculty_selected', 'focus_selected', 'activity_selected', 'campus_selected']:
        if key not in st.session_state:
            st.session_state[key] = 'All'

    st.sidebar.header("Filters")

    # Selectboxes
    faculty_selected = st.sidebar.selectbox(
        "Faculty:", options=['All'] + faculty_list, key='faculty_selected'
    )
    focus_selected = st.sidebar.selectbox(
        "Focus Area:", options=['All'] + focus_area_list, key='focus_selected'
    )
    activity_selected = st.sidebar.selectbox(
        "Activity:", options=['All'] + activity_list, key='activity_selected'
    )
    campus_selected = st.sidebar.selectbox(
        "Campus Partner:", options=['All'] + campus_partner_list, key='campus_selected'
    )

    # Reset button (below filters)
    st.sidebar.button("Reset Filters", on_click=reset_filters)

    # Folium Map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles=None)
    folium.TileLayer(
        tiles='https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png',
        attr='© OpenStreetMap contributors, © CARTO',
        control=False
    ).add_to(m)

    for feature in nj_features:
        county = feature['properties']['NAME']
        color = county_color_map.get(county, '#ddd')
        folium.GeoJson(
            feature['geometry'],
            style_function=lambda f, color=color: {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.6,
            }
        ).add_to(m)

    for feature in nj_features:
        county = feature['properties']['NAME']
        geom = shape(feature['geometry'])
        centroid = geom.centroid
        folium.Marker(
            [centroid.y, centroid.x],
            icon=folium.DivIcon(html=f'<div style="font-size:13px; font-weight:bold; color:black; text-shadow:1px 1px white;">{county}</div>')
        ).add_to(m)

    world = Polygon([(-180, -90), (-180, 90), (180, 90), (180, -90)])
    holes = [poly.exterior.coords[:] for poly in nj_polygons if poly.exterior]
    mask = Polygon(world.exterior.coords, holes=holes)
    folium.GeoJson(
        data=mask.__geo_interface__,
        style_function=lambda x: {
            'fillColor': 'white',
            'fillOpacity': 1,
            'weight': 0,
            'color': 'white'
        }
    ).add_to(m)

    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():
        lat = row['lat_jittered']
        lon = row['long_jittered']
        pt = Point(lon, lat)
        if not nj_boundary.contains(pt):
            continue

        faculties = [x.strip() for x in str(row['faculty_partners']).split(',')] if pd.notna(row['faculty_partners']) else []
        focuses = [x.strip() for x in str(row['focus_cleaned']).split(',')] if pd.notna(row['focus_cleaned']) else []
        campuses = [x.strip() for x in str(row['campus_partners']).split(',')] if pd.notna(row['campus_partners']) else []

        if ((faculty_selected == 'All' or faculty_selected in faculties) and
            (focus_selected == 'All' or focus_selected in focuses) and
            (activity_selected == 'All' or activity_selected == row['activity_name']) and
            (campus_selected == 'All' or campus_selected in campuses)):

            popup_html = f"""
            <div style="width:300px; font-size:13px;">
                <b>Activity:</b> <a href="{row['activity_url']}" target="_blank">{row['activity_name']}</a><br>
                <b>Faculty:</b> {row['faculty_partners']}<br>
                <b>Campus:</b> {row['campus_partners']}<br>
                <b>Contact:</b> <a href="mailto:{row['primary_contact_email']}">{row['primary_contact_email']}</a>
            </div>
            """

            folium.CircleMarker(
                location=[lat, lon],
                radius=7,
                color='crimson',
                fill=True,
                fill_opacity=0.8,
                popup=popup_html,
                tooltip=row['activity_name']
            ).add_to(marker_cluster)

    # Show map directly without extra borders or containers
    st_folium(m, width=900, height=600)

if __name__ == "__main__":
    main()
