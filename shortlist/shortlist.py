#!/usr/bin/env python3
"""
Form King Shortlist Engine
==========================
Runs your saved profiles against today's upcoming meetings and writes a
shortlist CSV.

This file is the engine only — it contains no opinion about how to synthesise
ratings or what constitutes a good runner.  Computed fields live in fields/.
Shortlist criteria live in profiles.json (or profiles_library/).

Usage
-----
  python shortlist.py               — interactive menu
  shortlist.bat  (Windows)           — double-click launcher
  shortlist.command  (macOS/Linux)   — double-click launcher
"""

import csv
import hashlib
import json
import os
import re
import time
from urllib import error, request

# ── project root ──────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))

# ── field registry (populated by fields/*.py on import) ──────────────────────
from fields import FIELD_REGISTRY, get_field  # noqa: E402

# ── constants ─────────────────────────────────────────────────────────────────
FORMKING_FORMGUIDE_BASE = "https://www.formking.com.au/member/formGuide"


# ── utility helpers ───────────────────────────────────────────────────────────

def clean(s):
    """Strip invisible/zero-width characters that can sneak into pasted text."""
    if not isinstance(s, str):
        return s
    return re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", s).strip()


def load_json(name):
    with open(os.path.join(ROOT, name)) as f:
        return json.load(f)


def slugify(name):
    """Turn a profile name into a filesystem-safe slug."""
    s = (name or "profile").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "profile"


