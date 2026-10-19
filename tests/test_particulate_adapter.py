from pathlib import Path

import pytest

from ai4d.adapters.particulate import ParticulateOutputAdapter


BASELINE_ROOT = Path(__file__).parents[2] / "baselines" / "000-default"


def _baseline_output() -> Path:
    outputs = sorted(BASELINE_ROOT.glob("*/metadata.json"))
    if not outputs:
        pytest.skip("official baseline output is not included in this release")
    return outputs[-1].parent


def test_parse_official_baseline_output():
    structure = ParticulateOutputAdapter().parse(_baseline_output())

    assert structure["schema_version"] == "1.0"
    assert structure["source"]["name"] == "instruct_particulate"
    assert structure["input"]["model_fingerprint"].startswith("sha256:")
    assert [part["id"] for part in structure["parts"]] == ["part_0", "part_1"]
    assert structure["joints"][0]["type"] == "revolute"
    assert len(structure["joints"][0]["raw_prediction"]["revolute_axis"]) == 6
    assert len(structure["joints"][0]["axis"]) == 3
    assert len(structure["joints"][0]["origin_mm"]) == 3
    assert structure["raw_prediction"]["segmentation"]["num_faces"] == 39996
    assert "query_points" in structure["raw_prediction"]["query_predictions"]["keys"]
    assert structure["review"]["needs_human_review"] is True
