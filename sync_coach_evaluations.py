"""
sync_coach_evaluations.py
=========================
Synchronizes coach evaluations between the remote GitHub 'evaluations-data'
branch and the local `data/ktff.db` SQLite database without modifying any
other project files.
"""

import sys
from database.github_sync import pull_evaluations_from_github_to_db, push_evaluations_to_github

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass


def main():
    print("=" * 65)
    print(" 🔄 SCOUTME ANTRENÖR DEĞERLENDİRME SENKRONİZASYONU (GITHUB <-> DB)")
    print("=" * 65)
    added, total = pull_evaluations_from_github_to_db()
    print(f"[+] GitHub'dan yerel veritabanına eklenen yeni kayıt : {added}")
    print(f"[*] Yerel veritabanındaki toplam değerlendirme adedi : {total}")
    ok, msg = push_evaluations_to_github()
    print(f"[✓] Durum: {msg}")
    print("=" * 65)


if __name__ == "__main__":
    main()