def output_path(cfg, spec):
    """Build a timestamped CSV output path.
    Pattern: output/shortlist_<slug>_<YYYY-MM-DD_HHMM>.csv
    """
    folder = os.path.join(ROOT, cfg["output_folder"])
    os.makedirs(folder, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M")
    fname = f"shortlist_{slugify(clean(spec.get('name')))}_{stamp}.csv"
    return os.path.join(folder, fname)


# ── Form King URL builder ─────────────────────────────────────────────────────

def _slug(name):
    s = (name or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def race_url(meeting, race):
    """Return a Form King member form-guide URL for a race, or empty string."""
    track  = meeting.get("trackName")
    date_ms = meeting.get("date") or race.get("_meeting_date")
    rno    = race.get("number")
    if not track or not date_ms or rno is None:
        return ""
    ymd = time.strftime("%Y%m%d", time.gmtime(date_ms / 1000))
    return f"{FORMKING_FORMGUIDE_BASE}/{_slug(track)}-{ymd}?r={rno}"


# ── API client with local response cache ──────────────────────────────────────

class FormKing:
    def __init__(self, cfg):
        self.base       = cfg["base_url"].rstrip("/")
        self.key        = cfg["api_key"]
        self.cache_dir  = os.path.join(ROOT, ".cache")
        self.cache_secs = cfg.get("cache_hours", 6) * 3600
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get(self, path):
        cf = os.path.join(
            self.cache_dir,
            hashlib.md5(path.encode()).hexdigest() + ".json",
        )
        if os.path.exists(cf) and (time.time() - os.path.getmtime(cf)) < self.cache_secs:
            with open(cf) as f:
                return json.load(f)
        req = request.Request(
            self.base + path,
            headers={"x-api-key": self.key, "Accept": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode())
        except error.HTTPError as e:
            print(f"  ! API error {e.code} on {path}: {e.reason}")
            return None
        except Exception as e:
            print(f"  ! Network error on {path}: {e}")
            return None
        with open(cf, "w") as f:
            json.dump(data, f)
        return data

    def upcoming(self):
        return self._get("/b2c/meetings/upcoming") or []

    def meeting(self, mid):
        return self._get(f"/b2c/meetings/{mid}")


# ── result helpers ────────────────────────────────────────────────────────────

def _horse_result(entry):
    hr = entry.get("horseResult")
    return hr if isinstance(hr, dict) else None


def entry_finish_pos(entry):
    hr = _horse_result(entry)
    return "" if not hr else (hr.get("finishPosition") if hr.get("finishPosition") is not None else "")


def entry_starting_price(entry):
    hr = _horse_result(entry)
    return "" if not hr else (hr.get("startingPrice") if hr.get("startingPrice") is not None else "")


def entry_margin(entry):
    hr = _horse_result(entry)
    return "" if not hr else (hr.get("margin") if hr.get("margin") is not None else "")


# ── past-run helpers ──────────────────────────────────────────────────────────

def tab_only(spec):
    """Profile flag: when True, exclude non-TAB meetings/past events. Default True."""
    return bool(spec.get("tab_only", True))


def past_runs(entry, tab):
    """Non-trial past runs with a date, sorted newest-first.
    When `tab` is True, non-TAB past events are excluded from analysis."""
    runs = [
        p for p in (entry.get("pastEvents") or [])
        if p.get("date") and not p.get("trial")
    ]
    if tab:
        runs = [p for p in runs if p.get("tabMeeting")]
    return sorted(runs, key=lambda p: p["date"], reverse=True)


# ── field resolution ──────────────────────────────────────────────────────────

def resolve_field(field, entry, race, meeting, ctx):
    """Resolve a field value, checking sources in priority order:

      1. Registered computed field  (fields/ registry)
      2. Raw key on entry           (entry dict or entry["form"])
      3. Raw key on race / meeting  (API response fields)

    Returns None on any miss — criteria then evaluate to None and fail safely.
    """
    field = clean(field)

    # 1. Computed field
    if field in FIELD_REGISTRY:
        return get_field(field, entry, race, meeting, ctx)

    # 2. Raw entry / form fields (entry is None for race-scope checks)
    if entry is not None:
        if field in entry:
            return entry.get(field)
        if field in (entry.get("form") or {}):
            return entry["form"].get(field)

    # 3. Raw race / meeting fields
    if race is not None and field in race:
        return race.get(field)
    if meeting is not None:
        return meeting.get(field)

    return None


# ── criteria engine ───────────────────────────────────────────────────────────

OPS = {
    "==":     lambda a, b: a == b,
    "!=":     lambda a, b: a != b,
    ">":      lambda a, b: a is not None and a > b,
    ">=":     lambda a, b: a is not None and a >= b,
    "<":      lambda a, b: a is not None and a < b,
    "<=":     lambda a, b: a is not None and a <= b,
    "in":     lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
}


def apply_op(criterion, value):
    op = clean(criterion["op"])
    if op not in OPS:
        raise ValueError(f"Unknown operator '{op}' in criterion — valid ops: {list(OPS)}")
    return OPS[op](value, criterion["value"])


def race_criteria(spec):
    return [c for c in spec["criteria"] if clean(c["scope"]) == "race"]


def entry_criteria(spec):
    return [c for c in spec["criteria"] if clean(c["scope"]) == "entry"]


def race_passes(race, meeting, spec, ctx):
    checks = [
        apply_op(c, resolve_field(c["field"], None, race, meeting, ctx))
        for c in race_criteria(spec)
    ]
    if not checks:
        return True
    return all(checks) if clean(spec.get("match", "ALL")) == "ALL" else any(checks)


def entry_passes(entry, spec, race, meeting, ctx):
    checks = [
        apply_op(c, resolve_field(c["field"], entry, race, meeting, ctx))
        for c in entry_criteria(spec)
    ]
    if not checks:
        return True
    return all(checks) if clean(spec.get("match", "ALL")) == "ALL" else any(checks)


# ── meeting filter ────────────────────────────────────────────────────────────

def meeting_allowed(m, spec, wl):
    """True if the meeting passes watchlist filters and the TAB-only flag."""
    if wl.get("meeting_ids") and m.get("id") not in wl["meeting_ids"]:
        return False
    if wl.get("states") and m.get("state") not in wl["states"]:
        return False
    if wl.get("tracks") and m.get("trackName") not in wl["tracks"]:
        return False
    if tab_only(spec) and not m.get("tabMeeting"):
        return False
    return True


# ── shortlist runner ──────────────────────────────────────────────────────────

def run_shortlist(cfg, spec):
    fk  = FormKing(cfg)
    wl  = cfg.get("watchlist", {})
    tab = tab_only(spec)
    ctx = {"past_runs": lambda e: past_runs(e, tab), "tab": tab}

    # Collect the names of any computed entry fields referenced in this profile,
    # in definition order, for extra CSV columns.
    extra_fields = list(dict.fromkeys(
        clean(c["field"])
        for c in entry_criteria(spec)
        if clean(c["field"]) in FIELD_REGISTRY
    ))

    level = clean(spec.get("output", "race"))
    print(f"\nRunning profile : '{spec['name']}'")
    print(f"Output level    : {level}  |  TAB-only: {tab}")
    print("Scanning upcoming meetings…\n")
    out = output_path(cfg, spec)

    if level == "entry":
        _run_entry_shortlist(fk, wl, spec, ctx, extra_fields, out)
    else:
        _run_race_shortlist(fk, wl, spec, ctx, out)


def _run_entry_shortlist(fk, wl, spec, ctx, extra_fields, out):
    """Shortlist at the runner level — one CSV row per matched runner.

    CSV columns:
      Core metadata  (track, race, distance, etc.)
      + one column per computed entry field referenced in the profile's criteria
      + result columns (populated if the race has been run)
      + IDs and Form King URL
    """
    CORE_COLS   = ["track", "state", "race_no", "distance", "going", "runner_no", "horse"]
    RESULT_COLS = ["finishing_pos", "starting_price", "margin"]
    META_COLS   = ["jockey", "trainer", "meeting_id", "race_id", "formking_url"]
    headers     = CORE_COLS + extra_fields + RESULT_COLS + META_COLS

    rows, hits = [], 0
    for m in fk.upcoming():
        if not meeting_allowed(m, spec, wl):
            continue
        detail = fk.meeting(m["id"]) or m
        for race in detail.get("races", []):
            race["_meeting_date"] = detail.get("date")
            if not race_passes(race, detail, spec, ctx):
                continue
            url = race_url(detail, race)
            for e in race.get("entries", []):
                if e.get("scratched"):
                    continue
                if not entry_passes(e, spec, race, detail, ctx):
                    continue
                hits += 1
                core = [
                    detail.get("trackName"), detail.get("state"),
                    race.get("number"), race.get("distance"), race.get("going"),
                    e.get("number"), (e.get("horse") or {}).get("name"),
                ]
                extra  = [resolve_field(f, e, race, detail, ctx) for f in extra_fields]
                result = [entry_finish_pos(e), entry_starting_price(e), entry_margin(e)]
                meta   = [e.get("jockey"), e.get("trainer"),
                          detail.get("id"), race.get("raceId"), url]
                rows.append(core + extra + result + meta)

    with open(out, "w", newline="") as f:
        csv.writer(f).writerows([headers] + rows)

    print(f"{hits} runner(s) matched.")
    print(f"Saved → {out}\n")

    for r in rows:
        fin_pos = r[headers.index("finishing_pos")]
        sp      = r[headers.index("starting_price")]
        fin_str = f" [FINISHED: {fin_pos} @ ${sp}]" if fin_pos != "" else ""
        extra_str = "  ".join(
            f"{f}={r[headers.index(f)]}"
            for f in extra_fields
        )
        print(f"  {r[0]} R{r[2]} {r[3]}m {str(r[4]):<6} "
              f"#{str(r[5]):>2} {str(r[6])[:22]:22}  {extra_str}{fin_str}")
        print(f"      {r[headers.index('formking_url')]}")


def _run_race_shortlist(fk, wl, spec, ctx, out):
    """Shortlist at the race level — one CSV row per matched race.

    When entry-scope criteria are present, a race is only included if at least
    one non-scratched runner passes those criteria.
    """
    headers = ["track", "state", "race_no", "race_name", "distance",
               "going", "field_size", "meeting_id", "race_id", "formking_url"]
    rows = []
    for m in fk.upcoming():
        if not meeting_allowed(m, spec, wl):
            continue
        detail = fk.meeting(m["id"]) or m
        for race in detail.get("races", []):
            race["_meeting_date"] = detail.get("date")
            if not race_passes(race, detail, spec, ctx):
                continue
            # If there are entry criteria, require at least one runner to pass them.
            if entry_criteria(spec) and not any(
                entry_passes(e, spec, race, detail, ctx)
                for e in race.get("entries", [])
                if not e.get("scratched")
            ):
                continue
            fs = len([e for e in race.get("entries", []) if not e.get("scratched")])
            rows.append([
                detail.get("trackName"), detail.get("state"),
                race.get("number"), race.get("name"),
                race.get("distance"), race.get("going"), fs,
                detail.get("id"), race.get("raceId"),
                race_url(detail, race),
            ])

    with open(out, "w", newline="") as f:
        csv.writer(f).writerows([headers] + rows)

    print(f"{len(rows)} race(s) matched.")
    print(f"Saved → {out}\n")
    for r in rows:
        print(f"  {r[0]} R{r[2]} {r[4]}m {r[5]}")
        print(f"      {r[9]}")


# ── interactive menu ──────────────────────────────────────────────────────────

BACK = "__BACK__"


def choose(prompt, options, back_label=None):
    for i, o in enumerate(options, 1):
        print(f"  {i}. {o}")
    if back_label:
        print(f"  0. {back_label}")
    while True:
        s = input(prompt).strip()
        if back_label and s == "0":
            return BACK
        if s.isdigit() and 1 <= int(s) <= len(options):
            return int(s) - 1
        print("  Invalid choice — try again.")


def shortlist_menu(cfg):
    while True:
        profiles = load_json("profiles.json")["profiles"]
        if not profiles:
            print("No profiles found in profiles.json.")
            return
        print("\nAvailable shortlist profiles:")
        idx = choose(
            "\nSelect a profile (0 to go back): ",
            [clean(p["name"]) for p in profiles],
            back_label="Back to main menu",
        )
        if idx == BACK:
            return
        run_shortlist(cfg, profiles[idx])
        input("\nPress Enter to return to the profile menu…")


def main():
    cfg = load_json("config.json")
    print("=" * 52)
    print("  FORM KING SHORTLIST ENGINE")
    print("=" * 52)
    while True:
        mode = choose(
            "\nSelect mode (0 to quit): ",
            ["Shortlist", "Pricing (coming soon)"],
            back_label="Quit",
        )
        if mode == BACK:
            print("\nBye 👋")
            return
        if mode == 1:
            print("\nPricing mode is not available yet — coming in a later release.")
            continue
        shortlist_menu(cfg)


if __name__ == "__main__":
    main()
