"""
Test script for the Telemetry Engine
"""
from telemetry.engine import get_f1_session, compare_driver_telemetry

def main():
    print("Starting Telemetry Test...")
    # Load Silverstone 2023 Qualifying session
    session = get_f1_session(2023, "Silverstone", "Q")
    
    # Compare Verstappen vs Hamilton
    df, meta = compare_driver_telemetry(session, "VER", "HAM")
    
    print("\n TELEMETRY LOADED SUCCESSFUL!")
    print(f"Driver A (VER) Lap Time: {meta['lap_time_a']:.3f}s")
    print(f"Driver B (HAM) Lap Time: {meta['lap_time_b']:.3f}s")
    print(f"Aligned DataFrame Shape: {df.shape}")
    print("\nFirst 5 rows of aligned telemetry:")
    print(df[['Distance', 'Speed_VER', 'Speed_HAM', 'DeltaTime']].head())

if __name__ == "__main__":
    main()