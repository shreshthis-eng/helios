"""
Model Evaluation Metrics matching Paper Section 5.4 formulas.
Includes MAE, MSE, RMSE, and WMAPE.
"""

import numpy as np


def calc_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Error (MAE)."""
    return float(np.mean(np.abs(y_true.flatten() - y_pred.flatten())))


def calc_mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Squared Error (MSE)."""
    return float(np.mean((y_true.flatten() - y_pred.flatten()) ** 2))


def calc_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Squared Error (RMSE)."""
    return float(np.sqrt(calc_mse(y_true, y_pred)))


def calc_wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Weighted Mean Absolute Percentage Error (WMAPE)."""
    y_t = y_true.flatten()
    y_p = y_pred.flatten()
    sum_true = np.sum(y_t)
    if sum_true == 0:
        return 0.0
    return float(np.sum(np.abs(y_p - y_t)) / sum_true)


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Returns all 4 paper evaluation metrics in a formatted dictionary."""
    return {
        "MAE": calc_mae(y_true, y_pred),
        "MSE": calc_mse(y_true, y_pred),
        "RMSE": calc_rmse(y_true, y_pred),
        "WMAPE": calc_wmape(y_true, y_pred),
    }
