# Form King Shortlist Engine

A lightweight filter engine for [Form King](https://www.formking.com.au) API data.

Point it at today's upcoming races, define your rules in a profile, and get a ready-to-open CSV shortlist.

---

## Quick start

1. **Edit `config.json`** — paste your API key (from your Form King account settings).
2. **Double-click `shortlist.bat`** (Windows) or **`shortlist.command`** (macOS / Linux).
3. Select a profile and press Enter.
4. Find your CSV in the `output/` folder — open in Excel or Google Sheets.

---

## Project structure

```
shortlist/
├── shortlist.py            Engine: API client, criteria matcher, CSV writer
├── config.json             Your API key, watchlist, cache settings
├── profiles.json           Active profiles shown in the menu
├── shortlist.bat            Windows launcher (double-click to run)
├── shortlist.command        macOS / Linux launcher (double-click to run)
│
├── fields/                 Computed field library
│   ├── __init__.py         Field registry (the "plugin" wiring)
│   ├── core.py             Built-in fields: days_last_run_to_race, field_size
│   └── war_margin.py       WAR margin fields (Form King ratings-based)
│
├── profiles_library/       Community profile packs — browse, copy, contribute
│   ├── README.md
│   ├── example_layoff_resumers.json
│   └── example_war_margin.json
│
└── output/                 Generated CSV shortlists (auto-created, git-ignored)
```

---

## Adding a computed field

A computed field is a small Python function that derives a value from the API data for a runner or race.

1. Open (or create) a `.py` file in `fields/`.
2. Write your function and decorate it:

```python
from fields import register_field

@register_field("my_field_name")
def _compute(entry, race, meeting, ctx):
    """One-line description of the racing logic."""
    # ctx["past_runs"](entry) → filtered past runs, newest first
    # ctx["tab"]              → True if tab_only is active
    return ...  # a number, string, or None
```

3. Add an import for your module at the bottom of `fields/__init__.py`.
4. Use `"my_field_name"` in any profile's `criteria` — no other changes needed.

**PR tip:** one file per field (or a tightly related group of fields). The docstring explaining the racing logic is the most valuable part of the contribution.

---

## Adding or editing a profile

Open `profiles.json` and add an object to the `profiles` array:

```json
{
  "name": "My profile",
  "output": "entry",
  "tab_only": true,
  "match": "ALL",
  "criteria": [
    { "scope": "race",  "field": "distance",              "op": ">=", "value": 1400 },
    { "scope": "entry", "field": "days_last_run_to_race",  "op": "<=", "value": 7 }
  ]
}
```

| Key | Values | Description |
|---|---|---|
| `output` | `"entry"` / `"race"` | One CSV row per runner, or one per race |
| `tab_only` | `true` / `false` | Exclude non-TAB meetings and past events |
| `match` | `"ALL"` / `"ANY"` | AND all criteria, or OR them |
| `scope` | `"race"` / `"entry"` | Whether the criterion applies to the race or to each runner |

**Operators:** `==`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `not_in`

Browse `profiles_library/` for community examples. Copy the profile objects you like into `profiles.json`.

---

## Using AI to build your own rules

This project is designed to be extended with the help of AI coding assistants (Claude, ChatGPT, Cursor, etc.).

Suggested prompt to get started:

> "I have a Python project that filters horse racing runners using a registry of computed fields.  
> The field functions live in `fields/` and have the signature:  
> `def my_field(entry, race, meeting, ctx) -> value | None`  
> `ctx["past_runs"](entry)` returns a list of past run dicts, newest first.  
> Each dict has keys like `date`, `finishPosition`, `margin`, `ratingScale`, `adjustedForTodaysWeight`.  
> Can you write a field called `[your idea]` that [does what you want]?"

---

## Contributing

- **New field** → single-file PR to `fields/`
- **New profile** → single JSON file PR to `profiles_library/`

Keep each contribution self-contained and documented. The racing-logic docstring or `_comment` is the most important part of any contribution — it's what helps the next person decide whether to use your idea.
