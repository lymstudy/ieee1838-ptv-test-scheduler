from __future__ import annotations

import argparse
import csv
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_SSH_EXTRA = [
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=10",
    "-o",
    "StrictHostKeyChecking=no",
    "-o",
    "UserKnownHostsFile=/dev/null",
    "-o",
    "HostKeyAlgorithms=+ssh-rsa,ssh-dss",
    "-o",
    "PubkeyAcceptedAlgorithms=+ssh-rsa",
]

SUMMARY_FIELDS = [
    "case_id",
    "schedule_id",
    "status",
    "reason",
    "proxy_profile",
    "proxy_peak_temperature_c",
    "proxy_peak_region",
    "hotspot_peak_temperature_c",
    "hotspot_peak_block",
    "peak_region_match",
    "hotspot_output_path",
    "remote_work_dir",
    "hotspot_command",
]


@dataclass(frozen=True)
class RemoteConfig:
    user: str
    host: str
    key_path: str
    remote_root: str
    hotspot_bin: str
    remote_config: str
    ssh_extra: tuple[str, ...] = tuple(DEFAULT_SSH_EXTRA)

    @property
    def target(self) -> str:
        return f"{self.user}@{self.host}"

    @property
    def remote_root_path(self) -> str:
        if self.remote_root == "~":
            return f"/home/{self.user}"
        if self.remote_root.startswith("~/"):
            return f"/home/{self.user}/{self.remote_root[2:]}"
        return self.remote_root


@dataclass(frozen=True)
class HotSpotParseResult:
    peak_temperature_c: float
    peak_block: str
    sample_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M12b remote HotSpot validation on exported .flp/.ptrace inputs.")
    parser.add_argument("--manifest", default="results/hotspot/m12_hotspot_export_manifest.csv", help="HotSpot export manifest from M12.")
    parser.add_argument("--proxy-summary", default="results/tables/m12_thermal_validation_summary.csv", help="M12 proxy thermal summary CSV.")
    parser.add_argument("--proxy-profile", default="stress_proxy", help="Proxy profile used for comparison.")
    parser.add_argument("--output", default="results/tables/m12_hotspot_validation_summary.csv", help="Output summary CSV.")
    parser.add_argument("--report-output", default="results/reports/m12_hotspot_validation_report.md", help="Output Markdown report.")
    parser.add_argument("--local-result-dir", default="results/hotspot/m12b_outputs", help="Local directory for pulled HotSpot outputs.")
    parser.add_argument("--ssh-user", default="autumn", help="Remote VM SSH user.")
    parser.add_argument("--ssh-host", default="192.168.113.142", help="Remote VM SSH host.")
    parser.add_argument("--ssh-key", default=r"C:\Users\ZhuanZ1\.ssh\codex_rhel6", help="SSH private key path.")
    parser.add_argument("--remote-root", default="~/m12b_hotspot_validation", help="Remote work directory.")
    parser.add_argument("--hotspot-bin", default="hotspot", help="Remote HotSpot executable or absolute path.")
    parser.add_argument("--remote-config", default="", help="Optional remote HotSpot config file path.")
    parser.add_argument("--dry-run", action="store_true", help="Do not run SSH/SCP; validate inputs and write skipped rows.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = RemoteConfig(
        user=args.ssh_user,
        host=args.ssh_host,
        key_path=args.ssh_key,
        remote_root=args.remote_root,
        hotspot_bin=args.hotspot_bin,
        remote_config=args.remote_config,
    )
    rows = run_remote_validation(
        manifest_path=Path(args.manifest),
        proxy_summary_path=Path(args.proxy_summary),
        proxy_profile=args.proxy_profile,
        output_dir=Path(args.local_result_dir),
        config=config,
        dry_run=args.dry_run,
    )
    write_summary(rows, args.output)
    write_report(rows, args.report_output)
    print(f"rows={len(rows)}")
    print(f"output={args.output}")
    print(f"report_output={args.report_output}")


