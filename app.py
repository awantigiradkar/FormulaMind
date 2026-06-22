"""
FormulaMind — AI-Powered Formula 1 Race Strategy Simulator
Main Streamlit Application Dashboard.
"""

import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from telemetry import (
    setup_cache,
    get_f1_session,
    get_driver_list,
    compare_driver_telemetry,
    plot_speed_comparison,
    plot_pedal_analysis,
    plot_gear_shifts,
    plot_track_dominance,
    get_session_weather,
    plot_driver_scorecard,
    detect_corners,
    plot_corner_performance
)
from strategy import StrategyOptimizer, UndercutAnalyzer
from simulation import RaceSimulator
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score


@st.cache_data
def get_gp_list(year):
    """
    Fetches the list of official championship Grand Prix events for a given year
    directly from FastF1's schedule database.
    """
    try:
        import fastf1
        schedule = fastf1.get_event_schedule(year)
        # Filter out pre-season testing rounds (RoundNumber == 0)
        rounds = schedule[schedule['RoundNumber'] > 0]
        return rounds['EventName'].tolist()
    except Exception as e:
        # Fallback list of major tracks if the API fails or is offline
        return [
            "Bahrain Grand Prix", "Saudi Arabian Grand Prix", "Australian Grand Prix",
            "Azerbaijan Grand Prix", "Miami Grand Prix", "Monaco Grand Prix",
            "Spanish Grand Prix", "Canadian Grand Prix", "Austrian Grand Prix",
            "British Grand Prix", "Hungarian Grand Prix", "Belgian Grand Prix",
            "Dutch Grand Prix", "Italian Grand Prix", "Singapore Grand Prix",
            "Japanese Grand Prix", "Qatar Grand Prix", "United States Grand Prix",
            "Mexico City Grand Prix", "São Paulo Grand Prix", "Las Vegas Grand Prix",
            "Abu Dhabi Grand Prix"
        ]

def calculate_driver_offsets(session):
    """
    Calculates each driver's relative pace offset (in seconds)
    compared to the session's overall median lap time.
    """
    try:
        laps = session.laps
        laps_clean = laps[laps['PitInTime'].isna() & laps['PitOutTime'].isna()].copy()
        laps_clean = laps_clean[laps_clean['TrackStatus'] == '1'].copy()
        laps_clean['LapTimeSecs'] = laps_clean['LapTime'].dt.total_seconds()
        
        overall_median = laps_clean['LapTimeSecs'].median()
        
        driver_offsets = {}
        for d in session.drivers:
            try:
                info = session.get_driver(d)
                abbr = info['Abbreviation']
                drv_laps = laps_clean[laps_clean['Driver'] == abbr]
                if len(drv_laps) > 3:
                    drv_median = drv_laps['LapTimeSecs'].median()
                    # Clamp offset between -1.5s and +1.5s to keep it realistic
                    offset = np.clip(drv_median - overall_median, -1.5, 1.5)
                    driver_offsets[abbr] = float(offset)
            except Exception:
                pass
        return driver_offsets
    except Exception:
        return {}

def train_dynamic_model(session):
    """
    Cleans lap data from the loaded race session and trains a 
    Random Forest model on the fly for the selected Grand Prix.
    """
    laps = session.laps
    
    # 1. Clean Data (Strict filtering for ML quality)
    laps_clean = laps[laps['PitInTime'].isna() & laps['PitOutTime'].isna()].copy()
    laps_clean = laps_clean[laps_clean['TrackStatus'] == '1'].copy()
    
    laps_clean['LapTimeSecs'] = laps_clean['LapTime'].dt.total_seconds()
    laps_clean = laps_clean.dropna(subset=['LapTimeSecs', 'TyreLife', 'Compound', 'LapNumber']).copy()
    
    # Remove speed outliers
    median_time = laps_clean['LapTimeSecs'].median()
    laps_clean = laps_clean[laps_clean['LapTimeSecs'] <= median_time * 1.07].copy()
    
    # 2. Feature Selection
    data = laps_clean[['LapTimeSecs', 'TyreLife', 'LapNumber', 'Compound']].copy()
    data['Compound'] = data['Compound'].str.upper()
    data = data[data['Compound'].isin(['SOFT', 'MEDIUM', 'HARD'])].copy()
    
    if len(data) < 20:
        raise ValueError("Not enough clean dry-weather laps in this session to train a model.")
        
    # One-hot encode Compounds
    for comp in ['SOFT', 'MEDIUM', 'HARD']:
        data[f'Compound_{comp}'] = (data['Compound'] == comp).astype(int)
        
    feature_cols = ['TyreLife', 'LapNumber', 'Compound_SOFT', 'Compound_MEDIUM', 'Compound_HARD']
    X = data[feature_cols]
    y = data['LapTimeSecs']
    
    # 3. Train Model (Fitted quickly with 80 trees)
    model = RandomForestRegressor(n_estimators=80, max_depth=6, random_state=42)
    model.fit(X, y)
    
    # Calculate performance metrics
    y_pred = model.predict(X)
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    
    return model, mae, r2

