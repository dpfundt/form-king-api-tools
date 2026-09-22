"""
Core computed fields
====================
Universal, opinion-free attributes derivable directly from the Form King API
response.  These fields require no knowledge of ratings methodology or
handicapping — they are straightforward derivations of the data shape.

Registered fields
-----------------
days_last_run_to_race
    Days between a runner's most-recent past start and today's race date.
    Useful for spotting quick back-ups (short gap) or first-uppers (long gap).

field_size
    Number of non-scratched runners in the race.
    Useful for filtering very small or very large fields.
"""

from fields import register_field


@register_field("days_last_run_to_race")
def _days_last_run(entry, race, meeting, ctx):
    """Days since a runner's last recorded start (positive integer, or None).

    Calculated as: (race date in ms − last past-event date in ms) / ms-per-day.
    Returns None when the runner has no recorded starts or the race date is
    unavailable.

    Racing logic: a gap of 1–5 days = quick back-up; 200+ days = spell resumption.
    The tab_only filter (ctx["past_runs"]) is applied before selecting the last run.
    """
    race_ms = (race or {}).get("date") or (meeting or {}).get("date")
    runs = ctx["past_runs"](entry) if entry is not None else []
    if not race_ms or not runs:
        return None
    last_ms = runs[0].get("date")   # list is newest-first
    return int((race_ms - last_ms) / 86_400_000)


@register_field("field_size")
def _field_size(entry, race, meeting, ctx):
    """Number of non-scratched runners in the race (integer).

    Note: ``entry`` is unused — this is a race-level attribute.  It is
    registered here so that profile criteria can use ``"field_size"`` at
    either race or entry scope without special-casing in the engine.

    Racing logic: field size influences pace dynamics, winning margins, and
    the reliability of ratings comparisons across the field.
    """
    return len([e for e in (race or {}).get("entries", []) if not e.get("scratched")])
