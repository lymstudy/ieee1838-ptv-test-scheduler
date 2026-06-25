from __future__ import annotations

import csv

from experiments.run_m12_hotspot_remote_validation import (
    RemoteConfig,
    build_ssh_command,
    build_hotspot_command,
    parse_hotspot_output,
    run_remote_validation,
)


def test_m12b_build_hotspot_command_with_optional_config() -> None:
    config = RemoteConfig(
        user="u",
        host="h",
        key_path="k",
        remote_root="~/work",
        hotspot_bin="/opt/hotspot",
        remote_config="/opt/hotspot.config",
        ssh_extra=(),
    )
    manifest = {"floorplan_path": "results/hotspot/m12/case.flp", "power_trace_path": "results/hotspot/m12/case.ptrace"}

    command = build_hotspot_command(config, manifest, "~/work/out.steady")

    assert "/opt/hotspot" in command
    assert "-c /opt/hotspot.config" in command
    assert "-f /home/u/work/case.flp" in command
    assert "-p /home/u/work/case.ptrace" in command


def test_m12b_remote_root_expands_tilde_to_user_home() -> None:
    config = RemoteConfig(user="autumn", host="h", key_path="k", remote_root="~/work", hotspot_bin="hotspot", remote_config="")

    assert config.remote_root_path == "/home/autumn/work"


def test_m12b_default_ssh_command_keeps_o_option_pairs() -> None:
    config = RemoteConfig(user="u", host="h", key_path="k", remote_root="~/work", hotspot_bin="hotspot", remote_config="")

    command = build_ssh_command(config, "echo ok")

    batch_index = command.index("BatchMode=yes")
    assert command[batch_index - 1] == "-o"


def test_m12b_parse_hotspot_pair_output_converts_kelvin(tmp_path) -> None:
    output = tmp_path / "out.steady"
    output.write_text("thermal_die0 300.0\nthermal_die1 310.0\n", encoding="utf-8")

    parsed = parse_hotspot_output(output)

    assert parsed.peak_block == "thermal_die1"
    assert round(parsed.peak_temperature_c, 2) == 36.85


def test_m12b_parse_hotspot_tabular_output(tmp_path) -> None:
    output = tmp_path / "out.ttrace"
    output.write_text("thermal_die0 thermal_die1\n25.1 25.2\n25.3 25.0\n", encoding="utf-8")

    parsed = parse_hotspot_output(output)

    assert parsed.peak_block == "thermal_die0"
    assert parsed.sample_count == 2
    assert parsed.peak_temperature_c == 25.3


def test_m12b_missing_manifest_inputs_are_reported(tmp_path) -> None:
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["case_id", "schedule_id", "floorplan_path", "power_trace_path", "sample_period_s", "sample_count", "region_count", "notes"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "case0",
                "schedule_id": "m4",
                "floorplan_path": str(tmp_path / "missing.flp"),
                "power_trace_path": str(tmp_path / "missing.ptrace"),
                "sample_period_s": "1e-5",
                "sample_count": "1",
                "region_count": "1",
                "notes": "",
            }
        )
    proxy = tmp_path / "proxy.csv"
    proxy.write_text("case_id,method_id,thermal_profile,peak_temperature_c,peak_region\n", encoding="utf-8")
    config = RemoteConfig("u", "h", "k", "~/work", "hotspot", "", ssh_extra=())

    rows = run_remote_validation(manifest, proxy, "stress_proxy", tmp_path / "out", config, dry_run=True)

    assert rows[0]["status"] == "missing_input"
