import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "ktff.db")
OUT_HTML = os.path.join(BASE_DIR, "scoutme_visual_boxes.html")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

clubs = [dict(r) for r in cur.execute("SELECT * FROM clubs ORDER BY name").fetchall()]
matches = [dict(r) for r in cur.execute("SELECT * FROM matches ORDER BY match_date DESC").fetchall()]
coaches = [dict(r) for r in cur.execute("SELECT * FROM coaches ORDER BY name").fetchall()]

# Aggregated stats per player from player_season_stats
stats_map = {}
for r in cur.execute("""
    SELECT 
        player_id,
        ktff_player_id,
        SUM(goals) as total_goals,
        SUM(yellow_cards) as total_yellow_cards,
        SUM(red_cards) as total_red_cards,
        SUM(starter_matches) as total_starter,
        SUM(sub_in_matches) as total_sub_in,
        SUM(bench_unused_matches) as total_bench,
        SUM(total_played_matches) as total_played,
        SUM(total_squad_matches) as total_squad
    FROM player_season_stats
    GROUP BY player_id, ktff_player_id
""").fetchall():
    stats_map[r["player_id"]] = dict(r)

# Detailed seasons list per player
season_breakdown = {}
for r in cur.execute("""
    SELECT player_id, season, goals, yellow_cards, red_cards, starter_matches, sub_in_matches, bench_unused_matches, total_played_matches
    FROM player_season_stats
    ORDER BY season DESC
""").fetchall():
    pid = r["player_id"]
    if pid not in season_breakdown:
        season_breakdown[pid] = []
    season_breakdown[pid].append(dict(r))

players_raw = [dict(r) for r in cur.execute("SELECT * FROM players ORDER BY name").fetchall()]
players = []

for p in players_raw:
    pid = p["id"]
    st = stats_map.get(pid, {})
    p["total_goals"] = st.get("total_goals", 0)
    p["total_yellow"] = st.get("total_yellow_cards", 0)
    p["total_red"] = st.get("total_red_cards", 0)
    p["total_starter"] = st.get("total_starter", 0)
    p["total_sub_in"] = st.get("total_sub_in", 0)
    p["total_bench"] = st.get("total_bench", 0)
    p["total_played"] = st.get("total_played", 0)
    p["seasons_list"] = season_breakdown.get(pid, [])
    players.append(p)

# Sort players with highest goals and appearances first
players.sort(key=lambda x: (x["total_goals"], x["total_played"]), reverse=True)

cards_data = {
    "clubs": clubs,
    "players": players,
    "matches": matches,
    "coaches": coaches
}

json_payload = json.dumps(cards_data, ensure_ascii=False)

