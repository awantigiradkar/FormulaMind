"""
Tire Degradation Model Trainer
Loads 2023 Silverstone Race session laps, filters outliers and pit stops,
engineers fuel load and compound features, trains a Random Forest Regressor,
and serializes the model for dashboard predictions.
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# Ensure the root folder is in the Python search path to import our telemetry modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from telemetry.engine import get_f1_session, setup_cache

def train_model():
    print("FormulaMind Tire Degradation Model Training")
    
    # 1. Setup cache path
    cache_path = os.path.join("data", "fastf1_cache")
    setup_cache(cache_path)
    
    # 2. Fetch the 2023 Silverstone GP Race
    print("Loading 2023 Silverstone GP - Race session...")
    try:
        session = get_f1_session(2023, 'Silverstone', 'R')
        print("Session loaded successfully!")
    except Exception as e:
        print(f"Failed to load race session: {e}")
        return
        
    # 3. Read raw laps
    laps = session.laps
    print(f"Total raw laps loaded: {len(laps)}")
    
    # 4. Data Cleansing
    # Remove pit stop laps (since they contain 20+ seconds of speed-limited pitlane driving)
    laps_clean = laps[laps['PitInTime'].isna() & laps['PitOutTime'].isna()].copy()
    print(f"Laps remaining after removing pit entry/exit: {len(laps_clean)}")
    
    # Filter for green flag conditions (TrackStatus == '1' means clear racing, no safety cars)
    laps_clean = laps_clean[laps_clean['TrackStatus'] == '1'].copy()
    print(f"Laps under green flag conditions: {len(laps_clean)}")
    
    # Convert LapTime timedelta to numerical seconds
    laps_clean['LapTimeSecs'] = laps_clean['LapTime'].dt.total_seconds()
    laps_clean = laps_clean.dropna(subset=['LapTimeSecs', 'TyreLife', 'Compound', 'LapNumber']).copy()
    
    # Remove extreme pace outliers (e.g., driver spins, off-track moments)
    # Keep only laps within 107% of the race median lap time
    median_time = laps_clean['LapTimeSecs'].median()
    laps_clean = laps_clean[laps_clean['LapTimeSecs'] <= median_time * 1.07].copy()
    print(f"Laps after speed outlier removal: {len(laps_clean)}")
    
    # 5. Feature Extraction
    data = laps_clean[['LapTimeSecs', 'TyreLife', 'LapNumber', 'Compound']].copy()
    data['Compound'] = data['Compound'].str.upper()
    
    # Filter out wet tire compounds (keep only dry racing slicks)
    data = data[data['Compound'].isin(['SOFT', 'MEDIUM', 'HARD'])].copy()
    print(f"Laps on dry slick compounds: {len(data)}")
    
    # One-hot encode the Compounds
    for comp in ['SOFT', 'MEDIUM', 'HARD']:
        data[f'Compound_{comp}'] = (data['Compound'] == comp).astype(int)
        
    # Define features and target variable
    feature_cols = ['TyreLife', 'LapNumber', 'Compound_SOFT', 'Compound_MEDIUM', 'Compound_HARD']
    X = data[feature_cols]
    y = data['LapTimeSecs']
    
    # 6. Train-Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"Train size: {X_train.shape[0]} | Test size: {X_test.shape[0]}")
    
    # 7. Model Training
    print("Training Random Forest Regressor...")
    model = RandomForestRegressor(n_estimators=150, max_depth=8, random_state=42)
    model.fit(X_train, y_train)
    
    # 8. Model Evaluation
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print("\nModel Performance Metrics:")
    print(f"Mean Absolute Error (MAE): {mae:.3f} seconds")
    print(f"R-squared Score (R2): {r2:.2%}")
    
    # Print feature importances
    importances = model.feature_importances_
    print("\nFeature Importances:")
    for col, imp in zip(feature_cols, importances):
        print(f" - {col}: {imp:.2%}")
        
    # 9. Serialize Model Artifacts
    os.makedirs("models", exist_ok=True)
    model_path = os.path.join("models", "tire_model.pkl")
    
    model_data = {
        'model': model,
        'features': feature_cols,
        'mae': mae,
        'r2': r2,
        'track': 'Silverstone',
        'season': 2023
    }
    
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
        
    print(f"\nTrained model successfully serialized and saved to: {model_path}")

if __name__ == "__main__":
    train_model()