import streamlit as st
import leafmap.foliumap as leafmap
import json
import random
from io import StringIO
import pandas as pd 
from matplotlib import colormaps


API_URL = 'https://a55kqhh6wf.execute-api.us-east-1.amazonaws.com/default/rasterList'

@st.cache_data
def get_raster_list():
    response = requests.get(API_URL)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch raster list")
        return []

def get_random_color():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def get_colors(num_colors):
    listColors = list(colormaps)
    return listColors[:num_colors]


rasters = get_raster_list()
rasters = json.loads(rasters['body'])


rasters_url = {}
raster_selections = {}
colors = {}
variables = {}

def set_checkbox_text_color(raster, color):
    st.markdown(
        f"""
        <style>
        div[aria-checked="false"] > label[data-testid="stMarkdownContainer"] > div {{
            color: {color};
        }}
        div[aria-checked="true"] > label[data-testid="stMarkdownContainer"] > div {{
            color: {color};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

with st.sidebar.expander("Rasters", expanded=False):
    for i, raster in enumerate(rasters):
        num_colors = len(rasters) 
        colormap = get_colors(num_colors)
        colors[raster] = colormap[i]
        rasters_url[raster] = rasters[raster]
        st.markdown(
        f"""
        <style>
        div[aria-checked="false"] > label[data-testid="stMarkdownContainer"] > div {{
            color: {colors[raster]};
        }}
        div[aria-checked="true"] > label[data-testid="stMarkdownContainer"] > div {{
            color: {colors[raster]};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )   
        if raster == 'final_df.csv':
            raster_selections[raster] = st.checkbox(f"OCR France", value=False)
        else:   
            raster_selections[raster] = st.checkbox(f"{raster}", value=False)


m = leafmap.Map(center=(46.603354, 1.888334), zoom=6)

m.add_basemap('OpenStreetMap')
m.add_basemap('HYBRID')

for raster, selected in raster_selections.items():
    if selected and raster != 'final_df.csv':
        raster_url = rasters_url[raster]
        m.add_cog_layer(raster_url, name=raster, nodata=-9999, palette=colors[raster])
    if selected and raster == 'final_df.csv': 
        geo_df = pd.read_csv('final_geo_df.csv')
        for lat, lon, city in zip(geo_df['latitude'], geo_df['longitude'], geo_df['hydrogen']):
            if lat and lon:
                m.add_marker([lat, lon], popup=city)

m.to_streamlit(height=900)


