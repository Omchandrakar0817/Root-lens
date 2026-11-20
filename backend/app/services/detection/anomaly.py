"""Anomaly detection and cautious trend forecasts.

Isolation Forest is used only after ANOMALY_MIN_SAMPLES real observations.
Before that, a statistical rule reports deviations and model_trained stays false.
Forecast records are separate from anomalies and are omitted when the series is too short.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from app.core.config import get_settings


@dataclass
class AnomalyResult:
    metric: str
    record_type: str
    method: str
    model_trained: bool
    score: float | None
    is_anomaly: bool
    value: float | None
    baseline: float | None
    evidence: dict


def _clean(values: list[float]) -> np.ndarray:
    array = np.array([float(v) for v in values if v is not None], dtype=float)
    return array.reshape(-1, 1)


def statistical_check(values: list[float], metric: str) -> AnomalyResult:
    series = [float(v) for v in values if v is not None]
    current = series[-1] if series else None
    baseline = float(np.mean(series[:-1])) if len(series) > 1 else (current or 0)
    deviation = None
    is_anomaly = False
    if len(series) >= 5 and current is not None:
        window = np.array(series[:-1], dtype=float)
        std = float(np.std(window)) or 1.0
        deviation = abs(current - float(np.mean(window))) / std
        is_anomaly = deviation >= 3 and current > float(np.mean(window))
    return AnomalyResult(
        metric=metric,
        record_type="anomaly",
        method="statistical_zscore",
        model_trained=False,
        score=round(deviation, 3) if deviation is not None else None,
        is_anomaly=is_anomaly,
        value=current,
        baseline=round(baseline, 3) if baseline is not None else None,
        evidence={
            "sample_count": len(series),
            "minimum_for_model": get_settings().anomaly_min_samples,
            "note": "Isolation Forest is not trained yet. This is a statistical cold-start check, not a prediction.",
        },
    )


def train_isolation_forest(values: list[float]) -> bytes:
    model = IsolationForest(n_estimators=100, contamination=0.08, random_state=42)
    model.fit(_clean(values))
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    return buffer.getvalue()


def score_with_model(model_blob: bytes, values: list[float], metric: str) -> AnomalyResult:
    model: IsolationForest = joblib.load(io.BytesIO(model_blob))
    series = _clean(values)
    current = float(series[-1][0])
    label = int(model.predict(series[-1].reshape(1, -1))[0])
    raw = float(model.score_samples(series[-1].reshape(1, -1))[0])
    anomaly_score = round(-raw, 4)
    baseline = float(np.median(series[:-1])) if len(series) > 1 else current
    return AnomalyResult(
        metric=metric,
        record_type="anomaly",
        method="isolation_forest",
        model_trained=True,
        score=anomaly_score,
        is_anomaly=label == -1,
        value=current,
        baseline=round(baseline, 3),
        evidence={
            "sample_count": int(series.shape[0]),
            "model": "IsolationForest",
            "note": "A negative Isolation Forest prediction marks the latest point as unusual relative to this website's history. This is detection, not a forecast.",
        },
    )


def evaluate_series(values: list[float], metric: str, model_blob: bytes | None) -> tuple[AnomalyResult, bytes | None]:
    settings = get_settings()
    usable = [float(v) for v in values if v is not None]
    if len(usable) < 5:
        result = statistical_check(usable, metric)
        result.evidence["note"] = "Not enough history for a statistical or ML check."
        result.is_anomaly = False
        return result, None
    if len(usable) < settings.anomaly_min_samples:
        return statistical_check(usable, metric), None
    blob = train_isolation_forest(usable)
    result = score_with_model(blob, usable, metric)
    return result, blob


def forecast_trend(values: list[float], metric: str, horizon_steps: int = 6) -> AnomalyResult | None:
    usable = [float(v) for v in values if v is not None]
    if len(usable) < 20:
        return None
    x = np.arange(len(usable), dtype=float)
    slope, intercept = np.polyfit(x, np.array(usable, dtype=float), 1)
    projected = float(intercept + slope * (len(usable) - 1 + horizon_steps))
    return AnomalyResult(
        metric=metric,
        record_type="forecast",
        method="linear_trend",
        model_trained=False,
        score=round(float(slope), 4),
        is_anomaly=False,
        value=round(projected, 3),
        baseline=round(float(np.mean(usable)), 3),
        evidence={
            "sample_count": len(usable),
            "horizon_steps": horizon_steps,
            "slope_per_step": round(float(slope), 4),
            "note": "This is a linear trend projection from historical measurements, not a confirmed future incident.",
        },
    )
