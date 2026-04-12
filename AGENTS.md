# AGENTS

## Repo Shape
- This is a single-root Python app / Home Assistant add-on, not a package workspace. Read `main.py`, `config.py`, `rtl_manager.py`, `mqtt_handler.py`, `data_processor.py`, `config.yaml`, `Dockerfile`, and `entrypoint.sh` first.
- `entrypoint.sh` chooses `/run.sh` for HA add-on mode (`/data/options.json` plus `with-contenv`) and `/run-standalone.sh` otherwise.

## Config And Runtime
- Standalone/Docker config comes from `.env`; add-on config comes from `config.yaml` -> `/data/options.json`. List/dict env vars such as `RTL_CONFIG`, `DEVICE_BLACKLIST`, and `DEVICE_WHITELIST` are JSON strings, not YAML.
- `config.py` and `run.sh` both participate in add-on startup/config loading; review both before changing add-on option loading or defaults.
- `main.py` is the runtime entrypoint: it starts MQTT, the throttle loop, discovers SDRs, and spawns one `rtl_loop` thread per radio. Auto-vs-manual radio behavior is driven by whether `RTL_CONFIG` is empty.
- `rtl_manager.build_rtl_433_command()` is the source of truth for `rtl_433` CLI assembly. `RTL_433_ARGS` is a global override, not an append-only extra: matching flags replace per-radio/default flags. The code always forces `-F json` and adds `-M level` if missing.
- Relative `rtl_433_config_path` is resolved through `/share`, `/config`, `/data`, then the current working directory. The add-on maps both `config` and `share`.
- Device filters are case-insensitive `fnmatch` globs against decoded `id`, `model`, and `type`, not regex.

## Publish Path
- Published field handling is split across `rtl_manager.py` (flattening plus derived/remapped fields), `data_processor.py` (throttling/averaging), and `mqtt_handler.py` (retained HA discovery/state, utility-unit inference, `battery_ok` -> `Battery Low` binary sensor). A field change usually needs all three checked.
- If you add or rename a published field, update `field_meta.py` or its model-specific overrides too. `tests/test_field_meta_fixture_unknowns.py` is the regression guard and prints paste-ready stubs from captured fixtures.

## Versions And Dependencies
- `config.yaml` `version:` is the canonical base version and must stay plain SemVer/prerelease. Display-only build metadata comes from `RTL_HAOS_BUILD` or `build.txt` via `version_utils.py` as `vX.Y.Z+build`.
- The Docker build runs `uv sync --frozen --no-dev --no-install-project` from `pyproject.toml` and `uv.lock`; if dependencies change, `uv.lock` must be regenerated too.
- Do not introduce Python 3.13-only syntax just because `pyproject.toml` says `requires-python = ">=3.13"`: CI runs 3.11/3.12 and the add-on base images are Python 3.12.

## Verification
- Local test env: `./scripts/pytest_venv.sh --no-run` then `source .venv-pytest/bin/activate`.
- CI gate order is `ruff check .` then `python -m pytest`. There is no mypy, formatter, or separate typecheck gate.
- Ruff is intentionally narrow: `E9` and `F` only, with `E501`, `F401`, and `F841` ignored. Do not create cleanup-only diffs based on default Ruff expectations.
- Default `pytest` is unit-only. Opt-in suites:
- `RUN_RTL433_TESTS=1 pytest -m integration`
- `RUN_RTL433_TESTS=1 pytest -m integration -k rtl433_replay`
- `RUN_HARDWARE_TESTS=1 pytest -m hardware`
- `tests/conftest.py` clears `RTL_HAOS_BUILD` and isolates device filters, so tests must set config/env explicitly instead of relying on your local `.env`.
- Replay captures under `tests/fixtures/rtl433/` are gitignored. `./scripts/record_rtl433_fixture.sh --dry-run ...` is useful because it rejects ambiguous values like `433.92` or `250` without `M`/`k` suffixes.

## HAOS And Docker
- `docker-compose.yml` defaults to `rtl_tcp` / network SDR mode. USB passthrough is intentionally commented out; enable `privileged: true` and `/dev/bus/usb` only when testing a local dongle.
- Use `./scripts/haos.sh` for HAOS local add-on work. It reads the slug from `config.yaml`, syncs to `/addons/local/<slug>`, can rebuild/restart/show logs, and writes an untracked `build.txt` with the current git SHA plus `-dirty` when applicable.
