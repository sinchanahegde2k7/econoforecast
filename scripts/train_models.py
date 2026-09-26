"""
Trains three forecasting models - Linear Regression, ARIMA, and LSTM -
for each economic indicator in the database, evaluates each one on a
held-out set of the most recent years, and saves the trained models to
disk along with their RMSE/MAE/R2 metrics in the forecast_models table.

Run this after fetch_data.py, with:
    python scripts/train_models.py
"""
import sys
import os
import pickle
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")  # statsmodels/tensorflow are noisy with routine convergence warnings

import numpy as np
import joblib
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from statsmodels.tsa.arima.model import ARIMA

from app import create_app, db
from app.models import EconomicIndicator, IndicatorValue, ForecastModel

N_LAGS = 3     # each model looks at the past 3 years to predict the next one
TEST_SIZE = 8  # most recent 8 years held out, never seen during training, used only for scoring
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, "saved_models")


def load_series(indicator_id):
    """Returns the indicator's historical values, oldest first."""
    rows = (
        IndicatorValue.query
        .filter_by(indicator_id=indicator_id)
        .order_by(IndicatorValue.period.asc())
        .all()
    )
    return np.array([r.value for r in rows], dtype=float)


def make_lagged_dataset(series, n_lags):
    """Turns a plain sequence of values into (X, y) training pairs:
    X = the previous n_lags values, y = the value right after them."""
    X, y = [], []
    for i in range(n_lags, len(series)):
        X.append(series[i - n_lags:i])
        y.append(series[i])
    return np.array(X), np.array(y)


def evaluate(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    return rmse, mae, r2


def train_linear_regression(train_series, test_series, n_lags):
    X_train, y_train = make_lagged_dataset(train_series, n_lags)
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Walk-forward evaluation: predict one year at a time using the REAL
    # previous values (not the model's own earlier guesses). This is the
    # standard, fair way to score a one-step-ahead forecaster.
    preds = []
    history = list(train_series)
    for true_val in test_series:
        window = np.array(history[-n_lags:]).reshape(1, -1)
        pred = model.predict(window)[0]
        preds.append(pred)
        history.append(true_val)

    return model, evaluate(test_series, preds)


def train_arima(train_series, test_series):
    fitted = ARIMA(train_series, order=(2, 1, 2)).fit()
    forecast = np.asarray(fitted.forecast(steps=len(test_series)))
    return fitted, evaluate(test_series, forecast)


def train_lstm(train_series, test_series, n_lags):
    from sklearn.preprocessing import MinMaxScaler
    from tensorflow import keras

    scaler = MinMaxScaler()
    train_scaled = scaler.fit_transform(train_series.reshape(-1, 1)).flatten()

    X_train, y_train = make_lagged_dataset(train_scaled, n_lags)
    X_train = X_train.reshape((X_train.shape[0], X_train.shape[1], 1))

    model = keras.Sequential([
        keras.layers.Input(shape=(n_lags, 1)),
        keras.layers.LSTM(32, activation="tanh"),
        keras.layers.Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")
    model.fit(X_train, y_train, epochs=150, batch_size=4, verbose=0)

    # Same walk-forward approach as Linear Regression, but each window
    # has to be scaled the same way the training data was scaled first.
    preds = []
    history = list(train_series)
    for true_val in test_series:
        window = np.array(history[-n_lags:]).reshape(-1, 1)
        window_scaled = scaler.transform(window).reshape(1, n_lags, 1)
        pred_scaled = model.predict(window_scaled, verbose=0)[0][0]
        pred = scaler.inverse_transform([[pred_scaled]])[0][0]
        preds.append(pred)
        history.append(true_val)

    return (model, scaler), evaluate(test_series, preds)


def save_forecast_model(indicator, model_type, version, file_path, metrics):
    rmse, mae, r2 = metrics
    record = ForecastModel(
        indicator_id=indicator.id,
        name=f"{indicator.name} - {model_type.upper()}",
        type=model_type,
        version=version,
        file_path=file_path,
        rmse=rmse,
        mae=mae,
        r2_score=r2,
        status="active",
    )
    db.session.add(record)
    db.session.commit()


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    app = create_app()

    with app.app_context():
        indicators = EconomicIndicator.query.all()

        for indicator in indicators:
            print(f"\n=== {indicator.name} ===")

            already_trained = ForecastModel.query.filter_by(indicator_id=indicator.id).count()
            if already_trained >= 3:
                print("  Already has trained models - skipping.")
                continue

            series = load_series(indicator.id)

            if len(series) < N_LAGS + TEST_SIZE + 5:
                print(f"  Skipping - not enough data ({len(series)} points)")
                continue

            train_series = series[:-TEST_SIZE]
            test_series = series[-TEST_SIZE:]
            safe_name = indicator.name.lower().replace(" ", "_").replace("(", "").replace(")", "")

            lr_model, lr_metrics = train_linear_regression(train_series, test_series, N_LAGS)
            lr_path = os.path.join(MODELS_DIR, f"{safe_name}_linear_regression.pkl")
            joblib.dump(lr_model, lr_path)
            save_forecast_model(indicator, "linear_regression", "v1.0", lr_path, lr_metrics)
            print(f"  Linear Regression -> RMSE {lr_metrics[0]:.3f}  MAE {lr_metrics[1]:.3f}  R2 {lr_metrics[2]:.3f}")

            arima_model, arima_metrics = train_arima(train_series, test_series)
            arima_path = os.path.join(MODELS_DIR, f"{safe_name}_arima.pkl")
            with open(arima_path, "wb") as f:
                pickle.dump(arima_model, f)
            save_forecast_model(indicator, "arima", "v1.0", arima_path, arima_metrics)
            print(f"  ARIMA              -> RMSE {arima_metrics[0]:.3f}  MAE {arima_metrics[1]:.3f}  R2 {arima_metrics[2]:.3f}")

            (lstm_model, scaler), lstm_metrics = train_lstm(train_series, test_series, N_LAGS)
            lstm_path = os.path.join(MODELS_DIR, f"{safe_name}_lstm.keras")
            lstm_model.save(lstm_path)
            scaler_path = os.path.join(MODELS_DIR, f"{safe_name}_lstm_scaler.pkl")
            joblib.dump(scaler, scaler_path)
            save_forecast_model(indicator, "lstm", "v1.0", lstm_path, lstm_metrics)
            print(f"  LSTM               -> RMSE {lstm_metrics[0]:.3f}  MAE {lstm_metrics[1]:.3f}  R2 {lstm_metrics[2]:.3f}")

        print("\nAll models trained and saved to saved_models/")


if __name__ == "__main__":
    main()
