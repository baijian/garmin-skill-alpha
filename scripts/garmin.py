#!/usr/bin/env python3
"""Unified CLI dispatcher for garmin-skill-alpha.

This file intentionally keeps business logic in the migrated source scripts.
It selects the right script, strips the unified --profile option, and forwards
the remaining arguments unchanged.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
HEALTH_DIR = SCRIPT_DIR / "health"
CN_DIR = SCRIPT_DIR / "cn"
SYNC_DIR = SCRIPT_DIR / "sync"

HEALTH_AUTH = HEALTH_DIR / "garmin_auth.py"
HEALTH_DATA = HEALTH_DIR / "garmin_data.py"
HEALTH_EXTENDED = HEALTH_DIR / "garmin_data_extended.py"
HEALTH_CHART = HEALTH_DIR / "garmin_chart.py"
HEALTH_QUERY = HEALTH_DIR / "garmin_query.py"
HEALTH_ACTIVITY_FILES = HEALTH_DIR / "garmin_activity_files.py"
CN_CLI = CN_DIR / "garmin_cli.py"
FIT_PARSER = CN_DIR / "fit_file_parser.py"
SYNC_CLI = SYNC_DIR / "sync.py"

PROFILES = {"all", "cn", "global"}

DATA_METRICS = {
    "sleep",
    "hrv",
    "body_battery",
    "heart_rate",
    "activities",
    "stress",
    "summary",
    "profile",
}

EXTENDED_METRICS = {
    "training_readiness",
    "training_status",
    "body_composition",
    "weigh_ins",
    "spo2",
    "respiration",
    "steps",
    "floors",
    "intensity_minutes",
    "hydration",
    "stress_detailed",
    "max_metrics",
    "fitness_age",
    "endurance_score",
    "hill_score",
    "hr_intraday",
}

ACTIVITY_FILE_ACTIONS = {"download", "parse", "query", "analyze"}


HEALTH_HELP = """Health route examples:
  garmin.py health login --profile cn --email <email> --password <password>
  garmin.py health login --profile global --email <email> --password <password>
  garmin.py health status --profile all
  garmin.py health sleep --days 14
  garmin.py health hrv --days 30 --profile global
  GARMIN_PROFILE=cn garmin.py health body_battery --days 7
  garmin.py health extended training_readiness
  garmin.py health chart dashboard --days 30
  garmin.py health query heart_rate "15:00" --date 2026-06-10
  garmin.py health activity-files download --activity-id 123456 --format fit

Health route targets:
  auth | login | status       Authentication helper
  data <metric>               health-analysis data script
  <metric>                    shortcut for data/extended metrics
  extended <metric>           extended health metrics
  chart <chart>               HTML chart/dashboard generation
  query <metric> <time>       time-based health query
  activity-files <action>     FIT/GPX/TCX download, parse, query, analyze
"""

CN_HELP = """CN route examples:
  garmin.py cn summary --date 2026-06-10
  garmin.py cn activities --days 7 --type running
  garmin.py cn detail <activity_id>
  garmin.py cn run <activity_id>
  garmin.py cn export <activity_id> --format csv --output /tmp

This route forwards to scripts/cn/garmin_cli.py.
"""

SYNC_HELP = """Sync route examples:
  garmin.py sync set-credentials --email-cn <email> --password-cn <password>
  garmin.py sync sync --new-only
  garmin.py sync status

This route forwards to scripts/sync/sync.py.
"""

FIT_PARSE_HELP = """FIT parser route examples:
  garmin.py fit-parse /path/to/activity.fit --pretty
  garmin.py fit-parse /path/to/activity.fit --targets 1,5,10,last --output /tmp/fit.json

