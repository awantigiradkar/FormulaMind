"""
Pit Stop Strategy Optimizer
Uses the trained ML model to simulate tyre stints, evaluate race strategies,
and recommend the mathematically fastest strategy.
"""

import os
import pickle
import numpy as np
import pandas as pd

DEFAULT_MODEL_PATH = os.path.join("models", "tire_model.pkl")

class StrategyOptimizer:
    def __init__(self, model_path=DEFAULT_MODEL_PATH, model_obj=None):
        self.model_path = model_path
        self.model_data = None
        self.model = model_obj
        
        # If no model object is passed directly, load the fallback model from disk
        if self.model is None:
            self.load_model()
        
    def load_model(self):
        """Loads the serialized ML model and features metadata."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Trained tire model not found at {self.model_path}. "
                f"Please run models/train_tire_model.py first."
            )
            
        with open(self.model_path, 'rb') as f:
            self.model_data = pickle.load(f)
            self.model = self.model_data['model']
            
    def predict_lap_time(self, tyre_life: int, lap_number: int, compound: str):
        """
        Uses the loaded ML model to predict a single lap time.
        """
        compound = compound.upper()
        # Order must match training: ['TyreLife', 'LapNumber', 'Compound_SOFT', 'Compound_MEDIUM', 'Compound_HARD']
        features = [[
            tyre_life,
            lap_number,
            1 if compound == 'SOFT' else 0,
            1 if compound == 'MEDIUM' else 0,
            1 if compound == 'HARD' else 0
        ]]
        
        # Suppress warnings about feature names during prediction loops
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            pred = self.model.predict(features)[0]
        return pred

    def simulate_strategy(self, total_laps: int, pit_laps: list, compounds: list, pit_loss=20.0):
        """
        Vectorized stint-based strategy simulator.
        Predicts lap times for each stint in batch for high performance.
        """
        if len(compounds) != len(pit_laps) + 1:
            raise ValueError("Number of compounds must equal number of stints (pit_laps + 1)")
            
        lap_details = []
        total_time = 0.0
        
        # Define boundaries, e.g. [0, 20, 52] for a 1-stop on Lap 20
        boundaries = [0] + list(pit_laps) + [total_laps]
        
        import warnings
        
        for stint_idx in range(len(boundaries) - 1):
            start_lap = boundaries[stint_idx] + 1
            end_lap = boundaries[stint_idx + 1]
            compound = compounds[stint_idx].upper()
            
            stint_len = end_lap - start_lap + 1
            if stint_len <= 0:
                continue
                
            tyre_lifes = np.arange(1, stint_len + 1)
            lap_numbers = np.arange(start_lap, end_lap + 1)
            
            is_soft = 1 if compound == 'SOFT' else 0
            is_medium = 1 if compound == 'MEDIUM' else 0
            is_hard = 1 if compound == 'HARD' else 0
            
            # Construct a 2D feature matrix of shape (stint_len, 5)
            feats = np.column_stack((
                tyre_lifes,
                lap_numbers,
                np.full(stint_len, is_soft),
                np.full(stint_len, is_medium),
                np.full(stint_len, is_hard)
            ))
            
            # Predict times for the entire stint at once
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UserWarning)
                stint_times = self.model.predict(feats)
                
            # Compile results lap by lap
            for idx, lap_time in enumerate(stint_times):
                lap_num = start_lap + idx
                is_pit_lap = lap_num in pit_laps
                lap_time_final = lap_time
                
                # Add pit stop time loss (tyre change overhead) to the pit lap
                if is_pit_lap:
                    lap_time_final += pit_loss
                    
                total_time += lap_time_final
                
                lap_details.append({
                    'LapNumber': lap_num,
                    'Stint': stint_idx + 1,
                    'Compound': compound,
                    'TyreLife': int(tyre_lifes[idx]),
                    'LapTime': lap_time_final,
                    'IsPitLap': is_pit_lap,
                    'TotalCumulativeTime': total_time
                })
                
        return total_time, pd.DataFrame(lap_details)

    def optimize_1_stop(self, total_laps: int, c1: str, c2: str, pit_loss=20.0, min_lap=10, max_lap=42):
        """
        Finds the mathematically optimal pit lap for a 1-stop strategy (c1 -> c2).
        """
        best_time = float('inf')
        best_pit_lap = -1
        best_df = None
        
        # Grid search over possible pit laps
        for pit_lap in range(min_lap, max_lap + 1):
            total_time, df_laps = self.simulate_strategy(total_laps, [pit_lap], [c1, c2], pit_loss)
            if total_time < best_time:
                best_time = total_time
                best_pit_lap = pit_lap
                best_df = df_laps
                
        return {
            'strategy_name': f"{c1} -> {c2}",
            'total_time_secs': best_time,
            'optimal_pit_lap': best_pit_lap,
            'laps_dataframe': best_df
        }

    def find_best_strategies(self, total_laps=52, pit_loss=20.0):
        """
        Evaluates and ranks common strategy variations for a given race distance.
        """
        strategies_to_test = [
            ('MEDIUM', 'HARD'),
            ('SOFT', 'HARD'),
            ('SOFT', 'MEDIUM'),
            ('HARD', 'MEDIUM')
        ]
        
        results = []
        for c1, c2 in strategies_to_test:
            # Set realistic pit windows depending on tire wear expectations
            min_l = 10 if c1 == 'MEDIUM' else (6 if c1 == 'SOFT' else 18)
            max_l = 32 if c1 == 'MEDIUM' else (20 if c1 == 'SOFT' else 40)
            
            res = self.optimize_1_stop(total_laps, c1, c2, pit_loss, min_l, max_l)
            results.append(res)
            
        # Evaluate a common 2-stop strategy: Medium -> Hard -> Medium
        best_2stop_time = float('inf')
        best_2stop_laps = [-1, -1]
        best_2stop_df = None
        
        for p1 in range(12, 23):
            for p2 in range(30, 42):
                if p2 > p1 + 5:  # Middle stint must be at least 5 laps
                    total_time, df_laps = self.simulate_strategy(
                        total_laps, [p1, p2], ['MEDIUM', 'HARD', 'MEDIUM'], pit_loss
                    )
                    if total_time < best_2stop_time:
                        best_2stop_time = total_time
                        best_2stop_laps = [p1, p2]
                        best_2stop_df = df_laps
                        
        results.append({
            'strategy_name': "MEDIUM -> HARD -> MEDIUM",
            'total_time_secs': best_2stop_time,
            'optimal_pit_lap': best_2stop_laps,
            'laps_dataframe': best_2stop_df
        })
        
        # Sort strategies: fastest overall time first
        return sorted(results, key=lambda x: x['total_time_secs'])