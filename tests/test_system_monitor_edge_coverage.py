import importlib
import importlib.util
import pathlib
import runpy

import pytest

import system_monitor


def test_system_stats_loop_bridge_stats_error_is_caught(mocker, capsys):
    """Covers [ERROR] Bridge Stats update failed path."""

    mqtt = mocker.Mock()
    mqtt.tracked_devices = {"dev1"}
    mqtt.send_sensor = mocker.Mock(side_effect=RuntimeError("boom"))

    mocker.patch("system_monitor.get_rtl_433_version_cached", return_value="rtl_433 version 24.01")
    mocker.patch("system_monitor.time.sleep", side_effect=InterruptedError("stop"))

    with pytest.raises(InterruptedError):
        system_monitor.system_stats_loop(mqtt, "ID", "MODEL")

    out = capsys.readouterr().out
    assert "Bridge Stats update failed" in out


def test_get_rtl_433_version_handles_generic_error(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("broken")

    monkeypatch.setattr(system_monitor.subprocess, "run", boom)

    assert system_monitor._get_rtl_433_version() == "Unknown (RuntimeError)"


def test_system_monitor_import_guard_handles_find_spec_valueerror(monkeypatch, capsys):
    """Import should still work even if find_spec is patched to explode."""

    def boom(_name: str):
        raise ValueError("bad spec")

    monkeypatch.setattr(importlib.util, "find_spec", boom)

    path = pathlib.Path(__file__).resolve().parents[1] / "system_monitor.py"
    ns = runpy.run_path(str(path))

    assert callable(ns["system_stats_loop"])
