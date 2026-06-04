import os
import sqlite3
import threading
from contextlib import contextmanager


DB_LOCK = threading.Lock()
DB_PATH = os.getenv("DATABASE_PATH", os.path.join("data", "app.db"))


def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def init_db():
    ensure_parent_dir(DB_PATH)
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                stream_started_at TEXT,
                active_source_label TEXT,
                status TEXT NOT NULL DEFAULT 'detected',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evidence_artifacts (
                artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER NOT NULL,
                artifact_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                metadata_path TEXT NOT NULL,
                file_sha256 TEXT NOT NULL,
                metadata_sha256 TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                storage_uri TEXT NOT NULL,
                verify_status TEXT NOT NULL DEFAULT 'verified',
                created_at TEXT NOT NULL,
                FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
            );

            CREATE TABLE IF NOT EXISTS blockchain_anchors (
                anchor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER NOT NULL,
                anchor_mode TEXT NOT NULL,
                anchor_status TEXT NOT NULL,
                tx_hash TEXT,
                block_number INTEGER,
                chain_id TEXT,
                ledger_path TEXT,
                anchor_payload_hash TEXT NOT NULL,
                error_message TEXT,
                anchored_at TEXT NOT NULL,
                FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_status TEXT NOT NULL,
                event_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                detail_json TEXT NOT NULL,
                FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
            );
            """
        )


@contextmanager
def get_connection():
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def create_incident(source, detected_at, stream_started_at=None, active_source_label=None, created_at=None):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO incidents (source, detected_at, stream_started_at, active_source_label, status, created_at)
            VALUES (?, ?, ?, ?, 'detected', ?)
            """,
            (source, detected_at, stream_started_at, active_source_label, created_at or detected_at),
        )
        return cursor.lastrowid


def add_evidence_artifact(
    incident_id,
    artifact_type,
    file_path,
    metadata_path,
    file_sha256,
    metadata_sha256,
    file_size,
    mime_type,
    storage_uri,
    verify_status,
    created_at,
):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO evidence_artifacts (
                incident_id, artifact_type, file_path, metadata_path, file_sha256,
                metadata_sha256, file_size, mime_type, storage_uri, verify_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id,
                artifact_type,
                file_path,
                metadata_path,
                file_sha256,
                metadata_sha256,
                file_size,
                mime_type,
                storage_uri,
                verify_status,
                created_at,
            ),
        )


def update_evidence_verify_status(incident_id, verify_status):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE evidence_artifacts
            SET verify_status = ?
            WHERE artifact_id = (
                SELECT artifact_id FROM evidence_artifacts
                WHERE incident_id = ?
                ORDER BY artifact_id DESC
                LIMIT 1
            )
            """,
            (verify_status, incident_id),
        )


def add_anchor_record(
    incident_id,
    anchor_mode,
    anchor_status,
    tx_hash,
    block_number,
    chain_id,
    ledger_path,
    anchor_payload_hash,
    error_message,
    anchored_at,
):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO blockchain_anchors (
                incident_id, anchor_mode, anchor_status, tx_hash, block_number, chain_id,
                ledger_path, anchor_payload_hash, error_message, anchored_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id,
                anchor_mode,
                anchor_status,
                tx_hash,
                block_number,
                chain_id,
                ledger_path,
                anchor_payload_hash,
                error_message,
                anchored_at,
            ),
        )


def add_audit_event(incident_id, event_type, event_status, event_at, actor, detail_json):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_events (incident_id, event_type, event_status, event_at, actor, detail_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (incident_id, event_type, event_status, event_at, actor, detail_json),
        )


def list_recent_incidents(limit=10):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                i.incident_id,
                i.source,
                i.detected_at,
                i.stream_started_at,
                i.active_source_label,
                e.artifact_type,
                e.file_path,
                e.metadata_path,
                e.file_sha256,
                e.metadata_sha256,
                e.storage_uri,
                e.verify_status,
                a.anchor_mode,
                a.anchor_status,
                a.tx_hash,
                a.block_number,
                a.chain_id,
                a.ledger_path,
                a.anchor_payload_hash,
                a.error_message,
                a.anchored_at
            FROM incidents i
            LEFT JOIN evidence_artifacts e
                ON e.artifact_id = (
                    SELECT artifact_id FROM evidence_artifacts
                    WHERE incident_id = i.incident_id
                    ORDER BY artifact_id DESC
                    LIMIT 1
                )
            LEFT JOIN blockchain_anchors a
                ON a.anchor_id = (
                    SELECT anchor_id FROM blockchain_anchors
                    WHERE incident_id = i.incident_id
                    ORDER BY anchor_id DESC
                    LIMIT 1
                )
            ORDER BY i.incident_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_incident_detail(incident_id):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                i.incident_id,
                i.source,
                i.detected_at,
                i.stream_started_at,
                i.active_source_label,
                i.status,
                e.artifact_type,
                e.file_path,
                e.metadata_path,
                e.file_sha256,
                e.metadata_sha256,
                e.file_size,
                e.mime_type,
                e.storage_uri,
                e.verify_status,
                a.anchor_mode,
                a.anchor_status,
                a.tx_hash,
                a.block_number,
                a.chain_id,
                a.ledger_path,
                a.anchor_payload_hash,
                a.error_message,
                a.anchored_at
            FROM incidents i
            LEFT JOIN evidence_artifacts e
                ON e.artifact_id = (
                    SELECT artifact_id FROM evidence_artifacts
                    WHERE incident_id = i.incident_id
                    ORDER BY artifact_id DESC
                    LIMIT 1
                )
            LEFT JOIN blockchain_anchors a
                ON a.anchor_id = (
                    SELECT anchor_id FROM blockchain_anchors
                    WHERE incident_id = i.incident_id
                    ORDER BY anchor_id DESC
                    LIMIT 1
                )
            WHERE i.incident_id = ?
            """,
            (incident_id,),
        ).fetchone()
        return dict(row) if row else None


def list_audit_events(incident_id):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT audit_id, incident_id, event_type, event_status, event_at, actor, detail_json
            FROM audit_events
            WHERE incident_id = ?
            ORDER BY audit_id ASC
            """,
            (incident_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def summarize_anchors():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT anchor_status, COUNT(*) AS total
            FROM blockchain_anchors
            GROUP BY anchor_status
            """
        ).fetchall()
        return {row["anchor_status"]: row["total"] for row in rows}


def count_incidents():
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM incidents").fetchone()
        return int(row["total"]) if row else 0
