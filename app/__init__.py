from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# These are created here (empty) and "attached" to the app inside create_app().
# This pattern (the "app factory") is standard Flask practice and matches
# what the report's architecture chapter describes.
db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Imported here (not at the top of the file) to avoid a circular import
    # between this file and models.py.
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.auth import auth_bp
    from app.main import main_bp
    from app.admin import admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_helpers():
        labels = {
            'linear_regression': 'Linear Regression',
            'arima': 'ARIMA',
            'lstm': 'LSTM',
        }
        return dict(model_label=lambda t: labels.get(t, t.replace('_', ' ').title()))

    return app