# Page configuration setup
st.set_page_config(
    page_title="FormulaMind — AI F1 Strategy Simulator",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply CSS styling overrides
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.warning(f"CSS styling file {file_name} not found.")

local_css(os.path.join("assets", "custom.css"))

# Neon Glowing Branding Headers
st.markdown("<h1 class='glow-text' style='text-align: center; margin-bottom: 2rem;'>FORMULAMIND</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 18px; margin-top: -1.5rem; margin-bottom: 2rem;'>AI-Powered Formula 1 Race Strategy & Telemetry Platform</p>", unsafe_allow_html=True)

# ----------------- SESSION STATE & INITIALIZATION -----------------
setup_cache(os.path.join("data", "fastf1_cache"))

@st.cache_resource
def load_session_cached(year, gp, session_type):
    """Caches the loaded session in Streamlit memory so it loads instantly on widget changes."""
    return get_f1_session(year, gp, session_type)

@st.cache_resource
def load_strategy_engine():
    """Tries to initialize Strategy engine models, failing gracefully if pkl model is not found."""
    try:
        return StrategyOptimizer(), UndercutAnalyzer()
    except Exception as e:
        return None, None

# ----------------- SIDEBAR CONTROLS -----------------
st.sidebar.markdown("Session Settings")

year = st.sidebar.selectbox("Season", [2023, 2024], index=0)

# Fetch the official Grand Prix list for the selected season
gp_list = get_gp_list(year)

# Determine a default GP to auto-select (British Grand Prix is a solid baseline)
default_index = 0
for idx, gp_name in enumerate(gp_list):
    if "British" in gp_name or "Silverstone" in gp_name:
        default_index = idx
        break

gp = st.sidebar.selectbox("Grand Prix", gp_list, index=default_index)
session_type = st.sidebar.selectbox("Session", ["Qualifying (Q)", "Race (R)"], index=0)

session_code = "Q" if "Qualifying" in session_type else "R"

# Initialize session states
if 'session_loaded' not in st.session_state:
    st.session_state['session_loaded'] = False
    st.session_state['session_obj'] = None
    st.session_state['drivers_list'] = None

load_btn = st.sidebar.button("Connect F1 Timing API", type="primary")

# Initialize strategy session states if not present
if 'optimizer' not in st.session_state:
    st.session_state['optimizer'] = None
    st.session_state['undercut_analyzer'] = None
    st.session_state['model_mae'] = 0.0
    st.session_state['model_r2'] = 0.0
    st.session_state['model_gp'] = ""

if load_btn:
    with st.sidebar:
        with st.spinner("Downloading F1 telemetry & training AI..."):
            try:
                # 1. Load telemetry session for Tab 1 (Qualifying or Race)
                session = load_session_cached(year, gp, session_code)
                st.session_state['session_obj'] = session
                st.session_state['drivers_list'] = get_driver_list(session)
                st.session_state['session_loaded'] = True
                
                # 2. Dynamic ML Training (Must use Race session data for tire degradation)
                if session_code == "R":
                    race_session = session
                else:
                    # If user loaded Qualifying, download the Race in the background for ML training
                    st.info("Qualifying loaded. Fetching Race session in background for ML training...")
                    race_session = load_session_cached(year, gp, "R")
                
                # Train the model on the fly
                model_obj, mae, r2 = train_dynamic_model(race_session)
                
                # Instatiate optimizer using the newly trained model object
                st.session_state['optimizer'] = StrategyOptimizer(model_obj=model_obj)
                st.session_state['undercut_analyzer'] = UndercutAnalyzer(st.session_state['optimizer'])
                st.session_state['model_mae'] = mae
                st.session_state['model_r2'] = r2
                st.session_state['model_gp'] = gp

                st.session_state['driver_offsets'] = calculate_driver_offsets(race_session)
                
                st.sidebar.success(f"Connected & AI Trained for {gp}!")
                
            except Exception as e:
                err = str(e).encode('ascii', 'replace').decode('ascii')
                st.sidebar.error(f"Error loading session: {err}")

# Status bar indicator
if st.session_state['session_loaded']:
    st.sidebar.markdown(f"🟢 **Connected**: {year} {gp} GP ({session_code})")
    
    weather = get_session_weather(st.session_state['session_obj'])
    if weather:
        with st.sidebar.expander("Track Weather logs", expanded=True):
            st.markdown(f"**Track Temp:** {weather['TrackTemp']:.1f} °C")
            st.markdown(f"**Air Temp:** {weather['AirTemp']:.1f} °C")
            st.markdown(f"**Humidity:** {weather['Humidity']:.1f} %")
            st.markdown(f"**Wind Speed:** {weather['WindSpeed']:.1f} km/h")
else:
    st.sidebar.markdown("🔴 **Offline**: Connect Timing API in sidebar to view live telemetry.")

# ----------------- MAIN INTERFACE -----------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Telemetry Analyzer", 
    "Tire Degradation & Strategy", 
    "Live Undercut Tracker", 
    "Multi-Agent Simulator",
    "AI Strategy Assistant"
])

