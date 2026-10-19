from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from ai4d.review import CHECK_KEYS


REGION_TYPES = (
    ("whole_child_part", "整个运动部件"),
    ("joint_proximal", "关节附近靠近连接处"),
    ("child_distal", "运动部件远离关节的一端"),
)
DIRECTION_STRENGTHS = (0.2, 0.4, 0.6, 0.8)


def generate_candidates(
    structure_path_value: str | Path,
    review_path_value: str | Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Generate review-only magnetization candidates from an approved structure."""
    structure_path = Path(structure_path_value).expanduser().resolve()
    if not structure_path.is_file():
        raise FileNotFoundError(f"Structure JSON not found: {structure_path}")
    structure = _read_object(structure_path)
    review_path = Path(review_path_value).expanduser().resolve() if review_path_value else structure_path.parent / "human_review.json"
    review = _read_object(review_path)
    _require_approved_review(review)

    joints = structure.get("joints", [])
    if not joints:
        raise ValueError("Structure JSON contains no joints")

    candidates: list[dict[str, Any]] = []
    for joint in joints:
        joint_id = str(joint.get("id", "joint_unknown"))
        child_part = str(joint.get("child_part", ""))
        axis = _normalise_axis(joint.get("axis"), joint_id)
        directions = _perpendicular_directions(axis)
        for region_index, (region_type, region_label) in enumerate(REGION_TYPES):
            for direction_index, direction in enumerate(directions):
                for strength in DIRECTION_STRENGTHS:
                    candidate_id = (
                        f"mag_{joint_id}_{region_index}_{direction_index}_"
                        f"{int(strength * 10):02d}"
                    )
                    candidates.append(
                        {
                            "id": candidate_id,
                            "joint_id": joint_id,
                            "target_part": child_part,
                            "region_id": f"{joint_id}_{region_type}",
                            "region_type": region_type,
                            "region_label": region_label,
                            "geometry_ref": {
                                "kind": "part_region_candidate",
                                "part_id": child_part,
                                "status": "symbolic_pending_geometry_mapping",
                            },
                            "direction_model": [round(float(value), 8) for value in direction],
                            "strength_normalized": strength,
                            "phase_rad": 0.0,
                            "predicted_motion": None,
                            "score": None,
                            "reason": "待磁-弹性物理模型和实验标定评估",
                            "approved": False,
                            "device_ready": False,
                            "needs_human_review": True,
                        }
                    )

    result = {
        "schema_version": "1.0",
        "source": {
            "structure_file": structure_path.name,
            "structure_fingerprint": structure.get("input", {}).get("model_fingerprint"),
            "review_file": review_path.name,
        },
        "material_assumption": {
            "flexible_by_default": True,
            "flexible_region_selection": False,
        },
        "candidates": candidates,
        "needs_human_review": True,
        "device_ready": False,
    }
    output_path = structure_path.parent / "magnetization_candidates.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path, result


def _read_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _require_approved_review(review: dict[str, Any]) -> None:
    checks = review.get("checks", {})
    if review.get("status") != "approved_for_planning":
        raise PermissionError("Structure review is not approved_for_planning")
    missing_or_failed = [key for key in CHECK_KEYS if checks.get(key) is not True]
    if missing_or_failed:
        raise PermissionError("Structure review checks failed: " + ", ".join(missing_or_failed))


def _normalise_axis(axis_value: Any, joint_id: str) -> np.ndarray:
    if not isinstance(axis_value, list) or len(axis_value) != 3:
        raise ValueError(f"Joint {joint_id} axis must contain three values")
    axis = np.asarray([float(value) for value in axis_value], dtype=np.float64)
    norm = float(np.linalg.norm(axis))
    if norm < 1e-8:
        raise ValueError(f"Joint {joint_id} axis is zero")
    return axis / norm


def _perpendicular_directions(axis: np.ndarray) -> list[np.ndarray]:
    reference = np.eye(3)[int(np.argmin(np.abs(axis)))]
    first = np.cross(axis, reference)
    first /= np.linalg.norm(first)
    second = np.cross(axis, first)
    second /= np.linalg.norm(second)
    return [first, -first, second, -second]
