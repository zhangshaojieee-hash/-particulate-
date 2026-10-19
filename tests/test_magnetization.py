import json
from pathlib import Path

import pytest

from ai4d.magnetization import generate_candidates


def _write_structure(path: Path) -> None:
    path.write_text(json.dumps({
        "input": {"model_fingerprint": "sha256:test"},
        "joints": [{
            "id": "joint_0",
            "type": "revolute",
            "parent_part": "part_0",
            "child_part": "part_1",
            "axis": [0.0, 0.0, 1.0],
        }],
    }), encoding="utf-8")


def _write_review(path: Path, approved: bool) -> None:
    checks = {
        key: approved for key in (
            "parts_correct",
            "segmentation_correct",
            "joint_exists",
            "joint_type_correct",
            "parent_child_correct",
            "axis_correct",
            "unit_confirmed",
        )
    }
    path.write_text(json.dumps({
        "status": "approved_for_planning" if approved else "待审核",
        "checks": checks,
    }), encoding="utf-8")


def test_candidates_require_approved_structure_review(tmp_path):
    structure = tmp_path / "structure.json"
    review = tmp_path / "human_review.json"
    _write_structure(structure)
    _write_review(review, approved=False)

    with pytest.raises(PermissionError, match="not approved_for_planning"):
        generate_candidates(structure, review)


def test_generate_candidates_is_review_only(tmp_path):
    structure = tmp_path / "structure.json"
    review = tmp_path / "human_review.json"
    _write_structure(structure)
    _write_review(review, approved=True)

    output_path, result = generate_candidates(structure, review)

    assert output_path.name == "magnetization_candidates.json"
    assert len(result["candidates"]) == 48
    assert result["material_assumption"]["flexible_region_selection"] is False
    assert all(item["approved"] is False for item in result["candidates"])
    assert all(item["device_ready"] is False for item in result["candidates"])
    assert all(item["needs_human_review"] is True for item in result["candidates"])
    assert json.loads(output_path.read_text(encoding="utf-8"))["device_ready"] is False
