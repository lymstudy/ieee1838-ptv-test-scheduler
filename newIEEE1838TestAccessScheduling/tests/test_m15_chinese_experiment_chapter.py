from __future__ import annotations

import csv

from experiments.generate_m15_chinese_experiment_chapter import build_caption_rows, write_caption_index


def test_m15_build_caption_rows_adds_known_figure_caption() -> None:
    rows = build_caption_rows(
        [
            {
                "figure_id": "m13_m12b_proxy_hotspot_peak_comparison",
                "path": "results/figures/m13/hotspot.png",
                "title": "HotSpot",
                "notes": "notes",
            }
        ]
    )

    assert rows[0]["artifact_type"] == "figure"
    assert "HotSpot" in rows[0]["caption"]
    assert "数值完全等价" in rows[0]["paper_usage"]
    assert any(row["artifact_id"] == "m12b_hotspot_validation" for row in rows)


def test_m15_write_caption_index(tmp_path) -> None:
    output = tmp_path / "captions.csv"
    rows = [
        {
            "artifact_id": "fig0",
            "artifact_type": "figure",
            "path": "results/figures/fig0.png",
            "caption": "图 1 示例",
            "paper_usage": "用于测试",
        }
    ]

    write_caption_index(output, rows)

    with output.open("r", encoding="utf-8", newline="") as handle:
        parsed = list(csv.DictReader(handle))
    assert parsed[0]["caption"] == "图 1 示例"
