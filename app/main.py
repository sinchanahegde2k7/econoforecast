from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.models import (
    EconomicIndicator,
    IndicatorValue,
    ForecastModel,
    ForecastRequest,
    ForecastResult,
    PredictedValue,
)
from app.forecasting import generate_forecast

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def home():
    indicators = EconomicIndicator.query.all()

    summary = []
    for ind in indicators:
        latest = (
            IndicatorValue.query
            .filter_by(indicator_id=ind.id)
            .order_by(IndicatorValue.period.desc())
            .first()
        )
        summary.append({
            'indicator': ind,
            'latest_value': latest.value if latest else None,
            'latest_period': latest.period if latest else None,
        })

    return render_template('home.html', summary=summary)


@main_bp.route('/indicators/<int:indicator_id>')
@login_required
def indicator_detail(indicator_id):
    indicator = EconomicIndicator.query.get_or_404(indicator_id)
    values = (
        IndicatorValue.query
        .filter_by(indicator_id=indicator.id)
        .order_by(IndicatorValue.period.asc())
        .all()
    )

    years = [v.period.year for v in values]
    data_values = [v.value for v in values]

    current_value = data_values[-1] if data_values else None
    recent_window = data_values[-10:] if len(data_values) >= 10 else data_values
    avg_value = (sum(recent_window) / len(recent_window)) if recent_window else None

    return render_template(
        'indicator_detail.html',
        indicator=indicator,
        years=years,
        data_values=data_values,
        current_value=current_value,
        avg_value=avg_value,
    )


@main_bp.route('/models/compare/<int:indicator_id>')
@login_required
def model_compare(indicator_id):
    indicator = EconomicIndicator.query.get_or_404(indicator_id)
    models = (
        ForecastModel.query
        .filter_by(indicator_id=indicator_id, status='active')
        .order_by(ForecastModel.type.asc())
        .all()
    )
    return render_template('model_compare.html', indicator=indicator, models=models)


@main_bp.route('/forecast/configure/<int:indicator_id>')
@login_required
def forecast_configure(indicator_id):
    indicator = EconomicIndicator.query.get_or_404(indicator_id)
    available_models = ForecastModel.query.filter_by(indicator_id=indicator_id, status='active').all()
    return render_template('forecast_configure.html', indicator=indicator, available_models=available_models)


@main_bp.route('/forecast/run/<int:indicator_id>', methods=['POST'])
@login_required
def forecast_run(indicator_id):
    model_type = request.form.get('model_type')
    horizon = int(request.form.get('horizon', 5))

    result_data = generate_forecast(indicator_id, model_type, horizon)
    model_record = result_data['model_record']

    forecast_request = ForecastRequest(
        user_id=current_user.id,
        indicator_id=indicator_id,
        horizon_months=horizon * 12,
        status='completed',
    )
    db.session.add(forecast_request)
    db.session.commit()

    forecast_result = ForecastResult(
        request_id=forecast_request.id,
        model_id=model_record.id,
        rmse=model_record.rmse,
        mae=model_record.mae,
        r2_score=model_record.r2_score,
    )
    db.session.add(forecast_result)
    db.session.commit()

    for year, value, lower, upper in zip(
        result_data['forecast_years'],
        result_data['forecast_values'],
        result_data['lower_bound'],
        result_data['upper_bound'],
    ):
        db.session.add(PredictedValue(
            result_id=forecast_result.id,
            period=date(year, 1, 1),
            predicted_value=value,
            lower_bound=lower,
            upper_bound=upper,
        ))
    db.session.commit()

    return redirect(url_for('main.forecast_results', request_id=forecast_request.id))


@main_bp.route('/forecast/results/<int:request_id>')
@login_required
def forecast_results(request_id):
    forecast_request = ForecastRequest.query.get_or_404(request_id)
    result = forecast_request.result
    indicator = EconomicIndicator.query.get(forecast_request.indicator_id)

    predicted_values = (
        PredictedValue.query
        .filter_by(result_id=result.id)
        .order_by(PredictedValue.period.asc())
        .all()
    )

    historical = (
        IndicatorValue.query
        .filter_by(indicator_id=forecast_request.indicator_id)
        .order_by(IndicatorValue.period.asc())
        .all()
    )

    hist_years = [h.period.year for h in historical]
    hist_values = [h.value for h in historical]
    fc_years = [p.period.year for p in predicted_values]
    fc_values = [p.predicted_value for p in predicted_values]
    fc_lower = [p.lower_bound for p in predicted_values]
    fc_upper = [p.upper_bound for p in predicted_values]

    labels = [str(y) for y in hist_years] + [str(y) for y in fc_years]
    historical_series = hist_values + [None] * len(fc_years)

    # Repeating the last real value as the first forecast point makes the
    # two lines connect visually instead of leaving a visible gap.
    forecast_series = [None] * (len(hist_values) - 1) + [hist_values[-1]] + fc_values
    lower_series = [None] * (len(hist_values) - 1) + [hist_values[-1]] + fc_lower
    upper_series = [None] * (len(hist_values) - 1) + [hist_values[-1]] + fc_upper

    chart_data = {
        'labels': labels,
        'historical': historical_series,
        'forecast': forecast_series,
        'lower': lower_series,
        'upper': upper_series,
    }

    return render_template(
        'forecast_results.html',
        forecast_request=forecast_request,
        result=result,
        indicator=indicator,
        predicted_values=predicted_values,
        chart_data=chart_data,
    )
