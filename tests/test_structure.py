from ai4d.schemas.structure import validate_structure


def test_validate_structure_accepts_candidate():
    data = {
        "coordinate_system": {"unit": "unknown"},
        "parts": [{"id": "part_0"}, {"id": "part_1"}],
        "joints": [{
            "id": "joint_0",
            "type": "revolute",
            "parent_part": "part_0",
            "child_part": "part_1",
            "axis": [0.0, 0.0, 1.0],
        }],
        "review": {"status": "candidate"},
    }
    assert validate_structure(data) == []


def test_validate_structure_rejects_unknown_parts_and_zero_axis():
    data = {
        "coordinate_system": {"unit": "unknown"},
        "parts": [{"id": "part_0"}],
        "joints": [{
            "id": "joint_0",
            "type": "revolute",
            "parent_part": "part_0",
            "child_part": "missing",
            "axis": [0.0, 0.0, 0.0],
        }],
        "review": {"status": "candidate"},
    }
    errors = validate_structure(data)
    assert "unknown child: missing" in errors
    assert "zero axis: joint_0" in errors
