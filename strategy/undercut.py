"""
Undercut Threat Analyzer
Predicts whether a trailing chaser can successfully overtake the leader
by pitting early for fresh tires, based on predicted wear curves.
"""

import os
from strategy.optimizer import StrategyOptimizer

class UndercutAnalyzer:
    def __init__(self, optimizer=None):
        if optimizer is None:
            self.optimizer = StrategyOptimizer()
        else:
            self.optimizer = optimizer

    def analyze_undercut_potential(self, 
                                   gap_seconds: float, 
                                   lap_number: int,
                                   tyre_age_leader: int, 
                                   compound_leader: str, 
                                   compound_chaser_fresh: str):
        """
        Calculates the potential time gained if the chaser pits on the current lap
        while the leader stays out for one more lap.
        """
        # 1. Predict leader's lap time if they stay out (tyre age increases by 1)
        leader_out_lap_time = self.optimizer.predict_lap_time(
            tyre_life=tyre_age_leader + 1, 
            lap_number=lap_number + 1, 
            compound=compound_leader
        )
        
        # 2. Predict chaser's lap time on fresh tires (tyre age resets to 1)
        chaser_out_lap_time = self.optimizer.predict_lap_time(
            tyre_life=1, 
            lap_number=lap_number + 1, 
            compound=compound_chaser_fresh
        )
        
        # 3. Calculate undercut gain (time chaser claws back on fresh out-lap vs leader's worn tire lap)
        undercut_gain = leader_out_lap_time - chaser_out_lap_time
        
        # 4. Resulting gap after both have pitted
        new_gap = gap_seconds - undercut_gain
        
        # 5. Determine threat level
        if new_gap < 0:
            threat_level = "CRITICAL - UNDERCUT SUCCESSFUL"
            action_recommendation = "Pit immediately on this lap to cover the undercut!"
        elif new_gap < 0.7:
            threat_level = "HIGH - EXTREME THREAT"
            action_recommendation = "Highly vulnerable. Consider pitting or increasing pace immediately."
        elif new_gap < 1.5:
            threat_level = "MEDIUM - VULNERABLE"
            action_recommendation = "Monitor gaps closely. Maintain delta gap above 1.5s."
        else:
            threat_level = "LOW - SECURE"
            action_recommendation = "Gap is safe. Continue with current stint length."
            
        return {
            'leader_lap_time_worn': leader_out_lap_time,
            'chaser_lap_time_fresh': chaser_out_lap_time,
            'undercut_gain_secs': undercut_gain,
            'original_gap_secs': gap_seconds,
            'predicted_gap_secs': new_gap,
            'threat_level': threat_level,
            'recommendation': action_recommendation
        }