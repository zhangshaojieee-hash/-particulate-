import json
from pathlib import Path

import pytest

from ai4d.review import load_structure, save_review


BASELINE = Path(__file__).parents[2] / "baselines" / "000-default" / (
    "a51d8e27b2a9d6efd4037ca9fc59928105bea0736faf3c0197a3e604fff4766c_20261014_134524"
) / "structure.json"


def test_save_review_requires_all_checks_for_planning(tmp_path):
    structure_path = tmp_path / "structure.json"
    structure_path.write_text(json.dumps({"parts": [], "joints": []}), encoding="utf-8")

    message, review = save_review(
        structure_path,
        "通过结构审核",
        "tester",
        "axis needs review",
        True,
        True,
        True,
        True,
        True,
        False,
        True,
    )

    assert review["status"] == "通过结构审核"
    assert "不能进入运动规划" in message
    persisted = json.loads((tmp_path / "human_review.json").read_text(encoding="utf-8"))
    assert persisted["checks"]["axis_correct"] is False


def test_save_review_allows_planning_only_when_all_checks_pass(tmp_path):
    structure_path = tmp_path / "structure.json"
    structure_path.write_text(json.dumps({"parts": [], "joints": []}), encoding="utf-8")

    _, review = save_review(
        structure_path,
        "通过结构审核",
        "tester",
        "ok",
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    )

    assert review["status"] == "approved_for_planning"


def test_load_structure_finds_visualization():
    if not BASELINE.exists():
        pytest.skip("official baseline output is not included in this release")
    structure, model_path, output_dir = load_structure(BASELINE)
    assert structure["source"]["name"] == "instruct_particulate"
    assert model_path is not None
    assert model_path.endswith("mesh_parts_with_axes.glb")
    assert output_dir.endswith("134524")
