from __future__ import annotations

import argparse
import hashlib
import json
from math import sqrt
from pathlib import Path
from typing import Any

import numpy as np

from ai4d.schemas.structure import validate_structure


class ParticulateOutputAdapter:
    """Convert one completed official Space output directory to Structure JSON."""

    REQUIRED_FILES = ("metadata.json", "kinematic.json", "seg.npy")

    def parse(self, output_dir: str | Path) -> dict[str, Any]:
        root = Path(output_dir).expanduser().resolve()
        metadata = self._read_json(root / "metadata.json")
        kinematic = self._read_json(root / "kinematic.json")
        self._require_files(root)
        segmentation = np.load(root / "seg.npy", allow_pickle=False)
        if segmentation.ndim != 1:
            raise ValueError(f"seg.npy must be one-dimensional, got {segmentation.shape}")

        links = self._links(kinematic)
        link_ids = {link["link_id"] for link in links}
        predicted_part_ids = sorted({int(value) for value in segmentation.tolist()})
        unknown_part_ids = set(predicted_part_ids) - link_ids
        if unknown_part_ids:
            raise ValueError(f"seg.npy contains unknown link IDs: {sorted(unknown_part_ids)}")

        source_path = self._source_path(root, metadata)
        source_sha256 = self._sha256(source_path) if source_path is not None else None
        joints = [self._joint_record(record, link_ids) for record in kinematic.get("joints", [])]
        structure = {
            "schema_version": "1.0",
            "source": {
                "name": "instruct_particulate",
                "version": self._source_version(metadata),
                "checkpoint": metadata.get("checkpoint_path"),
                "raw_output_dir": str(root),
            },
            "input": {
                "file_name": source_path.name if source_path else Path(str(metadata.get("input_path", "unknown"))).name,
                "model_fingerprint": f"sha256:{source_sha256}" if source_sha256 else None,
                "unit": metadata.get("unit", "unknown"),
                "up_direction": metadata.get("mesh_orientation", {}).get("input_up_dir", "+Z"),
            },
            "coordinate_system": {
                "name": "model_local_right_handed_z_up",
                "unit": metadata.get("unit", "unknown"),
                "version": 1,
            },
            "parts": [
                {
                    "id": f"part_{link['link_id']}",
                    "label": link["name"],
                    "official_link_id": link["link_id"],
                    "segmentation_present": link["link_id"] in predicted_part_ids,
                    "confidence": None,
                }
                for link in links
            ],
            "joints": joints,
            "motion_hierarchy": {
                "links": links,
                "joint_specs": metadata.get("joint_specs", []),
            },
            "confidence": None,
            "review": {
                "status": "candidate",
                "corrected": False,
                "reviewer": None,
                "needs_human_review": True,
                "reason": "Official prediction requires geometry and kinematic review before planning.",
            },
            "raw_prediction": {
                "metadata": metadata,
                "kinematic": kinematic,
                "segmentation": {
                    "file": "seg.npy",
                    "num_faces": int(segmentation.shape[0]),
                    "part_ids": predicted_part_ids,
                },
                "query_predictions": self._query_summary(root / "query_predictions.npz"),
            },
        }
        errors = validate_structure(structure)
        if errors:
            raise ValueError("Generated Structure JSON is invalid: " + "; ".join(errors))
        return structure

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise FileNotFoundError(path)
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError(f"{path.name} must contain a JSON object")
        return value

    @classmethod
    def _require_files(cls, root: Path) -> None:
        if not root.is_dir():
            raise NotADirectoryError(root)
        missing = [name for name in cls.REQUIRED_FILES if not (root / name).is_file()]
        if missing:
            raise FileNotFoundError(f"Missing official output files: {', '.join(missing)}")

    @staticmethod
    def _links(kinematic: dict[str, Any]) -> list[dict[str, Any]]:
        links: list[dict[str, Any]] = []
        for fallback_id, record in enumerate(kinematic.get("links", [])):
            link_id = int(record.get("link_id", fallback_id))
            links.append({"link_id": link_id, "name": str(record.get("name", f"link_{link_id}"))})
        if not links:
            raise ValueError("kinematic.json contains no links")
        return links

    @classmethod
    def _joint_record(cls, record: dict[str, Any], link_ids: set[int]) -> dict[str, Any]:
        parent = int(record["parent_link_id"])
        child = int(record["child_link_id"])
        if parent not in link_ids or child not in link_ids:
            raise ValueError(f"Joint references unknown links: {parent}->{child}")
        is_revolute = bool(record.get("is_revolute"))
        joint_type = "revolute" if is_revolute else "prismatic" if record.get("is_prismatic") else "unknown"
        raw_axis = record.get("revolute_axis") if is_revolute else record.get("prismatic_axis")
        axis, origin = cls._axis_and_origin_from_official_record(raw_axis, is_revolute)
        joint: dict[str, Any] = {
            "id": f"joint_{record.get('joint_id', 0)}",
            "type": joint_type,
            "parent_part": f"part_{parent}",
            "child_part": f"part_{child}",
            "axis": axis,
            "origin_mm": origin,
            "range_rad": record.get("revolute_range" if is_revolute else "prismatic_range"),
            "confidence": None,
            "needs_human_review": True,
            "raw_prediction": record,
        }
        return joint

    @staticmethod
    def _axis_and_origin_from_official_record(
        raw_axis: Any,
        is_revolute: bool,
    ) -> tuple[list[float], list[float] | None]:
        if not isinstance(raw_axis, list) or len(raw_axis) < 3:
            return [0.0, 0.0, 0.0], None
        direction = np.asarray([float(value) for value in raw_axis[:3]], dtype=np.float64)
        norm = float(np.linalg.norm(direction))
        if norm < 1e-8:
            return [0.0, 0.0, 0.0], None
        axis = direction / norm
        if not is_revolute or len(raw_axis) < 6:
            return axis.tolist(), None
        moment = np.asarray([float(value) for value in raw_axis[3:6]], dtype=np.float64)
        point = np.cross(moment, axis)
        return axis.tolist(), point.tolist()

    @staticmethod
    def _source_path(root: Path, metadata: dict[str, Any]) -> Path | None:
        copied = root / "input_mesh_original.glb"
        if copied.is_file():
            return copied
        candidate = Path(str(metadata.get("input_path", "")))
        return candidate if candidate.is_file() else None

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _source_version(metadata: dict[str, Any]) -> str:
        run_dir = str(metadata.get("run_dir", ""))
        return Path(run_dir).name or "unknown"

    @staticmethod
    def _query_summary(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        with np.load(path, allow_pickle=False) as payload:
            return {
                "file": path.name,
                "keys": list(payload.files),
                "shapes": {key: list(payload[key].shape) for key in payload.files},
            }

    def write(self, output_dir: str | Path, destination: str | Path | None = None) -> Path:
        structure = self.parse(output_dir)
        target = Path(destination) if destination else Path(output_dir) / "structure.json"
        target = target.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(structure, indent=2) + "\n", encoding="utf-8")
        return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    destination = ParticulateOutputAdapter().write(args.output_dir, args.output)
    print(destination)


if __name__ == "__main__":
    main()
