from __future__ import annotations

import csv

from experiments.generate_m13_visualizations import FigureEntry, read_ttrace, write_figure_index


def test_m13_read_ttrace_converts_kelvin_to_celsius(tmp_path) -> None:
    trace = tmp_path / "sample.ttrace"
    trace.write_text("thermal_die0 thermal_die1\n333.15 334.15\n", encoding="utf-8")

    headers, samples = read_ttrace(trace)

    assert headers == ["thermal_die0", "thermal_die1"]
    assert samples == [[60.0, 61.0]]


def test_m13_write_figure_index(tmp_path) -> None:
    output = tmp_path / "index.csv"
    entries = [
        FigureEntry(
            figure_id="fig0",
            path="results/figures/m13/fig0.png",
            title="Figure 0",
            source="results/tables/input.csv",
            notes="test figure",
        )
    ]

    write_figure_index(entries, output)

    with output.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["figure_id"] == "fig0"
    assert rows[0]["notes"] == "test figure"
