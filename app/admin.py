from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.models import Dataset, EconomicIndicator, ForecastModel, ForecastRequest

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _require_admin():
    if not current_user.is_authenticated or not current_user.is_admin():
        abort(403)


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    _require_admin()

    total_datasets = Dataset.query.count()
    total_indicators = EconomicIndicator.query.count()
    total_models = ForecastModel.query.filter_by(status='active').count()
    total_forecasts = ForecastRequest.query.count()

    r2_values = [
        m.r2_score for m in ForecastModel.query.filter_by(status='active').all()
        if m.r2_score is not None
    ]
    avg_r2 = (sum(r2_values) / len(r2_values)) if r2_values else None

    recent_requests = (
        ForecastRequest.query
        .order_by(ForecastRequest.created_at.desc())
        .limit(15)
        .all()
    )

    return render_template(
        'admin/dashboard.html',
        total_datasets=total_datasets,
        total_indicators=total_indicators,
        total_models=total_models,
        total_forecasts=total_forecasts,
        avg_r2=avg_r2,
        recent_requests=recent_requests,
    )
