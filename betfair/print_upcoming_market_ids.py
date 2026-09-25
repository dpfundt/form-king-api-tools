import argparse
import csv
import os
import re
import sys
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import betfairlightweight


SYDNEY = ZoneInfo("Australia/Sydney")
UTC = timezone.utc
WINDOW = timedelta(hours=3)


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date {value!r}; use YYYY-MM-DD"
        )


def utc_time(value):
    """Betfair market times are UTC; handle both naive and aware datetimes."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def api_time(value):
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    parser = argparse.ArgumentParser(
        description="Print published Australian thoroughbred win/place markets as CSV."
    )
    parser.add_argument("--from", dest="from_date", type=parse_date)
    parser.add_argument("--to", dest="to_date", type=parse_date)
    args = parser.parse_args()

    now = datetime.now(UTC).replace(microsecond=0)

    if (args.from_date is None) != (args.to_date is None):
        parser.error("Supply both --from and --to, or neither.")

    if args.from_date is None:
        start, end = now, now + timedelta(hours=24)
    else:
        if args.to_date < args.from_date:
            parser.error("--to must be on or after --from.")

        # Midnight at the start of --to's following day: --to is inclusive.
        start = datetime.combine(args.from_date, time.min, SYDNEY).astimezone(UTC)
        end = datetime.combine(
            args.to_date + timedelta(days=1), time.min, SYDNEY
        ).astimezone(UTC)

        if end <= now:
            parser.error(
                "This date range is entirely in the past. "
                "listMarketCatalogue is not a historical archive."
            )
        if start < now:
            print(
                "Note: the past portion of this range is unavailable; "
                "querying from now onward.",
                file=sys.stderr,
            )
            start = now

    client = betfairlightweight.APIClient(
        username=os.environ["BETFAIR_USERNAME"],
        password=os.environ["BETFAIR_PASSWORD"],
        app_key=os.environ["BETFAIR_APP_KEY"],
        certs=os.environ["BETFAIR_CERTS_PATH"],
    )
    client.login()

    # Key: (event ID, scheduled start in UTC).
    # Pairing by event and time accommodates generic "To Be Placed" names.
    races = {}
    window_start = start

    while window_start < end:
        window_end = min(window_start + WINDOW, end)

        for market_type in ("WIN", "PLACE"):
            markets = client.betting.list_market_catalogue(
                filter={
                    "eventTypeIds": ["7"],
                    "marketCountries": ["AU"],
                    "marketTypeCodes": [market_type],
                    "raceTypes": ["Flat", "Hurdle", "Steeple"],
                    "marketStartTime": {
                        "from": api_time(window_start),
                        "to": api_time(window_end),
                    },
                },
                market_projection=["EVENT", "MARKET_START_TIME"],
                sort="FIRST_TO_START",
                max_results=1000,
            )

            if len(markets) == 1000:
                raise RuntimeError(
                    "A catalogue request reached max_results; "
                    "reduce the three-hour WINDOW."
                )

            for market in markets:
                if not market.event or not market.market_start_time:
                    continue

                scheduled_utc = utc_time(market.market_start_time)

                # The API's time boundary may be inclusive; enforce our own
                # half-open range and avoid duplicate boundary records.
                if not start <= scheduled_utc < end:
                    continue

                key = (market.event.id, scheduled_utc)

                if market_type == "WIN":
                    match = re.match(r"^R\s*(\d+)\b", market.market_name, re.I)
                    if not match:
                        continue
                    if re.search(r"\b(?:pace|trot)\b", market.market_name, re.I):
                        continue

                    race = races.setdefault(key, {})
                    race["track"] = market.event.venue or market.event.name
                    race["race_number"] = int(match.group(1))
                    race["scheduled_utc"] = scheduled_utc
                    race["win_market_id"] = market.market_id
                else:
                    races.setdefault(key, {})["place_market_id"] = market.market_id

        window_start = window_end

    writer = csv.writer(sys.stdout)
    writer.writerow([
        "date_sydney",
        "scheduled_jump_time_sydney",
        "track",
        "race_number",
        "win_market_id",
        "place_market_id",
    ])

    for race in sorted(
            (race for race in races.values() if "win_market_id" in race),
            key=lambda race: (
                    race["scheduled_utc"],
                    race["track"],
                    race["race_number"],
            ),
    ):
        local_start = race["scheduled_utc"].astimezone(SYDNEY)
        writer.writerow([
            local_start.date().isoformat(),
            local_start.timetz().isoformat(timespec="seconds"),
            race["track"],
            race["race_number"],
            race["win_market_id"],
            race.get("place_market_id", ""),
        ])


if __name__ == "__main__":
    main()