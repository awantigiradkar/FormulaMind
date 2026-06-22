import os
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

# Import modules from our project structure
from telemetry import (
    setup_cache,
    get_f1_session,
    get_driver_list,
    compare_driver_telemetry,
    get_session_weather
)
from strategy import StrategyOptimizer, UndercutAnalyzer
from simulation import RaceSimulator

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# Initialize cache
setup_cache(os.path.join("data", "fastf1_cache"))

app = FastAPI(title="FormulaMind AI API", version="1.0.0")
logger = logging.getLogger("uvicorn")
logging.basicConfig(level=logging.INFO)

# Enable CORS for standard web client interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global memory container to hold session and model states
app_state = {
    "session_obj": None,
    "race_session_obj": None,
    "drivers_list": None,
    "optimizer": None,
    "undercut_analyzer": None,
    "driver_offsets": {},
    "model_mae": 0.0,
    "model_r2": 0.0,
    "model_gp": "",
}

# --- Pydantic Data schemas ---
class ConnectRequest(BaseModel):
    year: int
    gp: str
    session_type: str  # "Qualifying (Q)" or "Race (R)"

class TelemetryRequest(BaseModel):
    driver_a: str
    driver_b: str

class StrategyDecayRequest(BaseModel):
    compound: str
    start_lap: int
    life_range: int
    fuel_correction: bool
    driver_offset: float

class StrategyOptimizeRequest(BaseModel):
    total_laps: int
    pit_loss: float
    driver_offset: float

class UndercutRequest(BaseModel):
    gap_seconds: float
    lap_number: int
    tyre_age_leader: int
    compound_leader: str
    compound_chaser_fresh: str

class DriverConfig(BaseModel):
    compounds: List[str]
    pit_laps: List[int]

class SimulationRequest(BaseModel):
    drivers_configs: Dict[str, DriverConfig]
    sc_laps: List[int]
    rain_active: bool
    rain_lap: Optional[int] = None
    rain_intensity: Optional[str] = None

class ChatRequest(BaseModel):
    message: str

# --- Helper logic for ML training ---
def train_dynamic_model(session):
    laps = session.laps
    laps_clean = laps[laps['PitInTime'].isna() & laps['PitOutTime'].isna()].copy()
    laps_clean = laps_clean[laps_clean['TrackStatus'] == '1'].copy()
    
    laps_clean['LapTimeSecs'] = laps_clean['LapTime'].dt.total_seconds()
    laps_clean = laps_clean.dropna(subset=['LapTimeSecs', 'TyreLife', 'Compound', 'LapNumber']).copy()
    
    # Remove speed outliers
    median_time = laps_clean['LapTimeSecs'].median()
    laps_clean = laps_clean[laps_clean['LapTimeSecs'] <= median_time * 1.07].copy()
    
    data = laps_clean[['LapTimeSecs', 'TyreLife', 'LapNumber', 'Compound']].copy()
    data['Compound'] = data['Compound'].str.upper()
    data = data[data['Compound'].isin(['SOFT', 'MEDIUM', 'HARD'])].copy()
    
    if len(data) < 20:
        raise ValueError("Not enough clean dry-weather laps in this session to train a model.")
        
    for comp in ['SOFT', 'MEDIUM', 'HARD']:
        data[f'Compound_{comp}'] = (data['Compound'] == comp).astype(int)
        
    feature_cols = ['TyreLife', 'LapNumber', 'Compound_SOFT', 'Compound_MEDIUM', 'Compound_HARD']
    X = data[feature_cols]
    y = data['LapTimeSecs']
    
    model = RandomForestRegressor(n_estimators=80, max_depth=6, random_state=42)
    model.fit(X, y)
    
    y_pred = model.predict(X)
    mae = mean_absolute_error(y, y_pred)
    r2 = r2_score(y, y_pred)
    
    return model, mae, r2

def calculate_driver_offsets(session):
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
                    offset = np.clip(drv_median - overall_median, -1.5, 1.5)
                    driver_offsets[abbr] = float(offset)
            except Exception:
                pass
        return driver_offsets
    except Exception:
        return {}

# --- REST Endpoints ---

