"""Simple exponential smoothing, the forecast method from the course project."""
import numpy as np


def ses_fitted(values, alpha):
    """One-step-ahead forecasts. The first forecast is the first actual value."""
    forecasts = [values[0]]
    for actual in values[:-1]:
        forecasts.append(alpha * actual + (1 - alpha) * forecasts[-1])
    return np.array(forecasts, dtype=float)


def ses_next(values, alpha):
    """Forecast for the next period (SES gives the same level for all future periods)."""
    last_forecast = ses_fitted(values, alpha)[-1]
    return alpha * values[-1] + (1 - alpha) * last_forecast


def mape(actual, forecast):
    """Mean absolute percentage error, skipping the first (seed) period."""
    actual = np.asarray(actual, dtype=float)[1:]
    forecast = np.asarray(forecast, dtype=float)[1:]
    return float(np.mean(np.abs(actual - forecast) / actual))
