"""
Weight-Adjusted Rating (WAR) margin fields
==========================================
These fields measure how much better (or worse) a runner's weight-adjusted
rating is compared to the best-rated rival remaining in today's field.

  Positive margin → runner is rated above the next-best rival.
  Negative margin → runner is rated below the best rival.
  None            → insufficient rating history to compute.

Registered fields
-----------------
ls_war_margin_over_field
    Last-start WAR versus the best-rated rival.
    Uses the runner's single most-recent valid Form King rating.

avg_best2_last3_war_margin_over_field
    Average of the runner's two best Form King ratings from its last three
    valid starts, minus the same figure for the best-rated rival in today's
    field.  More stable than last-start alone.

Adding a new WAR margin variant
-------------------------------
Add one row to ``_WAR_VARIANTS`` — no other file needs to change::

    _WAR_VARIANTS["my_variant_name"] = (best_n, last_m)

Data source
-----------
Ratings are read from each past event using these API keys (in priority order):
    1. ``adjustedForTodaysWeight``   — weight-adjusted rating (preferred)
    2. ``weightForAgeRating``        — weight-for-age rating (fallback)

A rating is only accepted when:
    - ``ratingScale`` == ``"FORM_KING"`` (after stripping invisible characters)
    - The value is numeric and non-zero
"""

import re
from fields import register_field

# ── configuration ─────────────────────────────────────────────────────────────

# API keys to try when reading a run's WAR, in priority order.
_WAR_KEYS = ["adjustedForTodaysWeight", "weightForAgeRating"]

# Only accept ratings produced on the Form King scale.
_VALID_SCALE = "FORM_KING"

# WAR margin variants to register: field_name -> (best_n, last_m)
# best_n : take the N highest valid ratings from the last_m valid runs, then average.
# last_m : how many valid runs to look back across.
_WAR_VARIANTS = {
    "ls_war_margin_over_field":              (1, 1),
    "avg_best2_last3_war_margin_over_field": (2, 3),
}


# ── internal helpers ──────────────────────────────────────────────────────────

def _clean_str(s):
    """Strip invisible/zero-width characters that can appear in API text."""
    if not isinstance(s, str):
        return s
    return re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", s).strip()


def _valid_war_from_run(run):
    """Return a validated WAR float from a single past run dict, or None.

    Validation:
      - ratingScale must equal 'FORM_KING' (invisible-character-safe comparison)
      - Value must be numeric and non-zero
    """
    if _clean_str(run.get("ratingScale")) != _VALID_SCALE:
        return None
    for key in _WAR_KEYS:
        v = run.get(key)
        if isinstance(v, (int, float)) and v != 0:
            return float(v)
    return None


def _war_value(entry, best_n, last_m, ctx):
    """Average of the ``best_n`` highest valid WARs from a runner's last
    ``last_m`` valid (non-trial, FORM_KING, non-zero) starts.

    Walks past runs newest-first (as returned by ctx["past_runs"]), collecting
    up to ``last_m`` valid ratings, then averages the top ``best_n``.

    Returns None when fewer than ``best_n`` valid ratings are available.
    """
    ratings = []
    for run in ctx["past_runs"](entry):
        v = _valid_war_from_run(run)
        if v is not None:
            ratings.append(v)
        if len(ratings) >= last_m:
            break
    if len(ratings) < best_n:
        return None
    top = sorted(ratings, reverse=True)[:best_n]
    return round(sum(top) / len(top), 2)


def _war_margin(entry, race, best_n, last_m, ctx):
    """This runner's WAR value minus the highest WAR value of any live rival.

    Returns None when:
      - This runner lacks sufficient rating history, or
      - Every rival in the field lacks sufficient rating history.
    """
    mine = _war_value(entry, best_n, last_m, ctx)
    if mine is None or race is None:
        return None
    rivals = [
        _war_value(e, best_n, last_m, ctx)
        for e in race.get("entries", [])
        if e is not entry and not e.get("scratched")
    ]
    rivals = [v for v in rivals if v is not None]
    if not rivals:
        return None
    return round(mine - max(rivals), 2)


# ── register all variants ─────────────────────────────────────────────────────

def _make_war_field(best_n, last_m):
    """Factory: correctly captures best_n/last_m in each closure."""
    def _field(entry, race, meeting, ctx):
        return _war_margin(entry, race, best_n, last_m, ctx)
    return _field


for _name, (_bn, _lm) in _WAR_VARIANTS.items():
    register_field(_name)(_make_war_field(_bn, _lm))