# ================= TAB 1: TELEMETRY ANALYZER =================
with tab1:
    st.markdown("### Telemetry Driver Comparison")
    st.markdown("Compare two drivers' telemetry lines aligned by distance. Plots speed, throttle, braking, and track dominance.")
    
    if st.session_state['session_loaded']:
        drivers_df = st.session_state['drivers_list']
        driver_abbrs = list(drivers_df['Abbreviation'].unique())
        
        col1, col2 = st.columns(2)
        with col1:
            driver_a = st.selectbox("Select Driver A", driver_abbrs, index=driver_abbrs.index('HAM') if 'HAM' in driver_abbrs else 0)
        with col2:
            driver_b = st.selectbox("Select Driver B", driver_abbrs, index=driver_abbrs.index('VER') if 'VER' in driver_abbrs else min(1, len(driver_abbrs)-1))
            
        if driver_a == driver_b:
            st.warning("Please select two different drivers for comparison.")
        else:
            with st.spinner("Aligning telemetry grids..."):
                try:
                    df_aligned, metadata = compare_driver_telemetry(st.session_state['session_obj'], driver_a, driver_b)
                    
                    # --- Sector Timing Calculations ---
                    # Divide the 1000-point distance grid into 3 equal sectors
                    sec1_df = df_aligned.iloc[:333]
                    sec2_df = df_aligned.iloc[333:666]
                    sec3_df = df_aligned.iloc[666:]
                    
                    # Calculate sector time deltas
                    s1_delta = float(sec1_df['DeltaTime'].iloc[-1])
                    s2_delta = float(sec2_df['DeltaTime'].iloc[-1]) - s1_delta
                    s3_delta = float(df_aligned['DeltaTime'].iloc[-1]) - (s1_delta + s2_delta)
                    
                    # Top Metrics Row
                    m_col1, m_col2, m_col3 = st.columns(3)
                    with m_col1:
                        st.metric(f"Driver A ({driver_a}) Lap Time", f"{metadata['lap_time_a']:.3f}s")
                    with m_col2:
                        st.metric(f"Driver B ({driver_b}) Lap Time", f"{metadata['lap_time_b']:.3f}s")
                    with m_col3:
                        delta_lap = metadata['lap_time_a'] - metadata['lap_time_b']
                        st.metric("Lap Delta (A vs B)", f"{delta_lap:+.3f}s", delta_color="inverse")
                        
                    # Sector Winners Metrics Row
                    s_col1, s_col2, s_col3 = st.columns(3)
                    with s_col1:
                        s1_winner = driver_a if s1_delta < 0 else driver_b
                        st.metric("Sector 1 Winner", f"{s1_winner}", f"{abs(s1_delta):.3f}s gap")
                    with s_col2:
                        s2_winner = driver_a if s2_delta < 0 else driver_b
                        st.metric("Sector 2 Winner", f"{s2_winner}", f"{abs(s2_delta):.3f}s gap")
                    with s_col3:
                        s3_winner = driver_a if s3_delta < 0 else driver_b
                        st.metric("Sector 3 Winner", f"{s3_winner}", f"{abs(s3_delta):.3f}s gap")
                    # Speed comparison plots
                    st.plotly_chart(plot_speed_comparison(df_aligned, metadata), use_container_width=True)
                    
                    # Pedals and gears plots side by side
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        st.plotly_chart(plot_pedal_analysis(df_aligned, metadata), use_container_width=True)
                    with col_p2:
                        st.plotly_chart(plot_gear_shifts(df_aligned, metadata), use_container_width=True)
                        st.plotly_chart(plot_driver_scorecard(df_aligned, metadata), use_container_width=True)
                        
                    # --- NEW: ATLAS Corner Zoom Panel ---
                    st.markdown("#### ATLAS Apex Micro-Telemetry Zoom")
                    st.markdown("Zoom into individual corner zones to analyze driver deceleration and acceleration timings.")
                    
                    apexes = detect_corners(df_aligned, driver_a)
                    if len(apexes) > 0:
                        options_corners = [f"Turn Apex at {int(ap['distance'])}m" for ap in apexes]
                        selected_corner_str = st.selectbox("Select Corner Apex Zone", options_corners)
                        selected_idx = options_corners.index(selected_corner_str)
                        selected_apex = apexes[selected_idx]
                        
                        # Generate corner plot and statistics
                        fig_corner, stats_corner = plot_corner_performance(df_aligned, metadata, selected_apex)
                        
                        # Display stats cards
                        c_col1, c_col2 = st.columns(2)
                        with c_col1:
                            st.markdown(f"**{driver_a} Performance:**")
                            st.markdown(f"- **Braking Point:** `{int(stats_corner[driver_a]['brake_point'])}m`")
                            st.markdown(f"- **Apex Speed:** `{stats_corner[driver_a]['apex_speed']:.1f} km/h`")
                            st.markdown(f"- **Throttle Pick-up:** `{int(stats_corner[driver_a]['throttle_point'])}m`")
                        with c_col2:
                            st.markdown(f"**{driver_b} Performance:**")
                            st.markdown(f"- **Braking Point:** `{int(stats_corner[driver_b]['brake_point'])}m`")
                            st.markdown(f"- **Apex Speed:** `{stats_corner[driver_b]['apex_speed']:.1f} km/h`")
                            st.markdown(f"- **Throttle Pick-up:** `{int(stats_corner[driver_b]['throttle_point'])}m`")
                            
                        st.plotly_chart(fig_corner, use_container_width=True)
                    else:
                        st.info("No slow corner apexes detected in this telemetry slice.")
                        
                    # 2D Dominance map
                    st.plotly_chart(plot_track_dominance(st.session_state['session_obj'], driver_a, driver_b), use_container_width=True)
                    
                    # Exporter Button
                    csv_data = df_aligned.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Aligned Telemetry Data (CSV)",
                        data=csv_data,
                        file_name=f"F1_telemetry_{driver_a}_vs_{driver_b}_{year}_{gp}.csv",
                        mime="text/csv",
                        type="secondary"
                    )
                    
                except Exception as e:
                    err = str(e).encode('ascii', 'replace').decode('ascii')
                    st.error(f"Failed to align telemetry: {err}")
    else:
        st.info("Please click the 'Connect F1 Timing API' button in the sidebar to download telemetry and begin analysis.")

