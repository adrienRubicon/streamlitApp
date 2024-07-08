import streamlit as st
import leafmap.foliumap as leafmap
import json
import random
import requests
from matplotlib import colormaps
from scipy.ndimage import distance_transform_edt
import numpy as np
import rasterio
from io import BytesIO



API_URL = 'https://a55kqhh6wf.execute-api.us-east-1.amazonaws.com/default/rasterList'
API_URL2 = 'https://qbfas799rl.execute-api.us-east-1.amazonaws.com/default/getRaster'

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

def calculate_proximity_layer(selected_rasters_urls):
    raster_infos = []
    k_H = 0.01  # Decay hydrocarburesFoss
    k_M = 0.01  # Decay minerals
    w_H = 0.5   # Weight hydrocarburesFoss
    w_M = 0.5   # Weight minerals

    for url in selected_rasters_urls:
        response = requests.get(url)
        response.raise_for_status()
        
        with rasterio.open(BytesIO(response.content)) as src:
            hydrocarbon_permits = src.read(1)  
            profile = src.profile
        
        distance_to_hydrocarbon = distance_transform_edt(hydrocarbon_permits == 0)
        
        influence_hydrocarbon = np.exp(-k_H * distance_to_hydrocarbon)
        
        proximity_score = w_H * influence_hydrocarbon
        
        proximity_score = (proximity_score - np.min(proximity_score)) / (np.max(proximity_score) - np.min(proximity_score))
        
        profile.update(count=2, dtype='float32')
                 
        with rasterio.MemoryFile() as memfile:
            with memfile.open(
                driver='GTiff',
                height=src.height,
                width=src.width,
                count=src.count,
                dtype=src.dtypes[0],
                crs=src.crs,
                transform=src.transform,
                compress='lzw',
                tiled=True,
                blockxsize=256, 
                blockysize=256
            ) as dst:
                dst.write(proximity_score.astype(np.float32),1)
    
            cog_file = memfile.name
        
    return cog_file

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
        raster_selections[raster] = st.checkbox(f"{raster}", value=False)

with st.sidebar.expander("Selected Rasters", expanded=False):
    selected_rasters_urls = []
    if raster_selections.items(): 
        for raster, selected in raster_selections.items():
            if selected:
                selected_rasters_urls.append(rasters_url[raster])
                st.checkbox(f"{raster+'_selected'}", value=False)
                variables[raster] = {
                    'variable1': st.text_input(f"Decay for {raster}", key=f"{raster}_var1"),
                    'variable2': st.text_input(f"Radius for {raster}", key=f"{raster}_var2")
                }
    else: 
        st.write("No raster selected")

m = leafmap.Map(center=(46.603354, 1.888334), zoom=6)

m.add_basemap('OpenStreetMap')
m.add_basemap('HYBRID')

for raster, selected in raster_selections.items():
    if selected:
        raster_url = rasters_url[raster]
        m.add_cog_layer(raster_url, name=raster, nodata=-9999, palette=colors[raster])

if st.sidebar.button('Calculate Proximity Layer'):
    proximity_layer_url = calculate_proximity_layer(selected_rasters_urls)
    m.add_raster(proximity_layer_url, name="url", layer_name="TIFF Layer")

m.to_streamlit(height=900)


