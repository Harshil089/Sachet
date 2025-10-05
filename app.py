import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import numpy as np
from sklearn.cluster import KMeans
from datetime import datetime

# --- Imports and Initial Error Checking ---
# This block ensures the app provides a helpful error if models haven't been trained
try:
    # Attempt to import prediction functions and helper
    from predictor import predict_initial_case, refine_location_with_sightings, haversine
except ImportError:
    st.error("FATAL ERROR: The 'predictor.py' file was not found. Please ensure it is in the same directory.")
    st.stop()
except Exception as e:
    # This catches errors during model loading inside predictor.py
    st.error(f"FATAL ERROR on startup: Could not load models from predictor.py. Have you run train.py successfully? Details: {e}")
    st.stop()

# --- Configuration ---
RANDOM_SEED = 42
DATASET_PATH = "sachet_main_cases_2M.csv" # Ensure this points to the generated dataset

st.set_page_config(page_title="Sachet: Advanced Alert System", layout="wide")
st.title("🔔 Sachet: Advanced Predictive Alert System")

@st.cache_data
def load_data(path):
    """Loads historical case data for generating secondary hotspots."""
    if os.path.exists(path):
        # Load only necessary columns for efficiency
        return pd.read_csv(path, usecols=['case_id', 'abduction_time', 'abductor_relation', 'region_type', 'recovered', 'recovery_latitude', 'recovery_longitude'])
    return None

df = load_data(DATASET_PATH)
if df is None:
    st.error(f"FATAL ERROR: Dataset '{DATASET_PATH}' not found. Please run your data generator script first.")
    st.stop()

# --- Initialize Session State ---
# This ensures variables persist between user interactions, preventing UI bugs.
if 'prediction' not in st.session_state: st.session_state.prediction = None
if 'sightings' not in st.session_state: st.session_state.sightings = []
if 'refined_location' not in st.session_state: st.session_state.refined_location = None
if 'initial_case_input' not in st.session_state: st.session_state.initial_case_input = None
if 'map_key' not in st.session_state: st.session_state.map_key = 'initial_map'

# --- Sidebar: Input Form ---
st.sidebar.header("Enter Case Details")
age = st.sidebar.slider("Child Age", 1, 18, 9, key="age")
gender = st.sidebar.selectbox("Child Gender", ["M", "F"], key="gender")
hour = st.sidebar.slider("Abduction Time (24h format)", 0, 23, 17, key="hour")
dow = st.sidebar.slider("Day of Week (0=Mon, 6=Sun)", 0, 6, 4, key="dow")
st.sidebar.subheader("Location & Context")
# Default coordinates set to Mumbai (Maharashtra capital)
lat = st.sidebar.number_input("Last Seen Latitude", value=19.0760, format="%.4f", key="lat")
lon = st.sidebar.number_input("Last Seen Longitude", value=72.8777, format="%.4f", key="lon")
region_type = st.sidebar.selectbox("Region Type", df['region_type'].unique(), key="region")
pop_density = st.sidebar.number_input("Population Density", value=20000, min_value=10, key="pop")
transport_hub = st.sidebar.selectbox("Major Transport Hub Nearby?", [1, 0], format_func=lambda x: 'Yes' if x==1 else 'No', key="hub")
st.sidebar.subheader("Abductor Information")
relation = st.sidebar.selectbox("Abductor Relation", df['abductor_relation'].unique(), key="relation")