# ================= TAB 2: TIRE DEGRADATION & STRATEGY =================
with tab2:
    st.markdown("### AI Race Strategy & Stint Optimizer")
    
    optimizer = st.session_state.get('optimizer', None)
    if optimizer is None:
        st.error("No active ML model. Please connect to a Grand Prix in the sidebar first to train the AI.")
    else:
        # --- NEW: Driver Selection for Strategy Customization ---
        if st.session_state.get('session_loaded', False):
            drivers_df = st.session_state['drivers_list']
            driver_abbrs = list(drivers_df['Abbreviation'].unique())
            selected_opt_driver = st.selectbox("Select Driver to Optimize", driver_abbrs, key="opt_drv")
            
            # Fetch offset
            offsets = st.session_state.get('driver_offsets', {})
            drv_offset = offsets.get(selected_opt_driver, 0.0)
        else:
            drv_offset = 0.0
            selected_opt_driver = "Average Grid"

        # Display the training performance of the active model
        st.markdown(f"**Active AI Model:** trained on **{st.session_state.get('model_gp', 'Unknown')}GP** | MAE: **{st.session_state.get('model_mae', 0.0):.3f}s** | R² Score: **{st.session_state.get('model_r2', 0.0):.1%}**")
        col_s1, col_s2 = st.columns([0.4, 0.6])
        with col_s1:
            st.markdown("#### Stint Optimizer Controls")
            total_laps = st.slider("Total Race Laps", 10, 70, value=52)
            pit_loss = st.number_input("Pit Lane Time Loss (Seconds)", value=20.0, step=0.5)
            
            run_opt = st.button("Calculate Optimal Strategies", type="primary")
            
            # Interactive tyre decay curves
            st.markdown("---")
            st.markdown("#### Single Tyre Compound Pace Predictor")
            compound = st.selectbox("Tyre Compound", ["SOFT", "MEDIUM", "HARD"])
            start_lap = st.number_input("Start Lap (fuel weight factor)", 1, 70, value=1)
            life_range = st.slider("Target Tyre Stint Length (Laps)", 1, 40, value=25)
            
            # Fuel Correction Switch
            fuel_correction = st.checkbox("Enable F1 Fuel Correction (+0.065s/lap weight baseline)")
            
            laps_arr = np.arange(1, life_range + 1)
            pred_times = []
            for t_life in laps_arr:
                lap_num = start_lap + t_life - 1
                base_time = optimizer.predict_lap_time(t_life, lap_num, compound)
                base_time += drv_offset
                if fuel_correction:
                    # Subtracting the fuel weight benefit reveals the true, raw tire performance decay curve
                    base_time += (lap_num * 0.065)
                pred_times.append(base_time)
                
            # --- Tire Wear Cliff Warnings Heuristic ---
            max_safe_life = 15 if compound == "SOFT" else (26 if compound == "MEDIUM" else 38)
            if life_range > max_safe_life:
                st.warning(
                    f"**Tire Cliff Warning:** Running the **{compound}** compound for {life_range} laps "
                    f"exceeds its safe thermal limits. Expect lap times to drop off by up to "
                    f"+{(pred_times[-1] - pred_times[0]):.2f}s."
                )
                
            fig_decay = go.Figure()
            fig_decay.add_trace(go.Scatter(x=laps_arr, y=pred_times, mode='lines+markers', line=dict(color='#00E5FF', width=2)))
            fig_decay.update_layout(xaxis_title="Tyre Life (Laps)", yaxis_title="Predicted Lap Time (s)")
            from utils.styles import apply_premium_layout, get_driver_color
            fig_decay = apply_premium_layout(fig_decay, f"Predicted Pace Dropoff for {compound} compound")
            st.plotly_chart(fig_decay, use_container_width=True)
            
        with col_s2:
            st.markdown("#### Optimal F1 Strategies Ranked")
            if 'opt_results' not in st.session_state:
                st.session_state['opt_results'] = None
                
            if run_opt or st.session_state['opt_results'] is None:
                st.session_state['opt_results'] = optimizer.find_best_strategies(
                    total_laps=total_laps, pit_loss=pit_loss, driver_offset=drv_offset
                )
                
            results = st.session_state['opt_results']
            
            # Display ranked strategies
            for idx, res in enumerate(results):
                strat_name = res['strategy_name']
                opt_pit = res['optimal_pit_lap']
                total_duration = res['total_time_secs'] / 60.0
                
                with st.expander(f"Rank {idx+1}: {strat_name} | Pit Lap: {opt_pit} | Duration: {total_duration:.2f} mins", expanded=(idx==0)):
                    st.write(f"This strategy utilizes the {strat_name} tyres to complete the race in **{total_duration:.3f} minutes**.")
                    st.write(f"The mathematically optimal pit stop is on **Lap {opt_pit}**.")
                    
                    df_laps = res['laps_dataframe']
                    fig_strat = go.Figure()
                    fig_strat.add_trace(go.Scatter(
                        x=df_laps['LapNumber'], 
                        y=df_laps['LapTime'],
                        mode='lines+markers',
                        name='Lap Time',
                        line=dict(color='#FF007F', width=1.5)
                    ))
                    fig_strat.update_layout(xaxis_title="Race Lap", yaxis_title="Lap Time (s)")
                    fig_strat = apply_premium_layout(fig_strat, f"Race Lap Time Trace ({strat_name})")
                    st.plotly_chart(fig_strat, use_container_width=True)
                    
                                        # --- NEW: Traffic Window Planner ---
                    st.markdown("#### 🚦 Pit Stop Traffic Window Planner")
                    st.markdown("Projects where your driver will re-enter the race relative to other cars. Evaluates clean air vs dirty air traffic zones.")
                    
                    # 1. Estimate the driver's own average predicted base pace on this track
                    try:
                        _, df_base = optimizer.simulate_strategy(
                            total_laps, [], ['MEDIUM'], 0.0, driver_offset=drv_offset
                        )
                        driver_base_pace = float(df_base['LapTime'].mean())
                    except Exception:
                        driver_base_pace = 93.0  # Fallback race pace
                        
                    # 2. Scale competitors dynamically relative to the driver's own base pace
                    competitors = {
                        'HAM (Leader Pack)': {'lap_time_avg': driver_base_pace - 0.25},
                        'NOR (Leader Pack)': {'lap_time_avg': driver_base_pace + 0.15},
                        'ALB (Midfield)': {'lap_time_avg': driver_base_pace + 0.80},
                        'TSU (Midfield)': {'lap_time_avg': driver_base_pace + 1.20},
                        'BOT (Backmarker)': {'lap_time_avg': driver_base_pace + 2.00}
                    }
                    
                    traffic_laps = []
                    # Map out pit laps from Lap 10 to Lap 40
                    for plap in range(10, 41):
                        # Simulate the strategy for the selected driver
                        tot_t, df_sim = optimizer.simulate_strategy(
                            total_laps, [plap], ['MEDIUM', 'HARD'], pit_loss, driver_offset=drv_offset
                        )
                        
                        # Driver's cumulative time post-pit at lap plap
                        ver_post_pit = df_sim[df_sim['LapNumber'] == plap]['TotalCumulativeTime'].values[0]
                        
                        status = "Clean Air"
                        blocker = ""
                        
                        # Project competitor cumulative times
                        for comp, c_cfg in competitors.items():
                            # Competitor cumulative time at lap plap (no pit loss)
                            comp_time = plap * c_cfg['lap_time_avg']
                            gap = ver_post_pit - comp_time
                            
                            # If they exit within +/- 2.0 seconds, they are in dirty air traffic
                            if abs(gap) < 2.0:
                                status = "Traffic Blocker"
                                blocker = comp
                                break
                                
                        traffic_laps.append({
                            'Pit Lap': plap,
                            'Status': status,
                            'Details': f"Emerges next to {blocker}" if status != "Clean Air" else "Emerges in Clear Track Gap"
                        })
                        
                    df_traffic = pd.DataFrame(traffic_laps)
                    
                    # Render styling helper
                    def style_traffic(row):
                        if row['Status'] == "Clean Air":
                            return ['background-color: #064E3B; color: #A7F3D0'] * 3 # Green
                        return ['background-color: #7C2D12; color: #FED7AA'] * 3     # Red
                        
                    st.dataframe(
                        df_traffic.style.apply(style_traffic, axis=1), 
                        width='stretch', 
                        height=280
                    )

