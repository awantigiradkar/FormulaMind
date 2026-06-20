"""
Handles fetching F1 session data using FastF1, caching, data cleaning,
and distance-based interpolation for comparing driver telemetry.
"""

import os
import logging
import fastf1
import pandas as pd
import numpy as np

# Configure logging to keep track of telemetry fetching progress
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default Cache Directory
DEFAULT_CACHE_DIR = os.path.join("data", "fastf1_cache")

def setup_cache(cache_dir=DEFAULT_CACHE_DIR):
    """
    Enables FastF1 cache in the specified directory.
    Creates the folder if it does not exist to avoid re-downloading large datasets.
    """
    try:
        os.makedirs(cache_dir, exist_ok=True)
        fastf1.Cache.enable_cache(cache_dir)
        logger.info(f"FastF1 cache enabled at: {cache_dir}")
    except Exception as e:
        logger.error(f"Failed to enable FastF1 cache: {str(e)}")
        # In newer versions of FastF1, cache is managed via fastf1.api.Cache
        try:
            from fastf1 import api
            api.Cache.enable_cache(cache_dir)
            logger.info(f"FastF1 API cache fallback enabled at: {cache_dir}")
        except Exception as e_inner:
            logger.error(f"Fallback cache setup failed: {str(e_inner)}")

def get_f1_session(year: int, gp: str, session_type: str):
    """
    Loads an F1 session (cached if already downloaded).
    session_type can be: 'R' (Race), 'Q' (Qualifying), 'FP1', 'FP2', 'FP3'
    """
    setup_cache()
    logger.info(f"Loading session: {year} - {gp} - {session_type}")
    try:
        session = fastf1.get_session(year, gp, session_type)
        session.load()
        return session
    except Exception as e:
        logger.error(f"Error loading session {year} {gp} {session_type}: {str(e)}")
        raise e

def get_driver_list(session):
    """
    Returns a DataFrame of all drivers in the session.
    """
    drivers = session.drivers
    driver_data = []
    for d in drivers:
        try:
            info = session.get_driver(d)
            driver_data.append({
                'DriverNumber': d,
                'Abbreviation': info['Abbreviation'],
                'FullName': info['FullName'],
                'TeamName': info['TeamName'],
                'TeamColor': info['TeamColor']
            })
        except Exception as e:
            logger.warning(f"Could not load driver info for driver number {d}: {str(e)}")
    return pd.DataFrame(driver_data)

def get_lap_telemetry(session, driver_abbr: str, lap_number=None):
    """
    Retrieves telemetry data for a specific driver's lap.
    If lap_number is None, fetches their fastest lap in the session.
    """
    try:
        # Filter laps by driver
        driver_laps = session.laps.pick_drivers(driver_abbr)
        if len(driver_laps) == 0:
            raise ValueError(f"No laps found for driver {driver_abbr}")
        
        if lap_number is None:
            # Get fastest lap
            lap = driver_laps.pick_fastest()
            lap_number = int(lap['LapNumber'])
            logger.info(f"Selected fastest lap ({lap_number}) for {driver_abbr}")
        else:
            lap = driver_laps[driver_laps['LapNumber'] == lap_number].iloc[0]
            logger.info(f"Selected lap {lap_number} for {driver_abbr}")
            
        telemetry = lap.get_telemetry()
        
        # Add metadata properties directly to telemetry DataFrame
        telemetry['Driver'] = driver_abbr
        telemetry['LapNumber'] = lap_number
        telemetry['Compound'] = lap['Compound']
        telemetry['Stint'] = lap['Stint']
        telemetry['LapTime'] = lap['LapTime'].total_seconds() if pd.notnull(lap['LapTime']) else None
        
        return telemetry, lap
    except Exception as e:
        logger.error(f"Error retrieving telemetry for {driver_abbr} (Lap: {lap_number}): {str(e)}")
        raise e