html_template = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScoutMe - KTFF Aktif Futbolcular ve Sezon İstatistikleri</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        :root {{
            --bg-color: #0b1120;
            --card-bg: #1e293b;
            --accent: #10b981;
            --accent-hover: #059669;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
        }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            padding-bottom: 70px;
        }}
        .navbar {{
            background: rgba(15, 23, 42, 0.9) !important;
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
        }}
        .badge-scout {{
            background: linear-gradient(135deg, #10b981, #065f46);
            color: white;
            font-weight: 600;
        }}
        .stat-card {{
            background: #1e293b;
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 18px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .stat-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
            border-color: var(--accent);
        }}
        .box-card {{
            background: #1e293b;
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 18px;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: all 0.2s ease-in-out;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        }}
        .box-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 14px 28px rgba(0,0,0,0.5);
            border-color: var(--accent);
        }}
        .box-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 5px;
            height: 100%;
            background: var(--accent);
            opacity: 0.9;
        }}
        .box-card.club-card::before {{ background: #3b82f6; }}
        .box-card.coach-card::before {{ background: #f59e0b; }}
        .box-card.match-card::before {{ background: #ec4899; }}
        
        .player-avatar {{
            width: 54px;
            height: 54px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid var(--accent);
            background: #0f172a;
        }}
        .player-avatar-placeholder {{
            width: 54px;
            height: 54px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #334155;
            color: #94a3b8;
            font-size: 1.5rem;
            border: 2px solid #475569;
        }}
        .stat-badge-box {{
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 6px 10px;
            text-align: center;
        }}
        .stat-badge-box .num {{
            font-size: 1.1rem;
            font-weight: 700;
        }}
        .stat-badge-box .label {{
            font-size: 0.68rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
        }}
        .nav-pills .nav-link {{
            color: var(--text-muted);
            border-radius: 10px;
            padding: 10px 20px;
            font-weight: 600;
            margin-right: 8px;
            border: 1px solid transparent;
            transition: all 0.2s;
        }}
        .nav-pills .nav-link.active {{
            background-color: var(--accent);
            color: #0b1120;
            font-weight: 700;
            border-color: var(--accent);
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
        }}
        .search-box {{
            background: #1e293b;
            border: 1px solid var(--border-color);
            color: white;
            border-radius: 10px;
            padding: 12px 18px;
        }}
        .search-box:focus {{
            background: #1e293b;
            color: white;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.25);
        }}
        .schema-box {{
            background: #1e293b;
            border: 2px solid #3b82f6;
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 20px;
            height: 100%;
        }}
        .field-pill {{
            display: inline-block;
            background: #0b1120;
            border: 1px solid #334155;
            padding: 4px 9px;
            border-radius: 6px;
            font-size: 0.82rem;
            margin: 2px;
            color: #cbd5e1;
        }}
        .field-pill.pk {{
            border-color: #f59e0b;
            color: #fbbf24;
            font-weight: bold;
        }}
        .field-pill.fk {{
            border-color: #10b981;
            color: #34d399;
            font-weight: bold;
        }}
    </style>
</head>
<body>

<nav class="navbar navbar-dark sticky-top px-4 py-3 mb-4">
    <div class="container-fluid d-flex justify-content-between align-items-center">
        <div class="d-flex align-items-center gap-3">
            <div style="background: #10b981; width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);">
                <i class="fa-solid fa-futbol fa-xl text-dark"></i>
            </div>
            <div>
                <h4 class="m-0 fw-bold">ScoutMe <span style="color: #10b981; font-weight: 500; font-size: 1.1rem;">| KTFF Oyuncu ve Sezon İstatistikleri</span></h4>
                <small class="text-secondary">Goller, Kartlar, İlk 11, Sonradan Giren, Yedek ve Toplam Süreler</small>
            </div>
        </div>
        <div class="d-flex gap-2">
            <span class="badge bg-dark border border-secondary px-3 py-2 d-flex align-items-center">
                <i class="fa-solid fa-database me-2 text-success"></i> SQLite: ktff.db (Canlı Veri)
            </span>
        </div>
    </div>
</nav>

<div class="container-fluid px-4">

    <!-- Stats Summary Row -->
    <div class="row g-3 mb-4">
        <div class="col-6 col-md-3">
            <div class="stat-card d-flex align-items-center justify-content-between">
                <div>
                    <div class="text-muted small">Kayıtlı Futbolcu</div>
                    <div class="fs-3 fw-bold text-success">{len(players)}</div>
                </div>
                <i class="fa-solid fa-users fa-2x text-secondary opacity-50"></i>
            </div>
        </div>
        <div class="col-6 col-md-3">
            <div class="stat-card d-flex align-items-center justify-content-between">
                <div>
                    <div class="text-muted small">Aktif Kulüp</div>
                    <div class="fs-3 fw-bold text-primary">{len(clubs)}</div>
                </div>
                <i class="fa-solid fa-shield-halved fa-2x text-secondary opacity-50"></i>
            </div>
        </div>
        <div class="col-6 col-md-3">
            <div class="stat-card d-flex align-items-center justify-content-between">
                <div>
                    <div class="text-muted small">Sezon İstatistik Kaydı</div>
                    <div class="fs-3 fw-bold text-warning">{sum(len(p['seasons_list']) for p in players)}</div>
                </div>
                <i class="fa-solid fa-chart-line fa-2x text-secondary opacity-50"></i>
            </div>
        </div>
        <div class="col-6 col-md-3">
            <div class="stat-card d-flex align-items-center justify-content-between">
                <div>
                    <div class="text-muted small">Teknik Direktör</div>
                    <div class="fs-3 fw-bold text-info">{len(coaches)}</div>
                </div>
                <i class="fa-solid fa-user-tie fa-2x text-secondary opacity-50"></i>
            </div>
        </div>
    </div>

    <!-- Navigation Tabs & Live Search -->
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <ul class="nav nav-pills" id="pills-tab" role="tablist">
            <li class="nav-item">
                <button class="nav-link active" id="tab-players-btn" data-bs-toggle="pill" data-bs-target="#tab-players"><i class="fa-solid fa-running me-2"></i>Futbolcu İstatistik Kutuları ({len(players)})</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="tab-clubs-btn" data-bs-toggle="pill" data-bs-target="#tab-clubs"><i class="fa-solid fa-shield me-2"></i>Kulüp Kutuları ({len(clubs)})</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="tab-matches-btn" data-bs-toggle="pill" data-bs-target="#tab-matches"><i class="fa-solid fa-calendar-days me-2"></i>Maç Kutuları ({len(matches)})</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="tab-coaches-btn" data-bs-toggle="pill" data-bs-target="#tab-coaches"><i class="fa-solid fa-user-tie me-2"></i>Antrenör Kutuları ({len(coaches)})</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="tab-schema-btn" data-bs-toggle="pill" data-bs-target="#tab-schema"><i class="fa-solid fa-diagram-project me-2"></i>Veritabanı Şeması (ERD)</button>
            </li>
        </ul>

        <div class="flex-grow-1" style="max-width: 350px;">
            <input type="text" id="search-input" class="form-control search-box" placeholder="Futbolcu, kulüp, mevki ara...">
        </div>
    </div>

    <!-- Content Tabs -->
    <div class="tab-content" id="pills-tabContent">

        <!-- TAB: PLAYERS -->
        <div class="tab-pane fade show active" id="tab-players">
            <div class="row g-3" id="players-grid"></div>
        </div>

        <!-- TAB: CLUBS -->
        <div class="tab-pane fade" id="tab-clubs">
            <div class="row g-3" id="clubs-grid"></div>
        </div>

        <!-- TAB: MATCHES -->
        <div class="tab-pane fade" id="tab-matches">
            <div class="row g-3" id="matches-grid"></div>
        </div>

        <!-- TAB: COACHES -->
        <div class="tab-pane fade" id="tab-coaches">
            <div class="row g-3" id="coaches-grid"></div>
        </div>

        <!-- TAB: SCHEMA -->
        <div class="tab-pane fade" id="tab-schema">
            <div class="row g-4">
                <div class="col-md-4">
                    <div class="schema-box" style="border-color: #10b981;">
                        <h5 class="text-success"><i class="fa-solid fa-table me-2"></i>player_season_stats (YENİ)</h5>
                        <p class="small text-muted">Oyuncunun tüm sezonlardaki maç, gol, kart ve süre dağılımı</p>
                        <div>
                            <span class="field-pill pk">id (PK)</span>
                            <span class="field-pill fk">player_id (FK &rarr; players.id)</span>
                            <span class="field-pill">ktff_player_id</span>
                            <span class="field-pill">season</span>
                            <span class="field-pill">goals</span>
                            <span class="field-pill">yellow_cards</span>
                            <span class="field-pill">red_cards</span>
                            <span class="field-pill">starter_matches (İlk 11)</span>
                            <span class="field-pill">sub_in_matches (Sonradan)</span>
                            <span class="field-pill">bench_unused_matches (Yedek)</span>
                            <span class="field-pill">total_played_matches</span>
                            <span class="field-pill">total_squad_matches</span>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="schema-box" style="border-color: #3b82f6;">
                        <h5 class="text-primary"><i class="fa-solid fa-running me-2"></i>players</h5>
                        <p class="small text-muted">Oyuncu profili, fotoğrafı, mevkisi, kimlik bilgileri</p>
                        <div>
                            <span class="field-pill pk">id (PK)</span>
                            <span class="field-pill">ktff_player_id</span>
                            <span class="field-pill">license_no</span>
                            <span class="field-pill">name</span>
                            <span class="field-pill">current_club</span>
                            <span class="field-pill">positions</span>
                            <span class="field-pill">birth_date</span>
                            <span class="field-pill">status</span>
                            <span class="field-pill">photo_url</span>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="schema-box" style="border-color: #ec4899;">
                        <h5 class="text-danger"><i class="fa-solid fa-shield me-2"></i>clubs & matches</h5>
                        <p class="small text-muted">Lig kulüpleri, maçlar, esameler ve olaylar</p>
                        <div>
                            <span class="field-pill">clubs</span>
                            <span class="field-pill">matches</span>
                            <span class="field-pill">match_lineups</span>
                            <span class="field-pill">match_events</span>
                            <span class="field-pill">coaches</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>

</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
    const data = {json_payload};
    const playersData = data.players;
    const clubsData = data.clubs;
    const matchesData = data.matches;
    const coachesData = data.coaches;

    function renderPlayers(list) {{
        const grid = document.getElementById('players-grid');
        grid.innerHTML = list.map(p => `
            <div class="col-12 col-md-6 col-lg-4 col-xl-3">
                <div class="box-card">
                    <div>
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <span class="badge bg-secondary small">KTFF ID: ${{p.ktff_player_id || '-'}}</span>
                            <span class="badge ${{p.positions ? 'badge-scout' : 'bg-dark border border-secondary'}}">${{p.positions || 'Mevki Belirtilmemiş'}}</span>
                        </div>

                        <div class="d-flex align-items-center gap-3 mb-3">
                            <div class="position-relative">
                                ${{p.photo_url ? `<img src="${{p.photo_url}}" class="player-avatar" alt="${{p.name}}">` : `<div class="player-avatar-placeholder"><i class="fa-solid fa-user"></i></div>`}}
                                <span class="position-absolute bottom-0 end-0 badge rounded-pill ${{p.skill_overall >= 80 ? 'bg-warning text-dark' : (p.skill_overall >= 70 ? 'bg-success' : 'bg-secondary')}}" style="font-size: 0.72rem; font-weight: 700;">
                                    ${{Math.round(p.skill_overall || 50)}}
                                </span>
                            </div>
                            <div class="overflow-hidden">
                                <h5 class="fw-bold text-white mb-0 text-truncate" title="${{p.name}}">${{p.name}}</h5>
                                <div class="text-success small text-truncate"><i class="fa-solid fa-shield-halved me-1"></i>${{p.current_club || 'Kulüpsüz'}}</div>
                            </div>
                        </div>

                        <!-- ScoutMe 4 Skills Radar Badges -->
                        <div class="row g-1 mb-2 text-center" style="font-size: 0.75rem;">
                            <div class="col-3">
                                <div style="background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 6px; padding: 3px 2px;">
                                    <span class="text-secondary d-block" style="font-size: 0.65rem;">FİZ</span>
                                    <strong class="text-primary">${{Math.round(p.skill_physical || 50)}}</strong>
                                </div>
                            </div>
                            <div class="col-3">
                                <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; padding: 3px 2px;">
                                    <span class="text-secondary d-block" style="font-size: 0.65rem;">ŞUT</span>
                                    <strong class="text-danger">${{Math.round(p.skill_shooting || 50)}}</strong>
                                </div>
                            </div>
                            <div class="col-3">
                                <div style="background: rgba(234, 179, 8, 0.15); border: 1px solid rgba(234, 179, 8, 0.3); border-radius: 6px; padding: 3px 2px;">
                                    <span class="text-secondary d-block" style="font-size: 0.65rem;">TEK</span>
                                    <strong class="text-warning">${{Math.round(p.skill_technical || 50)}}</strong>
                                </div>
                            </div>
                            <div class="col-3">
                                <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 6px; padding: 3px 2px;">
                                    <span class="text-secondary d-block" style="font-size: 0.65rem;">DEF</span>
                                    <strong class="text-success">${{Math.round(p.skill_defending || 50)}}</strong>
                                </div>
                            </div>
                        </div>

                        <!-- Match and Goal Statistics Grid -->
                        <div class="row g-2 mb-3">
                            <div class="col-3">
                                <div class="stat-badge-box">
                                    <div class="num text-warning">${{p.total_goals}}</div>
                                    <div class="label">Gol</div>
                                </div>
                            </div>
                            <div class="col-3">
                                <div class="stat-badge-box">
                                    <div class="num text-info">${{p.total_played}}</div>
                                    <div class="label">Maç</div>
                                </div>
                            </div>
                            <div class="col-3">
                                <div class="stat-badge-box">
                                    <div class="num text-success">${{p.total_starter}}</div>
                                    <div class="label">İlk 11</div>
                                </div>
                            </div>
                            <div class="col-3">
                                <div class="stat-badge-box">
                                    <div class="num text-secondary">${{p.total_sub_in}}</div>
                                    <div class="label">Sonradan</div>
                                </div>
                            </div>
                        </div>

                        <div class="small text-muted d-flex flex-column gap-1">
                            <div><i class="fa-solid fa-passport me-2 text-secondary"></i>Lisans: <span class="text-light">${{p.license_no || '-'}}</span></div>
                            <div><i class="fa-solid fa-cake-candles me-2 text-secondary"></i>D. Tarihi: <span class="text-light">${{p.birth_date || '-'}} (${{p.birth_place || '-'}})</span></div>
                            <div><i class="fa-solid fa-square text-warning me-1"></i>${{p.total_yellow}} Sarı &bull; <i class="fa-solid fa-square text-danger me-1"></i>${{p.total_red}} Kırmızı</div>
                        </div>

                        ${{p.seasons_list.length > 0 ? `
                        <div class="mt-2 pt-2 border-top border-secondary border-opacity-25">
                            <div class="small text-secondary mb-1">Sezon Dağılımı:</div>
                            <div class="d-flex flex-wrap gap-1">
                                ${{p.seasons_list.map(s => `
                                    <span class="badge bg-dark border border-secondary" style="font-size: 0.72rem;">
                                        ${{s.season}}: <strong>${{s.goals}}G</strong> / ${{s.total_played_matches}}M (${{s.starter_matches}} İlk11, ${{s.sub_in_matches}} Sonra, ${{s.bench_unused_matches}} Yedek)
                                    </span>
                                `).join('')}}
                            </div>
                        </div>
                        ` : ''}}
                    </div>

                    <div class="mt-3 pt-2 border-top border-secondary border-opacity-25 d-flex justify-content-between align-items-center">
                        <span class="badge bg-dark border border-secondary text-secondary">Yedek: ${{p.total_bench}}</span>
                        <span class="badge bg-success bg-opacity-25 text-success border border-success border-opacity-50">${{p.status || 'Aktif'}}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }}

    function renderClubs(list) {{
        const grid = document.getElementById('clubs-grid');
        grid.innerHTML = list.map(c => `
            <div class="col-12 col-md-6 col-lg-4 col-xl-3">
                <div class="box-card club-card">
                    <div>
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <span class="badge bg-primary bg-opacity-25 text-primary border border-primary border-opacity-50"><i class="fa-solid fa-location-dot me-1"></i>${{c.city || 'Kıbrıs'}}</span>
                            <span class="badge bg-dark border border-secondary">ID: ${{c.id}}</span>
                        </div>
                        <h5 class="fw-bold text-white mb-2">${{c.name}}</h5>
                        <div class="small text-muted d-flex flex-column gap-2 mb-3">
                            <div><i class="fa-solid fa-landmark me-2 text-secondary"></i>Stat: <span class="text-light">${{c.stadium_name || '-'}}</span></div>
                            <div><i class="fa-solid fa-user-tie me-2 text-secondary"></i>Başkan: <span class="text-light">${{c.president || '-'}}</span></div>
                            <div><i class="fa-solid fa-phone me-2 text-secondary"></i>Tel: <span class="text-light">${{c.phone || '-'}}</span></div>
                        </div>
                    </div>
                    <div class="mt-2 pt-2 border-top border-secondary border-opacity-25 d-flex justify-content-between align-items-center">
                        <span class="small text-secondary">Slug: ${{c.slug || '-'}}</span>
                        <span class="badge bg-primary">KTFF Kulübü</span>
                    </div>
                </div>
            </div>
        `).join('');
    }}

    function renderMatches(list) {{
        const grid = document.getElementById('matches-grid');
        grid.innerHTML = list.map(m => `
            <div class="col-12 col-md-6 col-lg-4">
                <div class="box-card match-card">
                    <div>
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span class="badge bg-danger bg-opacity-25 text-danger border border-danger border-opacity-50">${{m.league_name || 'Lig Maçı'}}</span>
                            <span class="text-muted small"><i class="fa-regular fa-clock me-1"></i>${{m.match_date || ''}} ${{m.match_time || ''}}</span>
                        </div>
                        
                        <div class="bg-dark p-3 rounded-3 text-center my-3 border border-secondary border-opacity-50">
                            <div class="row align-items-center">
                                <div class="col-5 text-truncate fw-bold text-white small">${{m.home_club}}</div>
                                <div class="col-2 fs-4 fw-bold text-warning">${{m.home_score !== null ? m.home_score : '-'}} - ${{m.away_score !== null ? m.away_score : '-'}}</div>
                                <div class="col-5 text-truncate fw-bold text-white small">${{m.away_club}}</div>
                            </div>
                        </div>

                        <div class="small text-muted d-flex flex-column gap-1">
                            <div><i class="fa-solid fa-landmark me-2 text-secondary"></i>Stat: <span class="text-light">${{m.stadium_name || '-'}}</span></div>
                            <div><i class="fa-solid fa-whistle me-2 text-secondary"></i>Hakem: <span class="text-light">${{m.referee || '-'}}</span></div>
                        </div>
                    </div>
                    <div class="mt-3 pt-2 border-top border-secondary border-opacity-25 d-flex justify-content-between align-items-center">
                        <span class="badge bg-dark border border-secondary text-secondary">KTFF ID: ${{m.ktff_match_id}}</span>
                        <span class="badge bg-secondary">${{m.status || 'Tamamlandı'}}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }}

    function renderCoaches(list) {{
        const grid = document.getElementById('coaches-grid');
        grid.innerHTML = list.map(ch => `
            <div class="col-12 col-md-6 col-lg-4 col-xl-3">
                <div class="box-card coach-card">
                    <div>
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <span class="badge bg-warning bg-opacity-25 text-warning border border-warning border-opacity-50">${{ch.role || 'Teknik Direktör'}}</span>
                            <span class="badge bg-dark border border-secondary">ID: ${{ch.ktff_coach_id || '-'}}</span>
                        </div>
                        <h5 class="fw-bold text-white mb-1">${{ch.name}}</h5>
                        <div class="text-warning small mb-3"><i class="fa-solid fa-shield-halved me-1"></i>${{ch.club_name || 'Serbest'}}</div>
                        
                        <div class="small text-muted d-flex flex-column gap-1">
                            <div><i class="fa-solid fa-id-card me-2 text-secondary"></i>Lisans: <span class="text-light">${{ch.license_no || '-'}}</span></div>
                            <div><i class="fa-solid fa-calendar me-2 text-secondary"></i>D. Tarihi: <span class="text-light">${{ch.birth_date || '-'}} (${{ch.birth_place || '-'}})</span></div>
                            <div><i class="fa-solid fa-flag me-2 text-secondary"></i>Uyruk: <span class="text-light">${{ch.nationality || 'KKTC'}}</span></div>
                        </div>
                    </div>
                    <div class="mt-3 pt-2 border-top border-secondary border-opacity-25 d-flex justify-content-between align-items-center">
                        <span class="small text-secondary">${{ch.gender || 'Erkek'}}</span>
                        <span class="badge bg-warning text-dark">Aktif Lisans</span>
                    </div>
                </div>
            </div>
        `).join('');
    }}

    renderPlayers(playersData);
    renderClubs(clubsData);
    renderMatches(matchesData);
    renderCoaches(coachesData);

    document.getElementById('search-input').addEventListener('input', function(e) {{
        const query = e.target.value.toLowerCase().trim();
        
        renderPlayers(playersData.filter(p => 
            (p.name && p.name.toLowerCase().includes(query)) ||
            (p.current_club && p.current_club.toLowerCase().includes(query)) ||
            (p.positions && p.positions.toLowerCase().includes(query)) ||
            (p.nationality && p.nationality.toLowerCase().includes(query))
        ));

        renderClubs(clubsData.filter(c => 
            (c.name && c.name.toLowerCase().includes(query)) ||
            (c.city && c.city.toLowerCase().includes(query)) ||
            (c.stadium_name && c.stadium_name.toLowerCase().includes(query))
        ));

        renderMatches(matchesData.filter(m => 
            (m.home_club && m.home_club.toLowerCase().includes(query)) ||
            (m.away_club && m.away_club.toLowerCase().includes(query)) ||
            (m.league_name && m.league_name.toLowerCase().includes(query))
        ));

        renderCoaches(coachesData.filter(ch => 
            (ch.name && ch.name.toLowerCase().includes(query)) ||
            (ch.club_name && ch.club_name.toLowerCase().includes(query)) ||
            (ch.role && ch.role.toLowerCase().includes(query))
        ));
    }});
</script>

</body>
</html>
"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_template)

print(f"SUCCESS: Generated updated visual boxes panel with season statistics at: {OUT_HTML}")
conn.close()
