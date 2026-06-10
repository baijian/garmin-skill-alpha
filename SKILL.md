---
name: garmin-skill-alpha
description: >
  Unified Garmin/佳明 skill for health analysis, recovery trends, activity file
  download/parsing, Garmin Connect CN raw queries and exports, and CN to Global
  activity sync. Use this whenever the user asks about Garmin/佳明 sleep, HRV,
  Body Battery, stress, resting heart rate, training readiness/status, activity
  details, FIT/GPX/TCX/CSV files, race/event data, dashboards, or Garmin account
  sync.
---

# Garmin Skill Alpha

This is the single Garmin entrypoint. It combines the former health-analysis,
Garmin Connect CN data, and CN-to-Global sync skills into one skill directory.

## Default Routing

- Health, sleep, recovery, HRV, Body Battery, resting heart rate, stress,
  training status/readiness, charts, dashboards, and trend analysis: start with
  the `health` route. Default profile is `cn`.
- Garmin Connect CN raw checks, one-day `summary --date`, raw activity `detail`,
  `run` analysis, CSV export, CN-account reconciliation, and Garmin API-shaped
  output: use the `cn` route.
- FIT/GPX/TCX activity file download and general activity-file analysis:
  use `health activity-files ...` for analysis-oriented workflows, or `cn export`
  when CN raw export format matters. Use `fit-parse` for standardized FIT JSON.
- CN to Global activity sync: use the `sync` route.
- Events/race calendar requests belong to the CN route. If the bundled CN CLI
  does not expose an events command, report that this source snapshot has not
  migrated events yet instead of inventing data.

## Unified CLI

Use the local dispatcher:

```bash
python3 <SKILL_DIR>/scripts/garmin.py --help
```

The dispatcher accepts `--profile cn|global` anywhere in the command line and
defaults to `cn`. It also accepts `--profile all` for auth status checks. The
profile is stripped before calling child scripts and is exposed as
`GARMIN_PROFILE` for profile-aware scripts.

Health scripts can also be run directly with `--profile cn|global`, or by
setting `GARMIN_PROFILE=cn` / `GARMIN_PROFILE=global`.

Health token stores:

- CN: `~/.config/garmin/cn/`
- Global: `~/.config/garmin/global/`
- Legacy global tokens from `~/.clawdbot/garmin/` are copied into the new global
  token directory when the global profile is used and the new directory is not
  present.

### Health route

```bash
python3 <SKILL_DIR>/scripts/garmin.py health --help
python3 <SKILL_DIR>/scripts/garmin.py health login --profile cn --email <email> --password <password>
python3 <SKILL_DIR>/scripts/garmin.py health login --profile global --email <email> --password <password>
python3 <SKILL_DIR>/scripts/garmin.py health status --profile all
python3 <SKILL_DIR>/scripts/garmin.py health sleep --days 14
python3 <SKILL_DIR>/scripts/garmin.py health hrv --days 30 --profile global
GARMIN_PROFILE=cn python3 <SKILL_DIR>/scripts/garmin.py health body_battery --days 7
python3 <SKILL_DIR>/scripts/garmin.py health extended training_readiness
python3 <SKILL_DIR>/scripts/garmin.py health chart dashboard --days 30
python3 <SKILL_DIR>/scripts/garmin.py health query heart_rate "15:00" --date 2026-06-10
python3 <SKILL_DIR>/scripts/garmin.py health activity-files download --activity-id 123456 --format fit
```

Health subroutes:

- `auth`, `login`, `status`: authentication helper.
- `data` or metric shortcuts: `sleep`, `hrv`, `body_battery`, `heart_rate`,
  `activities`, `stress`, `summary`, `profile`.
- `extended` or metric shortcuts: `training_readiness`, `training_status`,
  `body_composition`, `weigh_ins`, `spo2`, `respiration`, `steps`, `floors`,
  `intensity_minutes`, `hydration`, `stress_detailed`, `max_metrics`,
  `fitness_age`, `endurance_score`, `hill_score`, `hr_intraday`.
- `chart`: `sleep`, `body_battery`, `hrv`, `activities`, `dashboard`.
- `query`: time-based health queries.
- `activity-files`: activity file download, parse, query, and analysis.

Direct health script examples:

```bash
python3 <SKILL_DIR>/scripts/health/garmin_data.py sleep --days 14 --profile cn
python3 <SKILL_DIR>/scripts/health/garmin_data_extended.py training_readiness --profile global
python3 <SKILL_DIR>/scripts/health/garmin_chart.py dashboard --days 30 --profile cn
python3 <SKILL_DIR>/scripts/health/garmin_query.py heart_rate "15:00" --profile cn
python3 <SKILL_DIR>/scripts/health/garmin_activity_files.py download --activity-id 123456 --format fit --profile global
python3 <SKILL_DIR>/scripts/health/garmin_auth.py status --profile all
```

For interpretation guidance, read `references/health_analysis.md`. For extended
metric examples, read `references/extended_capabilities.md`.

### CN raw route

```bash
python3 <SKILL_DIR>/scripts/garmin.py cn --help
python3 <SKILL_DIR>/scripts/garmin.py cn summary --date 2026-06-10
python3 <SKILL_DIR>/scripts/garmin.py cn activities --days 7 --type running
python3 <SKILL_DIR>/scripts/garmin.py cn detail <activity_id>
python3 <SKILL_DIR>/scripts/garmin.py cn run <activity_id>
python3 <SKILL_DIR>/scripts/garmin.py cn export <activity_id> --format csv --output /tmp
```

Use this route when exact Garmin Connect CN output, CSV export, raw activity
details, or account reconciliation is more important than synthesized analysis.
For long-range CN batch workflows, read `references/advanced-usage.md`.

### FIT parser route

```bash
python3 <SKILL_DIR>/scripts/garmin.py fit-parse --help
python3 <SKILL_DIR>/scripts/garmin.py fit-parse /path/to/activity.fit --pretty
```

This route wraps the CN FIT parser and produces standardized JSON with FIT
header details, message counts, metric availability, and kilometer samples.

### Sync route

```bash
python3 <SKILL_DIR>/scripts/garmin.py sync --help
python3 <SKILL_DIR>/scripts/garmin.py sync set-credentials --email-cn <email> --password-cn <password>
python3 <SKILL_DIR>/scripts/garmin.py sync sync --new-only
python3 <SKILL_DIR>/scripts/garmin.py sync status
```

This performs one-way CN to Global activity sync. Do not run sync or login
commands unless the user explicitly asks for account access or synchronization.

## Safety And Privacy

- Do not make real Garmin login, query, export, or sync calls during setup or
  verification unless the user asks for live data.
- Credentials and tokens are stored locally by the underlying scripts. Prefer
  existing token/session state when available.
- For health interpretation, give informational guidance only; do not present it
  as medical diagnosis.

## Bundled Files

- `scripts/health/`: migrated health-analysis scripts.
- `scripts/cn/`: migrated Garmin Connect CN CLI and FIT parser.
- `scripts/sync/`: migrated CN-to-Global sync script.
- `references/`: health analysis, extended capabilities, API notes, MCP setup,
  and CN advanced usage references.