def compare_driver_telemetry(session, driver_a: str, driver_b: str, lap_a=None, lap_b=None, points=1000):
    """
    Fetches telemetry for two drivers and interpolates them onto a common distance grid.
    Calculates a continuous delta time gap between the two.
    
    Returns:
        pd.DataFrame containing aligned telemetry, and a metadata dictionary.
    """
    # 1. Fetch telemetry
    tel_a, lap_obj_a = get_lap_telemetry(session, driver_a, lap_a)
    tel_b, lap_obj_b = get_lap_telemetry(session, driver_b, lap_b)
    
    # 2. Establish distance grid
    max_dist_a = tel_a['Distance'].max()
    max_dist_b = tel_b['Distance'].max()
    max_distance = min(max_dist_a, max_dist_b)  # Limit to the shorter lap to prevent interpolation overflow
    
    distance_grid = np.linspace(0, max_distance, points)
    
    # 3. Interpolate variables for Driver A
    speed_a = np.interp(distance_grid, tel_a['Distance'], tel_a['Speed'])
    throttle_a = np.interp(distance_grid, tel_a['Distance'], tel_a['Throttle'])
    brake_a = np.interp(distance_grid, tel_a['Distance'], tel_a['Brake'].astype(float))
    gear_a = np.interp(distance_grid, tel_a['Distance'], tel_a['nGear'])
    rpm_a = np.interp(distance_grid, tel_a['Distance'], tel_a['RPM'])
    drs_a = np.interp(distance_grid, tel_a['Distance'], tel_a['DRS']) if 'DRS' in tel_a.columns else np.zeros(points)
    
    # 4. Interpolate variables for Driver B
    speed_b = np.interp(distance_grid, tel_b['Distance'], tel_b['Speed'])
    throttle_b = np.interp(distance_grid, tel_b['Distance'], tel_b['Throttle'])
    brake_b = np.interp(distance_grid, tel_b['Distance'], tel_b['Brake'].astype(float))
    gear_b = np.interp(distance_grid, tel_b['Distance'], tel_b['nGear'])
    rpm_b = np.interp(distance_grid, tel_b['Distance'], tel_b['RPM'])
    drs_b = np.interp(distance_grid, tel_b['Distance'], tel_b['DRS']) if 'DRS' in tel_b.columns else np.zeros(points)
    
    # 5. Calculate Delta Time (dynamic time gap along the lap)
    delta_time = np.zeros(points)
    try:
        # Time = Distance / Speed. Convert speed from km/h to m/s: (Speed / 3.6)
        speed_a_m_s = np.clip(speed_a / 3.6, 1.0, 100.0) # Clip to avoid division by zero or negative values
        speed_b_m_s = np.clip(speed_b / 3.6, 1.0, 100.0)
        
        dx = distance_grid[1] - distance_grid[0]
        
        time_a = np.cumsum(dx / speed_a_m_s)
        time_b = np.cumsum(dx / speed_b_m_s)
        
        # Delta: A relative to B (negative means A is faster/ahead)
        delta_time = time_a - time_b
    except Exception as e:
        logger.warning(f"Fallback delta time computation failed: {str(e)}")

    # 6. Combine into aligned DataFrame
    df_aligned = pd.DataFrame({
        'Distance': distance_grid,
        f'Speed_{driver_a}': speed_a,
        f'Speed_{driver_b}': speed_b,
        f'Throttle_{driver_a}': throttle_a,
        f'Throttle_{driver_b}': throttle_b,
        f'Brake_{driver_a}': brake_a,
        f'Brake_{driver_b}': brake_b,
        f'Gear_{driver_a}': np.round(gear_a).astype(int),
        f'Gear_{driver_b}': np.round(gear_b).astype(int),
        f'RPM_{driver_a}': rpm_a,
        f'RPM_{driver_b}': rpm_b,
        f'DRS_{driver_a}': drs_a,
        f'DRS_{driver_b}': drs_b,
        'DeltaTime': delta_time
    })
    
    metadata = {
        'driver_a': driver_a,
        'driver_b': driver_b,
        'lap_a': int(lap_obj_a['LapNumber']),
        'lap_b': int(lap_obj_b['LapNumber']),
        'lap_time_a': lap_obj_a['LapTime'].total_seconds() if pd.notnull(lap_obj_a['LapTime']) else None,
        'lap_time_b': lap_obj_b['LapTime'].total_seconds() if pd.notnull(lap_obj_b['LapTime']) else None,
        'team_a': session.get_driver(driver_a)['TeamName'],
        'team_b': session.get_driver(driver_b)['TeamName'],
    }
    
    return df_aligned, metadata

def get_session_weather(session):
    """
    Retrieves a summary of weather conditions recorded during the session.
    Returns average values for air temperature, track temperature, and humidity,
    plus a flag indicating if rain occurred.
    """
    try:
        wd = session.weather_data
        if wd.empty:
            return None
            
        summary = {
            'AirTemp': float(wd['AirTemp'].mean()),
            'TrackTemp': float(wd['TrackTemp'].mean()),
            'Humidity': float(wd['Humidity'].mean()),
            'WindSpeed': float(wd['WindSpeed'].mean()),
            'Rainfall': bool(wd['Rainfall'].any())
        }
        return summary
    except Exception:
        return None