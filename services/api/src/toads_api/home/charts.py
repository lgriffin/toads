"""Checks a chart payload from the analyzer (wcl_app.charts, contract in guides/charts.md in
lgriffin/warcraftlogs_project) before the hub stores it. The web draws charts straight from the payload, so every
list is bounded and every number the drawing depends on is checked here. The limits are the analyzer's own; only
the worker imports the analyzer, so they are repeated here rather than imported.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, TypeGuard

# The analyzer's CHART_SCHEMA_VERSION this hub draws.
CHART_VERSION = 1
KINDS = frozenset({"line", "bar"})
MAX_SERIES = 8
MAX_POINTS = 52
MAX_REFERENCES = 3
MAX_TEXT = 120
MAX_NOTES = 10


def _number(value: Any) -> TypeGuard[float]:
    if not isinstance(value, int | float) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:  # an int too large for a float
        return False


def _text(value: Any) -> bool:
    return isinstance(value, str) and len(value) <= MAX_TEXT


def _texts(value: Any, limit: int) -> TypeGuard[list[str]]:
    return isinstance(value, list) and len(value) <= limit and all(_text(v) for v in value)


def _series_problem(s: Any, points: int, y_max: float) -> str | None:
    if not isinstance(s, Mapping) or not _text(s.get("key")) or not _text(s.get("name")):
        return "a series needs a key and a name"
    values, display = s.get("values"), s.get("display")
    if not isinstance(values, list) or len(values) != points or not _texts(display, points) or len(display) != points:
        return f"series {s['key']!r} does not line up with the categories"
    if any(v is not None and not (_number(v) and 0 <= v <= y_max) for v in values):
        return f"series {s['key']!r} has a value outside 0 to y_max"
    if not isinstance(s.get("emphasis", False), bool):
        return "emphasis must be true or false"
    return None


def _reference_problem(r: Any, y_max: float) -> str | None:
    if not isinstance(r, Mapping) or not all(_text(r.get(k)) for k in ("key", "label", "display")):
        return "a reference needs a key, label and display"
    if not (_number(r.get("value")) and 0 <= r["value"] <= y_max):
        return f"reference {r['key']!r} is outside 0 to y_max"
    return None


def chart_problem(chart: Any, widget_id: str | None = None) -> str | None:
    """Why `chart` is not a chart payload this hub can draw, or None when it is. With `widget_id`, the chart must
    also be the one that widget shows."""
    if not isinstance(chart, Mapping):
        return "chart must be an object"
    if widget_id is not None and chart.get("id") != widget_id:
        return f"chart {chart.get('id')!r} does not belong to widget {widget_id!r}"
    if chart.get("version") != CHART_VERSION:
        return f"unsupported chart version {chart.get('version')!r}"
    if chart.get("kind") not in KINDS:
        return f"unsupported chart kind {chart.get('kind')!r}"
    for name in ("id", "title", "subtitle", "x_label", "y_label", "empty"):
        if not _text(chart.get(name)):
            return f"{name} must be text of at most {MAX_TEXT} characters"
    categories = chart.get("categories")
    if not _texts(categories, MAX_POINTS):
        return f"categories must be at most {MAX_POINTS} short labels"
    if not _texts(chart.get("notes"), MAX_NOTES):
        return f"notes must be at most {MAX_NOTES} short lines"
    raw_max = chart.get("y_max")
    if not (_number(raw_max) and raw_max >= 0):
        return "y_max must be a number of at least 0"
    y_max = float(raw_max)
    series, references = chart.get("series"), chart.get("references")
    if not isinstance(series, list) or len(series) > MAX_SERIES:
        return f"series must be a list of at most {MAX_SERIES}"
    if not isinstance(references, list) or len(references) > MAX_REFERENCES:
        return f"references must be a list of at most {MAX_REFERENCES}"
    for s in series:
        problem = _series_problem(s, len(categories), y_max)
        if problem:
            return problem
    if len({s["key"] for s in series}) != len(series):
        return "series keys must be unique"
    for r in references:
        problem = _reference_problem(r, y_max)
        if problem:
            return problem
    if len({r["key"] for r in references}) != len(references):
        return "reference keys must be unique"
    return None
