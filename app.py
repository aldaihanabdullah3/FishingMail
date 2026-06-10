"""
app.py — FishingMail
====================
A fake webmail application used in APT phishing simulation scenarios.

Features
--------
* Gmail-inspired single-page web UI with automation-friendly attributes
* SQLite inbox — pre-seeded on startup, then auto-populated on a timer
* POST /api/inject  — RAS control plane can inject a phishing email at any time
* GET  /api/status  — machine-readable inbox state
* Attachment download served as forced downloads

Configuration (env vars)
------------------------
  FISHMAIL_HOST          bind host (default 0.0.0.0)
  FISHMAIL_PORT          bind port (default 8025)
  FISHMAIL_RECIPIENT     the victim's display name/email (default user@corp.local)
  FISHMAIL_INTERVAL_MIN  min seconds between new emails (default 60)
  FISHMAIL_INTERVAL_MAX  max seconds between new emails (default 180)
  FISHMAIL_SEED_EMAILS   number of pre-existing emails on startup (default 8)
"""

import os
import io
import json
import base64
import random
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from flask import (Flask, Response, abort, g, jsonify,
                   render_template, request, send_file)

from email_generator import generate_email
from attachment_generator import generate_attachment, MIME_TYPES

# --------------------------------------------------------------------------- #
# Config                                                                        #
# --------------------------------------------------------------------------- #

HOST           = os.getenv("FISHMAIL_HOST", "0.0.0.0")
PORT           = int(os.getenv("FISHMAIL_PORT", "8025"))
RECIPIENT      = os.getenv("FISHMAIL_RECIPIENT", "j.anderson@meridian-corp.local")
INTERVAL_MIN   = int(os.getenv("FISHMAIL_INTERVAL_MIN", "60"))
INTERVAL_MAX   = int(os.getenv("FISHMAIL_INTERVAL_MAX", "180"))
SEED_COUNT     = int(os.getenv("FISHMAIL_SEED_EMAILS", "8"))
TLS_CERT       = os.getenv("FISHMAIL_TLS_CERT")   # path to PEM certificate
TLS_KEY        = os.getenv("FISHMAIL_TLS_KEY")    # path to PEM private key

# Injected phishing emails get ts = now + this offset (~10 years) so they stay
# pinned at the top of the inbox; their displayed date is capped at "now".
PHISH_TS_OFFSET = 10 * 365 * 86400

DB_PATH = Path(__file__).parent / "fishmail.db"

app = Flask(__name__)


@app.template_filter("datefmt")
def datefmt(ts):
    """Short date for inbox list: 'Jan 15' or 'HH:MM' if today."""
    # Cap at now so far-future (pinned phishing) ts shows as a fresh arrival.
    dt = datetime.fromtimestamp(min(float(ts), time.time()))
    if dt.date() == datetime.now().date():
        return dt.strftime("%-I:%M %p")
    return dt.strftime("%b %-d")


@app.template_filter("datefmt_long")
def datefmt_long(ts):
    dt = datetime.fromtimestamp(min(float(ts), time.time()))
    return dt.strftime("%a, %b %-d, %Y at %-I:%M %p")

# --------------------------------------------------------------------------- #
# Database                                                                      #
# --------------------------------------------------------------------------- #

SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_name      TEXT    NOT NULL,
    sender_email     TEXT    NOT NULL,
    recipient        TEXT    NOT NULL,
    subject          TEXT    NOT NULL,
    body             TEXT    NOT NULL,
    ts               REAL    NOT NULL,
    is_read          INTEGER NOT NULL DEFAULT 0,
    has_attachment   INTEGER NOT NULL DEFAULT 0,
    attach_filename  TEXT,
    attach_data      BLOB,
    attach_mime      TEXT,
    is_phishing      INTEGER NOT NULL DEFAULT 0,
    category         TEXT    NOT NULL DEFAULT 'normal'
);
"""

def get_db() -> sqlite3.Connection:
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(str(DB_PATH))
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def _init_db():
    with sqlite3.connect(str(DB_PATH)) as con:
        con.executescript(SCHEMA)
        con.commit()


def _insert_email(
    sender_name: str,
    sender_email: str,
    subject: str,
    body: str,
    ts: float = None,
    is_read: int = 0,
    attach_filename: str = None,
    attach_data: bytes = None,
    attach_mime: str = None,
    is_phishing: int = 0,
    category: str = "normal",
) -> int:
    has_attachment = 1 if attach_data is not None else 0
    if ts is None:
        ts = time.time()
    with sqlite3.connect(str(DB_PATH)) as con:
        cur = con.execute(
            """INSERT INTO emails
               (sender_name, sender_email, recipient, subject, body,
                ts, is_read, has_attachment, attach_filename,
                attach_data, attach_mime, is_phishing, category)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (sender_name, sender_email, RECIPIENT, subject, body,
             ts, is_read, has_attachment, attach_filename,
             attach_data, attach_mime, is_phishing, category),
        )
        return cur.lastrowid