if st.sidebar.button("Predict Initial Case", type="primary", use_container_width=True):
    # 1. Collect all input features
    case_input = {
        'child_age':age, 'child_gender':gender, 'abduction_time':hour, 'abductor_relation':relation, 
        'latitude':lat, 'longitude':lon, 'day_of_week':dow, 'region_type':region_type, 
        'population_density':pop_density, 'transport_hub_nearby':transport_hub
    }
    
    # 2. Calculate dist_to_nearest_city (Required for Stage 2 static features)
    CITY_CENTERS = {"Mumbai":(19.0760,72.8777),"Pune":(18.5204,73.8567),"Nagpur":(21.1458,79.0882),"Nashik":(20.0112,73.7909)}
    dist = min([haversine(lat, lon, c_lat, c_lon) for c_lat, c_lon in CITY_CENTERS.values()]);
    case_input['dist_to_nearest_city'] = dist
    
    # 3. Run Stage 1 Prediction
    with st.spinner("Running initial prediction using Stage 1 AI..."):
        st.session_state.initial_case_input = case_input # Save for Stage 2
        st.session_state.prediction = predict_initial_case(case_input)
        st.session_state.sightings = [] # Clear old sightings
        st.session_state.refined_location = None
        st.session_state.start_time = datetime.now()
        # Pre-fill sighting inputs with a likely first location
        st.session_state.s_lat_input = lat + np.random.uniform(-0.1, 0.1)
        st.session_state.s_lon_input = lon + np.random.uniform(-0.1, 0.1)
        st.session_state.s_hours_input = 5.0
        st.session_state.s_text_input = "heading towards major road"
        st.session_state.map_key = f'map_{datetime.now().timestamp()}'

# --- Sidebar: Live Sightings ---
st.sidebar.subheader("Live Sightings Management")
if st.session_state.prediction and st.session_state.prediction['recovered_label'] == 1:
    s_lat = st.sidebar.number_input("Sighting Latitude", format="%.4f", key="s_lat_input")
    s_lon = st.sidebar.number_input("Sighting Longitude", format="%.4f", key="s_lon_input")
    s_text = st.sidebar.text_input("Direction Description", key="s_text_input")
    s_hours = st.sidebar.number_input("Hours Since Abduction", min_value=0.1, step=0.5, format="%.1f", key="s_hours_input")

    if st.sidebar.button("Add Sighting"):
        # --- LON CORRECTION LOGIC ---
        # Automatically fix single-digit longitudes (e.g., 7.8) to the 70s (e.g., 77.8)
        # as the model data is entirely in Maharashtra (Lon 72 to 80).
        if s_lon < 70:
            s_lon += 70
            st.warning(f"Sighting Longitude corrected from {s_lon-70:.2f} to {s_lon:.4f} for Maharashtra's range.")
        
        # Add new sighting and sort by time
        new_sighting = {'lat': s_lat, 'lon': s_lon, 'direction_text': s_text, 'hours_since': s_hours}
        st.session_state.sightings.append(new_sighting)
        st.session_state.sightings.sort(key=lambda s: s['hours_since'])
        st.sidebar.success("Sighting added! Click 'Refine Prediction' below.")
        st.session_state.map_key = f'map_{datetime.now().timestamp()}' # Force map redraw
else:
    st.sidebar.warning("Predict a case first. If the case is predicted as 'Not Recovered', refinement is disabled.")