def run_remote_validation(
    manifest_path: Path,
    proxy_summary_path: Path,
    proxy_profile: str,
    output_dir: Path,
    config: RemoteConfig,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    manifest_rows = read_manifest(manifest_path)
    proxy_by_key = read_proxy_summary(proxy_summary_path, proxy_profile)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    remote_ready, remote_reason = (False, "dry-run") if dry_run else check_remote_hotspot(config)
    if not dry_run and remote_ready:
        try:
            run_checked(build_ssh_command(config, f"mkdir -p {sh_quote(config.remote_root_path)}"))
        except RuntimeError as exc:
            remote_ready = False
            remote_reason = str(exc)

    for manifest in manifest_rows:
        local_flp = Path(manifest["floorplan_path"])
        local_ptrace = Path(manifest["power_trace_path"])
        proxy = proxy_by_key.get((manifest["case_id"], manifest["schedule_id"]), {})
        base_row = {
            "case_id": manifest["case_id"],
            "schedule_id": manifest["schedule_id"],
            "proxy_profile": proxy_profile,
            "proxy_peak_temperature_c": proxy.get("peak_temperature_c", ""),
            "proxy_peak_region": proxy.get("peak_region", ""),
            "remote_work_dir": config.remote_root_path,
        }

        missing = [str(path) for path in (local_flp, local_ptrace) if not path.exists()]
        if missing:
            rows.append(_row(base_row, "missing_input", "missing local input: " + ";".join(missing)))
            continue
        if dry_run:
            command = build_hotspot_command(config, manifest, local_output_name(manifest))
            rows.append(_row(base_row, "dry_run", "remote execution disabled", hotspot_command=command))
            continue
        if not remote_ready:
            rows.append(_row(base_row, "skipped", remote_reason))
            continue

        remote_flp = f"{config.remote_root_path}/{local_flp.name}"
        remote_ptrace = f"{config.remote_root_path}/{local_ptrace.name}"
        remote_output = f"{config.remote_root_path}/{local_output_name(manifest)}"
        local_output = output_dir / local_output_name(manifest)
        hotspot_command = build_hotspot_command(config, manifest, remote_output)

        try:
            run_checked(build_scp_to_remote_command(config, local_flp, remote_flp))
            run_checked(build_scp_to_remote_command(config, local_ptrace, remote_ptrace))
            run_checked(build_ssh_command(config, hotspot_command))
            run_checked(build_scp_from_remote_command(config, remote_output, local_output))
            parsed = parse_hotspot_output(local_output)
        except (RuntimeError, FileNotFoundError, ValueError) as exc:
            rows.append(_row(base_row, "failed", str(exc), hotspot_command=hotspot_command))
            continue

        rows.append(
            _row(
                base_row,
                "ok",
                "",
                hotspot_peak_temperature_c=parsed.peak_temperature_c,
                hotspot_peak_block=parsed.peak_block,
                peak_region_match=str(parsed.peak_block) == str(proxy.get("peak_region", "")),
                hotspot_output_path=local_output.as_posix(),
                hotspot_command=hotspot_command,
            )
        )
    return rows


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"missing HotSpot export manifest: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_proxy_summary(path: Path, profile: str) -> dict[tuple[str, str], dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {
            (row["case_id"], row["method_id"]): row
            for row in csv.DictReader(handle)
            if row.get("thermal_profile") == profile
        }


def check_remote_hotspot(config: RemoteConfig) -> tuple[bool, str]:
    check = (
        f"command -v {sh_quote(config.hotspot_bin)} >/dev/null 2>&1 "
        f"&& command -v gcc >/dev/null 2>&1 "
        f"&& command -v make >/dev/null 2>&1"
    )
    result = subprocess.run(build_ssh_command(config, check), capture_output=True, text=True)
    if result.returncode == 0:
        return True, ""
    detail = clean_remote_detail(result.stderr or result.stdout or "")
    return False, "remote HotSpot/gcc/make check failed" + (f": {detail}" if detail else "")


def build_hotspot_command(config: RemoteConfig, manifest: dict[str, str], remote_output: str) -> str:
    remote_flp = f"{config.remote_root_path}/{Path(manifest['floorplan_path']).name}"
    remote_ptrace = f"{config.remote_root_path}/{Path(manifest['power_trace_path']).name}"
    parts = [sh_quote(config.hotspot_bin)]
    if config.remote_config:
        parts.extend(["-c", sh_quote(config.remote_config)])
    parts.extend(["-f", sh_quote(remote_flp), "-p", sh_quote(remote_ptrace), "-o", sh_quote(remote_output)])
    return " ".join(parts)


def build_ssh_command(config: RemoteConfig, remote_command: str) -> list[str]:
    return ["ssh", "-i", config.key_path, *config.ssh_extra, config.target, remote_command]


def build_scp_to_remote_command(config: RemoteConfig, local_path: Path, remote_path: str) -> list[str]:
    return ["scp", "-i", config.key_path, *config.ssh_extra, str(local_path), f"{config.target}:{remote_path}"]


