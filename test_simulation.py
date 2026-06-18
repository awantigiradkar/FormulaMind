import sys
import os
import pandas as pd

# Ensure project root is in python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from simulation import RaceSimulator

def test_race_simulator():
    print("=== FormulaMind Race Simulator Verification ===")
    
    # 1. Define Driver Strategy Configurations
    # - VER: Pits Lap 20 (Hard), Lap 42 (reacts to rain with Intermediates)
    # - HAM: Pits Lap 22 (Hard), stays out on dry Hards (gambles on rain stopping)
    # - NOR: Pits Lap 10 (Medium), Lap 30 (Hard), Lap 42 (Intermediates)
    drivers_configs = {
        'VER': {
            'compounds': ['MEDIUM', 'HARD', 'INTERMEDIATE'],
            'pit_laps': [20, 42]
        },
        'HAM': {
            'compounds': ['MEDIUM', 'HARD'],
            'pit_laps': [22]
        },
        'NOR': {
            'compounds': ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE'],
            'pit_laps': [10, 30, 42]
        }
    }
    
    # 2. Configure race parameters
    total_laps = 52
    sc_laps = [35, 36, 37]  # Safety Car deployed on laps 35-37
    rain_lap = 42           # Rain starts on lap 42
    rain_intensity = 'LIGHT'
    
    print("\nRace Parameters:")
    print(f" - Total Laps: {total_laps}")
    print(f" - Safety Car Laps: {sc_laps}")
    print(f" - Rain starts on Lap: {rain_lap} (Intensity: {rain_intensity})")
    
    # 3. Instantiate and run simulator
    try:
        simulator = RaceSimulator()
        df_history, states = simulator.run_race_simulation(
            drivers_configs=drivers_configs,
            total_laps=total_laps,
            sc_laps=sc_laps,
            rain_lap=rain_lap,
            rain_intensity=rain_intensity
        )
        
        print("\nSimulation completed successfully!")
        
        # 4. Display Final Standings
        final_standings = df_history[df_history['LapNumber'] == total_laps].sort_values('Position')
        
        print("\n=== FINAL RACE STANDINGS ===")
        for idx, row in final_standings.iterrows():
            dname = row['Driver']
            pos = row['Position']
            cum_time_min = row['CumulativeTime'] / 60.0
            gap = row['GapToLeader']
            comp = row['Compound']
            gap_str = "Leader" if pos == 1 else f"+{gap:.3f}s"
            print(f" P{pos}. {dname:4} | Final Compound: {comp:12} | Time: {cum_time_min:.3f} mins | Gap: {gap_str}")
            
        # 5. Show lap times on Lap 45 (wet track) to observe tire offsets
        print("\nLap Times on Lap 45 (Wet Track):")
        lap_45_data = df_history[df_history['LapNumber'] == 45]
        for idx, row in lap_45_data.iterrows():
            print(f" - {row['Driver']}: {row['LapTime']:.3f}s (Compound: {row['Compound']})")
            
        print("\n=== Race Simulation Check PASSED ===")
        return True
    except Exception as e:
        import traceback
        err_msg = str(e).encode('ascii', 'replace').decode('ascii')
        print(f"Failed simulation testing: {err_msg}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_race_simulator()