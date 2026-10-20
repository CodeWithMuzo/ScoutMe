"""
database/github_sync.py
=======================
Automatic GitHub & CSV Synchronization for ScoutMe Coach Evaluations (Method A).
- Stores coach evaluations in a dedicated 'evaluations-data' branch on GitHub
  (CodeWithMuzo/ScoutMe) so live submissions on Streamlit Cloud never trigger
  a 'main' branch hot-reload while a coach is filling out forms, and never
  conflict with local code commits.
- Restores evaluations automatically if the Streamlit Cloud container restarts.
- Allows one-command local synchronization via `sync_coach_evaluations.py`.
"""

import os
import io
import base64
import sqlite3
import subprocess
import requests
import pandas as pd

GITHUB_REPO = "CodeWithMuzo/ScoutMe"
GITHUB_BRANCH = "evaluations-data"
GITHUB_FILE_PATH = "coach_evaluations.csv"


def get_github_token():
    """
    Resolves GitHub token from:
    1. Streamlit secrets (`st.secrets["GITHUB_TOKEN"]`)
    2. Environment variable (`GITHUB_TOKEN`)
    3. Local Git Credential Manager (when running on local PC)
    """
    # 1. Try Streamlit secrets
    try:
        import streamlit as st
        if "GITHUB_TOKEN" in st.secrets:
            return str(st.secrets["GITHUB_TOKEN"]).strip()
    except Exception:
        pass

    # 2. Try environment variable
    env_tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if env_tok:
        return env_tok

    # 3. Try local .streamlit/secrets.toml directly (for CLI scripts)
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GITHUB_TOKEN"):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
        except Exception:
            pass

    # 4. Try local git credential manager
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, timeout=4
        )
        creds = dict(line.split("=", 1) for line in proc.stdout.splitlines() if "=" in line)
        tok = creds.get("password", "").strip()
        if tok:
            return tok
    except Exception:
        pass

    return ""


def ensure_evaluations_branch(token):
    """Ensures the 'evaluations-data' branch exists on GitHub."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    branch_url = f"https://api.github.com/repos/{GITHUB_REPO}/git/ref/heads/{GITHUB_BRANCH}"
    r = requests.get(branch_url, headers=headers, timeout=8)
    if r.status_code == 200:
        return True

    # Get main branch SHA and create evaluations-data branch
    main_url = f"https://api.github.com/repos/{GITHUB_REPO}/git/ref/heads/main"
    r_main = requests.get(main_url, headers=headers, timeout=8)
    if r_main.status_code != 200:
        return False

    main_sha = r_main.json()["object"]["sha"]
    create_url = f"https://api.github.com/repos/{GITHUB_REPO}/git/refs"
    r_create = requests.post(
        create_url,
        headers=headers,
        json={"ref": f"refs/heads/{GITHUB_BRANCH}", "sha": main_sha},
        timeout=8
    )
    return r_create.status_code in (200, 201)


def export_db_evaluations_to_csv(db_path="data/ktff.db", csv_path="data/coach_evaluations.csv"):
    """Exports the local SQLite coach_evaluations table to CSV and returns DataFrame."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM coach_evaluations ORDER BY id ASC", conn)
    conn.close()
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    return df


def push_evaluations_to_github(db_path="data/ktff.db", csv_path="data/coach_evaluations.csv"):
    """
    Exports `coach_evaluations` from SQLite to CSV and commits it to the
    `evaluations-data` branch on GitHub via the GitHub Contents API.
    Returns (success: bool, message: str).
    """
    df = export_db_evaluations_to_csv(db_path=db_path, csv_path=csv_path)
    token = get_github_token()
    if not token:
        return False, "GITHUB_TOKEN tanımlı değil (yerel veritabanına kaydedildi)."

    try:
        if not ensure_evaluations_branch(token):
            return False, "GitHub 'evaluations-data' dalı oluşturulamadı."

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"

        # First pull any remote evaluations we might not have locally so we never overwrite remote rows
        pull_evaluations_from_github_to_db(db_path=db_path, csv_path=csv_path)
        df = export_db_evaluations_to_csv(db_path=db_path, csv_path=csv_path)

        csv_bytes = df.to_csv(index=False, encoding="utf-8").encode("utf-8")
        b64_content = base64.b64encode(csv_bytes).decode("ascii")

        # Check if file already exists on evaluations-data branch to get its SHA
        r_get = requests.get(api_url, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=8)
        payload = {
            "message": f"Sync coach evaluations ({len(df)} total records)",
            "content": b64_content,
            "branch": GITHUB_BRANCH
        }
        if r_get.status_code == 200:
            payload["sha"] = r_get.json()["sha"]

        r_put = requests.put(api_url, headers=headers, json=payload, timeout=10)
        if r_put.status_code in (200, 201):
            return True, f"GitHub senkronizasyonu başarılı ({len(df)} kayıt)."
        return False, f"GitHub API Hatası ({r_put.status_code})"
    except Exception as e:
        return False, f"GitHub bağlantı hatası: {e}"


