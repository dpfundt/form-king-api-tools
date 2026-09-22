"""
Form King field registry
========================
Computed fields are small functions that derive a value from API data.
The engine calls ``get_field(name, entry, race, meeting, ctx)`` and never
needs to know which module provides which field.

Each field function must have this signature::

    def my_field(entry, race, meeting, ctx):
        ...
        return value  # or None

``ctx`` is a dict provided by the engine at runtime::

    {
        "past_runs": callable(entry) -> list[dict],  # filtered runs, newest first
        "tab":       bool,                           # whether tab_only is active
    }

Adding a new field
------------------
1. Create (or add to) a ``.py`` file in this folder.
2. Decorate your function with ``@register_field("your_field_name")``.
3. Import your module at the bottom of *this* file so the decorator runs.
4. Done — the engine and all profiles can use ``"your_field_name"`` immediately.

Contribution tip: one field (or a tightly related group) per file makes
Pull Requests easy to review and merge.
"""

FIELD_REGISTRY = {}


def register_field(name):
    """Decorator: registers a field function under ``name``.

    Usage::

        @register_field("my_field")
        def _compute(entry, race, meeting, ctx):
            return entry.get("someApiKey")
    """
    def decorator(fn):
        FIELD_REGISTRY[name] = fn
        return fn
    return decorator


def get_field(name, entry, race, meeting, ctx):
    """Call the registered function for ``name``.

    Returns ``None`` if the field is not registered — criteria that reference
    an unknown field will evaluate to None and fail safely rather than crash.
    """
    fn = FIELD_REGISTRY.get(name)
    return fn(entry, race, meeting, ctx) if fn is not None else None


# ── auto-import field modules so their @register_field decorators execute ────
# Add a new import here whenever you add a new field module.
from . import core        # noqa: E402, F401  — days_last_run_to_race, field_size
from . import war_margin  # noqa: E402, F401  — ls_war_margin_over_field, avg_best2_last3_war_margin_over_field
