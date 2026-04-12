import builtins
import importlib
import sys


def _reload_system_monitor(monkeypatch, *, find_spec_behavior, import_psutil_error: bool):
    """Reload system_monitor while perturbing importlib/builtins hooks."""

    sys.modules.pop("system_monitor", None)

    monkeypatch.setattr(importlib.util, "find_spec", find_spec_behavior)

    if import_psutil_error:
        orig_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "psutil":
                raise ImportError("psutil blocked for test")
            return orig_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", fake_import)

    import system_monitor  # noqa: F401

    return sys.modules["system_monitor"]


def test_system_monitor_import_ignores_unrelated_find_spec_patch(monkeypatch):
    def boom(_name):
        raise ValueError("bad spec")

    sm = _reload_system_monitor(monkeypatch, find_spec_behavior=boom, import_psutil_error=False)
    assert hasattr(sm, "system_stats_loop")
    assert hasattr(sm, "format_list_for_ha")


def test_system_monitor_import_ignores_blocked_psutil_import(monkeypatch):
    sm = _reload_system_monitor(
        monkeypatch,
        find_spec_behavior=lambda _name: object(),
        import_psutil_error=True,
    )
    assert hasattr(sm, "system_stats_loop")


def test_format_list_for_ha_and_loop_one_iteration(monkeypatch):
    import system_monitor as sm

    assert sm.format_list_for_ha([]) == "None"

    long_list = ["x" * 10] * 100
    out = sm.format_list_for_ha(long_list)
    assert len(out) <= 250

    # Run a single loop iteration by forcing time.sleep to abort.
    class DummyMQTT:
        def __init__(self):
            self.tracked_devices = {"a", "b"}
            self.calls = []

        def send_sensor(self, device_id, field, value, device_name, model_name, is_rtl=True):
            self.calls.append((device_id, field, value, device_name, model_name, is_rtl))

    dm = DummyMQTT()
    monkeypatch.setattr(sm, "get_rtl_433_version_cached", lambda: "rtl_433 version 24.01")

    def stop(_sec):
        raise StopIteration

    monkeypatch.setattr(sm.time, "sleep", stop)

    try:
        sm.system_stats_loop(dm, "dev", "Model")
    except StopIteration:
        pass

    assert any(
        field == "sys_device_count" and value == 2 for (_d, field, value, *_rest) in dm.calls
    )
    assert any(
        field == "sys_rtl_433_version" and value == "rtl_433 version 24.01"
        for (_d, field, value, *_rest) in dm.calls
    )
