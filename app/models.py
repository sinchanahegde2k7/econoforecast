from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    """Analysts and administrators. UserMixin gives us the methods
    Flask-Login needs (is_authenticated, get_id, etc.) for free."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='analyst')  # 'analyst' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    datasets = db.relationship('Dataset', backref='uploaded_by', lazy=True)
    forecast_requests = db.relationship('ForecastRequest', backref='requested_by', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'


class Dataset(db.Model):
    """Metadata about a collection of ingested data (e.g. one World Bank pull)."""
    __tablename__ = 'datasets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    source = db.Column(db.String(120), nullable=False)   # e.g. 'World Bank API'
    filename = db.Column(db.String(255))
    records = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='ready')   # ready / processing / archived
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    indicators = db.relationship('EconomicIndicator', backref='dataset', lazy=True)


class EconomicIndicator(db.Model):
    """A specific indicator, e.g. 'GDP Growth Rate' for 'India'."""
    __tablename__ = 'economic_indicators'

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    country = db.Column(db.String(80), nullable=False, default='India')
    unit = db.Column(db.String(50))                      # e.g. '% change'
    category = db.Column(db.String(50))                  # e.g. 'GDP', 'Inflation'
    frequency = db.Column(db.String(20))                 # 'monthly' / 'quarterly' / 'annual'

    values = db.relationship('IndicatorValue', backref='indicator', lazy=True, cascade='all, delete-orphan')
    forecast_requests = db.relationship('ForecastRequest', backref='indicator', lazy=True)
    forecast_models = db.relationship('ForecastModel', backref='indicator', lazy=True)


class IndicatorValue(db.Model):
    """One historical data point (one period's value) for one indicator."""
    __tablename__ = 'indicator_values'

    id = db.Column(db.Integer, primary_key=True)
    indicator_id = db.Column(db.Integer, db.ForeignKey('economic_indicators.id'), nullable=False)
    period = db.Column(db.Date, nullable=False)
    value = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('indicator_id', 'period', name='uq_indicator_period'),
    )


class ForecastModel(db.Model):
    """A trained model saved to disk, with its evaluation metrics."""
    __tablename__ = 'forecast_models'

    id = db.Column(db.Integer, primary_key=True)
    indicator_id = db.Column(db.Integer, db.ForeignKey('economic_indicators.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)      # e.g. 'GDP Growth - LSTM'
    type = db.Column(db.String(30), nullable=False)       # 'linear_regression' / 'arima' / 'lstm'
    version = db.Column(db.String(20), default='v1.0')
    file_path = db.Column(db.String(255))                 # where the trained model is saved on disk
    trained_at = db.Column(db.DateTime, default=datetime.utcnow)
    rmse = db.Column(db.Float)
    mae = db.Column(db.Float)
    r2_score = db.Column(db.Float)
    status = db.Column(db.String(20), default='active')   # active / retraining / archived

    forecast_results = db.relationship('ForecastResult', backref='model', lazy=True)


class ForecastRequest(db.Model):
    """One analyst's request: 'forecast indicator X, Y months ahead'."""
    __tablename__ = 'forecast_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    indicator_id = db.Column(db.Integer, db.ForeignKey('economic_indicators.id'), nullable=False)
    horizon_months = db.Column(db.Integer, nullable=False, default=12)
    status = db.Column(db.String(20), default='pending')  # pending / completed / failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    result = db.relationship('ForecastResult', backref='request', uselist=False, lazy=True)


class ForecastResult(db.Model):
    """The outcome of a completed forecast request - which model was used
    and how accurate it was on the held-out test data."""
    __tablename__ = 'forecast_results'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('forecast_requests.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('forecast_models.id'), nullable=False)
    rmse = db.Column(db.Float)
    mae = db.Column(db.Float)
    r2_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    predicted_values = db.relationship('PredictedValue', backref='result', lazy=True, cascade='all, delete-orphan')


class PredictedValue(db.Model):
    """One forecasted data point, with its confidence interval."""
    __tablename__ = 'predicted_values'

    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('forecast_results.id'), nullable=False)
    period = db.Column(db.Date, nullable=False)
    predicted_value = db.Column(db.Float, nullable=False)
    lower_bound = db.Column(db.Float)
    upper_bound = db.Column(db.Float)