def build_scp_from_remote_command(config: RemoteConfig, remote_path: str, local_path: Path) -> list[str]:
    return ["scp", "-i", config.key_path, *config.ssh_extra, f"{config.target}:{remote_path}", str(local_path)]


def run_checked(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        return
    detail = clean_remote_detail(result.stderr or result.stdout or "")
    message = f"{command[0]} failed with exit code {result.returncode}"
    if detail:
        message += f": {detail}"
    raise RuntimeError(message)


def parse_hotspot_output(path: str | Path) -> HotSpotParseResult:
    lines = [line.split() for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"empty HotSpot output: {path}")

    if len(lines[0]) == 2 and _is_float(lines[0][1]):
        pairs = [(tokens[0], float(tokens[1])) for tokens in lines if len(tokens) >= 2 and _is_float(tokens[1])]
        if not pairs:
            raise ValueError(f"could not parse HotSpot output pairs: {path}")
        block, value = max(pairs, key=lambda item: item[1])
        return HotSpotParseResult(peak_temperature_c=_to_celsius(value), peak_block=block, sample_count=len(pairs))

    header = lines[0]
    samples = []
    for tokens in lines[1:]:
        values = [float(token) for token in tokens if _is_float(token)]
        if len(values) == len(header):
            samples.append(values)
    if not samples:
        raise ValueError(f"could not parse HotSpot tabular output: {path}")

    peak_value = max(max(sample) for sample in samples)
    peak_index = next(index for index, _name in enumerate(header) if any(sample[index] == peak_value for sample in samples))
    return HotSpotParseResult(peak_temperature_c=_to_celsius(peak_value), peak_block=header[peak_index], sample_count=len(samples))


def write_summary(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in SUMMARY_FIELDS})


def write_report(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    ok_rows = [row for row in rows if row["status"] == "ok"]
    lines = [
        "# M12b HotSpot Remote Validation Report",
        "",
        f"- HotSpot executed: {'yes' if ok_rows else 'no'}",
        f"- Total rows: {len(rows)}",
        f"- Successful HotSpot rows: {len(ok_rows)}",
        f"- Non-success rows: {len(rows) - len(ok_rows)}",
        "",
        "## Row Summary",
        "",
        "| case | schedule | status | proxy_peak_c | hotspot_peak_c | hotspot_block | reason |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {case_id} | {schedule_id} | {status} | {proxy_peak_temperature_c} | "
            "{hotspot_peak_temperature_c} | {hotspot_peak_block} | {reason} |".format(**{field: row.get(field, "") for field in SUMMARY_FIELDS})
        )

    if ok_rows:
        lines.extend(["", "## Method Ranking Check", ""])
        for case_id in sorted({row["case_id"] for row in ok_rows}):
            case_rows = [row for row in ok_rows if row["case_id"] == case_id]
            proxy_best = min(case_rows, key=lambda row: float(row["proxy_peak_temperature_c"] or "inf"))
            hotspot_best = min(case_rows, key=lambda row: float(row["hotspot_peak_temperature_c"] or "inf"))
            match = proxy_best["schedule_id"] == hotspot_best["schedule_id"]
            lines.append(
                f"- `{case_id}`: proxy best `{proxy_best['schedule_id']}`, HotSpot best `{hotspot_best['schedule_id']}`, ranking_match={match}."
            )

    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- This report is HotSpot execution evidence only for rows with `status=ok`.",
            "- Non-success rows must not be cited as HotSpot validation.",
            "- The exported floorplan is block-level and simplified; it supports trend validation, not industrial signoff.",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def local_output_name(manifest: dict[str, str]) -> str:
    return f"{manifest['case_id']}__{manifest['schedule_id']}.ttrace"


def _row(base: dict[str, Any], status: str, reason: str, **extra: Any) -> dict[str, Any]:
    payload = dict(base)
    clean_reason = clean_remote_detail(str(reason))
    payload.update(
        {
            "status": status,
            "reason": clean_reason,
            "hotspot_peak_temperature_c": "",
            "hotspot_peak_block": "",
            "peak_region_match": "",
            "hotspot_output_path": "",
            "hotspot_command": "",
        }
    )
    payload.update(extra)
    return payload


def _to_celsius(value: float) -> float:
    return value - 273.15 if value > 200.0 else value


def clean_remote_detail(text: str) -> str:
    collapsed = " ".join(text.split())
    return re.sub(r"Warning: Permanently added '[^']+' \([^)]+\) to the list of known hosts\. ?", "", collapsed).strip()


def _is_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def sh_quote(value: str) -> str:
    return shlex.quote(value)


if __name__ == "__main__":
    main()