def pull_evaluations_from_github_to_db(db_path="data/ktff.db", csv_path="data/coach_evaluations.csv"):
    """
    Fetches `coach_evaluations.csv` from GitHub ('evaluations-data' branch)
    and merges any new evaluation rows into `db_path` (`coach_evaluations` table)
    without duplicating existing records.
    Returns (added_count: int, total_count: int).
    """
    token = get_github_token()
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    csv_text = None
    try:
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
        r = requests.get(api_url, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=8)
        if r.status_code == 200:
            content_b64 = r.json().get("content", "")
            csv_text = base64.b64decode(content_b64).decode("utf-8")
        else:
            # Fallback to raw URL
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_FILE_PATH}"
            r_raw = requests.get(raw_url, timeout=8)
            if r_raw.status_code == 200:
                csv_text = r_raw.text
    except Exception:
        pass

    if not csv_text:
        conn = sqlite3.connect(db_path)
        cnt = conn.execute("SELECT COUNT(*) FROM coach_evaluations").fetchone()[0]
        conn.close()
        return 0, cnt

    remote_df = pd.read_csv(io.StringIO(csv_text))
    if remote_df.empty:
        return 0, 0

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Existing signatures in local DB to prevent duplicate insertion
    cur.execute("""
        SELECT coach_name, club_name, player_id, decision, COALESCE(feedback_note, ''), COALESCE(created_at, '')
        FROM coach_evaluations
    """)
    existing_sigs = set()
    for row in cur.fetchall():
        sig = (
            str(row[0] or "").strip(),
            str(row[1] or "").strip(),
            int(row[2] or 0),
            str(row[3] or "").strip(),
            str(row[4] or "").strip()
        )
        existing_sigs.add(sig)

    added = 0
    for _, r in remote_df.iterrows():
        c_name = str(r.get("coach_name", "") if pd.notna(r.get("coach_name")) else "").strip()
        cl_name = str(r.get("club_name", "") if pd.notna(r.get("club_name")) else "").strip()
        pid = int(r.get("player_id", 0)) if pd.notna(r.get("player_id")) else 0
        p_name = str(r.get("player_name", "") if pd.notna(r.get("player_name")) else "").strip()
        t_pos = str(r.get("target_position", "") if pd.notna(r.get("target_position")) else "").strip() or None
        form = str(r.get("formation", "") if pd.notna(r.get("formation")) else "").strip() or None
        ptype = str(r.get("player_type", "") if pd.notna(r.get("player_type")) else "").strip() or None
        is_kn = int(r.get("is_known", 0)) if pd.notna(r.get("is_known")) else None
        m_sc = float(r.get("model_score", 0.0)) if pd.notna(r.get("model_score")) else 0.0
        tf_r = int(r.get("tactical_fit_rating", 4)) if pd.notna(r.get("tactical_fit_rating")) else 4
        pt_r = int(r.get("playing_time_rating", 4)) if pd.notna(r.get("playing_time_rating")) else 4
        fe_r = int(r.get("feasibility_rating", 4)) if pd.notna(r.get("feasibility_rating")) else 4
        dec = str(r.get("decision", "") if pd.notna(r.get("decision")) else "").strip()
        note = str(r.get("feedback_note", "") if pd.notna(r.get("feedback_note")) else "").strip()
        c_at = str(r.get("created_at", "") if pd.notna(r.get("created_at")) else "").strip() or None

        sig = (c_name, cl_name, pid, dec, note)
        if sig not in existing_sigs:
            if c_at:
                cur.execute("""
                    INSERT INTO coach_evaluations
                    (coach_name, club_name, player_id, player_name, target_position,
                     formation, player_type, is_known, model_score, tactical_fit_rating,
                     playing_time_rating, feasibility_rating, decision, feedback_note, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (c_name, cl_name, pid, p_name, t_pos, form, ptype, is_kn, m_sc, tf_r, pt_r, fe_r, dec, note, c_at))
            else:
                cur.execute("""
                    INSERT INTO coach_evaluations
                    (coach_name, club_name, player_id, player_name, target_position,
                     formation, player_type, is_known, model_score, tactical_fit_rating,
                     playing_time_rating, feasibility_rating, decision, feedback_note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (c_name, cl_name, pid, p_name, t_pos, form, ptype, is_kn, m_sc, tf_r, pt_r, fe_r, dec, note))
            existing_sigs.add(sig)
            added += 1

    conn.commit()
    total_cnt = cur.execute("SELECT COUNT(*) FROM coach_evaluations").fetchone()[0]
    conn.close()
    return added, total_cnt
