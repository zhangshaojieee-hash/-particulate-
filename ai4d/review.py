from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CHECK_KEYS = (
    "parts_correct",
    "segmentation_correct",
    "joint_exists",
    "joint_type_correct",
    "parent_child_correct",
    "axis_correct",
    "unit_confirmed",
)


def load_structure(path_value: str | Path) -> tuple[dict[str, Any], str | None, str]:
    """Load Structure JSON and locate the official visualization asset."""
    structure_path = Path(path_value).expanduser().resolve()
    if not structure_path.is_file():
        raise FileNotFoundError(f"Structure JSON not found: {structure_path}")
    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    if not isinstance(structure, dict):
        raise ValueError("Structure JSON must contain an object")
    raw_output_dir = Path(structure.get("source", {}).get("raw_output_dir", ""))
    model_path = raw_output_dir / "mesh_parts_with_axes.glb"
    return structure, str(model_path) if model_path.is_file() else None, str(structure_path.parent)


def save_review(
    structure_path_value: str | Path,
    decision: str,
    reviewer: str,
    notes: str,
    *checks: bool,
) -> tuple[str, dict[str, Any]]:
    """Persist a human review beside Structure JSON without changing the prediction."""
    structure_path = Path(structure_path_value).expanduser().resolve()
    if not structure_path.is_file():
        raise FileNotFoundError(f"Structure JSON not found: {structure_path}")
    if len(checks) != len(CHECK_KEYS):
        raise ValueError(f"Expected {len(CHECK_KEYS)} review checks, got {len(checks)}")
    check_values = {key: bool(value) for key, value in zip(CHECK_KEYS, checks)}
    all_checks_pass = all(check_values.values())
    status = "approved_for_planning" if decision == "通过结构审核" and all_checks_pass else decision
    review = {
        "schema_version": "1.0",
        "structure_file": structure_path.name,
        "status": status,
        "checks": check_values,
        "reviewer": reviewer.strip() or None,
        "notes": notes.strip(),
    }
    review_path = structure_path.parent / "human_review.json"
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    message = f"已保存审核记录：{review_path}"
    if status != "approved_for_planning":
        message += "；当前结果不能进入运动规划。"
    return message, review
