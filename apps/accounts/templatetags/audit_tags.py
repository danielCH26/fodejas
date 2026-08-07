"""Custom template tags for audit."""
import json
from django import template

register = template.Library()


@register.filter
def pretty_json(value):
    """Format a dict/object as pretty JSON."""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return json.dumps(value, indent=2, ensure_ascii=False)
