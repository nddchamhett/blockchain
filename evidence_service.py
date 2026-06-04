import hashlib
import json
import os
from datetime import datetime

import cv2


EVIDENCE_ROOT = os.getenv("EVIDENCE_ROOT", "evidence")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_incident_paths(incident_id, detected_at):
    detected_dt = datetime.fromisoformat(detected_at.replace("Z", "+00:00"))
    dated_dir = os.path.join(
        EVIDENCE_ROOT,
        detected_dt.strftime("%Y"),
        detected_dt.strftime("%m"),
        detected_dt.strftime("%d"),
    )
    ensure_dir(dated_dir)

    stem = f"incident_{incident_id:06d}_{detected_dt.strftime('%Y%m%dT%H%M%SZ')}"
    image_path = os.path.join(dated_dir, f"{stem}.jpg")
    metadata_path = os.path.join(dated_dir, f"{stem}.json")
    return image_path, metadata_path


def create_evidence_package(incident, frame, runtime_context):
    image_path, metadata_path = build_incident_paths(incident["id"], incident["detected_at"])

    if frame is None:
        raise ValueError("Cannot create evidence package without a frame")

    if not cv2.imwrite(image_path, frame):
        raise RuntimeError(f"Failed to write evidence snapshot to {image_path}")

    file_sha256 = sha256_file(image_path)
    file_size = os.path.getsize(image_path)

    metadata = {
        "incident_id": incident["id"],
        "source": incident["source"],
        "detected_at": incident["detected_at"],
        "stream_started_at": incident.get("stream_started_at"),
        "active_source_label": incident.get("active_source_label"),
        "artifact_type": "snapshot",
        "snapshot_path": image_path,
        "snapshot_sha256": file_sha256,
        "runtime": runtime_context,
    }

    metadata_bytes = json.dumps(metadata, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
    with open(metadata_path, "wb") as handle:
        handle.write(metadata_bytes)

    metadata_sha256 = sha256_bytes(metadata_bytes)

    return {
        "artifact_type": "snapshot",
        "file_path": image_path,
        "metadata_path": metadata_path,
        "file_sha256": file_sha256,
        "metadata_sha256": metadata_sha256,
        "file_size": file_size,
        "mime_type": "image/jpeg",
        "storage_uri": image_path.replace("\\", "/"),
        "verify_status": "verified",
    }


def verify_evidence_artifact(detail):
    file_path = detail.get("file_path")
    metadata_path = detail.get("metadata_path")
    file_sha256 = detail.get("file_sha256")
    metadata_sha256 = detail.get("metadata_sha256")

    if not file_path or not metadata_path:
        return "missing"
    if not os.path.exists(file_path) or not os.path.exists(metadata_path):
        return "missing"
    if sha256_file(file_path) != file_sha256:
        return "tampered"
    if sha256_file(metadata_path) != metadata_sha256:
        return "tampered"
    return "verified"