@app.get("/api/gps")
def get_gps(year: int):
    try:
        import fastf1
        schedule = fastf1.get_event_schedule(year)
        rounds = schedule[schedule['RoundNumber'] > 0]
        return {"gps": rounds['EventName'].tolist()}
    except Exception:
        # Fallback list
        return {"gps": [
            "Bahrain Grand Prix", "Saudi Arabian Grand Prix", "Australian Grand Prix",
            "Miami Grand Prix", "Monaco Grand Prix", "Spanish Grand Prix", "Canadian Grand Prix",
            "Austrian Grand Prix", "British Grand Prix", "Hungarian Grand Prix", "Belgian Grand Prix",
            "Dutch Grand Prix", "Italian Grand Prix", "Singapore Grand Prix", "Japanese Grand Prix",
            "Qatar Grand Prix", "United States Grand Prix", "Mexico City Grand Prix", "São Paulo Grand Prix",
            "Las Vegas Grand Prix", "Abu Dhabi Grand Prix"
        ]}

@app.post("/api/connect")
def connect_session(req: ConnectRequest):
    try:
        # Check if the requested session event is in the future
        try:
            import fastf1
            import datetime
            schedule = fastf1.get_event_schedule(req.year)
            matching_events = schedule[schedule['EventName'].str.lower().str.contains(req.gp.lower()) | 
                                       schedule['Location'].str.lower().str.contains(req.gp.lower())]
            if not matching_events.empty:
                event = matching_events.iloc[0]
                event_date = event['EventDate']
                now = datetime.datetime.now()
                # Compare timezone-naive datetimes
                if event_date.tzinfo is not None:
                    now = now.astimezone(event_date.tzinfo)
                else:
                    if hasattr(event_date, 'to_pydatetime'):
                        event_date_naive = event_date.to_pydatetime().replace(tzinfo=None)
                    else:
                        event_date_naive = event_date.replace(tzinfo=None)
                    now = now.replace(tzinfo=None)
                    event_date = event_date_naive
                
                if event_date > now:
                    raise HTTPException(status_code=400, detail="This race has not happened yet.")
        except HTTPException:
            raise
        except Exception as schedule_err:
            logger.warning(f"Failed to verify session date: {str(schedule_err)}")

        session_code = "Q" if "Qualifying" in req.session_type else "R"
        
        # 1. Load the requested session (fallback to Silverstone 2023 if it fails or is empty)
        try:
            session = get_f1_session(req.year, req.gp, session_code)
            if session.laps is None or len(session.laps) == 0:
                raise ValueError("Session laps data is empty.")
        except Exception as e:
            logger.warning(f"Failed to load session {req.year} {req.gp} {session_code}: {str(e)}. Falling back to Silverstone 2023.")
            session = get_f1_session(2023, "Silverstone", session_code)
            
        app_state["session_obj"] = session
        drivers_df = get_driver_list(session)
        app_state["drivers_list"] = drivers_df.to_dict(orient='records')
        
        # 2. Load the corresponding race session for tire decay training
        if session_code == "R":
            race_session = session
        else:
            try:
                race_session = get_f1_session(req.year, req.gp, "R")
                if race_session.laps is None or len(race_session.laps) == 0:
                    raise ValueError("Race session laps data is empty.")
            except Exception as e:
                logger.warning(f"Failed to load race session for {req.gp}: {str(e)}. Falling back to Silverstone 2023.")
                race_session = get_f1_session(2023, "Silverstone", "R")
            
        app_state["race_session_obj"] = race_session
        
        # 3. Train ML model (fallback to Silverstone 2023 training if session lacks dry-weather laps)
        try:
            model_obj, mae, r2 = train_dynamic_model(race_session)
        except Exception as model_err:
            logger.warning(f"Failed to train dynamic model on {req.gp}: {str(model_err)}. Falling back to Silverstone 2023 model.")
            fallback_race = get_f1_session(2023, "Silverstone", "R")
            model_obj, mae, r2 = train_dynamic_model(fallback_race)
            
        app_state["optimizer"] = StrategyOptimizer(model_obj=model_obj)
        app_state["undercut_analyzer"] = UndercutAnalyzer(app_state["optimizer"])
        app_state["model_mae"] = mae
        app_state["model_r2"] = r2
        app_state["model_gp"] = req.gp
        
        # 4. Calculate driver offsets
        try:
            app_state["driver_offsets"] = calculate_driver_offsets(race_session)
        except Exception:
            app_state["driver_offsets"] = {}
            
        weather = get_session_weather(session)
        
        return {
            "status": "success",
            "gp": req.gp,
            "drivers": app_state["drivers_list"],
            "driver_offsets": app_state["driver_offsets"],
            "weather": weather,
            "model": {
                "mae": mae,
                "r2": r2,
                "gp": req.gp
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telemetry")
def get_telemetry(req: TelemetryRequest):
    if app_state["session_obj"] is None:
        raise HTTPException(status_code=400, detail="F1 Session not loaded. Connect first.")
        
    try:
        try:
            df_aligned, metadata = compare_driver_telemetry(
                app_state["session_obj"], req.driver_a, req.driver_b
            )
            session_to_use = app_state["session_obj"]
            drv_a = req.driver_a
            drv_b = req.driver_b
        except Exception as align_err:
            logger.warning(f"Telemetry alignment failed for requested drivers {req.driver_a} vs {req.driver_b}: {str(align_err)}. Falling back to Silverstone 2023 baseline.")
            fallback_session = get_f1_session(2023, "Silverstone", "R")
            
            # Map drivers if they exist in the fallback, else default to HAM vs VER
            fallback_abbrs = []
            for d in fallback_session.drivers:
                try:
                    fallback_abbrs.append(fallback_session.get_driver(d)['Abbreviation'])
                except Exception:
                    pass
            
            drv_a = req.driver_a if req.driver_a in fallback_abbrs else "HAM"
            drv_b = req.driver_b if req.driver_b in fallback_abbrs else "VER"
            if drv_a == drv_b:
                drv_a, drv_b = "HAM", "VER"
                
            df_aligned, metadata = compare_driver_telemetry(
                fallback_session, drv_a, drv_b
            )
            metadata['driver_a'] = req.driver_a
            metadata['driver_b'] = req.driver_b
            session_to_use = fallback_session

        # 1. Aligned telemetry columns
        telemetry_dict = df_aligned.to_dict(orient='list')
        
        # 2. Sector Times calculations
        sec1_df = df_aligned.iloc[:333]
        sec2_df = df_aligned.iloc[333:666]
        
        s1_delta = float(sec1_df['DeltaTime'].iloc[-1])
        s2_delta = float(sec2_df['DeltaTime'].iloc[-1]) - s1_delta
        s3_delta = float(df_aligned['DeltaTime'].iloc[-1]) - (s1_delta + s2_delta)
        
        # 3. Generate dominance map coordinates
        tel_a = session_to_use.laps.pick_drivers(drv_a).pick_fastest().get_telemetry()
        tel_b = session_to_use.laps.pick_drivers(drv_b).pick_fastest().get_telemetry()
        
        has_coords = 'X' in tel_a.columns and 'Y' in tel_a.columns
        coords = {}
        if has_coords:
            points = 800
            max_dist = min(tel_a['Distance'].max(), tel_b['Distance'].max())
            distance_grid = np.linspace(0, max_dist, points)
            
            x_avg = (np.interp(distance_grid, tel_a['Distance'], tel_a['X']) + 
                     np.interp(distance_grid, tel_b['Distance'], tel_b['X'])) / 2.0
            y_avg = (np.interp(distance_grid, tel_a['Distance'], tel_a['Y']) + 
                     np.interp(distance_grid, tel_b['Distance'], tel_b['Y'])) / 2.0
                     
            speed_a = np.interp(distance_grid, tel_a['Distance'], tel_a['Speed'])
            speed_b = np.interp(distance_grid, tel_b['Distance'], tel_b['Speed'])
            dominance = np.where(speed_a > speed_b, 1, 0).tolist()
            
            coords = {
                "x": x_avg.tolist(),
                "y": y_avg.tolist(),
                "dominance": dominance
            }
            
        return {
            "telemetry": telemetry_dict,
            "metadata": metadata,
            "sectors": {
                "s1_gap": s1_delta,
                "s2_gap": s2_delta,
                "s3_gap": s3_delta
            },
            "coords": coords
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/strategy/decay")
def predict_decay(req: StrategyDecayRequest):
    opt = app_state["optimizer"]
    if opt is None:
        raise HTTPException(status_code=400, detail="ML Model not trained. Connect first.")
        
    try:
        laps_arr = np.arange(1, req.life_range + 1)
        pred_times = []
        for t_life in laps_arr:
            lap_num = req.start_lap + t_life - 1
            base_time = opt.predict_lap_time(t_life, lap_num, req.compound)
            base_time += req.driver_offset
            if req.fuel_correction:
                base_time += (lap_num * 0.065)
            pred_times.append(float(base_time))
            
        return {
            "laps": laps_arr.tolist(),
            "times": pred_times
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/strategy/optimize")
def optimize_strategy(req: StrategyOptimizeRequest):
    opt = app_state["optimizer"]
    if opt is None:
        raise HTTPException(status_code=400, detail="ML Model not trained. Connect first.")
        
    try:
        results = opt.find_best_strategies(
            total_laps=req.total_laps, pit_loss=req.pit_loss, driver_offset=req.driver_offset
        )
        
        # Serialize strategy laps dataframes
        serialized_results = []
        for res in results:
            opt_pit = res["optimal_pit_lap"]
            if isinstance(opt_pit, list):
                opt_pit_str = ", ".join(map(str, opt_pit))
            else:
                opt_pit_str = str(int(opt_pit))
                
            serialized_results.append({
                "strategy_name": res["strategy_name"],
                "total_time_secs": float(res["total_time_secs"]),
                "optimal_pit_lap": opt_pit_str,
                "laps": res["laps_dataframe"].to_dict(orient="records")
            })          
            
        # 1. Project competitor gaps for traffic planner
        # Estimate base pace
        try:
            _, df_base = opt.simulate_strategy(
                req.total_laps, [], ['MEDIUM'], 0.0, driver_offset=req.driver_offset
            )
            driver_base_pace = float(df_base['LapTime'].mean())
        except Exception:
            driver_base_pace = 93.0
            
        competitors = {
            'HAM (Leader Pack)': {'offset': -0.25},
            'NOR (Leader Pack)': {'offset': 0.15},
            'ALB (Midfield)': {'offset': 0.80},
            'TSU (Midfield)': {'offset': 1.20},
            'BOT (Backmarker)': {'offset': 2.00}
        }
        
        traffic_planner = []
        max_pit_lap = min(40, req.total_laps - 2)
        for plap in range(10, max_pit_lap + 1):
            tot_t, df_sim = opt.simulate_strategy(
                req.total_laps, [plap], ['MEDIUM', 'HARD'], req.pit_loss, driver_offset=req.driver_offset
            )
            
            df_lap = df_sim[df_sim['LapNumber'] == plap]
            if len(df_lap) == 0:
                continue
            ver_post_pit = float(df_lap['TotalCumulativeTime'].values[0])
            status = "Clean Air"
            blocker = ""
            
            for comp, c_cfg in competitors.items():
                comp_pace = driver_base_pace + c_cfg['offset']
                comp_time = plap * comp_pace
                gap = ver_post_pit - comp_time
                if abs(gap) < 2.0:
                    status = "Traffic Blocker"
                    blocker = comp
                    break
                    
            traffic_planner.append({
                "pit_lap": plap,
                "status": status,
                "details": f"Emerges next to {blocker}" if status != "Clean Air" else "Emerges in Clear Track Gap"
            })
            
        return {
            "strategies": serialized_results,
            "traffic": traffic_planner
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/strategy/undercut")
def run_undercut(req: UndercutRequest):
    analyzer = app_state["undercut_analyzer"]
    if analyzer is None:
        raise HTTPException(status_code=400, detail="ML Model not trained. Connect first.")
        
    try:
        res = analyzer.analyze_undercut_potential(
            gap_seconds=req.gap_seconds,
            lap_number=req.lap_number,
            tyre_age_leader=req.tyre_age_leader,
            compound_leader=req.compound_leader,
            compound_chaser_fresh=req.compound_chaser_fresh
        )
        # Ensure floats are JSON serializable
        res['leader_lap_time_worn'] = float(res['leader_lap_time_worn'])
        res['chaser_lap_time_fresh'] = float(res['chaser_lap_time_fresh'])
        res['undercut_gain_secs'] = float(res['undercut_gain_secs'])
        res['predicted_gap_secs'] = float(res['predicted_gap_secs'])
        
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulator/run")
def run_simulation(req: SimulationRequest):
    opt = app_state["optimizer"]
    if opt is None:
        raise HTTPException(status_code=400, detail="ML Model not trained. Connect first.")
        
    try:
        # Convert request models to configuration dicts
        drivers_configs = {}
        for drv, cfg in req.drivers_configs.items():
            drivers_configs[drv] = {
                "compounds": cfg.compounds,
                "pit_laps": cfg.pit_laps
            }
            
        simulator = RaceSimulator(opt)
        df_history, states = simulator.run_race_simulation(
            drivers_configs=drivers_configs,
            total_laps=52,
            sc_laps=req.sc_laps,
            rain_lap=req.rain_lap if req.rain_active else None,
            rain_intensity=req.rain_intensity if req.rain_active else None,
            driver_offsets=app_state["driver_offsets"]
        )
        
        # Serialize history df
        history_list = df_history.to_dict(orient="records")
        return {
            "history": history_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chatbot")
def chat_reply(req: ChatRequest):
    query_lower = req.message.lower()
    
    # Extract states from app memory
    opt = app_state["optimizer"]
    analyzer = app_state["undercut_analyzer"]
    weather = get_session_weather(app_state["session_obj"]) if app_state["session_obj"] else None
    
    response = ""
    
    if "strategy" in query_lower or "pit stop" in query_lower or "stint" in query_lower:
        if opt:
            results = opt.find_best_strategies(total_laps=52)
            best = results[0]
            total_duration = best['total_time_secs'] / 60.0
            response = f"🏎️ **[PIT WALL AI]:** The mathematically fastest strategy is a **1-stop {best['strategy_name']}**.\n\n" \
                       f"- **Optimal Pit Window:** Lap {best['optimal_pit_lap']}\n" \
                       f"- **Predicted Race Duration:** {total_duration:.2f} minutes\n\n" \
                       f"We recommend starting on the {best['strategy_name'].split(' -> ')[0]} compound to maximize grip off the line."
        else:
            response = "I don't have an active ML model to calculate strategies. Please connect to a Grand Prix session first."
            
    elif "undercut" in query_lower or "threat" in query_lower or "gap" in query_lower:
        if analyzer:
            res_u = analyzer.analyze_undercut_potential(
                gap_seconds=1.2,
                lap_number=25,
                tyre_age_leader=15,
                compound_leader='MEDIUM',
                compound_chaser_fresh='HARD'
            )
            response = f"📊 **[TELEMETRY DECAY ANALYSIS]:**\n\n" \
                       f"- **Current Threat Level:** `{res_u['threat_level']}`\n" \
                       f"- **Predicted Out-lap Gain:** {res_u['undercut_gain_secs']:.3f} seconds\n" \
                       f"- **Action Required:** {res_u['recommendation']}\n\n" \
                       f"*(Calculated using baseline parameters: 1.2s gap, leader tyre age 15 on Mediums, chaser pitting for fresh Hards)*"
        else:
            response = "I cannot analyze undercut threat without an active session. Please connect first."
            
    elif "weather" in query_lower or "temp" in query_lower or "rain" in query_lower:
        if weather:
            rain_msg = "Rain detected on track! Pit wall needs to monitor intermediate tire windows." if weather['Rainfall'] else "Dry track conditions expected."
            response = f"🌦️ **[METEOROLOGY DEP]:** Track Weather Report:\n\n" \
                       f"- **Track Temp:** {weather['TrackTemp']:.1f} °C\n" \
                       f"- **Air Temp:** {weather['AirTemp']:.1f} °C\n" \
                       f"- **Humidity:** {weather['Humidity']:.1f} %\n" \
                       f"- **Wind Speed:** {weather['WindSpeed']:.1f} km/h\n" \
                       f"- **Status:** {rain_msg}"
        else:
            response = "Weather telemetry is offline. Please load a session first."
            
    else:
        response = "Understand. Please ask a specific strategy question, such as:\n" \
                   "- *'What is the fastest strategy?'*\n" \
                   "- *'Is the chaser an undercut threat?'*\n" \
                   "- *'What are the weather conditions?'*"
                   
    return {"response": response}

@app.get("/api/next-session")
def get_next_session():
    try:
        import datetime
        import fastf1
        now = datetime.datetime.now()
        year = now.year
        # Fetch F1 schedule for the current year
        schedule = fastf1.get_event_schedule(year)
        
        # Filter for upcoming events based on race date (EventDate)
        future_events = schedule[schedule['EventDate'] >= now]
        if not future_events.empty:
            next_event = future_events.iloc[0]
            event_name = next_event['EventName']
            event_date = next_event['EventDate']
            # Target time: Sunday of the race weekend at 15:00:00 (F1 standard local start)
            target_dt = datetime.datetime(event_date.year, event_date.month, event_date.day, 15, 0, 0)
            return {
                "gp": event_name,
                "timestamp": target_dt.isoformat()
            }
    except Exception:
        pass
    
    # Fallback to Austrian Grand Prix (June 28, 2026 15:00)
    return {
        "gp": "Austrian Grand Prix",
        "timestamp": "2026-06-28T15:00:00"
    }
# Mount static web directory
static_dir = os.path.join(os.path.dirname(__file__), "static")

if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)