def _seed():
    """Insert a set of pre-existing emails spanning the last 7 days."""
    now = time.time()
    for i in range(SEED_COUNT):
        age_seconds = random.randint(300, 7 * 86400)
        ts = now - age_seconds
        msg = generate_email()
        fname = fdata = fmime = None
        if msg["has_attachment"] and msg["attach_type"]:
            fname, fdata, fmime = generate_attachment(
                msg["subject"], msg["body"], msg["attach_type"]
            )
        _insert_email(
            sender_name    = msg["sender_name"],
            sender_email   = msg["sender_email"],
            subject        = msg["subject"],
            body           = msg["body"],
            ts             = ts,
            is_read        = 1 if random.random() < 0.65 else 0,
            attach_filename= fname,
            attach_data    = fdata,
            attach_mime    = fmime,
            category       = msg["category"],
        )
    print(f"[fishmail] seeded {SEED_COUNT} emails")


# --------------------------------------------------------------------------- #
# Background email generator                                                    #
# --------------------------------------------------------------------------- #

_stop_event = threading.Event()

def _email_loop():
    """Periodically insert a new generated email into the DB."""
    while not _stop_event.is_set():
        delay = random.randint(INTERVAL_MIN, INTERVAL_MAX)
        _stop_event.wait(delay)
        if _stop_event.is_set():
            break
        msg = generate_email()
        fname = fdata = fmime = None
        if msg["has_attachment"] and msg["attach_type"]:
            fname, fdata, fmime = generate_attachment(
                msg["subject"], msg["body"], msg["attach_type"]
            )
        eid = _insert_email(
            sender_name    = msg["sender_name"],
            sender_email   = msg["sender_email"],
            subject        = msg["subject"],
            body           = msg["body"],
            attach_filename= fname,
            attach_data    = fdata,
            attach_mime    = fmime,
            category       = msg["category"],
        )
        print(f"[fishmail] new email id={eid} subject='{msg['subject'][:50]}'")


# --------------------------------------------------------------------------- #
# Routes — UI                                                                   #
# --------------------------------------------------------------------------- #

@app.route("/")
def inbox():
    db = get_db()
    rows = db.execute(
        """SELECT id, sender_name, sender_email, subject, ts,
                  is_read, has_attachment, is_phishing
           FROM emails
           ORDER BY ts DESC"""
    ).fetchall()
    unread = sum(1 for r in rows if not r["is_read"])
    return render_template("index.html",
                           emails=rows,
                           unread=unread,
                           recipient=RECIPIENT)


@app.route("/email/<int:email_id>")
def view_email(email_id: int):
    db = get_db()
    row = db.execute("SELECT * FROM emails WHERE id=?", (email_id,)).fetchone()
    if row is None:
        abort(404)
    # Mark as read
    db.execute("UPDATE emails SET is_read=1 WHERE id=?", (email_id,))
    db.commit()
    all_rows = db.execute(
        """SELECT id, sender_name, sender_email, subject, ts,
                  is_read, has_attachment, is_phishing
           FROM emails ORDER BY ts DESC"""
    ).fetchall()
    unread = sum(1 for r in all_rows if not r["is_read"])
    return render_template("index.html",
                           emails=all_rows,
                           selected=row,
                           unread=unread,
                           recipient=RECIPIENT)


@app.route("/attachment/<int:email_id>")
def download_attachment(email_id: int):
    db = get_db()
    row = db.execute(
        "SELECT attach_filename, attach_data, attach_mime FROM emails WHERE id=?",
        (email_id,)
    ).fetchone()
    if row is None or row["attach_data"] is None:
        abort(404)
    return send_file(
        io.BytesIO(row["attach_data"]),
        mimetype=row["attach_mime"] or "application/octet-stream",
        as_attachment=True,
        download_name=row["attach_filename"],
    )


@app.route("/compose/reply", methods=["POST"])
def reply():
    """Simulated reply — just records the action and returns success."""
    email_id = request.form.get("email_id", type=int)
    body     = request.form.get("body", "")
    if not email_id:
        return jsonify({"ok": False, "error": "missing email_id"}), 400
    print(f"[fishmail] reply to email id={email_id}: {body[:80]!r}")
    return jsonify({"ok": True, "message": "Reply sent."})


# --------------------------------------------------------------------------- #
# Routes — Machine / RAS API                                                    #
# --------------------------------------------------------------------------- #

@app.route("/api/status")
def api_status():
    db = get_db()
    total  = db.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    unread = db.execute("SELECT COUNT(*) FROM emails WHERE is_read=0").fetchone()[0]
    latest = db.execute(
        "SELECT id, subject, ts FROM emails ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    return jsonify({
        "total_emails": total,
        "unread":       unread,
        "latest_id":    latest["id"]   if latest else None,
        "latest_subj":  latest["subject"] if latest else None,
    })


