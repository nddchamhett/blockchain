import os
import tempfile
import unittest
from datetime import datetime, timezone
import io

import numpy as np

import anchor_service
import evidence_service
import persistence
import json
import main


class BlockchainPipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "app.db")
        self.ledger_path = os.path.join(self.temp_dir.name, "anchor-ledger.jsonl")
        self.evidence_root = os.path.join(self.temp_dir.name, "evidence")
        self.upload_root = os.path.join(self.temp_dir.name, "uploads")

        persistence.DB_PATH = self.db_path
        evidence_service.EVIDENCE_ROOT = self.evidence_root
        main.UPLOAD_ROOT = self.upload_root
        anchor_service.ANCHOR_MODE = "local-ledger"
        anchor_service.ANCHOR_LEDGER_PATH = self.ledger_path
        anchor_service.ANCHOR_CHAIN_ID = "local-demo-chain"
        anchor_service.ANCHOR_EXPLORER_TX_BASE = ""

        persistence.init_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_local_anchor_pipeline_and_verification(self):
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        incident_id = persistence.create_incident("demo-source", now, now, "Demo source", now)
        incident = {
            "id": incident_id,
            "source": "demo-source",
            "detected_at": now,
            "stream_started_at": now,
            "active_source_label": "Demo source",
        }
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        frame[:, :, 1] = 200

        package = evidence_service.create_evidence_package(incident, frame, {"mode": "test"})
        persistence.add_evidence_artifact(
            incident_id=incident_id,
            artifact_type=package["artifact_type"],
            file_path=package["file_path"],
            metadata_path=package["metadata_path"],
            file_sha256=package["file_sha256"],
            metadata_sha256=package["metadata_sha256"],
            file_size=package["file_size"],
            mime_type=package["mime_type"],
            storage_uri=package["storage_uri"],
            verify_status=package["verify_status"],
            created_at=now,
        )

        anchor = anchor_service.anchor_evidence(incident, package, now)
        persistence.add_anchor_record(
            incident_id=incident_id,
            anchor_mode=anchor["anchor_mode"],
            anchor_status=anchor["anchor_status"],
            tx_hash=anchor["tx_hash"],
            block_number=anchor["block_number"],
            chain_id=anchor["chain_id"],
            ledger_path=anchor["ledger_path"],
            anchor_payload_hash=anchor["anchor_payload_hash"],
            error_message=anchor["error_message"],
            anchored_at=anchor["anchored_at"],
        )
        persistence.add_audit_event(
            incident_id,
            "evidence_anchored",
            anchor["anchor_status"],
            now,
            "test",
            json.dumps({"tx_hash": anchor["tx_hash"]}, sort_keys=True),
        )

        detail = persistence.get_incident_detail(incident_id)
        self.assertEqual(evidence_service.verify_evidence_artifact(detail), "verified")
        self.assertEqual(anchor_service.verify_anchor_record(detail), "anchored")
        self.assertEqual(detail["anchor_status"], "anchored")
        self.assertTrue(os.path.exists(detail["file_path"]))
        self.assertTrue(os.path.exists(detail["metadata_path"]))
        persistence.update_evidence_verify_status(incident_id, "verified")
        detail = persistence.get_incident_detail(incident_id)
        self.assertEqual(detail["verify_status"], "verified")
        events = persistence.list_audit_events(incident_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "evidence_anchored")

    def test_incident_page_route_renders(self):
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        incident_id = persistence.create_incident("page-source", now, now, "Page source", now)
        client = main.app.test_client()
        response = client.get(f"/incidents/{incident_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Chain of Custody", response.get_data(as_text=True))

    def test_archive_page_route_renders(self):
        client = main.app.test_client()
        response = client.get("/archive")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Evidence Archive", response.get_data(as_text=True))

    def test_upload_route_rejects_invalid_extension(self):
        client = main.app.test_client()
        response = client.post(
            "/upload",
            data={"video_file": (io.BytesIO(b"not-a-video"), "sample.txt")},
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("Unsupported+video+format", response.headers["Location"])

    def test_upload_route_saves_video_and_starts_detection(self):
        client = main.app.test_client()
        captured = {}
        original_start_detection = main.start_detection

        def fake_start_detection(path, source_label=None):
            captured["path"] = path
            captured["source_label"] = source_label
            return True

        main.start_detection = fake_start_detection
        try:
            response = client.post(
                "/upload",
                data={"video_file": (io.BytesIO(b"fake-video"), "demo.mp4")},
                content_type="multipart/form-data",
                follow_redirects=False,
            )
        finally:
            main.start_detection = original_start_detection

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        self.assertTrue(os.path.exists(captured["path"]))
        self.assertTrue(captured["path"].endswith(".mp4"))
        self.assertTrue(captured["source_label"].endswith(".mp4"))

    def test_self_check_endpoint_renders(self):
        client = main.app.test_client()
        response = client.get("/api/self-check")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("database_exists", payload)
        self.assertIn("web3_available", payload)

    def test_evm_local_anchor_pipeline(self):
        if not os.path.exists(os.path.join("contracts", "EvidenceRegistry.bytecode.json")):
            self.skipTest("Compiled bytecode artifact is required for evm-local mode")

        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        incident_id = persistence.create_incident("evm-local-source", now, now, "EVM local source", now)
        incident = {
            "id": incident_id,
            "source": "evm-local-source",
            "detected_at": now,
            "stream_started_at": now,
            "active_source_label": "EVM local source",
        }
        frame = np.zeros((48, 48, 3), dtype=np.uint8)
        frame[:, :, 0] = 150

        package = evidence_service.create_evidence_package(incident, frame, {"mode": "evm-local-test"})
        previous_mode = anchor_service.ANCHOR_MODE
        try:
            anchor_service.ANCHOR_MODE = "evm-local"
            anchor = anchor_service.anchor_evidence(incident, package, now)
        finally:
            anchor_service.ANCHOR_MODE = previous_mode

        self.assertEqual(anchor["anchor_status"], "anchored")
        self.assertEqual(anchor["anchor_mode"], "evm-local")
        self.assertTrue(anchor["tx_hash"])


if __name__ == "__main__":
    unittest.main()
