"""
Executable Runner for Short-Term PV Power Forecasting Model
Implements end-to-end workflow from Liu et al. (2023):
  1. Data generation & Solar Longitude calculation.
  2. 24 Solar Terms Partitioning & Similarity Analysis.
  3. Adaboost-GA-BP training and benchmark model evaluation (BP vs GA-BP vs Ada-BP vs Ada-GA-BP).
"""

import os
import sys
import numpy as np
from datetime import datetime

# Add local path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adaboost_ga_bp_pv import (
    PVDataGenerator,
    SolarTermPartitioner,
    BPNeuralNetwork,
    AdaboostGABPModel,
    evaluate_predictions,
)


def run_demo():
    print("=" * 80)
    print("  SHORT-TERM PV POWER PREDICTION SYSTEM")
    print("  Based on 24 Traditional Chinese Solar Terms & Adaboost-GA-BP Model")
    print("  (Paper: Liu et al., 2023 - Frontiers in Energy Research)")
    print("=" * 80)

    # 1. Dataset Generation
    print("\n[Step 1/4] Generating high-resolution 15-min PV & meteorological dataset...")
    generator = PVDataGenerator(capacity_mw=20.0, seed=42)
    dataset = generator.generate_dataset(start_date=datetime(2018, 7, 1), days=347)
    print(f" -> Successfully generated {len(dataset):,} valid 15-minute observations.")

    # 2. 24 Solar Terms Partitioning
    print("\n[Step 2/4] Partitioning data into 24 Solar Terms and computing Similarity Metrics...")
    partitioner = SolarTermPartitioner()
    solar_partitions = partitioner.partition_by_solar_terms(dataset)
    gregorian_partitions = partitioner.partition_by_gregorian_half_months(dataset)

    print(f" -> Created {len(solar_partitions)} Solar Term partitions.")
    
    # Calculate sample similarity metrics (SED & Spearman) for key terms
    sample_terms = ["SE", "SS", "AE", "WS", "WD", "FD"]
    print("\n--- Data Similarity Analysis (24 Solar Terms vs Gregorian Calendar) ---")
    print(f"{'Solar Term':<12} | {'Sample Count':<12} | {'Spearman Rho (Power-GHI)':<25} | {'SED':<10}")
    print("-" * 68)

    for term_key in sample_terms:
        rows = solar_partitions.get(term_key, [])
        if not rows:
            continue
        power_vals = np.array([r["power_mw"] for r in rows])
        ghi_vals = np.array([r["ghi"] for r in rows])
        temp_vals = np.array([r["temp"] for r in rows])

        rho = partitioner.calc_spearman_correlation(power_vals, ghi_vals)
        sed = partitioner.calc_standardized_euclidean_distance(ghi_vals, temp_vals)
        print(f"{term_key:<12} | {len(rows):<12} | {rho:<25.4f} | {sed:<10.4f}")

    # 3. Model Training & Benchmarking
    print("\n[Step 3/4] Training and Evaluating Models on Solar Term Datasets...")
    
    # Pick a representative solar term dataset for evaluation (e.g. White Dew / WD or Frost's Descent / FD)
    eval_term = "WD"
    rows = solar_partitions[eval_term]

    X = np.array([[r["ghi"], r["dhi"], r["temp"], r["wind_speed"]] for r in rows])
    y = np.array([r["power_mw"] for r in rows])

    # Normalize inputs
    X_mean, X_std = np.mean(X, axis=0), np.std(X, axis=0) + 1e-8
    X_norm = (X - X_mean) / X_std

    # Train / Test split (80% train, 20% test as specified in paper Section 6.1)
    split_idx = int(0.8 * len(rows))
    X_train, X_test = X_norm[:split_idx], X_norm[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f" -> Target Solar Term: '{eval_term}' ({len(rows)} samples: {len(y_train)} train, {len(y_test)} test)")

    # Model 1: Standard BP Neural Network
    print(" -> Training Model 1/4: Standard BP Neural Network...")
    bp_model = BPNeuralNetwork(input_dim=4, hidden_dim=19, output_dim=1, learning_rate=0.05)
    for _ in range(30):
        bp_model.train_epoch(X_train, y_train)
    bp_preds = bp_model.predict(X_test).flatten()
    bp_metrics = evaluate_predictions(y_test, bp_preds)

    # Model 2: GA-BP Model
    print(" -> Training Model 2/4: GA-BP Neural Network...")
    ga_bp_ensemble = AdaboostGABPModel(n_estimators=1, epochs_per_estimator=30, learning_rate=0.05)
    ga_bp_ensemble.fit(X_train, y_train, run_ga=True)
    ga_bp_preds = ga_bp_ensemble.predict(X_test)
    ga_bp_metrics = evaluate_predictions(y_test, ga_bp_preds)

    # Model 3: Adaboost-BP Model
    print(" -> Training Model 3/4: Adaboost-BP Neural Network...")
    ada_bp_ensemble = AdaboostGABPModel(n_estimators=5, epochs_per_estimator=20, learning_rate=0.05)
    ada_bp_ensemble.fit(X_train, y_train, run_ga=False)
    ada_bp_preds = ada_bp_ensemble.predict(X_test)
    ada_bp_metrics = evaluate_predictions(y_test, ada_bp_preds)

    # Model 4: Full Adaboost-GA-BP Master Model
    print(" -> Training Model 4/4: Adaboost-GA-BP Master Ensemble Model...")
    ada_ga_bp_model = AdaboostGABPModel(n_estimators=5, epochs_per_estimator=20, learning_rate=0.05)
    ada_ga_bp_model.fit(X_train, y_train, run_ga=True)
    ada_ga_bp_preds = ada_ga_bp_model.predict(X_test)
    ada_ga_bp_metrics = evaluate_predictions(y_test, ada_ga_bp_preds)

    # 4. Results & Summary Comparison
    print("\n[Step 4/4] Model Performance Benchmark Comparison Results")
    print("=" * 80)
    print(f"{'Model Architecture':<22} | {'MAE (MW)':<10} | {'MSE (MW^2)':<12} | {'RMSE (MW)':<10} | {'WMAPE':<10}")
    print("-" * 80)
    print(f"{'Standard BP':<22} | {bp_metrics['MAE']:<10.4f} | {bp_metrics['MSE']:<12.4f} | {bp_metrics['RMSE']:<10.4f} | {bp_metrics['WMAPE']:<10.4f}")
    print(f"{'GA-BP':<22} | {ga_bp_metrics['MAE']:<10.4f} | {ga_bp_metrics['MSE']:<12.4f} | {ga_bp_metrics['RMSE']:<10.4f} | {ga_bp_metrics['WMAPE']:<10.4f}")
    print(f"{'Adaboost-BP':<22} | {ada_bp_metrics['MAE']:<10.4f} | {ada_bp_metrics['MSE']:<12.4f} | {ada_bp_metrics['RMSE']:<10.4f} | {ada_bp_metrics['WMAPE']:<10.4f}")
    print(f"{'Adaboost-GA-BP (Proposed)':<22} | {ada_ga_bp_metrics['MAE']:<10.4f} | {ada_ga_bp_metrics['MSE']:<12.4f} | {ada_ga_bp_metrics['RMSE']:<10.4f} | {ada_ga_bp_metrics['WMAPE']:<10.4f}")
    print("=" * 80)

    # Calculate error reduction percentage of proposed model vs baseline BP
    mae_reduction = (bp_metrics["MAE"] - ada_ga_bp_metrics["MAE"]) / bp_metrics["MAE"] * 100
    rmse_reduction = (bp_metrics["RMSE"] - ada_ga_bp_metrics["RMSE"]) / bp_metrics["RMSE"] * 100
    wmape_reduction = (bp_metrics["WMAPE"] - ada_ga_bp_metrics["WMAPE"]) / bp_metrics["WMAPE"] * 100

    print(f"\n[SUCCESS] Verification Complete!")
    print(f" -> Adaboost-GA-BP reduced MAE error by {mae_reduction:.2f}% compared to Standard BP.")
    print(f" -> Adaboost-GA-BP reduced RMSE error by {rmse_reduction:.2f}% compared to Standard BP.")
    print(f" -> Adaboost-GA-BP reduced WMAPE error by {wmape_reduction:.2f}% compared to Standard BP.")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