# ================= TAB 3: LIVE UNDERCUT TRACKER =================
with tab3:
    st.markdown("### Live Pit Lane Undercut Analyzer")
    st.markdown("Enter timing parameters for a leading and chasing driver to evaluate the undercut threat delta.")
    
    undercut_analyzer = st.session_state.get('undercut_analyzer', None)
    if undercut_analyzer is None:
        st.error("No active ML model. Please connect to a Grand Prix in the sidebar first to train the AI.")
    else:
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            st.markdown("#### Track Gap Variables")
            current_lap = st.number_input("Current Race Lap Number", 1, 70, value=25)
            gap_slider = st.slider("Time Gap (Leader to Chaser)", 0.2, 5.0, value=1.2, step=0.1)
            
            st.markdown("#### Leader (Driver Staying Out) Status")
            lead_compound = st.selectbox("Leader Compound", ["SOFT", "MEDIUM", "HARD"], index=1)
            lead_tyre_age = st.slider("Leader Tyre Life (Laps Run)", 1, 35, value=15)
            
            st.markdown("#### Chaser (Driver Pitting) Status")
            chase_fresh_compound = st.selectbox("Chaser Fresh Tyre Compound", ["SOFT", "MEDIUM", "HARD"], index=2)
            
        with col_u2:
            st.markdown("#### AI Strategy Calculation")
            res_undercut = undercut_analyzer.analyze_undercut_potential(
                gap_seconds=gap_slider,
                lap_number=current_lap,
                tyre_age_leader=lead_tyre_age,
                compound_leader=lead_compound,
                compound_chaser_fresh=chase_fresh_compound
            )
            
            threat = res_undercut['threat_level']
            if "CRITICAL" in threat:
                bg_color = "#991B1B"
                text_color = "#FCA5A5"
            elif "HIGH" in threat:
                bg_color = "#7C2D12"
                text_color = "#FED7AA"
            elif "MEDIUM" in threat:
                bg_color = "#713F12"
                text_color = "#FEF08A"
            else:
                bg_color = "#064E3B"
                text_color = "#A7F3D0"
                
            st.markdown(f"""
            <div style="background-color: {bg_color}; padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px;">
                <h3 style="color: {text_color}; margin-top: 0;">THREAT STATUS: {threat}</h3>
                <p style="color: #F1F5F9; font-size: 16px; font-weight: 600; margin-bottom: 0;">{res_undercut['recommendation']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            c_m1, c_m2 = st.columns(2)
            with c_m1:
                st.metric("Leader Stays Out Pace", f"{res_undercut['leader_lap_time_worn']:.2f}s", f"Tyre Age: {lead_tyre_age + 1}")
                st.metric("Undercut Gain", f"{res_undercut['undercut_gain_secs']:.3f}s", "Outlap Delta")
            with c_m2:
                st.metric("Chaser Fresh Tyre Pace", f"{res_undercut['chaser_lap_time_fresh']:.2f}s", f"New {chase_fresh_compound}")
                st.metric("Resulting Gap Post-Pit", f"{res_undercut['predicted_gap_secs']:.3f}s", "Overtake if negative")

# ================= TAB 4: MULTI-AGENT SIMULATOR =================
with tab4:
    st.markdown("### Multi-Driver Strategy Race Simulator")
    st.markdown("Simulate a lap-by-lap race under dynamic track conditions (Safety Cars and rain weather).")
    
    col_sim1, col_sim2 = st.columns([0.4, 0.6])
    with col_sim1:
        st.markdown("#### Driver Stint Strategies")
        
        if st.session_state['session_loaded']:
            drivers_df = st.session_state['drivers_list']
            driver_abbrs = list(drivers_df['Abbreviation'].unique())
        else:
            driver_abbrs = ["VER", "HAM", "NOR", "LEC", "SAI", "ALO"]
            
        # Let the user select which drivers to run in the simulator
        selected_sim_drivers = st.multiselect(
            "Select Drivers to Simulate", 
            driver_abbrs, 
            default=["VER", "HAM", "NOR"][:len(driver_abbrs)]
        )
        
        # Helper to parse laps list input
        def parse_laps(laps_str):
            if not laps_str.strip():
                return []
            try:
                return [int(x.strip()) for x in laps_str.split(',')]
            except:
                return []
                
        # Generate input widgets dynamically for each selected driver
        drivers_configs = {}
        for driver in selected_sim_drivers:
            with st.expander(f"Strategy Config: {driver}", expanded=True):
                # Side-by-side stint compounds and pit lap inputs
                c1, c2 = st.columns(2)
                with c1:
                    stints = st.multiselect(
                        f"Tyres", ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE"], 
                        default=["MEDIUM", "HARD"][:len(driver_abbrs)] if len(driver_abbrs) >= 2 else ["MEDIUM"], 
                        key=f"stints_{driver}"
                    )
                with c2:
                    pits_str = st.text_input(
                        f"Pit Laps", 
                        value="20", 
                        key=f"pits_{driver}"
                    )
                
                drivers_configs[driver] = {
                    'compounds': stints,
                    'pit_laps': parse_laps(pits_str)
                }
        
        st.markdown("#### Dynamic Events")
        sc_input = st.text_input("Safety Car Laps (comma separated)", value="35,36,37")
        sc_laps = parse_laps(sc_input)
        
        rain_active = st.checkbox("Trigger Rain Weather", value=True)
        if rain_active:
            rain_lap = st.number_input("Rain Begins on Lap", 1, 52, value=42)
            rain_intensity = st.selectbox("Rain Severity", ["LIGHT", "HEAVY"])
        else:
            rain_lap = None
            rain_intensity = None
            
        run_sim = st.button("Start Race Simulation", type="primary")
        
    with col_sim2:
        st.markdown("Live Telemetry Sim Board")
        if run_sim:
            with st.spinner("Simulating telemetry ticks..."):
                simulator = RaceSimulator(optimizer)
                # Retrieve stored driver offsets from session state
                offsets = st.session_state.get('driver_offsets', None)
                
                df_history, states = simulator.run_race_simulation(
                    drivers_configs=drivers_configs,
                    total_laps=52,
                    sc_laps=sc_laps,
                    rain_lap=rain_lap,
                    rain_intensity=rain_intensity,
                    driver_offsets=offsets  # Pass the offsets here!
                )
                
                # Standings dataframe display
                final_lap = df_history[df_history['LapNumber'] == 52].sort_values('Position')
                
                st.markdown("Final Standings")
                standings_data = []
                for _, row in final_lap.iterrows():
                    standings_data.append({
                        'Pos': row['Position'],
                        'Driver': row['Driver'],
                        'Final Tyre': row['Compound'].upper(),
                        'Race Time': f"{row['CumulativeTime'] / 60.0:.2f} mins",
                        'Gap to Winner': "Leader" if row['Position'] == 1 else f"+{row['GapToLeader']:.2f}s"
                    })
                st.dataframe(pd.DataFrame(standings_data), width='stretch')
                
                # Plot position history chart
                fig_pos = go.Figure()
                for driver in drivers_configs.keys():
                    df_drv = df_history[df_history['Driver'] == driver].sort_values('LapNumber')
                    team_color = get_driver_color(driver)
                    fig_pos.add_trace(go.Scatter(
                        x=df_drv['LapNumber'],
                        y=df_drv['Position'],
                        mode='lines+markers',
                        name=driver,
                        line=dict(color=team_color, width=2)
                    ))
                fig_pos.update_yaxes(title="Position", tickvals=[1, 2, 3], range=[3.2, 0.8])
                fig_pos.update_xaxes(title="Race Lap")
                fig_pos = apply_premium_layout(fig_pos, "Lap-by-Lap Position Tracker")
                st.plotly_chart(fig_pos, use_container_width=True)
                
                # Plot lap times comparison chart
                fig_ltimes = go.Figure()
                for driver in drivers_configs.keys():
                    df_drv = df_history[df_history['Driver'] == driver].sort_values('LapNumber')
                    team_color = get_driver_color(driver)
                    fig_ltimes.add_trace(go.Scatter(
                        x=df_drv['LapNumber'],
                        y=df_drv['LapTime'],
                        mode='lines',
                        name=f"{driver} Lap Time",
                        line=dict(color=team_color, width=1.5)
                    ))
                fig_ltimes.update_layout(yaxis_title="Lap Time (s)", xaxis_title="Race Lap")
                fig_ltimes = apply_premium_layout(fig_ltimes, "Race Lap Times Comparison")
                st.plotly_chart(fig_ltimes, use_container_width=True)
        else:
            st.info("Set driver tyre strategies and dynamic weather triggers on the left, then click 'Start Race Simulation' to view the outcome.")

# ================= TAB 5: AI STRATEGY ASSISTANT =================
with tab5:
    st.markdown("###Pit Wall AI Strategy Assistant")
    st.markdown("Ask the AI Race Engineer questions about race strategies, undercut threats, or track weather conditions.")
    
    # Initialize chat history in session state
    if 'chat_messages' not in st.session_state:
        st.session_state['chat_messages'] = [
            {"role": "assistant", "content": "**[RADIO COMM]:** Copy that. F1 AI Race Engineer online. Ask me about track weather, undercut threats, or optimal pit strategies."}
        ]
        
    # Render chat history
    for msg in st.session_state['chat_messages']:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])
            
    # Interactive chat input box
    user_query = st.chat_input("Ask a question (e.g., 'What is the fastest strategy?', 'Are we safe from undercut?')")
    
    if user_query:
        # Render user message
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state['chat_messages'].append({"role": "user", "content": user_query})
        
        # Parse query keywords
        query_lower = user_query.lower()
        response = ""
        
        optimizer = st.session_state.get('optimizer', None)
        undercut_analyzer = st.session_state.get('undercut_analyzer', None)
        
        # Try to pull weather logs if a session is loaded
        weather = get_session_weather(st.session_state['session_obj']) if st.session_state.get('session_obj', None) else None
        
        # Heuristics/Routing based on query content
        if "strategy" in query_lower or "pit stop" in query_lower or "stint" in query_lower:
            if optimizer:
                with st.spinner("Simulating stint profiles..."):
                    results = optimizer.find_best_strategies(total_laps=52)
                    best = results[0]
                    total_duration = best['total_time_secs'] / 60.0
                    response = f"**[PIT WALL AI]:** The mathematically fastest strategy is a **1-stop {best['strategy_name']}**.\n\n" \
                               f"- **Optimal Pit Window:** Lap {best['optimal_pit_lap']}\n" \
                               f"- **Predicted Race Duration:** {total_duration:.2f} minutes\n\n" \
                               f"We recommend starting on the {best['strategy_name'].split(' -> ')[0]} compound to maximize grip off the line."
            else:
                response = "I don't have an active ML model to calculate strategies. Please connect to a Grand Prix in the sidebar first to train the AI."
                
        elif "undercut" in query_lower or "threat" in query_lower or "gap" in query_lower:
            if undercut_analyzer:
                # Run analyzer on baseline values
                res_u = undercut_analyzer.analyze_undercut_potential(
                    gap_seconds=1.2,
                    lap_number=25,
                    tyre_age_leader=15,
                    compound_leader='MEDIUM',
                    compound_chaser_fresh='HARD'
                )
                response = f"**[TELEMETRY DECAY ANALYSIS]:**\n\n" \
                           f"- **Current Threat Level:** `{res_u['threat_level']}`\n" \
                           f"- **Predicted Out-lap Gain:** {res_u['undercut_gain_secs']:.3f} seconds\n" \
                           f"- **Action Required:** {res_u['recommendation']}\n\n" \
                           f"*(Calculated using baseline parameters: 1.2s gap, leader tyre age 15 on Mediums, chaser pitting for fresh Hards)*"
            else:
                response = "I cannot analyze undercut threat without an active session. Please connect in the sidebar."
                
        elif "weather" in query_lower or "temp" in query_lower or "rain" in query_lower:
            if weather:
                rain_msg = "Rain detected on track! Pit wall needs to monitor intermediate tire windows." if weather['Rainfall'] else "Dry track conditions expected."
                response = f"**[METEOROLOGY DEP]:** Track Weather Report:\n\n" \
                           f"-**Track Temp:** {weather['TrackTemp']:.1f} °C\n" \
                           f"-**Air Temp:** {weather['AirTemp']:.1f} °C\n" \
                           f"-**Humidity:** {weather['Humidity']:.1f} %\n" \
                           f"-**Wind Speed:** {weather['WindSpeed']:.1f} km/h\n" \
                           f"-**Status:** {rain_msg}"
            else:
                response = "Weather telemetry is offline. Please load a session in the sidebar first."
                
        else:
            response = "Understand. Please ask a specific strategy question, such as:\n" \
                       "- *'What is the fastest strategy?'*\n" \
                       "- *'Is the chaser an undercut threat?'*\n" \
                       "- *'What are the weather conditions?'*"
                       
        # Render assistant response
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state['chat_messages'].append({"role": "assistant", "content": response})

# Footer section
st.markdown(
    """
    <div class="footer-text">
        FormulaMind — AI F1 Strategy Platform | Built with FastF1 API, Plotly & Streamlit | Powered by Scikit-Learn
    </div>
    """, 
    unsafe_allow_html=True
)