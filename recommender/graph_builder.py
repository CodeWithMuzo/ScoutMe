"""
ScoutMe Heterogeneous Graph Builder
===================================
Constructs a heterogeneous graph connecting Players, Clubs, Coaches, and Scouts
from the KTFF SQLite database (data/ktff.db).

Node Types:
- Player: 16-dim feature vector (Competition-Calibrated Skills, OVR, Pos, Age, CI, Diff, Senior Ratio, etc.)
- Club (30 nodes): 12-dim feature vector (Senior Tier, A-Team Squad OVR, Skills, Position Ratios, Senior Goals)
- Coach (36 nodes): 8-dim feature vector (Style, Youth ratio, Aggressiveness, Tactical consistency)
- Scout (4 archetype nodes): 8-dim feature vector (Domain emphasis profiles)

Edge Types:
- (Player, plays_for, Club) & (Club, has_player, Player)
- (Player, coached_by, Coach) & (Coach, trains, Player)
- (Coach, manages, Club) & (Club, managed_by, Coach)
- (Player, teammate_with, Player)
- (Scout, recommends, Player) & (Player, scouted_by, Scout)
"""

import sqlite3
import numpy as np
import torch
from collections import defaultdict


def build_scoutme_graph(db_path='data/ktff.db'):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # ==========================================
    # 1. PLAYERS & PLAYER SKILLS EXTRACTION
    # ==========================================
    cur.execute('''
        SELECT 
            p.id, p.license_no, p.name, p.current_club, p.birth_date,
            p.position_category, p.primary_position,
            COALESCE(s.physical_score, p.skill_physical, 50.0),
            COALESCE(s.shooting_score, p.skill_shooting, 45.0),
            COALESCE(s.technical_score, p.skill_technical, 50.0),
            COALESCE(s.defending_score, p.skill_defending, 50.0),
            COALESCE(s.overall_rating, p.skill_overall, 50.0),
            COALESCE(s.ci_continuity_index, 0.5),
            COALESCE(s.on_pitch_diff_per90, 0.0),
            COALESCE(s.p90_goals, 0.0),
            COALESCE(s.total_played_matches, 0),
            COALESCE(s.clean_sheets, 0),
            COALESCE(s.age, 24),
            COALESCE(s.a_team_matches, 0),
            COALESCE(s.senior_minutes, 0),
            COALESCE(s.competition_factor, 0.5),
            COALESCE(s.total_goals, 0),
            COALESCE(s.starter_ratio, 0.5)
        FROM players p
        LEFT JOIN player_skills s ON p.id = s.player_id
        ORDER BY p.id
    ''')
    raw_players = cur.fetchall()

    player_id_to_idx = {}
    idx_to_player_id = {}
    player_license_to_idx = {}
    player_features = []
    player_metadata = {}

    for idx, row in enumerate(raw_players):
        (pid, lic, name, club, bdate, pos_cat, prim_pos,
         phys, shoot, tech, def_sc, ovr, ci, diff, p90_g, played_m,
         cs_cnt, age, a_team_matches, senior_minutes, comp_factor,
         total_goals, starter_ratio) = row

        player_id_to_idx[pid] = idx
        idx_to_player_id[idx] = pid
        if lic:
            player_license_to_idx[str(lic).strip()] = idx

        age = float(age) if age else 24.0
        a_team_matches = int(a_team_matches or 0)
        senior_minutes = int(senior_minutes or 0)
        comp_factor = float(comp_factor or 0.5)

        # One-hot position
        is_gk = 1.0 if pos_cat == 'GK' else 0.0
        is_df = 1.0 if pos_cat == 'DF' else 0.0
        is_mf = 1.0 if pos_cat == 'MF' else 0.0
        is_fw = 1.0 if pos_cat == 'FW' else 0.0

        # Normalized features (16 dimensions)
        # Note: Slot 15 encodes Competition Factor / Senior Provenness
        feat = [
            phys / 100.0,
            shoot / 100.0,
            tech / 100.0,
            def_sc / 100.0,
            ovr / 100.0,
            float(np.clip((age - 15.0) / 25.0, 0.0, 1.0)),
            is_gk, is_df, is_mf, is_fw,
            float(np.clip(p90_g / 1.2, 0.0, 1.0)),
            float(np.clip(ci, 0.0, 1.0)),
            float(np.clip((diff + 4.0) / 8.0, 0.0, 1.0)),
            float(np.clip(a_team_matches / 50.0, 0.0, 1.0)),
            float(np.clip(cs_cnt / 15.0, 0.0, 1.0)),
            float(np.clip(comp_factor, 0.0, 1.0))
        ]
        player_features.append(feat)

        player_metadata[idx] = {
            'player_id': pid,
            'license_no': lic,
            'name': name,
            'club_name': club,
            'age': int(age),
            'pos_cat': pos_cat or 'MF',
            'prim_pos': prim_pos or 'Orta Saha',
            'ovr': round(float(ovr), 1),
            'phys': round(float(phys), 1),
            'shoot': round(float(shoot), 1),
            'tech': round(float(tech), 1),
            'def': round(float(def_sc), 1),
            'ci': round(float(ci), 2),
            'starter_ratio': round(float(starter_ratio), 2),
            'diff': round(float(diff), 2),
            'p90_goals': round(float(p90_g), 2),
            'total_goals': int(total_goals or 0),
            'played_matches': int(played_m),
            'is_youth': bool(age <= 21.0),
            'a_team_matches': a_team_matches,
            'senior_minutes': senior_minutes,
            'competition_factor': round(comp_factor, 3)
        }

    # ==========================================
    # 2. CLUBS & SENIOR A-TEAM SQUAD METRICS
    # ==========================================
    cur.execute('''
        SELECT id, name, league_name, city, stadium_name
        FROM clubs
        ORDER BY id
    ''')
    raw_clubs = cur.fetchall()

    club_id_to_idx = {}
    idx_to_club_id = {}
    club_name_to_idx = {}
    club_metadata = {}

    for idx, (cid, cname, cleague, city, stadium) in enumerate(raw_clubs):
        club_id_to_idx[cid] = idx
        idx_to_club_id[idx] = cid
        clean_cname = cname.strip()
        club_name_to_idx[clean_cname] = idx
        club_metadata[idx] = {
            'club_id': cid,
            'name': clean_cname,
            'league_name': cleague,
            'city': city,
            'stadium': stadium,
            'is_super_lig': bool('Süper' in str(cleague) or 'Super' in str(cleague))
        }

    # Aggregate SENIOR A-Team squad metrics per club (only players with >= 3 A-Team matches)
    cur.execute('''
        SELECT 
            p.current_club,
            COUNT(*) as squad_size,
            AVG(s.overall_rating) as avg_ovr,
            AVG(s.physical_score) as avg_phys,
            AVG(s.shooting_score) as avg_shoot,
            AVG(s.technical_score) as avg_tech,
            AVG(s.defending_score) as avg_def,
            SUM(CASE WHEN p.position_category = 'GK' THEN 1 ELSE 0 END) as gk_cnt,
            SUM(CASE WHEN p.position_category = 'DF' THEN 1 ELSE 0 END) as df_cnt,
            SUM(CASE WHEN p.position_category = 'MF' THEN 1 ELSE 0 END) as mf_cnt,
            SUM(CASE WHEN p.position_category = 'FW' THEN 1 ELSE 0 END) as fw_cnt
        FROM players p
        JOIN player_skills s ON p.id = s.player_id
        WHERE s.a_team_matches >= 3
        GROUP BY p.current_club
    ''')
    squad_stats = {r[0].strip(): r[1:] for r in cur.fetchall() if r[0]}

    # SENIOR A-Team match goals aggregated per club (exclude A2 and U17 matches!)
    cur.execute('''
        SELECT home_club, SUM(home_score) as scored, SUM(away_score) as conceded, COUNT(*) as matches
        FROM matches 
        WHERE status = 'played' AND league_name IN ('AKSA Süper Lig', 'AKSA 1.Lig')
        GROUP BY home_club
    ''')
    home_matches = {r[0].strip(): (r[1] or 0, r[2] or 0, r[3] or 0) for r in cur.fetchall() if r[0]}

    cur.execute('''
        SELECT away_club, SUM(away_score) as scored, SUM(home_score) as conceded, COUNT(*) as matches
        FROM matches 
        WHERE status = 'played' AND league_name IN ('AKSA Süper Lig', 'AKSA 1.Lig')
        GROUP BY away_club
    ''')
    away_matches = {r[0].strip(): (r[1] or 0, r[2] or 0, r[3] or 0) for r in cur.fetchall() if r[0]}

    club_features = []
    for idx in range(len(raw_clubs)):
        cname = club_metadata[idx]['name']
        is_super = 1.0 if club_metadata[idx]['is_super_lig'] else 0.0

        sq = squad_stats.get(cname, (20, 64.0, 64.0, 55.0, 61.0, 64.0, 2, 6, 8, 4))
        (sq_size, avg_ovr, avg_phys, avg_shoot, avg_tech, avg_def, gk_c, df_c, mf_c, fw_c) = sq
        sq_size = max(1, sq_size)

        hm = home_matches.get(cname, (0, 0, 0))
        am = away_matches.get(cname, (0, 0, 0))
        total_m = max(1, hm[2] + am[2])
        goals_for_p90 = (hm[0] + am[0]) / total_m
        goals_against_p90 = (hm[1] + am[1]) / total_m

        club_metadata[idx].update({
            'avg_ovr': round(float(avg_ovr or 64.0), 1),
            'avg_phys': round(float(avg_phys or 64.0), 1),
            'avg_shoot': round(float(avg_shoot or 55.0), 1),
            'avg_tech': round(float(avg_tech or 61.0), 1),
            'avg_def': round(float(avg_def or 64.0), 1),
            'goals_for_p90': round(float(goals_for_p90), 2),
            'goals_against_p90': round(float(goals_against_p90), 2),
            'squad_size': int(sq_size)
        })

        feat = [
            is_super,
            (avg_ovr or 64.0) / 100.0,
            (avg_phys or 64.0) / 100.0,
            (avg_shoot or 55.0) / 100.0,
            (avg_tech or 61.0) / 100.0,
            (avg_def or 64.0) / 100.0,
            float(gk_c or 2) / sq_size,
            float(df_c or 6) / sq_size,
            float(mf_c or 8) / sq_size,
            float(fw_c or 4) / sq_size,
            float(np.clip(goals_for_p90 / 3.0, 0.0, 1.0)),
            float(np.clip(goals_against_p90 / 3.0, 0.0, 1.0))
        ]
        club_features.append(feat)

    # ==========================================
    # 3. COACHES EXTRACTION (DATA-DRIVEN FEATURES)
    # ==========================================
    cur.execute('''
        SELECT id, name, role, club_name, nationality, birth_date
        FROM coaches
        ORDER BY id
    ''')
    raw_coaches = cur.fetchall()

    # Compute club-specific youth senior usage ratio (how much A-team minutes U21 players get)
    club_u21_minutes_share = {}
    for c_idx, c_meta in club_metadata.items():
        cname = c_meta['name']
        tot_s_min = 0
        u21_s_min = 0
        for p_meta in player_metadata.values():
            if (p_meta.get('club_name') or '').strip() == cname:
                smin = p_meta.get('senior_minutes', 0)
                tot_s_min += smin
                if p_meta.get('is_youth', False):
                    u21_s_min += smin
        club_u21_minutes_share[c_idx] = (u21_s_min / max(1, tot_s_min)) if tot_s_min > 0 else 0.25

    coach_id_to_idx = {}
    idx_to_coach_id = {}
    coach_metadata = {}
    coach_features = []

    for idx, (tid, tname, trole, tclub, tnat, tbdate) in enumerate(raw_coaches):
        coach_id_to_idx[tid] = idx
        idx_to_coach_id[idx] = tid
        tclub_clean = tclub.strip() if tclub else ''
        club_idx = club_name_to_idx.get(tclub_clean, None)

        c_meta = club_metadata.get(club_idx, {})
        is_super = 1.0 if c_meta.get('is_super_lig', False) else 0.0
        g_for = c_meta.get('goals_for_p90', 1.5)
        g_against = c_meta.get('goals_against_p90', 1.5)
        u21_pref = float(np.clip(club_u21_minutes_share.get(club_idx, 0.25) * 2.5, 0.20, 0.95))
        avg_tech_c = c_meta.get('avg_tech', 61.0) / 100.0
        avg_def_c = c_meta.get('avg_def', 64.0) / 100.0
        avg_phys_c = c_meta.get('avg_phys', 64.0) / 100.0

        coach_metadata[idx] = {
            'coach_id': tid,
            'name': tname,
            'club_name': tclub_clean,
            'club_idx': club_idx,
            'role': trole,
            'is_super_lig': bool(is_super),
            'youth_preference': round(u21_pref, 2)
        }

        feat = [
            is_super,
            float(np.clip(g_for / 3.0, 0.0, 1.0)),
            float(np.clip(g_against / 3.0, 0.0, 1.0)),
            u21_pref,
            avg_tech_c,
            avg_def_c,
            avg_phys_c,
            1.0 if club_idx is not None else 0.0
        ]
        coach_features.append(feat)

    # ==========================================
    # 4. SCOUT ARCHETYPE NODES
    # ==========================================
    scout_archetypes = [
        {
            'id': 1, 'name': 'Scout Hücum & Bitiricilik', 'role': 'Offensive Scout',
            'desc': 'Forvet ve kanatlarda saf gol vuruşu, patlayıcılık ve ceza sahası önsezisini arar.',
            'feat': [0.2, 0.95, 0.7, 0.2, 0.85, 0.9, 0.5, 0.8]
        },
        {
            'id': 2, 'name': 'Scout Oyun Kurma & Metronom', 'role': 'Playmaker Scout',
            'desc': 'Orta saha ve merkezde pas kalitesi, saha içi skor averajı katkısı ve oyun vizyonunu değerlendirir.',
            'feat': [0.4, 0.5, 0.95, 0.5, 0.85, 0.3, 0.8, 0.9]
        },
        {
            'id': 3, 'name': 'Scout Defansif Kaya & Çapa', 'role': 'Defensive Anchor Scout',
            'desc': 'Stoper ve defansif beklerde yenilen gol azlığı, hava hakimiyeti ve kalesini gole kapatma başarısını inceler.',
            'feat': [0.8, 0.2, 0.4, 0.95, 0.80, 0.1, 0.9, 0.6]
        },
        {
            'id': 4, 'name': 'Scout Genç Gelişim & Dinamizm', 'role': 'Youth Development Scout',
            'desc': '21 yaş ve altı, süreklilik endeksi yüksek, takıma dinamizm katan geleceğin yıldız adaylarını tarar.',
            'feat': [0.85, 0.6, 0.7, 0.6, 0.70, 0.7, 0.95, 0.9]
        }
    ]

    scout_metadata = {}
    scout_features = []
    scout_id_to_idx = {}
    idx_to_scout_id = {}

    for s_idx, sc in enumerate(scout_archetypes):
        scout_id_to_idx[sc['id']] = s_idx
        idx_to_scout_id[s_idx] = sc['id']
        scout_metadata[s_idx] = sc
        scout_features.append(sc['feat'])

    # ==========================================
    # 5. EDGE EXTRACTION (RELATIONAL CONNECTIONS)
    # ==========================================

    # A) Player <-> Club edges (prefer Senior A-Team lineups + current_club)
    cur.execute('''
        SELECT l.license_no, l.club_name, m.league_name, COUNT(*) as match_count, SUM(l.minutes_played) as total_min
        FROM match_lineups l
        JOIN matches m ON l.match_id = m.id
        WHERE l.license_no IS NOT NULL AND l.club_name IS NOT NULL AND l.minutes_played > 0
        GROUP BY l.license_no, l.club_name, m.league_name
    ''')
    lineup_edges = cur.fetchall()

    player_club_edges = set()
    player_club_weights = {}

    for lic, cname, lname, cnt, m_sum in lineup_edges:
        lic_str = str(lic).strip()
        cname_clean = cname.strip()
        p_idx = player_license_to_idx.get(lic_str)
        c_idx = club_name_to_idx.get(cname_clean)
        if p_idx is not None and c_idx is not None:
            is_sen = lname in ('AKSA Süper Lig', 'AKSA 1.Lig')
            tier_mult = 1.0 if is_sen else 0.35
            weight = float(np.log1p((m_sum or (cnt * 60)) * tier_mult))
            player_club_edges.add((p_idx, c_idx))
            player_club_weights[(p_idx, c_idx)] = max(player_club_weights.get((p_idx, c_idx), 0.0), weight)

    # Add active current_club fallback
    for p_idx, p_meta in player_metadata.items():
        cname = (p_meta.get('club_name') or '').strip()
        c_idx = club_name_to_idx.get(cname)
        if c_idx is not None:
            player_club_edges.add((p_idx, c_idx))
            if (p_idx, c_idx) not in player_club_weights:
                player_club_weights[(p_idx, c_idx)] = 2.0

    # B) Coach <-> Club edges
    coach_club_edges = []
    for t_idx, t_meta in coach_metadata.items():
        c_idx = t_meta.get('club_idx')
        if c_idx is not None:
            coach_club_edges.append((t_idx, c_idx))

    # C) Player <-> Coach edges (through shared club, plus positive coach_evaluations if any!)
    player_coach_edges = set()
    for (p_idx, c_idx) in player_club_edges:
        for t_idx, c_edge_idx in coach_club_edges:
            if c_idx == c_edge_idx:
                player_coach_edges.add((p_idx, t_idx))

    # Incorporate Human-in-the-Loop (HITL) positive coach evaluations as direct graph edges
    try:
        cur.execute('''
            SELECT coach_name, club_name, player_id, decision, tactical_fit_rating
            FROM coach_evaluations
        ''')
        eval_rows = cur.fetchall()
        coach_name_to_idx = {m['name'].strip().upper(): idx for idx, m in coach_metadata.items()}
        for c_name, cl_name, pid, dec, tf_rating in eval_rows:
            p_idx = player_id_to_idx.get(pid)
            if p_idx is None:
                continue
            is_pos = ('Evet' in str(dec) or 'Takip' in str(dec) or (tf_rating and tf_rating >= 4))
            if is_pos:
                c_idx = club_name_to_idx.get((cl_name or '').strip())
                if c_idx is not None:
                    player_club_edges.add((p_idx, c_idx))
                t_idx = coach_name_to_idx.get((c_name or '').strip().upper())
                if t_idx is not None:
                    player_coach_edges.add((p_idx, t_idx))
    except sqlite3.OperationalError:
        pass

    player_coach_edges = list(player_coach_edges)

    # D) Player <-> Player (Teammate co-occurrence in SENIOR match lineups)
    cur.execute('''
        SELECT l.match_id, l.club_name, p.id as player_id
        FROM match_lineups l
        JOIN matches m ON l.match_id = m.id
        JOIN players p ON l.license_no = p.license_no
        WHERE l.minutes_played > 0 AND m.league_name IN ('AKSA Süper Lig', 'AKSA 1.Lig')
    ''')
    lineup_p_rows = cur.fetchall()
    match_club_players = defaultdict(list)
    for mid, cname, pid in lineup_p_rows:
        p_idx = player_id_to_idx.get(pid)
        if p_idx is not None:
            match_club_players[(mid, cname.strip())].append(p_idx)

    teammate_co_counts = defaultdict(int)
    for p_list in match_club_players.values():
        n = len(p_list)
        for i in range(n):
            for j in range(i + 1, n):
                u, v = sorted((p_list[i], p_list[j]))
                teammate_co_counts[(u, v)] += 1

    # Keep strong Senior teammate bonds (played together >= 3 Senior matches)
    player_teammate_edges = []
    for (u, v), co_c in teammate_co_counts.items():
        if co_c >= 3:
            player_teammate_edges.append((u, v))
            player_teammate_edges.append((v, u))

    # E) Scout <-> Player edges (Competition-Aware Qualitative Archetype Assignment)
    scout_player_edges = []
    for p_idx, p_meta in player_metadata.items():
        is_sen_proven = p_meta['a_team_matches'] >= 5
        # Scout 1 (Offensive): Proven senior high shoot or striker with good goals
        if is_sen_proven and (p_meta['shoot'] >= 72.0 or (p_meta['pos_cat'] == 'FW' and p_meta['p90_goals'] >= 0.30)):
            scout_player_edges.append((0, p_idx))
        # Scout 2 (Playmaker): Proven senior high tech or positive differential
        if is_sen_proven and (p_meta['tech'] >= 70.0 or (p_meta['pos_cat'] == 'MF' and p_meta['diff'] >= 0.8)):
            scout_player_edges.append((1, p_idx))
        # Scout 3 (Defensive): Proven senior high def or solid center back
        if is_sen_proven and (p_meta['def'] >= 74.0 or (p_meta['pos_cat'] in ('DF', 'GK') and p_meta['ovr'] >= 68.0)):
            scout_player_edges.append((2, p_idx))
        # Scout 4 (Youth): Age <= 21 with promising rating or A-Team minutes
        if p_meta['is_youth'] and (p_meta['a_team_matches'] >= 2 or p_meta['ovr'] >= 56.0):
            scout_player_edges.append((3, p_idx))

    conn.close()

    # Convert to PyTorch Tensors
    pc_list = list(player_club_edges)
    pc_weights = [player_club_weights.get(edge, 1.0) for edge in pc_list]

    graph_data = {
        'x_player': torch.tensor(player_features, dtype=torch.float32),
        'x_club': torch.tensor(club_features, dtype=torch.float32),
        'x_coach': torch.tensor(coach_features, dtype=torch.float32),
        'x_scout': torch.tensor(scout_features, dtype=torch.float32),

        # Edge indices [2, E]
        'edge_player_club': torch.tensor(pc_list, dtype=torch.long).t().contiguous() if pc_list else torch.zeros((2, 0), dtype=torch.long),
        'edge_club_player': torch.tensor([(c, p) for (p, c) in pc_list], dtype=torch.long).t().contiguous() if pc_list else torch.zeros((2, 0), dtype=torch.long),
        'edge_player_club_weight': torch.tensor(pc_weights, dtype=torch.float32) if pc_weights else torch.zeros((0,), dtype=torch.float32),

        'edge_coach_club': torch.tensor(coach_club_edges, dtype=torch.long).t().contiguous() if coach_club_edges else torch.zeros((2, 0), dtype=torch.long),
        'edge_club_coach': torch.tensor([(c, t) for (t, c) in coach_club_edges], dtype=torch.long).t().contiguous() if coach_club_edges else torch.zeros((2, 0), dtype=torch.long),

        'edge_player_coach': torch.tensor(player_coach_edges, dtype=torch.long).t().contiguous() if player_coach_edges else torch.zeros((2, 0), dtype=torch.long),
        'edge_coach_player': torch.tensor([(t, p) for (p, t) in player_coach_edges], dtype=torch.long).t().contiguous() if player_coach_edges else torch.zeros((2, 0), dtype=torch.long),

        'edge_player_teammate': torch.tensor(player_teammate_edges, dtype=torch.long).t().contiguous() if player_teammate_edges else torch.zeros((2, 0), dtype=torch.long),

        'edge_scout_player': torch.tensor(scout_player_edges, dtype=torch.long).t().contiguous() if scout_player_edges else torch.zeros((2, 0), dtype=torch.long),
        'edge_player_scout': torch.tensor([(p, s) for (s, p) in scout_player_edges], dtype=torch.long).t().contiguous() if scout_player_edges else torch.zeros((2, 0), dtype=torch.long),

        # Metadata
        'player_metadata': player_metadata,
        'club_metadata': club_metadata,
        'coach_metadata': coach_metadata,
        'scout_metadata': scout_metadata,
        'player_id_to_idx': player_id_to_idx,
        'idx_to_player_id': idx_to_player_id,
        'club_id_to_idx': club_id_to_idx,
        'idx_to_club_id': idx_to_club_id,
        'coach_id_to_idx': coach_id_to_idx,
        'idx_to_coach_id': idx_to_coach_id,
        'scout_id_to_idx': scout_id_to_idx,
        'idx_to_scout_id': idx_to_scout_id
    }

    return graph_data


if __name__ == '__main__':
    print('Testing ScoutMe Graph Builder...')
    g = build_scoutme_graph()
    print(f'[OK] Players Node Tensor : {g["x_player"].shape}')
    print(f'[OK] Clubs Node Tensor   : {g["x_club"].shape}')
    print(f'[OK] Coaches Node Tensor : {g["x_coach"].shape}')
    print(f'[OK] Scouts Node Tensor  : {g["x_scout"].shape}')
    print(f'[EDGE] Player-Club Edges : {g["edge_player_club"].shape[1]}')
    print(f'[EDGE] Coach-Club Edges  : {g["edge_coach_club"].shape[1]}')
    print(f'[EDGE] Player-Coach Edges: {g["edge_player_coach"].shape[1]}')
    print(f'[EDGE] Teammate Edges    : {g["edge_player_teammate"].shape[1]}')
    print(f'[EDGE] Scout-Player Edges: {g["edge_scout_player"].shape[1]}')
