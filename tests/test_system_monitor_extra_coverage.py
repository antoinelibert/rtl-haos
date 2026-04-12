import pytest


def test_format_list_for_ha_empty_and_nonempty():
    import system_monitor

    assert system_monitor.format_list_for_ha([]) == "None"
    assert system_monitor.format_list_for_ha(["a", "b"]) == "a, b"


def _run_one_iteration(system_monitor, mqtt, monkeypatch):
    def stop_sleep(_s):
        raise KeyboardInterrupt()

    monkeypatch.setattr(system_monitor.time, "sleep", stop_sleep)

    with pytest.raises(KeyboardInterrupt):
        system_monitor.system_stats_loop(mqtt, "sysid", "Bridge")


def test_system_stats_loop_publishes_bridge_metrics(monkeypatch):
    import system_monitor

    sent = []

    class DummyMQTT:
        tracked_devices = {"A", "B", "C"}

        def send_sensor(self, *a, **k):
            sent.append((a, k))

    monkeypatch.setattr(
        system_monitor, "get_rtl_433_version_cached", lambda: "rtl_433 version 24.01"
    )

    _run_one_iteration(system_monitor, DummyMQTT(), monkeypatch)

    assert sent == [
        (("sysid", "sys_device_count", 3, "Bridge (sysid)", "Bridge"), {"is_rtl": True}),
        (
            ("sysid", "sys_rtl_433_version", "rtl_433 version 24.01", "Bridge (sysid)", "Bridge"),
            {"is_rtl": True},
        ),
    ]


def test_system_stats_loop_handles_empty_device_set(monkeypatch):
    import system_monitor

    sent = []

    class DummyMQTT:
        tracked_devices = set()

        def send_sensor(self, *a, **k):
            sent.append((a, k))

    monkeypatch.setattr(system_monitor, "get_rtl_433_version_cached", lambda: "rtl_433 not found")

    _run_one_iteration(system_monitor, DummyMQTT(), monkeypatch)

    assert sent == [
        (("sysid", "sys_device_count", 0, "Bridge (sysid)", "Bridge"), {"is_rtl": True}),
        (
            ("sysid", "sys_rtl_433_version", "rtl_433 not found", "Bridge (sysid)", "Bridge"),
            {"is_rtl": True},
        ),
    ]
