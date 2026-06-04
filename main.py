import os
import threading
import time
from datetime import datetime, timezone
import json

import cv2
import dotenv
import imutils
import torch
from flask import Flask, Response, jsonify, redirect, render_template_string, request
from werkzeug.utils import secure_filename

dotenv.load_dotenv(override=True)

import anchor_service
import evidence_service
import persistence
import fight_module

YOLO_MODEL = os.getenv("YOLO_MODEL")
FIGHT_MODEL = os.getenv("FIGHT_MODEL")
AUTO_CAMERA_TOKEN = "auto"
UPLOAD_ROOT = os.getenv("UPLOAD_ROOT", os.path.join("data", "uploads"))
ALLOWED_UPLOAD_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

outputFrame = None
lock = threading.Lock()
app = Flask(__name__)

detect_thread_started = False
active_source = None
stream_started_at = None
latest_frame_fight = False
latest_alert_at = None
state_lock = threading.Lock()

persistence.init_db()


DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fight Detection Control Center</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0a111d;
      --panel: rgba(15, 23, 42, 0.92);
      --panel-2: rgba(19, 31, 52, 0.94);
      --line: #23314a;
      --text: #edf3fb;
      --muted: #91a2bb;
      --accent: #58d5ff;
      --accent-2: #34d399;
      --warn: #f59e0b;
      --danger: #fb7185;
      --signal: #8b5cf6;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(88, 213, 255, 0.18), transparent 30%),
        radial-gradient(circle at top right, rgba(139, 92, 246, 0.14), transparent 26%),
        linear-gradient(180deg, #09111b 0%, #0e1729 100%);
      color: var(--text);
    }
    .page {
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px 24px 40px;
    }
    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.7fr) minmax(320px, 0.9fr);
      gap: 18px;
      margin-bottom: 18px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 22px 60px rgba(0, 0, 0, 0.26);
      min-width: 0;
    }
    .panel.blockchain-shell {
      background:
        linear-gradient(180deg, rgba(13, 24, 42, 0.95), rgba(10, 18, 32, 0.95)),
        radial-gradient(circle at top right, rgba(88, 213, 255, 0.1), transparent 32%);
    }
    .headline {
      font-size: 36px;
      line-height: 1.1;
      margin: 0 0 10px;
    }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid rgba(88, 213, 255, 0.18);
      border-radius: 999px;
      padding: 8px 12px;
      background: rgba(8, 47, 73, 0.26);
      color: #bfefff;
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .subtitle, .label, .muted { color: var(--muted); }
    .hero-metrics, .grid-3 {
      display: grid;
      gap: 12px;
    }
    .hero-metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); margin-top: 20px; }
    .metric, .mini-card {
      background: var(--panel-2);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      min-height: 94px;
    }
    .metric-value {
      display: block;
      font-size: 24px;
      font-weight: 700;
      margin-top: 8px;
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(300px, 0.92fr) minmax(0, 1.4fr) minmax(360px, 1fr);
      gap: 18px;
    }
    .stack { display: grid; gap: 16px; }
    .panel-title {
      margin: 0 0 14px;
      font-size: 20px;
    }
    .panel-subtitle {
      margin: -6px 0 14px;
      color: var(--muted);
      font-size: 14px;
    }
    .control-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 12px;
    }
    .field-span {
      grid-column: 1 / -1;
    }
    .field {
      display: grid;
      gap: 8px;
    }
    .field-card {
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(8, 15, 29, 0.7);
      padding: 14px;
      margin-bottom: 12px;
    }
    .camera-hint {
      margin-top: 10px;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid rgba(56, 189, 248, 0.24);
      background: rgba(8, 47, 73, 0.32);
      font-size: 13px;
      color: #b9e6fb;
    }
    input, select, button {
      width: 100%;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: #0f172a;
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
    }
    button {
      cursor: pointer;
      background: linear-gradient(180deg, #2563eb, #1d4ed8);
      border-color: #3153c9;
      font-weight: 600;
    }
    button.secondary {
      background: linear-gradient(180deg, #1a2840, #162033);
    }
    a.button-link {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: #0f172a;
      color: var(--text);
      padding: 10px 12px;
      text-decoration: none;
      font: inherit;
      font-weight: 600;
    }
    .preview {
      width: 100%;
      aspect-ratio: 16 / 9;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, #09111d, #0f172a);
      object-fit: contain;
      display: block;
    }
    .preview-shell {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 12px;
      background: rgba(6, 12, 22, 0.7);
    }
    .preview-meta {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }
    .status-row, .chain-grid {
      display: grid;
      gap: 12px;
    }
    .status-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .chain-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .status-stack {
      display: grid;
      gap: 12px;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 13px;
      font-weight: 600;
      border: 1px solid var(--line);
      background: #101927;
    }
    .chip-dot {
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--muted);
    }
    .chip.live .chip-dot { background: var(--accent-2); }
    .chip.alert .chip-dot { background: var(--danger); }
    .chip.idle .chip-dot { background: var(--warn); }
    .status-strip {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-top: 12px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(8, 15, 29, 0.72);
    }
    .status-strip strong {
      display: block;
      margin-bottom: 4px;
    }
    .blockchain-summary {
      display: grid;
      gap: 12px;
      margin-bottom: 14px;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .blockchain-note {
      margin: 0;
      padding: 14px;
      border: 1px solid rgba(88, 213, 255, 0.2);
      border-radius: 16px;
      background: rgba(7, 22, 37, 0.5);
      color: #c8e8ff;
      font-size: 14px;
      line-height: 1.5;
    }
    .proof-spotlight {
      border: 1px solid rgba(88, 213, 255, 0.2);
      border-radius: 16px;
      padding: 14px;
      background: rgba(7, 18, 31, 0.76);
    }
    .proof-spotlight-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
      align-items: center;
    }
    .spotlight-title {
      font-size: 15px;
      font-weight: 700;
      color: #cbefff;
    }
    .spotlight-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .incident-list {
      display: grid;
      gap: 10px;
      max-height: 780px;
      overflow: auto;
      padding-right: 4px;
    }
    .incident {
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(11, 18, 31, 0.98), rgba(9, 15, 27, 0.96));
      border-radius: 18px;
      padding: 14px;
    }
    .incident-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
      font-size: 14px;
    }
    .incident-head strong {
      font-size: 15px;
    }
    .incident-grid {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 12px;
      margin-bottom: 12px;
    }
    .detail-grid {
      display: grid;
      gap: 10px;
    }
    .detail-card {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(14, 21, 36, 0.88);
      padding: 12px;
    }
    .detail-card .label {
      display: block;
      margin-bottom: 6px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .detail-card .value {
      font-size: 14px;
      word-break: break-word;
    }
    .evidence-block {
      display: grid;
      gap: 10px;
    }
    .chain-log {
      border: 1px solid rgba(88, 213, 255, 0.18);
      border-radius: 16px;
      padding: 12px;
      background: linear-gradient(180deg, rgba(7, 24, 36, 0.82), rgba(8, 16, 28, 0.92));
    }
    .chain-log-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }
    .chain-log-title {
      font-size: 15px;
      font-weight: 700;
      color: #bfefff;
    }
    .state-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 11px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 12px;
      font-weight: 700;
      background: rgba(14, 24, 39, 0.85);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }
    .state-pill.good { color: #9ef0c8; border-color: rgba(52, 211, 153, 0.35); }
    .state-pill.warn { color: #ffd38a; border-color: rgba(245, 158, 11, 0.35); }
    .state-pill.bad { color: #ffb0bf; border-color: rgba(251, 113, 133, 0.35); }
    .chain-steps {
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }
    .chain-step {
      display: grid;
      grid-template-columns: 18px 1fr;
      gap: 10px;
      align-items: start;
      color: #d6e7f7;
      font-size: 13px;
    }
    .step-dot {
      width: 12px;
      height: 12px;
      margin-top: 3px;
      border-radius: 999px;
      background: var(--accent);
      box-shadow: 0 0 0 4px rgba(88, 213, 255, 0.12);
    }
    .hash {
      font-family: Consolas, monospace;
      font-size: 12px;
      color: #9bdaf4;
      word-break: break-all;
    }
    .muted-path {
      color: #adc0d9;
      font-size: 12px;
      word-break: break-word;
    }
    .helper {
      margin-top: 8px;
      font-size: 13px;
      color: var(--muted);
    }
    .section-kicker {
      display: block;
      margin-bottom: 8px;
      color: #bfefff;
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .banner {
      margin-bottom: 16px;
      padding: 12px 14px;
      border: 1px solid rgba(249, 115, 22, 0.35);
      background: rgba(249, 115, 22, 0.12);
      border-radius: 8px;
      color: #fdba74;
    }
    @media (max-width: 980px) {
      .hero, .layout { grid-template-columns: 1fr; }
      .hero-metrics, .status-row, .chain-grid, .control-grid, .preview-meta, .incident-grid, .summary-grid, .spotlight-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="page">
    {% if error %}
      <div class="banner">{{ error }}</div>
    {% endif %}

    <section class="hero">
      <div class="panel">
        <div class="eyebrow">Surveillance Operations</div>
        <h1 class="headline">Fight Detection Control Center</h1>
        <p class="subtitle">Theo doi camera, quan sat detector va doc duoc toan bo chuoi bang chung blockchain trong mot dashboard de demo de tai ro rang hon.</p>
        <div class="hero-metrics">
          <div class="metric">
            <span class="label">Detection status</span>
            <span class="metric-value" id="hero-status">Idle</span>
          </div>
          <div class="metric">
            <span class="label">Active source</span>
            <span class="metric-value" id="hero-source">Not started</span>
          </div>
          <div class="metric">
            <span class="label">Incident records</span>
            <span class="metric-value" id="hero-incidents">0</span>
          </div>
        </div>
      </div>

      <div class="panel">
        <h2 class="panel-title">Runtime Configuration</h2>
        <p class="panel-subtitle">Thong so detector duoc hien rieng, phan evidence va blockchain nam o cac khoi ben duoi de de theo doi.</p>
        <div class="grid-3">
          <div class="mini-card">
            <div class="label">Fight threshold</div>
            <div class="metric-value">{{ threshold }}</div>
          </div>
          <div class="mini-card">
            <div class="label">Conclusion decay</div>
            <div class="metric-value">{{ conclusion_threshold }}</div>
          </div>
          <div class="mini-card">
            <div class="label">Alert hold frames</div>
            <div class="metric-value">{{ final_threshold }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="layout">
      <div class="stack">
        <div class="panel">
          <h2 class="panel-title">Stream Control</h2>
          <p class="panel-subtitle">Chon dung nguon video de tranh chay trung detector. Moi incident moi se duoc package thanh evidence va anchor blockchain.</p>

          <div class="field-card">
            <form class="control-grid" action="/start" method="get">
              <div class="field field-span">
                <label class="label" for="video_input">RTSP or video URL</label>
                <input id="video_input" name="video_input" placeholder="rtsp://camera.local/live or https://example.com/video.mp4" required>
              </div>
              <button type="submit" class="field-span">Start remote stream</button>
            </form>
          </div>

          <div class="field-card">
            <form class="control-grid" action="/webcam" method="get">
              <div class="field">
                <label class="label" for="camera">Webcam source</label>
                <input id="camera" name="camera" value="{{ default_camera_input }}" placeholder="auto or 0">
              </div>
              <div class="field" style="align-self: end;">
                <button type="submit" class="secondary">Start webcam</button>
              </div>
              <div class="camera-hint field-span">
                Default webcam: <strong>{{ default_camera_label }}</strong>. Use <code>auto</code> to open it, or enter another camera index manually.
              </div>
            </form>
          </div>

          <div class="field-card">
            <form class="control-grid" action="/upload" method="post" enctype="multipart/form-data">
              <div class="field field-span">
                <label class="label" for="video_file">Upload local video</label>
                <input id="video_file" name="video_file" type="file" accept=".mp4,.avi,.mov,.mkv,.webm" required>
              </div>
              <button type="submit" class="field-span secondary">Upload and run detection</button>
            </form>
          </div>

          <a class="button-link" href="/archive">Open evidence archive</a>

          <p class="helper">The detector currently runs one active source at a time to avoid overlapping inference threads.</p>
        </div>

        <div class="panel">
          <h2 class="panel-title">System Status</h2>
          <p class="panel-subtitle">Trang thai detector va canh bao hien tai duoc tach rieng de nhin nhanh hon trong luc demo.</p>
          <div class="status-row">
            <div class="mini-card">
              <div class="label">Inference engine</div>
              <div class="metric-value" id="stream-state">Stopped</div>
            </div>
            <div class="mini-card">
              <div class="label">GPU</div>
              <div class="metric-value">{{ gpu_label }}</div>
            </div>
          </div>
          <div class="status-strip">
            <div>
              <strong>Current alert state</strong>
              <div class="muted" id="last-alert-copy">No fight incident has been recorded yet.</div>
            </div>
            <span class="chip idle" id="alert-chip"><span class="chip-dot"></span><span id="alert-chip-text">No active alert</span></span>
          </div>
        </div>
      </div>

      <div class="stack">
        <div class="panel">
          <h2 class="panel-title">Live Preview</h2>
          <p class="panel-subtitle">Khung preview chay song song voi thong tin source, runtime va tong so incident vua ghi.</p>
          <div class="preview-shell">
            <img class="preview" src="/raw" alt="Live fight detection stream">
          </div>
          <div class="preview-meta">
            <div class="mini-card">
              <div class="label">Source label</div>
              <div class="metric-value" id="preview-source">Not started</div>
            </div>
            <div class="mini-card">
              <div class="label">Stream started</div>
              <div class="metric-value" id="preview-started">-</div>
            </div>
            <div class="mini-card">
              <div class="label">Incidents stored</div>
              <div class="metric-value" id="preview-incidents">0</div>
            </div>
          </div>
        </div>
      </div>

      <div class="stack">
        <div class="panel blockchain-shell">
          <span class="section-kicker">Evidence integrity</span>
          <h2 class="panel-title">Blockchain Log</h2>
          <p class="panel-subtitle">Moi record duoi day cho thay bang chung da duoc dong goi, hash, anchor va verify nhu the nao. Day la phan can xem ro nhat khi bao ve de tai.</p>
          <div class="blockchain-summary">
            <div class="chain-grid">
              <div class="mini-card">
                <div class="label">Anchoring mode</div>
                <div class="metric-value" id="anchor-mode">{{ anchor_mode }}</div>
              </div>
              <div class="mini-card">
                <div class="label">Ledger state</div>
                <div class="metric-value" id="ledger-state">Ready</div>
              </div>
            </div>
            <div class="summary-grid">
              <div class="mini-card">
                <div class="label">Anchored incidents</div>
                <div class="metric-value" id="summary-anchored">0</div>
              </div>
              <div class="mini-card">
                <div class="label">Evidence verified</div>
                <div class="metric-value" id="summary-verified">0</div>
              </div>
              <div class="mini-card">
                <div class="label">Pending or review</div>
                <div class="metric-value" id="summary-pending">0</div>
              </div>
            </div>
            <p class="blockchain-note">
              Blockchain log hien ro 4 buoc: tao incident, tao evidence package, anchor hash len chain, va verify lai toan ven cua evidence.
            </p>
            <div class="proof-spotlight" id="proof-spotlight">
              <div class="proof-spotlight-head">
                <div class="spotlight-title">Latest proof snapshot</div>
                <span class="state-pill warn" id="spotlight-pill">Waiting</span>
              </div>
              <div class="spotlight-grid">
                <div class="detail-card">
                  <span class="label">Incident</span>
                  <div class="value" id="spotlight-incident">No incident yet</div>
                </div>
                <div class="detail-card">
                  <span class="label">Anchor reference</span>
                  <div class="hash" id="spotlight-reference">-</div>
                </div>
                <div class="detail-card">
                  <span class="label">Integrity status</span>
                  <div class="value" id="spotlight-status">Waiting for evidence</div>
                </div>
                <div class="detail-card">
                  <span class="label">Open detail</span>
                  <div class="value" id="spotlight-link">Detail page will appear here</div>
                </div>
              </div>
            </div>
          </div>
          <div class="incident-list" id="incident-list">
            <div class="incident muted">No incidents recorded.</div>
          </div>
        </div>
      </div>
    </section>
  </div>

  <script>
    async function refreshStatus() {
      try {
        const response = await fetch("/api/status", { cache: "no-store" });
        if (!response.ok) {
          throw new Error("status " + response.status);
        }

        const data = await response.json();

        const statusLabel = data.stream_active ? (data.latest_frame_fight ? "Alert" : "Monitoring") : "Idle";
        document.getElementById("hero-status").textContent = statusLabel;
        document.getElementById("hero-source").textContent = data.active_source || "Not started";
        document.getElementById("hero-incidents").textContent = String(data.total_incidents);
        document.getElementById("stream-state").textContent = data.stream_active ? "Running" : "Stopped";
        document.getElementById("preview-source").textContent = data.active_source || "Not started";
        document.getElementById("preview-started").textContent = data.stream_started_at || "-";
        document.getElementById("preview-incidents").textContent = String(data.total_incidents);
        document.getElementById("anchor-mode").textContent = data.anchor_mode;
        const anchoredCount = data.anchor_summary.anchored || 0;
        const pendingCount = data.anchor_summary.pending_external_chain || 0;
        const verifiedCount = data.incidents.filter((incident) => (incident.verify_status || "").toLowerCase() === "verified").length;
        const pendingReviewCount = data.incidents.filter((incident) => {
          const anchorStatus = (incident.anchor_status || "").toLowerCase();
          const verifyStatus = (incident.verify_status || "").toLowerCase();
          return anchorStatus !== "anchored" || verifyStatus !== "verified";
        }).length;
        const ledgerState = anchoredCount ? "Anchored" : pendingCount ? "Pending external chain" : data.incidents.length ? "Evidence captured" : "Ready";
        document.getElementById("ledger-state").textContent = ledgerState;
        document.getElementById("summary-anchored").textContent = String(anchoredCount);
        document.getElementById("summary-verified").textContent = String(verifiedCount);
        document.getElementById("summary-pending").textContent = String(pendingReviewCount);

        const chip = document.getElementById("alert-chip");
        const chipText = document.getElementById("alert-chip-text");
        chip.className = "chip " + (data.latest_frame_fight ? "alert" : data.stream_active ? "live" : "idle");
        chipText.textContent = data.latest_frame_fight ? "Fight alert active" : data.stream_active ? "Monitoring live frames" : "No active alert";

        const lastAlertCopy = document.getElementById("last-alert-copy");
        if (data.latest_alert_at) {
          lastAlertCopy.textContent = "Last incident: " + data.latest_alert_at + " UTC";
        } else if (data.stream_started_at) {
          lastAlertCopy.textContent = "Stream started: " + data.stream_started_at + " UTC";
        } else {
          lastAlertCopy.textContent = "No fight incident has been recorded yet.";
        }

        const list = document.getElementById("incident-list");
        if (!data.incidents.length) {
          document.getElementById("spotlight-incident").textContent = "No incident yet";
          document.getElementById("spotlight-reference").textContent = "-";
          document.getElementById("spotlight-status").textContent = "Waiting for evidence";
          document.getElementById("spotlight-link").textContent = "Detail page will appear here";
          document.getElementById("spotlight-pill").className = "state-pill warn";
          document.getElementById("spotlight-pill").textContent = "Waiting";
          list.innerHTML = '<div class="incident muted">No incidents recorded.</div>';
          return;
        }

        function stateClass(value) {
          const normalized = (value || "").toLowerCase();
          if (normalized === "anchored" || normalized === "verified" || normalized === "ok") {
            return "good";
          }
          if (normalized.includes("pending") || normalized === "unknown" || normalized === "ready") {
            return "warn";
          }
          return "bad";
        }

        const latestIncident = data.incidents[0];
        document.getElementById("spotlight-incident").textContent = `#${latestIncident.id} from ${latestIncident.source || "unknown source"}`;
        document.getElementById("spotlight-reference").textContent = latestIncident.tx_hash || latestIncident.ledger_path || "-";
        document.getElementById("spotlight-status").textContent = `${latestIncident.anchor_status || "unknown"} / ${latestIncident.verify_status || "unknown"} / ${latestIncident.anchor_verify_status || "unknown"}`;
        document.getElementById("spotlight-link").innerHTML = `<a href="/incidents/${latestIncident.id}">Open chain of custody for incident #${latestIncident.id}</a>`;
        document.getElementById("spotlight-pill").className = `state-pill ${stateClass(latestIncident.anchor_status)}`;
        document.getElementById("spotlight-pill").textContent = latestIncident.anchor_status || "unknown";

        list.innerHTML = data.incidents.map((incident) => `
          <article class="incident">
            <div class="incident-head">
              <strong>Incident #${incident.id}</strong>
              <span class="muted">${incident.detected_at}</span>
            </div>
            <div class="incident-grid">
              <div class="evidence-block">
                <div class="detail-card">
                  <span class="label">Source</span>
                  <div class="value">${incident.source || "Unknown source"}</div>
                </div>
                <div class="detail-card">
                  <span class="label">Evidence file</span>
                  <div class="muted-path">${incident.file_path || "Not available"}</div>
                </div>
                <div class="detail-card">
                  <span class="label">Evidence hash</span>
                  <div class="hash">${incident.evidence_hash || "Not available"}</div>
                </div>
                <div class="detail-card">
                  <span class="label">Metadata hash</span>
                  <div class="hash">${incident.metadata_hash || "Not available"}</div>
                </div>
              </div>
              <div class="chain-log">
                <div class="chain-log-header">
                  <div class="chain-log-title">Immutable Record</div>
                  <span class="state-pill ${stateClass(incident.anchor_status)}">${incident.anchor_status || "Not anchored"}</span>
                </div>
                <div class="detail-grid">
                  <div class="detail-card">
                    <span class="label">Verify status</span>
                    <div class="value">${incident.verify_status || "Unknown"}</div>
                  </div>
                  <div class="detail-card">
                    <span class="label">Anchor verify</span>
                    <div class="value">${incident.anchor_verify_status || "Unknown"}</div>
                  </div>
                  <div class="detail-card">
                    <span class="label">Transaction hash</span>
                    <div class="hash">${incident.tx_hash || "Not available"}</div>
                  </div>
                  <div class="detail-card">
                    <span class="label">Ledger / explorer</span>
                    <div class="muted-path">${incident.tx_url || incident.ledger_path || "No explorer or ledger path available"}</div>
                  </div>
                </div>
                <div class="chain-steps">
                  <div class="chain-step"><span class="step-dot"></span><span>Incident captured at <strong>${incident.detected_at}</strong></span></div>
                  <div class="chain-step"><span class="step-dot"></span><span>Evidence package saved with file and metadata hashes.</span></div>
                  <div class="chain-step"><span class="step-dot"></span><span>Anchor mode <strong>${incident.anchor_mode || data.anchor_mode}</strong> wrote transaction or ledger proof.</span></div>
                  <div class="chain-step"><span class="step-dot"></span><span>Verification result: <strong>${incident.verify_status || "unknown"}</strong> / anchor check <strong>${incident.anchor_verify_status || "unknown"}</strong>.</span></div>
                </div>
              </div>
            </div>
            <div style="margin-top: 12px;">
              <a class="button-link" href="/incidents/${incident.id}">Open chain of custody</a>
            </div>
          </article>
        `).join("");
      } catch (error) {
        document.getElementById("hero-status").textContent = "Unavailable";
        document.getElementById("stream-state").textContent = "Unavailable";
        document.getElementById("preview-source").textContent = "Unavailable";
        document.getElementById("preview-started").textContent = "Unavailable";
        document.getElementById("ledger-state").textContent = "Retrying";
        document.getElementById("summary-anchored").textContent = "-";
        document.getElementById("summary-verified").textContent = "-";
        document.getElementById("summary-pending").textContent = "-";
        document.getElementById("alert-chip").className = "chip idle";
        document.getElementById("alert-chip-text").textContent = "Status reconnecting";
        document.getElementById("last-alert-copy").textContent = "Dashboard status refresh failed. Retrying automatically.";
        document.getElementById("spotlight-incident").textContent = "Status unavailable";
        document.getElementById("spotlight-reference").textContent = "-";
        document.getElementById("spotlight-status").textContent = "Retrying blockchain summary";
        document.getElementById("spotlight-link").textContent = "Unable to load detail link";
        document.getElementById("spotlight-pill").className = "state-pill warn";
        document.getElementById("spotlight-pill").textContent = "Retrying";
      }
    }

    refreshStatus();
    setInterval(refreshStatus, 3000);
  </script>
</body>
</html>
"""


INCIDENT_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Incident {{ incident_id }} Chain of Custody</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #09111d;
      --panel: #111a2c;
      --line: #24324a;
      --text: #e5ecf5;
      --muted: #8fa0ba;
      --accent: #38bdf8;
      --good: #34d399;
      --warn: #f59e0b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.12), transparent 28%),
        linear-gradient(180deg, #09111d 0%, #0f172a 100%);
      color: var(--text);
    }
    .page {
      max-width: 1100px;
      margin: 0 auto;
      padding: 24px;
    }
    .topbar, .grid {
      display: grid;
      gap: 18px;
    }
    .topbar {
      grid-template-columns: 1.3fr 0.7fr;
      margin-bottom: 16px;
    }
    .grid {
      grid-template-columns: 1fr 1fr;
    }
    .panel {
      background: rgba(17, 26, 44, 0.95);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 20px;
      min-width: 0;
    }
    .headline {
      margin: 0 0 8px;
      font-size: 28px;
    }
    .muted, .label {
      color: var(--muted);
    }
    .label {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .value {
      margin-top: 6px;
      font-size: 16px;
      word-break: break-word;
    }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .metric {
      border: 1px solid var(--line);
      background: rgba(9, 17, 29, 0.9);
      border-radius: 14px;
      padding: 12px;
    }
    .status-banner {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      margin-top: 14px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(9, 17, 29, 0.9);
    }
    .state-pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      border: 1px solid var(--line);
    }
    .state-pill.good {
      color: #9ef0c8;
      border-color: rgba(52, 211, 153, 0.35);
    }
    .state-pill.warn {
      color: #ffd38a;
      border-color: rgba(245, 158, 11, 0.35);
    }
    .timeline {
      display: grid;
      gap: 12px;
    }
    .event {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: rgba(9, 17, 29, 0.9);
    }
    .event-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 8px;
    }
    .hash, pre {
      font-family: Consolas, monospace;
      font-size: 12px;
      color: #9bdaf4;
      white-space: pre-wrap;
      word-break: break-word;
    }
    a {
      color: var(--accent);
    }
    .actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 12px;
    }
    .action {
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      text-decoration: none;
      color: var(--text);
      background: rgba(9, 17, 29, 0.9);
    }
    .anchor-log {
      border: 1px solid rgba(56, 189, 248, 0.22);
      border-radius: 16px;
      padding: 14px;
      background: linear-gradient(180deg, rgba(7, 22, 37, 0.72), rgba(8, 16, 28, 0.92));
      margin-top: 14px;
    }
    .anchor-log h3 {
      margin: 0 0 10px;
      font-size: 16px;
    }
    .anchor-steps {
      display: grid;
      gap: 8px;
    }
    .anchor-step {
      display: grid;
      grid-template-columns: 18px 1fr;
      gap: 10px;
      align-items: start;
      font-size: 13px;
      color: #d6e7f7;
    }
    .dot {
      width: 12px;
      height: 12px;
      margin-top: 3px;
      border-radius: 999px;
      background: var(--accent);
      box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.14);
    }
    @media (max-width: 900px) {
      .topbar, .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="page">
    <section class="topbar">
      <div class="panel">
        <p class="label">Incident</p>
        <h1 class="headline">Chain of Custody #{{ incident_id }}</h1>
        <div class="muted">This page loads the exported evidence package, anchor result, and audit trail for a single incident.</div>
        <div class="actions">
          <a class="action" href="/">Back to dashboard</a>
          <a class="action" href="/api/incidents/{{ incident_id }}/export">Open export JSON</a>
          <a class="action" href="/api/incidents/{{ incident_id }}/verify">Run verify API</a>
        </div>
      </div>
      <div class="panel">
        <div class="label">Status summary</div>
        <div id="status-summary" class="value">Loading...</div>
        <div class="status-banner">
          <div>
            <div class="label">Integrity overview</div>
            <div class="muted">Tach rieng trang thai evidence va trang thai anchor de nguoi xem thay ro bang chung da duoc khoa nhu the nao.</div>
          </div>
          <div id="status-pill" class="state-pill warn">Loading</div>
        </div>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2 style="margin-top: 0;">Evidence Package</h2>
        <div class="metric-grid">
          <div class="metric">
            <div class="label">Source</div>
            <div class="value" id="source-value">-</div>
          </div>
          <div class="metric">
            <div class="label">Detected at</div>
            <div class="value" id="detected-at">-</div>
          </div>
          <div class="metric">
            <div class="label">File path</div>
            <div class="value" id="file-path">-</div>
          </div>
          <div class="metric">
            <div class="label">Metadata path</div>
            <div class="value" id="metadata-path">-</div>
          </div>
          <div class="metric">
            <div class="label">Evidence hash</div>
            <div class="hash" id="file-hash">-</div>
          </div>
          <div class="metric">
            <div class="label">Metadata hash</div>
            <div class="hash" id="metadata-hash">-</div>
          </div>
        </div>
      </div>

      <div class="panel">
        <h2 style="margin-top: 0;">Anchor Record</h2>
        <div class="metric-grid">
          <div class="metric">
            <div class="label">Anchor mode</div>
            <div class="value" id="anchor-mode-value">-</div>
          </div>
          <div class="metric">
            <div class="label">Anchor status</div>
            <div class="value" id="anchor-status-value">-</div>
          </div>
          <div class="metric">
            <div class="label">Anchor verify</div>
            <div class="value" id="anchor-verify-value">-</div>
          </div>
          <div class="metric">
            <div class="label">Verify status</div>
            <div class="value" id="verify-status-value">-</div>
          </div>
          <div class="metric">
            <div class="label">Transaction hash</div>
            <div class="hash" id="tx-hash">-</div>
          </div>
          <div class="metric">
            <div class="label">Ledger / explorer</div>
            <div class="value" id="tx-link">-</div>
          </div>
        </div>
        <div class="anchor-log">
          <h3>Blockchain Proof Log</h3>
          <div class="anchor-steps" id="anchor-steps">
            <div class="anchor-step"><span class="dot"></span><span>Loading anchor trail...</span></div>
          </div>
        </div>
      </div>
    </section>

    <section class="panel" style="margin-top: 16px;">
      <h2 style="margin-top: 0;">Audit Timeline</h2>
      <div id="audit-timeline" class="timeline">
        <div class="event">Loading audit events...</div>
      </div>
    </section>
  </div>

  <script>
    const incidentId = {{ incident_id }};

    function setText(id, value) {
      document.getElementById(id).textContent = value || "-";
    }

    function stateClass(value) {
      const normalized = (value || "").toLowerCase();
      if (normalized === "anchored" || normalized === "verified" || normalized === "ok") {
        return "good";
      }
      return "warn";
    }

    async function loadIncidentPage() {
      const response = await fetch(`/api/incidents/${incidentId}/export`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error("Failed to load export " + response.status);
      }
      const payload = await response.json();
      const incident = payload.incident;

      setText("status-summary", `${incident.anchor_status || "unknown"} / ${incident.verify_status || "unknown"}`);
      const statusPill = document.getElementById("status-pill");
      statusPill.className = `state-pill ${stateClass(incident.anchor_status)}`
      statusPill.textContent = `${incident.anchor_status || "unknown"} | ${incident.verify_status || "unknown"}`;
      setText("source-value", incident.source);
      setText("detected-at", incident.detected_at);
      setText("file-path", incident.file_path);
      setText("metadata-path", incident.metadata_path);
      setText("file-hash", incident.evidence_hash);
      setText("metadata-hash", incident.metadata_hash);
      setText("anchor-mode-value", incident.anchor_mode);
      setText("anchor-status-value", incident.anchor_status);
      setText("anchor-verify-value", incident.anchor_verify_status);
      setText("verify-status-value", incident.verify_status);
      setText("tx-hash", incident.tx_hash);

      const txLink = document.getElementById("tx-link");
      const linkValue = incident.tx_url || incident.ledger_path || "-";
      txLink.innerHTML = incident.tx_url ? `<a href="${incident.tx_url}" target="_blank" rel="noreferrer">${incident.tx_url}</a>` : linkValue;

      document.getElementById("anchor-steps").innerHTML = `
        <div class="anchor-step"><span class="dot"></span><span>Evidence image and metadata JSON were persisted for incident <strong>#${incident.id}</strong>.</span></div>
        <div class="anchor-step"><span class="dot"></span><span>Evidence hash <strong>${incident.evidence_hash || "-"}</strong> was prepared for anchoring.</span></div>
        <div class="anchor-step"><span class="dot"></span><span>Anchor mode <strong>${incident.anchor_mode || "-"}</strong> produced transaction or ledger proof <strong>${incident.tx_hash || incident.ledger_path || "-"}</strong>.</span></div>
        <div class="anchor-step"><span class="dot"></span><span>Latest integrity result is <strong>${incident.verify_status || "unknown"}</strong> and anchor verification is <strong>${incident.anchor_verify_status || "unknown"}</strong>.</span></div>
      `;

      const timeline = document.getElementById("audit-timeline");
      if (!payload.audit_events.length) {
        timeline.innerHTML = '<div class="event">No audit events available.</div>';
        return;
      }

      timeline.innerHTML = payload.audit_events.map((event) => `
        <article class="event">
          <div class="event-head">
            <strong>${event.event_type}</strong>
            <span class="muted">${event.event_at}</span>
          </div>
          <div class="label">Status</div>
          <div class="value">${event.event_status}</div>
          <div class="label" style="margin-top: 8px;">Actor</div>
          <div class="value">${event.actor}</div>
          <div class="label" style="margin-top: 8px;">Detail</div>
          <pre>${JSON.stringify(event.detail, null, 2)}</pre>
        </article>
      `).join("");
    }

    loadIncidentPage().catch((error) => {
      document.getElementById("status-summary").textContent = "Unable to load incident";
      document.getElementById("audit-timeline").innerHTML = `<div class="event">${error.message}</div>`;
    });
  </script>
</body>
</html>
"""


ARCHIVE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Evidence Archive</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #09111d;
      --panel: #111a2c;
      --line: #24324a;
      --text: #e5ecf5;
      --muted: #8fa0ba;
      --accent: #38bdf8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.12), transparent 28%),
        linear-gradient(180deg, #09111d 0%, #0f172a 100%);
      color: var(--text);
    }
    .page {
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }
    .panel {
      background: rgba(17, 26, 44, 0.95);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 20px;
      margin-bottom: 16px;
    }
    .headline {
      margin: 0 0 8px;
      font-size: 30px;
    }
    .muted, .label {
      color: var(--muted);
    }
    .label {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .archive {
      display: grid;
      gap: 12px;
    }
    .archive-summary {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 14px;
    }
    .summary-card {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: rgba(9, 17, 29, 0.9);
    }
    .incident {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      background: rgba(9, 17, 29, 0.9);
    }
    .incident-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px 16px;
    }
    .chain-box {
      margin-top: 14px;
      border: 1px solid rgba(56, 189, 248, 0.2);
      border-radius: 16px;
      padding: 14px;
      background: linear-gradient(180deg, rgba(7, 22, 37, 0.66), rgba(8, 16, 28, 0.92));
    }
    .chain-box-title {
      margin: 0 0 10px;
      font-size: 15px;
      color: #bfefff;
    }
    .state-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 10px;
    }
    .state-pill {
      display: inline-flex;
      align-items: center;
      padding: 7px 11px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }
    .state-pill.good {
      color: #9ef0c8;
      border-color: rgba(52, 211, 153, 0.35);
    }
    .state-pill.warn {
      color: #ffd38a;
      border-color: rgba(245, 158, 11, 0.35);
    }
    .hash {
      font-family: Consolas, monospace;
      font-size: 12px;
      color: #9bdaf4;
      word-break: break-word;
    }
    .actions {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 12px;
    }
    a {
      color: var(--accent);
    }
    .action {
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      text-decoration: none;
      color: var(--text);
      background: rgba(9, 17, 29, 0.9);
    }
    @media (max-width: 900px) {
      .grid, .archive-summary { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="page">
    <section class="panel">
      <h1 class="headline">Evidence Archive</h1>
      <div class="muted">Browse all stored incidents, evidence hashes, anchor results, and chain-of-custody links from one archive page.</div>
      <div class="actions">
        <a class="action" href="/">Back to dashboard</a>
        <a class="action" href="/api/incidents">Open incidents JSON</a>
      </div>
      <div class="archive-summary">
        <div class="summary-card">
          <div class="label">Total incidents</div>
          <div class="headline" id="archive-total" style="font-size: 24px; margin-top: 6px;">0</div>
        </div>
        <div class="summary-card">
          <div class="label">Anchored</div>
          <div class="headline" id="archive-anchored" style="font-size: 24px; margin-top: 6px;">0</div>
        </div>
        <div class="summary-card">
          <div class="label">Evidence verified</div>
          <div class="headline" id="archive-verified" style="font-size: 24px; margin-top: 6px;">0</div>
        </div>
        <div class="summary-card">
          <div class="label">Need review</div>
          <div class="headline" id="archive-review" style="font-size: 24px; margin-top: 6px;">0</div>
        </div>
      </div>
    </section>

    <section id="archive" class="archive">
      <div class="panel">Loading evidence archive...</div>
    </section>
  </div>

  <script>
    async function loadArchive() {
      const response = await fetch("/api/incidents", { cache: "no-store" });
      if (!response.ok) {
        throw new Error("Failed to load incidents " + response.status);
      }
      const payload = await response.json();
      const archive = document.getElementById("archive");
      const incidents = payload.incidents;
      const anchoredCount = incidents.filter((incident) => (incident.anchor_status || "").toLowerCase() === "anchored").length;
      const verifiedCount = incidents.filter((incident) => (incident.verify_status || "").toLowerCase() === "verified").length;
      const reviewCount = incidents.filter((incident) => {
        const anchorStatus = (incident.anchor_status || "").toLowerCase();
        const verifyStatus = (incident.verify_status || "").toLowerCase();
        return anchorStatus !== "anchored" || verifyStatus !== "verified";
      }).length;
      document.getElementById("archive-total").textContent = String(incidents.length);
      document.getElementById("archive-anchored").textContent = String(anchoredCount);
      document.getElementById("archive-verified").textContent = String(verifiedCount);
      document.getElementById("archive-review").textContent = String(reviewCount);
      if (!incidents.length) {
        archive.innerHTML = '<div class="panel">No incidents stored yet.</div>';
        return;
      }

      archive.innerHTML = incidents.map((incident) => `
        <article class="incident">
          <div class="incident-head">
            <strong>Incident #${incident.id}</strong>
            <span class="muted">${incident.detected_at}</span>
          </div>
          <div class="grid">
            <div>
              <div class="label">Source</div>
              <div>${incident.source || "-"}</div>
            </div>
            <div>
              <div class="label">Anchor</div>
              <div>${incident.anchor_status || "-"}</div>
            </div>
            <div>
              <div class="label">Evidence verify</div>
              <div>${incident.verify_status || "-"}</div>
            </div>
            <div>
              <div class="label">Anchor verify</div>
              <div>${incident.anchor_verify_status || "-"}</div>
            </div>
            <div>
              <div class="label">Evidence hash</div>
              <div class="hash">${incident.evidence_hash || "-"}</div>
            </div>
            <div>
              <div class="label">Metadata hash</div>
              <div class="hash">${incident.metadata_hash || "-"}</div>
            </div>
          </div>
          <div class="chain-box">
            <div class="chain-box-title">Blockchain log snapshot</div>
            <div class="state-row">
              <span class="state-pill ${["anchored", "verified"].includes((incident.anchor_status || "").toLowerCase()) ? "good" : "warn"}">Anchor: ${incident.anchor_status || "-"}</span>
              <span class="state-pill ${["anchored", "verified"].includes((incident.anchor_verify_status || "").toLowerCase()) ? "good" : "warn"}">Anchor verify: ${incident.anchor_verify_status || "-"}</span>
              <span class="state-pill ${["anchored", "verified"].includes((incident.verify_status || "").toLowerCase()) ? "good" : "warn"}">Evidence verify: ${incident.verify_status || "-"}</span>
            </div>
            <div class="label">Transaction or ledger proof</div>
            <div class="hash">${incident.tx_hash || incident.ledger_path || "-"}</div>
          </div>
          <div class="actions">
            <a class="action" href="/incidents/${incident.id}">Open chain of custody</a>
            <a class="action" href="/api/incidents/${incident.id}/export">Export JSON</a>
            <a class="action" href="/api/incidents/${incident.id}/verify">Run verify API</a>
          </div>
        </article>
      `).join("");
    }

    loadArchive().catch((error) => {
      document.getElementById("archive").innerHTML = `<div class="panel">${error.message}</div>`;
    });
  </script>
</body>
</html>
"""


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_runtime_context():
    return {
        "threshold": os.getenv("THRESHOLD", "0.3"),
        "conclusion_threshold": os.getenv("CONCLUSION_THRESHOLD", "1"),
        "final_threshold": os.getenv("FINAL_THRESHOLD", "10"),
        "yolo_model": YOLO_MODEL,
        "fight_model": FIGHT_MODEL,
        "anchor_mode": anchor_service.ANCHOR_MODE,
    }


def ensure_upload_dir():
    os.makedirs(UPLOAD_ROOT, exist_ok=True)


def is_allowed_upload(filename):
    if not filename:
        return False
    return os.path.splitext(filename)[1].lower() in ALLOWED_UPLOAD_EXTENSIONS


def save_uploaded_video(file_storage):
    original_name = secure_filename(file_storage.filename or "")
    if not original_name:
        raise ValueError("Missing file name")
    if not is_allowed_upload(original_name):
        raise ValueError("Unsupported video format")

    ensure_upload_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem, ext = os.path.splitext(original_name)
    final_name = f"{timestamp}_{stem}{ext.lower()}"
    save_path = os.path.join(UPLOAD_ROOT, final_name)
    file_storage.save(save_path)
    return save_path


def add_audit_event(incident_id, event_type, event_status, detail, event_at=None, actor="system"):
    persistence.add_audit_event(
        incident_id=incident_id,
        event_type=event_type,
        event_status=event_status,
        event_at=event_at or utc_now_iso(),
        actor=actor,
        detail_json=json.dumps(detail, ensure_ascii=True, sort_keys=True),
    )


def build_incident(source):
    with state_lock:
        source_label = active_source
        started_at = stream_started_at

    timestamp = utc_now_iso()
    incident_id = persistence.create_incident(
        source=source,
        detected_at=timestamp,
        stream_started_at=started_at,
        active_source_label=source_label,
        created_at=timestamp,
    )
    add_audit_event(
        incident_id,
        "incident_created",
        "ok",
        {
            "source": source,
            "stream_started_at": started_at,
            "active_source_label": source_label,
        },
        event_at=timestamp,
    )
    return {
        "id": incident_id,
        "source": source,
        "detected_at": timestamp,
        "stream_started_at": started_at,
        "active_source_label": source_label,
    }


def persist_evidence_pipeline(incident, frame):
    evidence_package = evidence_service.create_evidence_package(
        incident=incident,
        frame=frame,
        runtime_context=get_runtime_context(),
    )
    persistence.add_evidence_artifact(
        incident_id=incident["id"],
        artifact_type=evidence_package["artifact_type"],
        file_path=evidence_package["file_path"],
        metadata_path=evidence_package["metadata_path"],
        file_sha256=evidence_package["file_sha256"],
        metadata_sha256=evidence_package["metadata_sha256"],
        file_size=evidence_package["file_size"],
        mime_type=evidence_package["mime_type"],
        storage_uri=evidence_package["storage_uri"],
        verify_status=evidence_package["verify_status"],
        created_at=incident["detected_at"],
    )
    add_audit_event(
        incident["id"],
        "evidence_packaged",
        "ok",
        {
            "artifact_type": evidence_package["artifact_type"],
            "file_path": evidence_package["file_path"],
            "metadata_path": evidence_package["metadata_path"],
            "file_sha256": evidence_package["file_sha256"],
            "metadata_sha256": evidence_package["metadata_sha256"],
            "storage_uri": evidence_package["storage_uri"],
        },
    )

    anchor_record = anchor_service.anchor_evidence(
        incident=incident,
        evidence_package=evidence_package,
        anchored_at=utc_now_iso(),
    )
    persistence.add_anchor_record(
        incident_id=incident["id"],
        anchor_mode=anchor_record["anchor_mode"],
        anchor_status=anchor_record["anchor_status"],
        tx_hash=anchor_record["tx_hash"],
        block_number=anchor_record["block_number"],
        chain_id=anchor_record["chain_id"],
        ledger_path=anchor_record["ledger_path"],
        anchor_payload_hash=anchor_record["anchor_payload_hash"],
        error_message=anchor_record["error_message"],
        anchored_at=anchor_record["anchored_at"],
    )
    add_audit_event(
        incident["id"],
        "evidence_anchored",
        anchor_record["anchor_status"],
        {
            "anchor_mode": anchor_record["anchor_mode"],
            "tx_hash": anchor_record["tx_hash"],
            "block_number": anchor_record["block_number"],
            "chain_id": anchor_record["chain_id"],
            "ledger_path": anchor_record["ledger_path"],
            "anchor_payload_hash": anchor_record["anchor_payload_hash"],
            "error_message": anchor_record["error_message"],
            "tx_url": anchor_record.get("tx_url"),
        },
        event_at=anchor_record["anchored_at"],
    )

    return persistence.get_incident_detail(incident["id"])


def serialize_incident(detail):
    if not detail:
        return None
    anchor_verify_status = anchor_service.verify_anchor_record(detail)
    tx_url = anchor_service.build_anchor_url(detail.get("tx_hash"))
    return {
        "id": detail["incident_id"],
        "source": detail["source"],
        "detected_at": detail["detected_at"],
        "active_source_label": detail.get("active_source_label"),
        "artifact_type": detail.get("artifact_type"),
        "file_path": detail.get("file_path"),
        "metadata_path": detail.get("metadata_path"),
        "evidence_hash": detail.get("file_sha256"),
        "metadata_hash": detail.get("metadata_sha256"),
        "storage_uri": detail.get("storage_uri"),
        "verify_status": detail.get("verify_status"),
        "anchor_mode": detail.get("anchor_mode"),
        "anchor_status": detail.get("anchor_status"),
        "tx_hash": detail.get("tx_hash"),
        "tx_url": tx_url,
        "block_number": detail.get("block_number"),
        "chain_id": detail.get("chain_id"),
        "ledger_path": detail.get("ledger_path"),
        "anchor_verify_status": anchor_verify_status,
        "anchor_payload_hash": detail.get("anchor_payload_hash"),
        "error_message": detail.get("error_message"),
        "anchored_at": detail.get("anchored_at"),
    }


def build_incident_export(incident_id):
    detail = persistence.get_incident_detail(incident_id)
    if not detail:
        return None
    serialized = serialize_incident(detail)
    audit_events = []
    for row in persistence.list_audit_events(incident_id):
        event = dict(row)
        try:
            event["detail"] = json.loads(event.pop("detail_json"))
        except json.JSONDecodeError:
            event["detail"] = {"raw": event.pop("detail_json")}
        audit_events.append(event)
    if not audit_events:
        if detail.get("detected_at"):
            audit_events.append({
                "audit_id": None,
                "incident_id": incident_id,
                "event_type": "incident_created",
                "event_status": "backfilled",
                "event_at": detail.get("detected_at"),
                "actor": "system-backfill",
                "detail": {
                    "source": detail.get("source"),
                    "active_source_label": detail.get("active_source_label"),
                },
            })
        if detail.get("file_path"):
            audit_events.append({
                "audit_id": None,
                "incident_id": incident_id,
                "event_type": "evidence_packaged",
                "event_status": "backfilled",
                "event_at": detail.get("detected_at"),
                "actor": "system-backfill",
                "detail": {
                    "file_path": detail.get("file_path"),
                    "metadata_path": detail.get("metadata_path"),
                    "file_sha256": detail.get("file_sha256"),
                    "metadata_sha256": detail.get("metadata_sha256"),
                },
            })
        if detail.get("tx_hash") or detail.get("ledger_path"):
            audit_events.append({
                "audit_id": None,
                "incident_id": incident_id,
                "event_type": "evidence_anchored",
                "event_status": "backfilled",
                "event_at": detail.get("anchored_at") or detail.get("detected_at"),
                "actor": "system-backfill",
                "detail": {
                    "anchor_mode": detail.get("anchor_mode"),
                    "anchor_status": detail.get("anchor_status"),
                    "tx_hash": detail.get("tx_hash"),
                    "ledger_path": detail.get("ledger_path"),
                    "anchor_payload_hash": detail.get("anchor_payload_hash"),
                },
            })
    return {
        "incident": serialized,
        "audit_events": audit_events,
        "runtime_context": get_runtime_context(),
        "exported_at": utc_now_iso(),
    }


def build_self_check():
    recent = persistence.list_recent_incidents(limit=10)
    latest = next(
        (
            item
            for item in recent
            if item.get("file_path") or item.get("tx_hash") or item.get("ledger_path")
        ),
        recent[0] if recent else None,
    )
    evidence_root = os.getenv("EVIDENCE_ROOT", "evidence")
    database_path = persistence.DB_PATH
    ledger_path = anchor_service.ANCHOR_LEDGER_PATH
    latest_verify = None
    latest_anchor_verify = None
    if latest:
        latest_verify = evidence_service.verify_evidence_artifact(latest)
        latest_anchor_verify = anchor_service.verify_anchor_record(latest)
    return {
        "checked_at": utc_now_iso(),
        "database_path": database_path,
        "database_exists": os.path.exists(database_path),
        "evidence_root": evidence_root,
        "evidence_root_exists": os.path.exists(evidence_root),
        "anchor_mode": anchor_service.ANCHOR_MODE,
        "anchor_ledger_path": ledger_path,
        "anchor_ledger_exists": os.path.exists(ledger_path),
        "web3_available": anchor_service.Web3 is not None,
        "recent_incident_count": persistence.count_incidents(),
        "latest_incident": serialize_incident(latest) if latest else None,
        "latest_verify_status": latest_verify,
        "latest_anchor_verify_status": latest_anchor_verify,
    }


def get_gpu_label():
    if not torch.cuda.is_available():
        return "CPU only"
    gpu = torch.cuda.get_device_properties(0)
    return gpu.name


def get_default_camera_index():
    return os.getenv("DEFAULT_CAMERA_INDEX", "0").strip() or "0"


def get_default_camera_input():
    configured = os.getenv("DEFAULT_CAMERA_INPUT", AUTO_CAMERA_TOKEN).strip().lower()
    return configured or AUTO_CAMERA_TOKEN


def resolve_camera_source(camera_value):
    raw_value = (camera_value or "").strip()
    normalized = raw_value.lower()

    if normalized in {"", AUTO_CAMERA_TOKEN, "default", "laptop"}:
        selected = get_default_camera_index()
        label = f"Laptop camera (index {selected})"
    else:
        selected = raw_value
        label = f"Camera index {raw_value}"

    if selected.lstrip("-").isdigit():
        return int(selected), label

    return selected, selected


def get_dashboard_context():
    default_camera_index = get_default_camera_index()
    default_camera_input = get_default_camera_input()
    return {
        "threshold": os.getenv("THRESHOLD", "0.3"),
        "conclusion_threshold": os.getenv("CONCLUSION_THRESHOLD", "1"),
        "final_threshold": os.getenv("FINAL_THRESHOLD", "10"),
        "gpu_label": get_gpu_label(),
        "default_camera_input": default_camera_input,
        "default_camera_label": f"Laptop camera (index {default_camera_index})",
        "anchor_mode": anchor_service.ANCHOR_MODE,
        "error": request.args.get("error"),
    }


@app.route("/")
def index():
    return render_template_string(DASHBOARD_TEMPLATE, **get_dashboard_context())


@app.route("/incidents/<int:incident_id>")
def incident_page(incident_id):
    return render_template_string(INCIDENT_TEMPLATE, incident_id=incident_id)


@app.route("/archive")
def archive_page():
    return render_template_string(ARCHIVE_TEMPLATE)


@app.route("/api/status")
def api_status():
    incidents = [serialize_incident(detail) for detail in persistence.list_recent_incidents(limit=10)]
    incidents = [incident for incident in incidents if incident]
    with state_lock:
        return jsonify({
            "stream_active": detect_thread_started,
            "active_source": active_source,
            "stream_started_at": stream_started_at,
            "latest_frame_fight": latest_frame_fight,
            "latest_alert_at": latest_alert_at,
            "incidents": incidents,
            "total_incidents": persistence.count_incidents(),
            "anchor_summary": persistence.summarize_anchors(),
            "anchor_mode": anchor_service.ANCHOR_MODE,
        })


@app.route("/api/incidents")
def api_incidents():
    incidents = [serialize_incident(detail) for detail in persistence.list_recent_incidents(limit=50)]
    return jsonify({"incidents": [incident for incident in incidents if incident]})


@app.route("/api/incidents/<int:incident_id>")
def api_incident_detail(incident_id):
    detail = serialize_incident(persistence.get_incident_detail(incident_id))
    if detail is None:
        return jsonify({"error": "Incident not found"}), 404
    return jsonify(detail)


@app.route("/api/incidents/<int:incident_id>/chain-of-custody")
def api_incident_chain_of_custody(incident_id):
    export_payload = build_incident_export(incident_id)
    if export_payload is None:
        return jsonify({"error": "Incident not found"}), 404
    return jsonify(export_payload)


@app.route("/api/incidents/<int:incident_id>/export")
def api_incident_export(incident_id):
    export_payload = build_incident_export(incident_id)
    if export_payload is None:
        return jsonify({"error": "Incident not found"}), 404
    return jsonify(export_payload)


@app.route("/api/incidents/<int:incident_id>/verify")
def api_incident_verify(incident_id):
    detail = persistence.get_incident_detail(incident_id)
    if detail is None:
        return jsonify({"error": "Incident not found"}), 404
    verify_status = evidence_service.verify_evidence_artifact(detail)
    anchor_verify_status = anchor_service.verify_anchor_record(detail)
    persistence.update_evidence_verify_status(incident_id, verify_status)
    add_audit_event(
        incident_id,
        "evidence_verified",
        "ok",
        {
            "verify_status": verify_status,
            "anchor_verify_status": anchor_verify_status,
            "tx_hash": detail.get("tx_hash"),
        },
        actor="api",
    )
    return jsonify({
        "incident_id": incident_id,
        "verify_status": verify_status,
        "anchor_verify_status": anchor_verify_status,
        "file_path": detail.get("file_path"),
        "metadata_path": detail.get("metadata_path"),
        "tx_hash": detail.get("tx_hash"),
        "tx_url": anchor_service.build_anchor_url(detail.get("tx_hash")),
        "anchor_status": detail.get("anchor_status"),
    })


@app.route("/api/self-check")
def api_self_check():
    return jsonify(build_self_check())


@app.route("/nvidia")
def nvidia():
    gpu_info = ""

    if torch.cuda.is_available():
        gpu_info += "CUDA is available. Showing GPU information:\n"
        for i in range(torch.cuda.device_count()):
            gpu = torch.cuda.get_device_properties(i)
            gpu_info += f"> GPU {i} - Brand: {gpu.name}\n"
    else:
        gpu_info = "CUDA is not available."

    return f"\n{gpu_info}\n"


@app.route("/raw")
def raw():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


def start_detection(video_input, source_label=None):
    global detect_thread_started, active_source, stream_started_at

    with state_lock:
        if detect_thread_started:
            return False

        detect_thread_started = True
        active_source = source_label or str(video_input)
        stream_started_at = utc_now_iso()

    t = threading.Thread(target=detect, args=(video_input,))
    t.daemon = True
    t.start()
    return True


@app.route("/start")
def start():
    video_input = request.args.get("video_input", "").strip()
    if not video_input:
        return redirect("/?error=Missing+video+input")

    if not start_detection(video_input):
        return redirect("/?error=Detector+is+already+running+for+an+active+source")

    return redirect("/")


@app.route("/upload", methods=["POST"])
def upload_video():
    if "video_file" not in request.files:
        return redirect("/?error=Missing+video+file")

    video_file = request.files["video_file"]
    if not video_file or not video_file.filename:
        return redirect("/?error=Missing+video+file")

    try:
        saved_path = save_uploaded_video(video_file)
    except ValueError as exc:
        return redirect(f"/?error={str(exc).replace(' ', '+')}")

    if not start_detection(saved_path, source_label=os.path.basename(saved_path)):
        return redirect("/?error=Detector+is+already+running+for+an+active+source")

    return redirect("/")


@app.route("/webcam")
def webcam():
    camera_value = request.args.get("camera", AUTO_CAMERA_TOKEN).strip()
    camera_source, camera_label = resolve_camera_source(camera_value)

    if not start_detection(camera_source, camera_label):
        return redirect("/?error=Detector+is+already+running+for+an+active+source")

    return redirect("/")


def detect(video_input):
    global active_source, detect_thread_started, latest_alert_at, latest_frame_fight, outputFrame, stream_started_at

    threshold = float(os.getenv("THRESHOLD", 0.3))
    conclusion_threshold = int(float(os.getenv("CONCLUSION_THRESHOLD", 1)))
    final_threshold = int(float(os.getenv("FINAL_THRESHOLD", 10)))

    fight_on = False
    fight_off_counter = 0

    print(
        f"[CONFIG] FightDetector: THRESHOLD={threshold}, "
        f"CONCLUSION={conclusion_threshold}, FINAL={final_threshold}"
    )

    fdet = fight_module.FightDetector(FIGHT_MODEL)
    yolo = fight_module.YoloPoseEstimation(YOLO_MODEL)

    try:
        for result in yolo.estimate(video_input):
            result_frame = result.plot()
            if result_frame.shape[0] > 720:
                result_frame = imutils.resize(result_frame, width=1280)

            frame_has_fight = False

            try:
                boxes = result.boxes.xyxy.tolist()
                xyn = result.keypoints.xyn.tolist()
                confs = result.keypoints.conf
                ids = result.boxes.id

                confs = [] if confs is None else confs.tolist()
                ids = [] if ids is None else [str(int(identity)) for identity in ids]

                interaction_boxes = fight_module.get_interaction_box(boxes)

                for inter_box in interaction_boxes:
                    x1, y1, x2, y2 = [int(value) for value in inter_box]
                    cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    both_fighting = []
                    for conf, xyn_person, box, identity in zip(confs, xyn, boxes, ids):
                        center_x = (box[2] + box[0]) / 2
                        center_y = (box[3] + box[1]) / 2
                        if x1 <= center_x <= x2 and y1 <= center_y <= y2:
                            is_fight = fdet.detect(conf, xyn_person)
                            both_fighting.append((identity, is_fight))

                    if both_fighting and any(is_fight for _, is_fight in both_fighting):
                        frame_has_fight = True
                        cv2.rectangle(result_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)

            except (AttributeError, TypeError, IndexError):
                pass

            if frame_has_fight:
                if not fight_on:
                    incident = build_incident(str(video_input))
                    latest_alert_at = incident["detected_at"]
                    try:
                        persisted_incident = persist_evidence_pipeline(incident, result_frame.copy())
                        print(
                            "[EVIDENCE] Incident #{id} anchored with status={status} tx={tx}".format(
                                id=incident["id"],
                                status=persisted_incident.get("anchor_status"),
                                tx=persisted_incident.get("tx_hash"),
                            )
                        )
                    except Exception as exc:
                        print(f"[EVIDENCE] Failed to persist incident #{incident['id']}: {exc}")
                fight_on = True
                fight_off_counter = final_threshold
            else:
                if fight_on:
                    fight_off_counter -= 1
                    if fight_off_counter <= 0:
                        fight_on = False

            if fight_on:
                text = "FIGHTING!"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 2
                color = (0, 0, 255)
                thickness = 3
                text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
                text_x = (result_frame.shape[1] - text_size[0]) // 2
                text_y = (result_frame.shape[0] + text_size[1]) // 2
                cv2.putText(result_frame, text, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)

            with state_lock:
                latest_frame_fight = fight_on

            with lock:
                outputFrame = result_frame.copy()
    finally:
        with state_lock:
            active_source = None
            detect_thread_started = False
            latest_frame_fight = False
            stream_started_at = None


def generate():
    global outputFrame

    while True:
        if outputFrame is None:
            time.sleep(0.05)
            continue

        flag, encoded_image = cv2.imencode(".jpg", outputFrame)
        if not flag:
            continue

        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + bytearray(encoded_image) + b"\r\n"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True, threaded=True, use_reloader=False)
