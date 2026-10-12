"""Custom template tags for audit."""

import json

from django import template

register = template.Library()


@register.filter
def pretty_json(value):
    """Format a dict/object as pretty JSON.

    Defensive: non-JSON-serializable objects (e.g. model instances) are
    stringified via ``default=str`` instead of raising a 500 — the audit
    detail page used to crash on ``{{ event|pretty_json }}``.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    try:
        return json.dumps(value, indent=2, ensure_ascii=False)
    except TypeError:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
