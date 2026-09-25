"""
Loads a trained model from disk (saved by train_models.py) and generates
genuine future forecasts - years beyond anything in the database - rather
than re-predicting years we already have real data for.
"""
import pickle
import numpy as np
import joblib

from app.models import IndicatorValue, ForecastModel

N_LAGS = 3       # must match train_models.py
TEST_SIZE = 8    # must match train_models.py - how many recent years were held out for evaluation


def load_full_series(indicator_id):
    rows = (
        IndicatorValue.query
        .filter_by(indicator_id=indicator_id)
        .order_by(IndicatorValue.period.asc())
        .all()
    )
    years = [r.period.year for r in rows]
    values = np.array([r.value for r in rows], dtype=float)
    return years, values


def _forecast_linear_regression(model_record, full_series, horizon):
    model = joblib.load(model_record.file_path)
    history = list(full_series)
    preds = []
    for _ in range(horizon):
        window = np.array(history[-N_LAGS:]).reshape(1, -1)
        pred = model.predict(window)[0]
        preds.append(float(pred))
        history.append(pred)
    return preds


def _forecast_arima(model_record, full_series, train_length, horizon):
    with open(model_record.file_path, "rb") as f:
        fitted = pickle.load(f)

    # The saved model's parameters were estimated using only the training
    # portion (everything except the years held out for evaluation). Before
    # forecasting the true future, we extend the model's internal state
    # through those already-known years - without re-estimating its
    # parameters - so the forecast genuinely starts from the present.
    known_after_train = full_series[train_length:]
    if len(known_after_train) > 0:
        fitted = fitted.append(known_after_train, refit=False)

    forecast = np.asarray(fitted.forecast(steps=horizon))
    return [float(v) for v in forecast]


def _forecast_lstm(model_record, full_series, horizon):
    from tensorflow import keras

    scaler_path = model_record.file_path.replace(".keras", "_scaler.pkl")
    model = keras.models.load_model(model_record.file_path)
    scaler = joblib.load(scaler_path)

    history = list(full_series)
    preds = []
    for _ in range(horizon):
        window = np.array(history[-N_LAGS:]).reshape(-1, 1)
        window_scaled = scaler.transform(window).reshape(1, N_LAGS, 1)
        pred_scaled = model.predict(window_scaled, verbose=0)[0][0]
        pred = float(scaler.inverse_transform([[pred_scaled]])[0][0])
        preds.append(pred)
        history.append(pred)
    return preds


def generate_forecast(indicator_id, model_type, horizon):
    """Returns a dict with historical data, real future forecast years/values,
    a simple confidence band, and the ForecastModel record that was used."""
    years, full_series = load_full_series(indicator_id)

    model_record = (
        ForecastModel.query
        .filter_by(indicator_id=indicator_id, type=model_type, status="active")
        .order_by(ForecastModel.trained_at.desc())
        .first()
    )
    if model_record is None:
        raise ValueError("No trained model found for this indicator and model type.")

    train_length = max(len(full_series) - TEST_SIZE, 1)

    if model_type == "linear_regression":
        preds = _forecast_linear_regression(model_record, full_series, horizon)
    elif model_type == "arima":
        preds = _forecast_arima(model_record, full_series, train_length, horizon)
    elif model_type == "lstm":
        preds = _forecast_lstm(model_record, full_series, horizon)
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    last_year = years[-1]
    forecast_years = [last_year + i + 1 for i in range(horizon)]

    # Confidence band approximated from the model's own historical test-set
    # error (RMSE): a simple, defensible way to express forecast uncertainty,
    # matching the report's description of confidence intervals per forecast.
    margin = 1.96 * (model_record.rmse or 0)
    lower_bound = [p - margin for p in preds]
    upper_bound = [p + margin for p in preds]

    return {
        "years": years,
        "historical_values": full_series.tolist(),
        "forecast_years": forecast_years,
        "forecast_values": preds,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "model_record": model_record,
    }