# --- Main App Layout ---
if st.session_state.prediction:
    pred = st.session_state.prediction
    risk_map={0:"Low",1:"Medium",2:"High"}
    alert_map={0:"Internal Monitoring",1:"Local Alert",2:"State-Wide Alert (Amber)"}
    color_map={0:"green",1:"orange",2:"red"}

    st.header("🚨 Prediction Results")
    col1,col2=st.columns(2)
    col1.metric("Risk Level", f"{risk_map.get(pred['risk_label'])} Risk", f"Confidence: {pred['risk_prob']:.1%}")
    col2.metric("Recommended Alert", alert_map.get(pred['risk_label']))

    st.subheader("Recovery Prediction")
    colA,colB=st.columns(2)
    colA.metric("Probability of Recovery", f"{pred['recovered_prob']:.1%}")
    colB.metric("Est. Recovery Time", f"~{int(pred['recovery_time_hours'])} hours" if pred['recovery_time_hours']>0 else "N/A")

    st.subheader("📍 Predictive Location Analysis")
    
    # Initialize Folium Map centered on the last seen location
    m = folium.Map(location=[lat, lon], zoom_start=8, tiles="OpenStreetMap")
    folium.Marker([lat, lon], popup="Last Seen Location", icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)
    folium.Circle(radius=5000, location=[lat,lon], color="#800080", fill=True, fill_opacity=0.1, popup="Initial Search Area").add_to(m)

    # Display Sightings
    if st.session_state.sightings:
        st.info(f"{len(st.session_state.sightings)} sighting(s) logged. Use the button below to incorporate them.")
        
        # Display sightings table for verification
        st.markdown("**Logged Sightings (Sorted by Time):**")
        sightings_df = pd.DataFrame(st.session_state.sightings)
        st.dataframe(sightings_df.rename(columns={'lat': 'Lat', 'lon': 'Lon', 'hours_since': 'Hours Since', 'direction_text': 'Direction Text'}), use_container_width=True)

        sighting_points = []
        for s in st.session_state.sightings:
            # Enhanced sighting popup
            sighting_popup_text = f"Sighting @ {s['hours_since']:.1f} hrs<br>Direction: {s['direction_text']}"
            folium.Marker([s['lat'], s['lon']], popup=folium.Popup(sighting_popup_text, max_width=200), icon=folium.Icon(color='orange', icon='eye-open', prefix='fa')).add_to(m)
            sighting_points.append((s['lat'], s['lon']))
        if len(sighting_points) > 1:
            folium.PolyLine(sighting_points, color="orange", weight=2.5, opacity=0.8, popup="Sighting Path").add_to(m)

        # Refinement button
        if st.button("Refine Prediction with Live Sightings", type="secondary"):
            with st.spinner("Running Stage 2 AI (Deep Learning Refinement)..."):
                r_lat, r_lon = refine_location_with_sightings(pred, st.session_state.sightings, st.session_state.initial_case_input)
                st.session_state.refined_location = (r_lat, r_lon)
                st.session_state.map_key = f'map_{datetime.now().timestamp()}'
    
    # --- Primary Hotspot Determination (Initial or Refined) ---
    p_lat = st.session_state.refined_location[0] if st.session_state.refined_location else pred['predicted_latitude']
    p_lon = st.session_state.refined_location[1] if st.session_state.refined_location else pred['predicted_longitude']
    
    if p_lat!=0: # Check if a location was actually predicted
        # Display primary hotspot (initial or refined)
        if st.session_state.refined_location:
            p_popup="REFINED Primary Location (LSTM)"; p_icon_color="purple"; p_icon="bullseye"; p_prefix='fa'
            # Display coordinates in success message for user verification
            st.success(f"AI refined primary hotspot to: {p_lat:.4f}, {p_lon:.4f}") 
        else:
            p_popup="INITIAL Primary Location (LGBM)"; p_icon_color="red"; p_icon="star"; p_prefix='fa'
        
        # Enhanced popup for primary prediction
        primary_popup_html = f"""
            <b>{p_popup}</b><br>
            Coords: {p_lat:.4f}, {p_lon:.4f}<br>
            Risk: {risk_map.get(pred['risk_label'])} ({pred['risk_prob']:.1%})<br>
            Est. Recovery Time: {int(pred['recovery_time_hours'])} hrs
        """
        
        # Add primary location marker and search radius
        folium.Marker([p_lat, p_lon], popup=folium.Popup(primary_popup_html, max_width=300), icon=folium.Icon(color=p_icon_color, icon=p_icon, prefix=p_prefix)).add_to(m)
        
        # Radius shrinks as recovery probability increases
        radius_m = max(500, 15000 * (1 - pred['recovered_prob']))
        folium.Circle(radius=radius_m, location=[p_lat, p_lon], color=p_icon_color, fill=True, fill_opacity=0.15, popup="Primary Search Radius").add_to(m)

    # --- Secondary Hotspots (Historical Clustering) ---
    st.markdown("---")
    st.markdown("**Historical Context (Secondary Hotspots):** Analyzing similar past cases...")
    
    recovered_df = df[df['recovered']==1].dropna(subset=['recovery_latitude'])
    
    # Find historical cases with similar time and context
    if st.session_state.initial_case_input:
        hour = st.session_state.initial_case_input['abduction_time']
        relation = st.session_state.initial_case_input['abductor_relation']
        region_type = st.session_state.initial_case_input['region_type']
    
        time_mask = (recovered_df['abduction_time'].between(hour-2, hour+2))
        context_mask = (recovered_df['abductor_relation'] == relation) & (recovered_df['region_type'] == region_type)
        similar_cases = recovered_df[time_mask & context_mask].copy()
    
        if not similar_cases.empty:
            # Anchor for secondary hotspots is the last known location (either last sighting or initial point)
            anchor_lat = st.session_state.sightings[-1]['lat'] if st.session_state.sightings else lat
            anchor_lon = st.session_state.sightings[-1]['lon'] if st.session_state.sightings else lon
            
            # FIX: Explicitly convert scalar anchor coordinates to arrays of the same size 
            # as the DataFrame columns to enable vectorized Haversine calculation without error.
            anchor_lat_array = np.full_like(similar_cases['recovery_latitude'], anchor_lat)
            anchor_lon_array = np.full_like(similar_cases['recovery_longitude'], anchor_lon)
    
            distances = haversine(
                anchor_lat_array, 
                anchor_lon_array, 
                similar_cases['recovery_latitude'], 
                similar_cases['recovery_longitude']
            )
            relevant_cases = similar_cases[distances < 150]
    
            if len(relevant_cases) >= 10:
                coords=relevant_cases[['recovery_latitude','recovery_longitude']].values
                # Determine K for K-Means (max 4 clusters)
                k=max(1, min(4, len(relevant_cases)//20))
                # Use 'auto' for n_init to satisfy newer sklearn warnings/requirements
                kmeans=KMeans(n_clusters=k,n_init='auto',random_state=RANDOM_SEED).fit(coords)
                
                st.info(f"Identified {len(relevant_cases)} historically similar cases. Clustered into {k} secondary hotspots.")
    
                for i in range(k):
                    center_lat,center_lon = kmeans.cluster_centers_[i]
                    # Secondary circles use the risk color (using pred['risk_label'] which holds the score 0, 1, or 2)
                    folium.Circle(radius=10000, location=[center_lat, center_lon], color=color_map.get(pred['risk_label']), fill=True, fill_opacity=0.1, popup=f"Secondary Hotspot {i+1} (Historical Cluster)").add_to(m)
            elif len(relevant_cases) > 0:
                st.info(f"Found {len(relevant_cases)} historically similar cases, but not enough for clustering (min 10 required).")
            else:
                st.info("No historically similar cases found in the local area (within 150km radius).")
        else:
            st.info("No historically similar cases found with the same abduction time and context.")
            
    # Display the map using the unique key to force redraw when state changes
    st_folium(m, key=st.session_state.map_key, width=1200, height=600)

else:
    st.info("Enter case details in the sidebar and click 'Predict Initial Case' to begin.")













# import streamlit as st
# import pandas as pd
# import folium
# from streamlit_folium import st_folium
# import os
# import numpy as np
# from sklearn.cluster import KMeans
# from datetime import datetime

# # --- Imports and Initial Error Checking ---
# # This block ensures the app provides a helpful error if models haven't been trained
# try:
#     # Attempt to import prediction functions and helper
#     from predictor import predict_initial_case, refine_location_with_sightings, haversine
# except ImportError:
#     st.error("FATAL ERROR: The 'predictor.py' file was not found. Please ensure it is in the same directory.")
#     st.stop()
# except Exception as e:
#     # This catches errors during model loading inside predictor.py
#     st.error(f"FATAL ERROR on startup: Could not load models from predictor.py. Have you run train.py successfully? Details: {e}")
#     st.stop()

# # --- Configuration ---
# RANDOM_SEED = 42
# DATASET_PATH = "sachet_main_cases_2M.csv" # Ensure this points to the generated dataset

# st.set_page_config(page_title="Sachet: Advanced Alert System", layout="wide")
# st.title("🔔 Sachet: Advanced Predictive Alert System")

# @st.cache_data
# def load_data(path):
#     """Loads historical case data for generating secondary hotspots."""
#     if os.path.exists(path):
#         # Load only necessary columns for efficiency
#         return pd.read_csv(path, usecols=['case_id', 'abduction_time', 'abductor_relation', 'region_type', 'recovered', 'recovery_latitude', 'recovery_longitude'])
#     return None

# df = load_data(DATASET_PATH)
# if df is None:
#     st.error(f"FATAL ERROR: Dataset '{DATASET_PATH}' not found. Please run your data generator script first.")
#     st.stop()

# # --- Initialize Session State ---
# # This ensures variables persist between user interactions, preventing UI bugs.
# if 'prediction' not in st.session_state: st.session_state.prediction = None
# if 'sightings' not in st.session_state: st.session_state.sightings = []
# if 'refined_location' not in st.session_state: st.session_state.refined_location = None
# if 'initial_case_input' not in st.session_state: st.session_state.initial_case_input = None
# if 'map_key' not in st.session_state: st.session_state.map_key = 'initial_map'

# # --- Sidebar: Input Form ---
# st.sidebar.header("Enter Case Details")
# age = st.sidebar.slider("Child Age", 1, 18, 9, key="age")
# gender = st.sidebar.selectbox("Child Gender", ["M", "F"], key="gender")
# hour = st.sidebar.slider("Abduction Time (24h format)", 0, 23, 17, key="hour")
# dow = st.sidebar.slider("Day of Week (0=Mon, 6=Sun)", 0, 6, 4, key="dow")
# st.sidebar.subheader("Location & Context")
# # Default coordinates set to Mumbai (Maharashtra capital)
# lat = st.sidebar.number_input("Last Seen Latitude", value=19.0760, format="%.4f", key="lat")
# lon = st.sidebar.number_input("Last Seen Longitude", value=72.8777, format="%.4f", key="lon")
# region_type = st.sidebar.selectbox("Region Type", df['region_type'].unique(), key="region")
# pop_density = st.sidebar.number_input("Population Density", value=20000, min_value=10, key="pop")
# transport_hub = st.sidebar.selectbox("Major Transport Hub Nearby?", [1, 0], format_func=lambda x: 'Yes' if x==1 else 'No', key="hub")
# st.sidebar.subheader("Abductor Information")
# relation = st.sidebar.selectbox("Abductor Relation", df['abductor_relation'].unique(), key="relation")

# if st.sidebar.button("Predict Initial Case", type="primary", use_container_width=True):
#     # 1. Collect all input features
#     case_input = {
#         'child_age':age, 'child_gender':gender, 'abduction_time':hour, 'abductor_relation':relation, 
#         'latitude':lat, 'longitude':lon, 'day_of_week':dow, 'region_type':region_type, 
#         'population_density':pop_density, 'transport_hub_nearby':transport_hub
#     }
    
#     # 2. Calculate dist_to_nearest_city (Required for Stage 2 static features)
#     CITY_CENTERS = {"Mumbai":(19.0760,72.8777),"Pune":(18.5204,73.8567),"Nagpur":(21.1458,79.0882),"Nashik":(20.0112,73.7909)}
#     dist = min([haversine(lat, lon, c_lat, c_lon) for c_lat, c_lon in CITY_CENTERS.values()]);
#     case_input['dist_to_nearest_city'] = dist
    
#     # 3. Run Stage 1 Prediction
#     with st.spinner("Running initial prediction using Stage 1 AI..."):
#         st.session_state.initial_case_input = case_input # Save for Stage 2
#         st.session_state.prediction = predict_initial_case(case_input)
#         st.session_state.sightings = [] # Clear old sightings
#         st.session_state.refined_location = None
#         st.session_state.start_time = datetime.now()
#         # Pre-fill sighting inputs with a likely first location
#         st.session_state.s_lat_input = lat + np.random.uniform(-0.1, 0.1)
#         st.session_state.s_lon_input = lon + np.random.uniform(-0.1, 0.1)
#         st.session_state.s_hours_input = 5.0
#         st.session_state.s_text_input = "heading towards major road"
#         st.session_state.map_key = f'map_{datetime.now().timestamp()}'

# # --- Sidebar: Live Sightings ---
# st.sidebar.subheader("Live Sightings Management")
# if st.session_state.prediction and st.session_state.prediction['recovered_label'] == 1:
#     st.sidebar.number_input("Sighting Latitude", format="%.4f", key="s_lat_input")
#     st.sidebar.number_input("Sighting Longitude", format="%.4f", key="s_lon_input")
#     st.sidebar.text_input("Direction Description", key="s_text_input")
#     st.sidebar.number_input("Hours Since Abduction", min_value=0.1, step=0.5, format="%.1f", key="s_hours_input")

#     if st.sidebar.button("Add Sighting"):
#         # Add new sighting and sort by time
#         new_sighting = {'lat': st.session_state.s_lat_input, 'lon': st.session_state.s_lon_input, 'direction_text': st.session_state.s_text_input, 'hours_since': st.session_state.s_hours_input}
#         st.session_state.sightings.append(new_sighting)
#         st.session_state.sightings.sort(key=lambda s: s['hours_since'])
#         st.sidebar.success("Sighting added! Click 'Refine Prediction' below.")
#         st.session_state.map_key = f'map_{datetime.now().timestamp()}' # Force map redraw
# else:
#     st.sidebar.warning("Predict a case first. If the case is predicted as 'Not Recovered', refinement is disabled.")

# # --- Main App Layout ---
# if st.session_state.prediction:
#     pred = st.session_state.prediction
#     risk_map={0:"Low",1:"Medium",2:"High"}
#     alert_map={0:"Internal Monitoring",1:"Local Alert",2:"State-Wide Alert (Amber)"}
#     color_map={0:"green",1:"orange",2:"red"}

#     st.header("🚨 Prediction Results")
#     col1,col2=st.columns(2)
#     col1.metric("Risk Level", f"{risk_map.get(pred['risk_label'])} Risk", f"Confidence: {pred['risk_prob']:.1%}")
#     col2.metric("Recommended Alert", alert_map.get(pred['risk_label']))

#     st.subheader("Recovery Prediction")
#     colA,colB=st.columns(2)
#     colA.metric("Probability of Recovery", f"{pred['recovered_prob']:.1%}")
#     colB.metric("Est. Recovery Time", f"~{int(pred['recovery_time_hours'])} hours" if pred['recovery_time_hours']>0 else "N/A")

#     st.subheader("📍 Predictive Location Analysis")
    
#     # Initialize Folium Map centered on the last seen location
#     m = folium.Map(location=[lat, lon], zoom_start=8, tiles="OpenStreetMap")
#     folium.Marker([lat, lon], popup="Last Seen Location", icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)
#     folium.Circle(radius=5000, location=[lat,lon], color="#800080", fill=True, fill_opacity=0.1, popup="Initial Search Area").add_to(m)

#     # Display Sightings
#     if st.session_state.sightings:
#         st.info(f"{len(st.session_state.sightings)} sighting(s) logged. Use the button below to incorporate them.")
#         sighting_points = []
#         for s in st.session_state.sightings:
#             folium.Marker([s['lat'], s['lon']], popup=f"Sighting @ {s['hours_since']:.1f} hrs", icon=folium.Icon(color='orange', icon='eye-open', prefix='fa')).add_to(m)
#             sighting_points.append((s['lat'], s['lon']))
#         if len(sighting_points) > 1:
#             folium.PolyLine(sighting_points, color="orange", weight=2.5, opacity=0.8, popup="Sighting Path").add_to(m)

#         # Refinement button
#         if st.button("Refine Prediction with Live Sightings", type="secondary"):
#             with st.spinner("Running Stage 2 AI (Deep Learning Refinement)..."):
#                 r_lat, r_lon = refine_location_with_sightings(pred, st.session_state.sightings, st.session_state.initial_case_input)
#                 st.session_state.refined_location = (r_lat, r_lon)
#                 st.session_state.map_key = f'map_{datetime.now().timestamp()}'
    
#     # --- Primary Hotspot Determination (Initial or Refined) ---
#     p_lat = st.session_state.refined_location[0] if st.session_state.refined_location else pred['predicted_latitude']
#     p_lon = st.session_state.refined_location[1] if st.session_state.refined_location else pred['predicted_longitude']
    
#     if p_lat!=0: # Check if a location was actually predicted
#         # Display primary hotspot (initial or refined)
#         if st.session_state.refined_location:
#             p_popup="REFINED Primary Location (LSTM)"; p_icon_color="purple"; p_icon="bullseye"; p_prefix='fa'
#             st.success(f"AI refined primary hotspot to: {p_lat:.4f}, {p_lon:.4f}")
#         else:
#             p_popup="INITIAL Primary Location (LGBM)"; p_icon_color="red"; p_icon="star"; p_prefix='fa'
        
#         # Add primary location marker and search radius
#         folium.Marker([p_lat, p_lon], popup=p_popup, icon=folium.Icon(color=p_icon_color, icon=p_icon, prefix=p_prefix)).add_to(m)
        
#         # Radius shrinks as recovery probability increases
#         radius_m = max(500, 15000 * (1 - pred['recovered_prob']))
#         folium.Circle(radius=radius_m, location=[p_lat, p_lon], color=p_icon_color, fill=True, fill_opacity=0.15, popup="Primary Search Radius").add_to(m)

#     # --- Secondary Hotspots (Historical Clustering) ---
#     st.markdown("---")
#     st.markdown("**Historical Context (Secondary Hotspots):** Analyzing similar past cases...")
    
#     recovered_df = df[df['recovered']==1].dropna(subset=['recovery_latitude'])
    
#     # Find historical cases with similar time and context
#     hour = st.session_state.initial_case_input['abduction_time']
#     relation = st.session_state.initial_case_input['abductor_relation']
#     region_type = st.session_state.initial_case_input['region_type']

#     time_mask = (recovered_df['abduction_time'].between(hour-2, hour+2))
#     context_mask = (recovered_df['abductor_relation'] == relation) & (recovered_df['region_type'] == region_type)
#     similar_cases = recovered_df[time_mask & context_mask].copy()

#     if not similar_cases.empty:
#         # Anchor for secondary hotspots is the last known location (either last sighting or initial point)
#         anchor_lat = st.session_state.sightings[-1]['lat'] if st.session_state.sightings else lat
#         anchor_lon = st.session_state.sightings[-1]['lon'] if st.session_state.sightings else lon
        
#         # FIX: Explicitly convert scalar anchor coordinates to arrays of the same size 
#         # as the DataFrame columns to enable vectorized Haversine calculation without error.
#         anchor_lat_array = np.full_like(similar_cases['recovery_latitude'], anchor_lat)
#         anchor_lon_array = np.full_like(similar_cases['recovery_longitude'], anchor_lon)

#         distances = haversine(
#             anchor_lat_array, 
#             anchor_lon_array, 
#             similar_cases['recovery_latitude'], 
#             similar_cases['recovery_longitude']
#         )
#         relevant_cases = similar_cases[distances < 150]

#         if len(relevant_cases) >= 10:
#             coords=relevant_cases[['recovery_latitude','recovery_longitude']].values
#             # Determine K for K-Means (max 4 clusters)
#             k=max(1, min(4, len(relevant_cases)//20))
#             # Use 'auto' for n_init to satisfy newer sklearn warnings/requirements
#             kmeans=KMeans(n_clusters=k,n_init='auto',random_state=RANDOM_SEED).fit(coords)
            
#             st.info(f"Identified {len(relevant_cases)} historically similar cases. Clustered into {k} secondary hotspots.")

#             for i in range(k):
#                 center_lat,center_lon = kmeans.cluster_centers_[i]
#                 # Secondary circles use the risk color
#                 folium.Circle(radius=10000, location=[center_lat, center_lon], color=color_map.get(pred['risk_label']), fill=True, fill_opacity=0.1, popup=f"Secondary Hotspot {i+1} (Historical Cluster)").add_to(m)
#         elif len(relevant_cases) > 0:
#             st.info(f"Found {len(relevant_cases)} historically similar cases, but not enough for clustering (min 10 required).")
#         else:
#             st.info("No historically similar cases found in the local area (within 150km radius).")
            
#     # Display the map using the unique key to force redraw when state changes
#     st_folium(m, key=st.session_state.map_key, width=1200, height=600)

# else:
#     st.info("Enter case details in the sidebar and click 'Predict Initial Case' to begin.")

