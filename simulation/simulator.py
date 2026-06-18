"""
Race Simulation Engine
Simulates a multi-driver race lap-by-lap, modeling tire wear, fuel burn,
safety car periods, and dynamic rain weather events.
"""

import os
import pandas as pd
import numpy as np
from strategy.optimizer import StrategyOptimizer

class RaceSimulator:
    def __init__(self, optimizer=None):
        if optimizer is None:
            self.optimizer = StrategyOptimizer()
        else:
            self.optimizer = optimizer
            
    def run_race_simulation(self, 
                            drivers_configs: dict, 
                            total_laps: int = 52, 
                            pit_loss_normal: float = 20.0,
                            pit_loss_sc: float = 12.0,
                            sc_laps: list = None,
                            rain_lap: int = None,
                            rain_intensity: str = None):
        """
        Runs a lap-by-lap race simulation for multiple drivers under dynamic conditions.

        drivers_configs: dict mapping driver name -> strategy settings, e.g.:
            {
                'VER': {'compounds': ['MEDIUM', 'HARD', 'INTERMEDIATE'], 'pit_laps': [20, 42]}
            }
        sc_laps: list of lap numbers where a Safety Car is active.
        rain_lap: lap number when rain begins.
        rain_intensity: 'LIGHT' or 'HEAVY'
        """
        if sc_laps is None:
            sc_laps = []
            
        # Initialize the state for each driver
        driver_states = {}
        for driver, config in drivers_configs.items():
            driver_states[driver] = {
                'compounds': config['compounds'],
                'pit_laps': config['pit_laps'],
                'current_compound': config['compounds'][0],
                'tyre_life': 1,
                'stint': 1,
                'cumulative_time': 0.0,
                'lap_times': [],
                'compounds_history': []
            }
            
        lap_by_lap_history = []
        
        # Lap-by-lap simulation loop
        for lap in range(1, total_laps + 1):
            is_sc_active = lap in sc_laps
            is_raining = (rain_lap is not None) and (lap >= rain_lap)
            
            # 1. Compute lap times for each driver on this lap
            for driver, state in driver_states.items():
                compound = state['current_compound']
                tyre_life = state['tyre_life']
                
                # Predict base lap time on dry track
                base_lap_time = self.optimizer.predict_lap_time(tyre_life, lap, compound)
                
                final_lap_time = base_lap_time
                
                # Apply rain impacts
                if is_raining:
                    if compound in ['SOFT', 'MEDIUM', 'HARD']:
                        # Massive pace penalty on dry slick tires in the rain
                        penalty = 15.0 if rain_intensity == 'LIGHT' else 25.0
                        final_lap_time += penalty
                    else:
                        # Minor slowdown limit on rain tires on a wet track
                        wet_offset = 4.0 if compound == 'INTERMEDIATE' else 7.0
                        final_lap_time = base_lap_time + wet_offset
                else:
                    # Raining stopped/dry track, but driver on wet tires (overheating)
                    if compound in ['INTERMEDIATE', 'WET']:
                        final_lap_time += 12.0
                        
                # Apply Safety Car constant speed limit
                if is_sc_active:
                    final_lap_time = 120.0  # Under SC, everyone runs a slow 2-minute lap
                    
                # Check if driver is entering pit lane at the end of this lap
                is_pit_lap = lap in state['pit_laps']
                
                if is_pit_lap:
                    # Apply pit lane duration loss (Safety Car pits are cheaper!)
                    loss = pit_loss_sc if is_sc_active else pit_loss_normal
                    final_lap_time += loss
                    
                    state['lap_times'].append(final_lap_time)
                    state['cumulative_time'] += final_lap_time
                    state['compounds_history'].append(compound)
                    
                    # Swap tires for next lap
                    state['stint'] += 1
                    next_idx = min(state['stint'] - 1, len(state['compounds']) - 1)
                    state['current_compound'] = state['compounds'][next_idx]
                    state['tyre_life'] = 1
                else:
                    state['lap_times'].append(final_lap_time)
                    state['cumulative_time'] += final_lap_time
                    state['compounds_history'].append(compound)
                    state['tyre_life'] += 1
                    
            # 2. Dynamic standing ranking at the end of the lap
            standings = sorted(driver_states.keys(), key=lambda d: driver_states[d]['cumulative_time'])
            
            for rank, driver in enumerate(standings):
                driver_states[driver]['position'] = rank + 1
                
                # Calculate gap distance to leader
                leader_time = driver_states[standings[0]]['cumulative_time']
                my_time = driver_states[driver]['cumulative_time']
                gap_to_leader = my_time - leader_time
                
                lap_by_lap_history.append({
                    'LapNumber': lap,
                    'Driver': driver,
                    'Position': rank + 1,
                    'LapTime': driver_states[driver]['lap_times'][-1],
                    'CumulativeTime': my_time,
                    'GapToLeader': gap_to_leader,
                    'Compound': driver_states[driver]['compounds_history'][-1],
                    'TyreLife': driver_states[driver]['tyre_life'],
                    'IsSCActive': is_sc_active,
                    'IsRaining': is_raining
                })
                
        return pd.DataFrame(lap_by_lap_history), driver_states