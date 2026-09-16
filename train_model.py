"""
train_model.py - Hospital Consultation Duration ML Model Trainer
Trains a Random Forest Regressor to predict consultation duration in minutes.
Generates metrics (MAE, RMSE, R2 Score) suitable for Final Year Project Reports.
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

def generate_hospital_data(n_samples=1500):
    np.random.seed(42)
    
    # 1: Dr. Mehta (Cardio, baseline ~20m)
    # 2: Dr. Sharma (Derma, baseline ~15m)
    # 3: Dr. Iyer (General, baseline ~12m)
    doctor_ids = np.random.choice([1, 2, 3], size=n_samples, p=[0.35, 0.35, 0.30])
    ages = np.random.randint(5, 85, size=n_samples)
    is_new = np.random.choice([0, 1], size=n_samples, p=[0.45, 0.55])
    priorities = np.random.choice([0, 3, 10], size=n_samples, p=[0.70, 0.22, 0.08])
    visit_counts = np.random.choice(range(0, 15), size=n_samples)

    doctor_baselines = {1: 20, 2: 15, 3: 12}
    durations = []

    for doc, age, new, prio, vcount in zip(doctor_ids, ages, is_new, priorities, visit_counts):
        base = doctor_baselines[doc]
        adj = 0.0
        if new == 1:
            adj += 6.0
        if vcount > 5:
            adj -= 2.0
        if prio == 3:
            adj += 5.0
        elif prio == 10:
            adj += 9.0
        if age > 65:
            adj += 3.0
            
        noise = np.random.normal(0, 2.0)
        dur = max(5.0, round(base + adj + noise))
        durations.append(dur)

    df = pd.DataFrame({
        'doctor_id': doctor_ids,
        'patient_age': ages,
        'is_new': is_new,
        'priority_level': priorities,
        'visit_count': visit_counts,
        'actual_duration_minutes': durations
    })
    return df

def train_and_export():
    print("[+] Generating clinical dataset of 1,500 consultations...")
    df = generate_hospital_data(1500)

    X = df[['doctor_id', 'patient_age', 'is_new', 'priority_level', 'visit_count']]
    y = df['actual_duration_minutes']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)

    print("[+] Training Random Forest Regressor...")
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print("=" * 55)
    print(" MODEL EVALUATION RESULTS (For Final Year Project Report):")
    print(f"   - Mean Absolute Error (MAE) : {mae:.2f} minutes")
    print(f"   - Root Mean Squared Error (RMSE): {rmse:.2f} minutes")
    print(f"   - R2 Accuracy Score         : {r2:.4f} ({r2*100:.1f}%)")
    print("=" * 55)

    # Save model
    output_path = os.path.join(os.path.dirname(__file__), 'consultation_model.pkl')
    joblib.dump(model, output_path)
    print(f"[OK] Trained ML model saved to: {output_path}")

    # Feature Importance
    importances = model.feature_importances_
    features = X.columns
    print("\n Feature Importances in Consultation Duration:")
    for feat, imp in sorted(zip(features, importances), key=lambda x: x[1], reverse=True):
        print(f"   - {feat:16s}: {imp*100:.1f}%")

if __name__ == '__main__':
    train_and_export()
