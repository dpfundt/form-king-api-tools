# Profiles Library

Community-contributed shortlist profile packs. Each file contains one or more profiles grouped around a single racing idea or theme.

These files are **not active by default** — copy the profile object(s) you want into the top-level `profiles.json` to use them.

---

## How to use a profile from this library

1. Open the `.json` file that interests you.
2. Copy the profile object (the `{ "name": "...", "criteria": [...] }` block) you want.
3. Paste it into the `profiles` array in `profiles.json`.
4. Run the engine — it will appear in the menu.

---

## How to contribute a profile

1. Create a new file named `profiles_<your_idea>.json` in this folder.
2. Follow the same schema as the existing examples.
3. Add a `_comment` key to each profile explaining:
   - What it looks for
   - The racing logic behind it (why is this interesting?)
4. Submit a Pull Request — one file per racing idea / theme keeps things easy to browse.

No Python required — profile contributions are pure JSON.

---

## Field reference

| Field | Scope | Type | Description |
|---|---|---|---|
| `distance` | race | int | Race distance in metres |
| `field_size` | race / entry | int | Number of non-scratched runners |
| `going` | race | str | Track condition (e.g. `"Good4"`) |
| `state` | race | str | State code (e.g. `"VIC"`, `"NSW"`) |
| `days_last_run_to_race` | entry | int | Days since runner's last recorded start |
| `ls_war_margin_over_field` | entry | float | Last-start Form King Weight Adjusted Rating vs best rival |
| `avg_best2_last3_war_margin_over_field` | entry | float | Best-2-of-last-3 Form King Weight Adjusted Rating vs best rival |

Any raw API field (e.g. `barrier`, `weight`, `age`, `raceClass`) can also be used directly in criteria — the engine looks up the registry first, then falls back to the raw API response.

## Available operators

| Operator | Meaning |
|---|---|
| `==` | Equal |
| `!=` | Not equal |
| `>` | Greater than |
| `>=` | Greater than or equal |
| `<` | Less than |
| `<=` | Less than or equal |
| `in` | Value is in a list |
| `not_in` | Value is not in a list |