This route forwards to scripts/cn/fit_file_parser.py.
"""


def extract_profile(argv: Sequence[str]) -> Tuple[str, List[str]]:
    """Remove a unified --profile option from any position in argv."""
    profile = "cn"
    cleaned: List[str] = []
    i = 0

    while i < len(argv):
        item = argv[i]
        if item == "--profile":
            if i + 1 >= len(argv):
                raise SystemExit("--profile requires a value: cn or global")
            profile = argv[i + 1].lower()
            i += 2
            continue
        if item.startswith("--profile="):
            profile = item.split("=", 1)[1].lower()
            i += 1
            continue
        cleaned.append(item)
        i += 1

    if profile not in PROFILES:
        raise SystemExit(f"Unsupported profile '{profile}'. Choose one of: cn, global")
    return profile, cleaned


def run_python(script: Path, args: Iterable[str], profile: str) -> int:
    if not script.exists():
        print(f"Missing routed script: {script}", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env["GARMIN_PROFILE"] = profile
    env["GARMIN_SKILL_PROFILE"] = profile
    command = [sys.executable, str(script), *list(args)]
    return subprocess.call(command, env=env)


def print_block(text: str) -> int:
    print(text.rstrip())
    return 0


def dispatch_health(args: Sequence[str], profile: str) -> int:
    if not args or args[0] in {"-h", "--help"}:
        return print_block(HEALTH_HELP)

    target = args[0]
    rest = list(args[1:])

    if target == "auth":
        return run_python(HEALTH_AUTH, rest, profile)
    if target in {"login", "status"}:
        return run_python(HEALTH_AUTH, [target, *rest], profile)
    if target == "data":
        return run_python(HEALTH_DATA, rest, profile)
    if target in DATA_METRICS:
        return run_python(HEALTH_DATA, [target, *rest], profile)
    if target == "extended":
        return run_python(HEALTH_EXTENDED, rest, profile)
    if target in EXTENDED_METRICS:
        return run_python(HEALTH_EXTENDED, [target, *rest], profile)
    if target == "chart":
        return run_python(HEALTH_CHART, rest, profile)
    if target == "query":
        return run_python(HEALTH_QUERY, rest, profile)
    if target in {"activity-files", "files"}:
        return run_python(HEALTH_ACTIVITY_FILES, rest, profile)
    if target in ACTIVITY_FILE_ACTIONS:
        return run_python(HEALTH_ACTIVITY_FILES, [target, *rest], profile)

    print(f"Unknown health target: {target}", file=sys.stderr)
    print(HEALTH_HELP.rstrip(), file=sys.stderr)
    return 2


def dispatch_cn(args: Sequence[str], profile: str) -> int:
    if not args or args[0] in {"-h", "--help"}:
        return print_block(CN_HELP)
    return run_python(CN_CLI, args, profile)


def dispatch_sync(args: Sequence[str], profile: str) -> int:
    if not args or args[0] in {"-h", "--help"}:
        return print_block(SYNC_HELP)
    return run_python(SYNC_CLI, args, profile)


def dispatch_fit_parse(args: Sequence[str], profile: str) -> int:
    if not args or args[0] in {"-h", "--help"}:
        return print_block(FIT_PARSE_HELP)
    return run_python(FIT_PARSER, args, profile)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="garmin.py",
        description="Unified dispatcher for the garmin-skill-alpha scripts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Profile handling:\n"
            "  --profile cn|global may appear anywhere and defaults to cn.\n"
            "  --profile all is intended for health auth status checks.\n"
            "  The dispatcher strips it before forwarding to child scripts.\n"
        ),
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default="cn",
        help="Garmin profile to expose to routed scripts (default: cn)",
    )

    subparsers = parser.add_subparsers(dest="route", metavar="route")
    health_parser = subparsers.add_parser(
        "health",
        help="health-analysis route",
        description="Route to migrated health-analysis scripts.",
        epilog=HEALTH_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    health_parser.add_argument("route_args", nargs=argparse.REMAINDER)

    cn_parser = subparsers.add_parser(
        "cn",
        help="Garmin Connect CN raw route",
        description="Route to the migrated Garmin Connect CN CLI.",
        epilog=CN_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    cn_parser.add_argument("route_args", nargs=argparse.REMAINDER)

    sync_parser = subparsers.add_parser(
        "sync",
        help="CN to Global sync route",
        description="Route to the migrated CN to Global sync script.",
        epilog=SYNC_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sync_parser.add_argument("route_args", nargs=argparse.REMAINDER)

    fit_parser = subparsers.add_parser(
        "fit-parse",
        help="standardized FIT parser route",
        description="Route to the migrated standardized FIT parser.",
        epilog=FIT_PARSE_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    fit_parser.add_argument("route_args", nargs=argparse.REMAINDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    try:
        profile, cleaned_args = extract_profile(raw_args)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2

    parser = build_parser()
    parsed = parser.parse_args(cleaned_args)

    if not parsed.route:
        parser.print_help()
        return 2

    route_args = getattr(parsed, "route_args", [])
    if parsed.route == "health":
        return dispatch_health(route_args, profile)
    if parsed.route == "cn":
        return dispatch_cn(route_args, profile)
    if parsed.route == "sync":
        return dispatch_sync(route_args, profile)
    if parsed.route == "fit-parse":
        return dispatch_fit_parse(route_args, profile)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
