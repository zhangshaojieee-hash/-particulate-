from __future__ import annotations

from math import sqrt
from typing import Any


ALLOWED_JOINT_TYPES = {"revolute", "prismatic"}


def validate_structure(data: dict[str, Any]) -> list[str]:
    """Return deterministic validation errors for a project Structure JSON."""
    errors: list[str] = []
    part_ids = {part.get("id") for part in data.get("parts", [])}
    part_ids.discard(None)
    if not part_ids:
        errors.append("parts is empty")

    coordinate_system = data.get("coordinate_system", {})
    if coordinate_system.get("unit") not in {"mm", "unknown"}:
        errors.append("coordinate_system.unit must be 'mm' or 'unknown'")

    for joint in data.get("joints", []):
        joint_id = joint.get("id", "<unknown>")
        joint_type = joint.get("type")
        if joint_type not in ALLOWED_JOINT_TYPES:
            errors.append(f"unsupported joint type: {joint_type!r} ({joint_id})")
        if joint.get("parent_part") not in part_ids:
            errors.append(f"unknown parent: {joint.get('parent_part')}")
        if joint.get("child_part") not in part_ids:
            errors.append(f"unknown child: {joint.get('child_part')}")
        axis = joint.get("axis", [])
        norm = sqrt(sum(float(value) ** 2 for value in axis)) if len(axis) == 3 else 0.0
        if norm < 1e-8:
            errors.append(f"zero axis: {joint_id}")

    review = data.get("review", {})
    if review.get("status") not in {"candidate", "reviewed", "approved"}:
        errors.append("review.status must be candidate, reviewed, or approved")
    return errors