@app.route("/api/inject", methods=["POST"])
def api_inject():
    """
    RAS control-plane endpoint to inject a phishing email.

    JSON body:
      sender_name        str   required
      sender_email       str   required
      subject            str   required
      body               str   required
      attach_filename    str   optional
      attach_content_b64 str   optional  — base64-encoded attachment bytes
      attach_mime        str   optional  — MIME type (default application/octet-stream)
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"ok": False, "error": "expected JSON body"}), 400

    required = ("sender_name", "sender_email", "subject", "body")
    missing  = [k for k in required if not data.get(k)]
    if missing:
        return jsonify({"ok": False, "error": f"missing fields: {missing}"}), 400

    fname = data.get("attach_filename")
    fmime = data.get("attach_mime", "application/octet-stream")
    fdata = None
    if data.get("attach_content_b64"):
        try:
            fdata = base64.b64decode(data["attach_content_b64"])
        except Exception as exc:
            return jsonify({"ok": False, "error": f"bad base64: {exc}"}), 400

    eid = _insert_email(
        sender_name    = data["sender_name"],
        sender_email   = data["sender_email"],
        subject        = data["subject"],
        body           = data["body"],
        # Far-future ts pins injected phishing to the top of the inbox so later
        # auto-generated emails can't push it down. Display is capped at "now"
        # (see datefmt) so the UI still shows a plausible fresh-arrival time.
        ts             = time.time() + PHISH_TS_OFFSET,
        attach_filename= fname,
        attach_data    = fdata,
        attach_mime    = fmime if fdata else None,
        is_phishing    = 1,
        category       = "phishing",
    )
    print(f"[fishmail] PHISHING email injected id={eid} subject='{data['subject'][:50]}'")
    return jsonify({"ok": True, "email_id": eid})


@app.route("/api/restore", methods=["POST"])
def api_restore_all():
    """
    Un-pin every currently-pinned injected email, without needing an id.

    Pinned emails are exactly those with a future ts (now + PHISH_TS_OFFSET).
    Each is returned to its real arrival time so it sorts into its natural
    chronological place. Idempotent: if nothing is pinned, restores 0.
    """
    db = get_db()
    rows = db.execute(
        "SELECT id, ts FROM emails WHERE ts > ?", (time.time(),)
    ).fetchall()
    for r in rows:
        db.execute("UPDATE emails SET ts=? WHERE id=?",
                   (float(r["ts"]) - PHISH_TS_OFFSET, r["id"]))
    db.commit()
    ids = [r["id"] for r in rows]
    if ids:
        print(f"[fishmail] restored {len(ids)} pinned email(s) to natural position: {ids}")
    return jsonify({"ok": True, "restored": len(ids), "email_ids": ids})


@app.route("/api/emails/<int:email_id>/restore", methods=["POST"])
def api_restore(email_id: int):
    """
    Un-pin a previously injected phishing email.

    Injected emails are pinned to the top of the inbox via a far-future ts
    (now + PHISH_TS_OFFSET). This endpoint subtracts that offset back off,
    returning the email to its real arrival time so it sorts into its natural
    chronological place. Idempotent: an already-restored email is left as-is.
    """
    db = get_db()
    row = db.execute("SELECT ts FROM emails WHERE id=?", (email_id,)).fetchone()
    if row is None:
        return jsonify({"ok": False, "error": f"no email with id {email_id}"}), 404

    ts = float(row["ts"])
    if ts <= time.time():
        # Not pinned — already at its natural position.
        return jsonify({"ok": True, "email_id": email_id,
                        "restored": False, "ts": ts})

    new_ts = ts - PHISH_TS_OFFSET
    db.execute("UPDATE emails SET ts=? WHERE id=?", (new_ts, email_id))
    db.commit()
    print(f"[fishmail] restored email id={email_id} to natural position ts={new_ts}")
    return jsonify({"ok": True, "email_id": email_id,
                    "restored": True, "ts": new_ts})


@app.route("/api/emails")
def api_emails():
    """Returns inbox as JSON — useful for agents to poll state."""
    db = get_db()
    rows = db.execute(
        """SELECT id, sender_name, sender_email, subject, ts,
                  is_read, has_attachment, is_phishing, category
           FROM emails ORDER BY ts DESC"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/emails/<int:email_id>/read", methods=["POST"])
def api_mark_read(email_id: int):
    db = get_db()
    db.execute("UPDATE emails SET is_read=1 WHERE id=?", (email_id,))
    db.commit()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------- #
# Startup                                                                       #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    _init_db()

    # Only seed if the DB is empty
    with sqlite3.connect(str(DB_PATH)) as con:
        count = con.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    if count == 0:
        _seed()

    # Start background email generator
    t = threading.Thread(target=_email_loop, daemon=True)
    t.start()

    ssl_context = None
    if TLS_CERT and TLS_KEY:
        ssl_context = (TLS_CERT, TLS_KEY)
        print(f"[fishmail] TLS enabled  cert={TLS_CERT}  key={TLS_KEY}")
        print(f"[fishmail] listening on https://{HOST}:{PORT}")
    else:
        print(f"[fishmail] listening on http://{HOST}:{PORT}")

    app.run(host=HOST, port=PORT, debug=False, use_reloader=False,
            ssl_context=ssl_context)
