"""
ScoutMe Multi-Stakeholder Reciprocal Recommender Engine
======================================================
Implements Layer 3 of the ScoutMe AI Architecture:
- Competition-Level Calibrated Scoring (AKSA Süper Lig, 1.Lig, A2, U17 separation)
- Reciprocal Recommendation (Club/Coach Need + Senior Squad Playing Time Opportunity)
- Latent Tactical & Archetype Compatibility via HGNN Embeddings (zp, zc, zt, zs)
- Tactical Formation, Sub-Position & Player Archetype Dynamic Weighting
- Human-in-the-Loop (HITL) Coach Evaluation Feedback Integration
- Logarithmic Anti-Popularity Penalty for Underdog / Hidden Gem Discovery
- Explainable AI Scouting Badges & Justifications
"""

import os
import math
import sqlite3
import unicodedata
import torch
import numpy as np


def normalize_text(text):
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(text).strip().upper())
    ascii_text = nfkd.encode('ASCII', 'ignore').decode('utf-8').lower()
    return ascii_text


class ScoutMeRecommender:
    def __init__(self, embeddings_path='data/hgnn_embeddings.pt', db_path='data/ktff.db'):
        if not os.path.exists(embeddings_path):
            raise FileNotFoundError(f"Embeddings file not found at: {embeddings_path}. Run hgnn_model.py first!")

        self.db_path = db_path
        self.ckpt = torch.load(embeddings_path, map_location='cpu', weights_only=False)
        self.zp = self.ckpt['zp']  # [N_p, 64]
        self.zc = self.ckpt['zc']  # [30, 64]
        self.zt = self.ckpt['zt']  # [36, 64]
        self.zs = self.ckpt['zs']  # [4, 64]

        self.player_meta = self.ckpt['player_metadata']
        self.club_meta = self.ckpt['club_metadata']
        self.coach_meta = self.ckpt['coach_metadata']
        self.scout_meta = self.ckpt['scout_metadata']

        self.club_id_to_idx = self.ckpt['club_id_to_idx']
        self.idx_to_club_id = self.ckpt['idx_to_club_id']
        self.player_id_to_idx = self.ckpt['player_id_to_idx']
        self.idx_to_player_id = self.ckpt['idx_to_player_id']

        # Normalized lookup maps
        self.club_norm_to_idx = {
            normalize_text(meta['name']): idx for idx, meta in self.club_meta.items()
        }
        self.player_norm_to_idx = {
            normalize_text(meta['name']): idx for idx, meta in self.player_meta.items()
        }
        self.coach_norm_to_idx = {
            normalize_text(meta['name']): idx for idx, meta in self.coach_meta.items()
        }

    def _resolve_club_idx(self, club_identifier):
        if isinstance(club_identifier, int):
            if club_identifier in self.club_id_to_idx:
                return self.club_id_to_idx[club_identifier]
            if club_identifier in self.club_meta:
                return club_identifier
        elif isinstance(club_identifier, str):
            clean = normalize_text(club_identifier)
            if clean in self.club_norm_to_idx:
                return self.club_norm_to_idx[clean]
            for name, idx in self.club_norm_to_idx.items():
                if clean in name or name in clean:
                    return idx
        raise ValueError(f"Club '{club_identifier}' not found in database!")

    def _resolve_player_idx(self, player_identifier):
        if isinstance(player_identifier, int):
            if player_identifier in self.player_id_to_idx:
                return self.player_id_to_idx[player_identifier]
            if player_identifier in self.player_meta:
                return player_identifier
        elif isinstance(player_identifier, str):
            clean = normalize_text(player_identifier)
            if clean in self.player_norm_to_idx:
                return self.player_norm_to_idx[clean]
            for name, idx in self.player_norm_to_idx.items():
                if clean in name or name in clean:
                    return idx
        raise ValueError(f"Player '{player_identifier}' not found in database!")

    def _resolve_coach_idx(self, coach_identifier, fallback_club_idx=None):
        if coach_identifier and isinstance(coach_identifier, str):
            clean = normalize_text(coach_identifier)
            if clean in self.coach_norm_to_idx:
                return self.coach_norm_to_idx[clean]
            for name, idx in self.coach_norm_to_idx.items():
                if clean and (clean in name or name in clean):
                    return idx
        if fallback_club_idx is not None:
            for tidx, tmeta in self.coach_meta.items():
                if tmeta.get('club_idx') == fallback_club_idx:
                    return tidx
        return None

    def _load_hitl_feedback(self, club_name):
        """
        Loads Human-in-the-Loop (HITL) coach evaluation adjustments from ktff.db.
        Returns dict: player_id -> score delta (-0.15 to +0.10).
        """
        adjustments = {}
        if not os.path.exists(self.db_path):
            return adjustments
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('''
                SELECT player_id, club_name, decision, tactical_fit_rating, feasibility_rating
                FROM coach_evaluations
            ''')
            for pid, ev_club, dec, tf_r, feas_r in cur.fetchall():
                same_club = normalize_text(ev_club) == normalize_text(club_name)
                weight = 1.0 if same_club else 0.35
                dec_str = str(dec or '')
                if 'Hayır' in dec_str or 'Uygun Değil' in dec_str:
                    adjustments[pid] = adjustments.get(pid, 0.0) - 0.14 * weight
                elif 'Evet' in dec_str:
                    adjustments[pid] = adjustments.get(pid, 0.0) + 0.06 * weight
                elif 'Takip' in dec_str:
                    adjustments[pid] = adjustments.get(pid, 0.0) + 0.03 * weight
            conn.close()
        except Exception:
            pass
        return adjustments

    def _compute_archetype_and_formation_fit(self, p_meta, sim_scouts_p, formation=None, sub_position=None, archetype=None):
        """
        Computes tactical role & archetype compatibility (0.0 - 1.0) based on:
        - Selected player archetype (e.g., Target Man, Poacher, Playmaker, Box-to-Box, Ball-Playing CB)
        - Selected tactical formation (e.g., 4-3-3, 4-2-3-1, 3-5-2)
        - Selected sub-position (e.g., CB vs LB/RB, CDM vs CAM, ST vs Winger)
        - HGNN Scout Archetype latent alignment (sim_scouts_p)
        """
        phys = p_meta['phys'] / 100.0
        shoot = p_meta['shoot'] / 100.0
        tech = p_meta['tech'] / 100.0
        def_s = p_meta['def'] / 100.0
        p90_g = min(1.0, p_meta.get('p90_goals', 0.0) / 0.55)
        diff_n = float(np.clip((p_meta.get('diff', 0.0) + 2.0) / 5.0, 0.0, 1.0))
        prim_pos = str(p_meta.get('prim_pos', '')).lower()
        pos_cat = p_meta.get('pos_cat', 'MF')

        # Default balanced skill score by broad category
        if pos_cat == 'FW':
            role_score = 0.45 * shoot + 0.25 * phys + 0.25 * tech + 0.05 * def_s
            scout_idx = 0
        elif pos_cat == 'MF':
            role_score = 0.40 * tech + 0.25 * phys + 0.20 * def_s + 0.15 * shoot
            scout_idx = 1
        elif pos_cat == 'DF':
            role_score = 0.50 * def_s + 0.30 * phys + 0.15 * tech + 0.05 * shoot
            scout_idx = 2
        else:  # GK
            role_score = 0.55 * def_s + 0.30 * phys + 0.15 * tech
            scout_idx = 2

        arch_str = normalize_text(archetype) if archetype else ""
        sub_str = normalize_text(sub_position) if sub_position else ""
        form_str = str(formation or "")

        # Fine-grained Archetype Skill Matching
        if arch_str:
            if "hedef santrafor" in arch_str or "hava" in arch_str:
                role_score = 0.45 * phys + 0.40 * shoot + 0.15 * p90_g
                scout_idx = 0
            elif "kontratak" in arch_str or "patlayici" in arch_str:
                role_score = 0.45 * phys + 0.35 * shoot + 0.20 * tech
                scout_idx = 0
            elif "poacher" in arch_str or "ceza sahasi" in arch_str or "bitirici" in arch_str:
                role_score = 0.55 * shoot + 0.30 * p90_g + 0.15 * phys
                scout_idx = 0
            elif "sahte 9" in arch_str or "baglanti" in arch_str:
                role_score = 0.50 * tech + 0.30 * shoot + 0.20 * diff_n
                scout_idx = 1
            elif "inverted" in arch_str or "skorer kanat" in arch_str:
                role_score = 0.42 * shoot + 0.38 * tech + 0.20 * phys
                scout_idx = 0
            elif "cizgiye inen" in arch_str or "orta tehdidi" in arch_str:
                role_score = 0.45 * tech + 0.40 * phys + 0.15 * shoot
                scout_idx = 1
            elif "pres gucu" in arch_str or "caliskan kanat" in arch_str:
                role_score = 0.50 * phys + 0.25 * def_s + 0.25 * tech
                scout_idx = 3
            elif "oyun kurucu" in arch_str or "metronom" in arch_str or "yaratici 10" in arch_str:
                role_score = 0.55 * tech + 0.25 * diff_n + 0.20 * shoot
                scout_idx = 1
            elif "iki yonlu" in arch_str or "box to box" in arch_str or "dinamo" in arch_str:
                role_score = 0.45 * phys + 0.30 * tech + 0.25 * def_s
                scout_idx = 1
            elif "defansif capa" in arch_str or "kesici" in arch_str:
                role_score = 0.55 * def_s + 0.30 * phys + 0.15 * tech
                scout_idx = 2
            elif "regista" in arch_str or "derin oyun kurucu" in arch_str:
                role_score = 0.48 * tech + 0.35 * def_s + 0.17 * diff_n
                scout_idx = 1
            elif "sert lider stoper" in arch_str:
                role_score = 0.55 * def_s + 0.35 * phys + 0.10 * tech
                scout_idx = 2
            elif "pasor stoper" in arch_str or "topla cikan" in arch_str:
                role_score = 0.42 * def_s + 0.40 * tech + 0.18 * diff_n
                scout_idx = 1
            elif "cabuk stoper" in arch_str or "kademe" in arch_str:
                role_score = 0.48 * phys + 0.42 * def_s + 0.10 * tech
                scout_idx = 2
            elif "bindirmeci" in arch_str or "dinamik bek" in arch_str:
                role_score = 0.45 * phys + 0.30 * tech + 0.25 * def_s
                scout_idx = 3
            elif "pozisyonel bek" in arch_str or "savunma oncelikli" in arch_str:
                role_score = 0.58 * def_s + 0.28 * phys + 0.14 * tech
                scout_idx = 2
            elif "sweeper" in arch_str or "ayakli" in arch_str:
                role_score = 0.45 * def_s + 0.35 * tech + 0.20 * phys
                scout_idx = 2

        # Sub-position match bonus (e.g. Stoper vs Bek, Ön Libero vs 10 Numara, Santrafor vs Kanat)
        sub_bonus = 0.0
        if sub_str:
            if ("stoper" in sub_str or "cb" in sub_str) and ("stoper" in prim_pos):
                sub_bonus = 0.05
            elif ("bek" in sub_str or "lb" in sub_str) and ("bek" in prim_pos):
                sub_bonus = 0.05
            elif ("libero" in sub_str or "cdm" in sub_str) and ("libero" in prim_pos or def_s >= 0.70):
                sub_bonus = 0.05
            elif ("merkez" in sub_str or "ofansif" in sub_str) and ("10" in prim_pos or "merkez" in prim_pos or "orta" in prim_pos):
                sub_bonus = 0.04
            elif ("kanat" in sub_str or "winger" in sub_str) and ("kanat" in prim_pos or (tech >= 0.68 and phys >= 0.68)):
                sub_bonus = 0.05
            elif ("santrafor" in sub_str) and ("santrafor" in prim_pos or "forvet" in prim_pos):
                sub_bonus = 0.04

        # Formation synergy adjustment
        form_bonus = 0.0
        if "3-5-2" in form_str or "3-4-3" in form_str:
            # 3-at-the-back demands higher physical stamina & defensive coverage
            form_bonus = 0.03 * phys + 0.02 * def_s
        elif "4-3-3" in form_str or "4-2-3-1" in form_str:
            # Fluid attacking formations reward technical & transition output
            form_bonus = 0.03 * tech + 0.02 * shoot
        elif "4-4-2" in form_str or "4-1-4-1" in form_str:
            # Structured two-bank formations reward positional continuity & physicality
            form_bonus = 0.03 * p_meta.get('ci', 0.6) + 0.02 * phys

        scout_sim = float(np.clip((sim_scouts_p[scout_idx] + 1.0) / 2.0, 0.0, 1.0))
        combined = float(np.clip(0.75 * role_score + 0.25 * scout_sim + sub_bonus + form_bonus, 0.0, 1.0))
        return combined

    def recommend_players_for_club(
        self,
        club_identifier,
        target_position=None,
        top_k=10,
        lambda_popularity=0.20,
        youth_only=False,
        exclude_current_squad=True,
        formation=None,
        sub_position_label=None,
        player_archetype=None,
        coach_identifier=None
    ):
        """
        Multi-stakeholder competition-calibrated reciprocal recommendation for a target club.

        Args:
            club_identifier: Club ID or Name
            target_position: 'GK', 'DF', 'MF', 'FW' (or None for all)
            top_k: Number of recommendations
            lambda_popularity: Penalty factor for high-exposure players (enables hidden gem discovery)
            youth_only: Filter for U21 prospects (aged <= 21)
            exclude_current_squad: Do not recommend players already at this club
            formation: Optional tactical formation string (e.g. '4-3-3')
            sub_position_label: Optional detailed position label (e.g. 'Stoper / Savunma (CB)')
            player_archetype: Optional tactical archetype string
            coach_identifier: Optional Coach Name or ID
        """
        c_idx = self._resolve_club_idx(club_identifier)
        c_meta = self.club_meta[c_idx]
        zc_vec = self.zc[c_idx]

        # Resolve target coach embedding
        coach_idx = self._resolve_coach_idx(coach_identifier, fallback_club_idx=c_idx)
        zt_vec = self.zt[coach_idx] if coach_idx is not None else zc_vec

        # Club characteristics (computed on Senior A-Team matches & squad)
        is_super = c_meta.get('is_super_lig', True)
        c_def_need = max(0.0, (c_meta.get('goals_against_p90', 1.5) - 1.15) / 1.8)
        c_att_need = max(0.0, (1.95 - c_meta.get('goals_for_p90', 1.5)) / 1.8)
        c_avg_ovr = c_meta.get('avg_ovr', 64.0)

        # Precompute current SENIOR A-Team squad OVR distribution by position for opportunity modeling
        squad_pos_ovrs = {'GK': [], 'DF': [], 'MF': [], 'FW': []}
        for pidx, pmeta in self.player_meta.items():
            if (pmeta.get('club_name') or '').strip() == c_meta['name']:
                # Only count real Senior A-Team players in the club's benchmark!
                if pmeta.get('a_team_matches', 0) >= 3:
                    pcat = pmeta.get('pos_cat', 'MF')
                    if pcat in squad_pos_ovrs:
                        squad_pos_ovrs[pcat].append(pmeta['ovr'])

        pos_benchmarks = {}
        for pcat, ovr_list in squad_pos_ovrs.items():
            if ovr_list:
                # Top-half starter average in that position
                sorted_ovrs = sorted(ovr_list, reverse=True)
                starter_slice = sorted_ovrs[:max(2, len(sorted_ovrs) // 2)]
                pos_benchmarks[pcat] = float(np.mean(starter_slice))
            else:
                pos_benchmarks[pcat] = c_avg_ovr

        # Latent similarities across all players
        sim_club = torch.mv(self.zp, zc_vec).numpy()
        sim_coach = torch.mv(self.zp, zt_vec).numpy()
        sim_scouts = torch.mm(self.zp, self.zs.t()).numpy()  # [N_p, 4]
        tactical_match = 0.65 * sim_club + 0.35 * sim_coach

        # Human-in-the-Loop feedback adjustments
        hitl_map = self._load_hitl_feedback(c_meta['name'])

        candidates = []

        for p_idx, p_meta in self.player_meta.items():
            # 1. Exclude current squad
            if exclude_current_squad and (p_meta.get('club_name') or '').strip() == c_meta['name']:
                continue

            # 2. Position filter
            if target_position and p_meta.get('pos_cat') != target_position.upper():
                continue

            age = p_meta.get('age', 24)
            is_youth = p_meta.get('is_youth', age <= 21)
            a_team_matches = p_meta.get('a_team_matches', 0)
            senior_minutes = p_meta.get('senior_minutes', 0)
            total_matches = p_meta.get('played_matches', 0)
            comp_factor = p_meta.get('competition_factor', 0.5)
            ovr = p_meta['ovr']

            # -----------------------------------------------------------------
            # STRICT A-TEAM VS YOUTH LEAGUE SEPARATION & COMPETITION FILTERING
            # -----------------------------------------------------------------
            if not youth_only:
                # Standard A-Team Transfer Mode:
                # Never recommend 15, 16, 17-year-old youth league players or players without A-Team proof!
                if age < 18 and (a_team_matches < 10 or senior_minutes < 600):
                    continue
                if a_team_matches < 5 or senior_minutes < 225:
                    continue
            else:
                # U21 Youth Discovery Mode (Yaş <= 21):
                if not is_youth:
                    continue
                if total_matches < 4:
                    continue
                # For 15-17 year olds with 0 A-team matches, require strong youth productivity
                # but evaluate them with their true competition factor
                if age <= 17 and a_team_matches == 0 and total_matches < 10:
                    continue

            # 1. Tactical & Archetype Alignment (0 - 1)
            base_t_score = float(np.clip((tactical_match[p_idx] + 1.0) / 2.0, 0.0, 1.0))
            arch_fit = self._compute_archetype_and_formation_fit(
                p_meta, sim_scouts[p_idx],
                formation=formation,
                sub_position=sub_position_label,
                archetype=player_archetype
            )
            t_score = 0.55 * base_t_score + 0.45 * arch_fit

            # 2. Club Need & Quality Fit (Defense/Offense Deficit + Competition Tier Calibration)
            pos_cat = p_meta.get('pos_cat', 'MF')
            if pos_cat in ('DF', 'GK'):
                need_score = 0.42 + c_def_need * (p_meta['def'] / 100.0)
            else:
                need_score = 0.42 + c_att_need * (max(p_meta['shoot'], p_meta['tech']) / 100.0)

            # League Tier & Competition Realism Factor
            tier_fit = 1.0
            if not youth_only:
                if is_super:
                    if ovr < 62.0:
                        tier_fit = 0.72
                    elif ovr >= 72.0:
                        tier_fit = 1.06
                else:
                    # 1. Lig target club: elite Süper Lig stars (>79 OVR) are less likely to drop down
                    if ovr > 79.0:
                        tier_fit = 0.72
                    elif 60.0 <= ovr <= 74.0:
                        tier_fit = 1.06
            else:
                # In U21 mode, reward U21 players who HAVE proven themselves in Senior A-Team matches!
                if a_team_matches >= 10:
                    tier_fit = 1.15
                elif a_team_matches >= 3:
                    tier_fit = 1.02
                elif age <= 17:
                    # 15-17 yo pure youth league players have lower immediate A-Team readiness
                    tier_fit = 0.74
                else:
                    tier_fit = 0.84

            # 3. Reciprocal Opportunity Score (Player Playing Time Expectation against Senior Starters)
            bench = pos_benchmarks.get(pos_cat, c_avg_ovr)
            ovr_diff = ovr - bench
            opp_score = 1.0 / (1.0 + math.exp(-ovr_diff / 5.0))

            # 4. Competition-Calibrated Quality & Potential Factor
            # Directly ties recommendation score to competition-adjusted OVR and comp_factor
            quality_norm = float(np.clip((ovr - 45.0) / 42.0, 0.0, 1.0)) * (0.65 + 0.35 * comp_factor)

            youth_bonus = 0.0
            if is_youth and a_team_matches >= 5:
                # Proven U21 A-Team talent bonus
                youth_bonus = 0.07 * min(1.0, a_team_matches / 20.0)
            elif youth_only and is_youth:
                youth_bonus = 0.04 * comp_factor

            # 5. Logarithmic Anti-Popularity Penalty (Applied on Senior A-Team exposure)
            exposure_matches = max(1, a_team_matches if not youth_only else total_matches)
            pop_penalty = lambda_popularity * math.log1p(exposure_matches) / math.log1p(65)

            # 6. Human-in-the-Loop (HITL) Coach Feedback Adjustment
            hitl_delta = hitl_map.get(p_meta['player_id'], 0.0)

            # Composite Recommendation Score (0 - 100)
            raw_rec = (
                0.34 * t_score +
                0.24 * quality_norm * tier_fit +
                0.22 * need_score * tier_fit +
                0.20 * opp_score +
                youth_bonus +
                hitl_delta -
                pop_penalty
            )
            final_score = round(float(np.clip(raw_rec * 100.0 + 14.0, 10.0, 98.5)), 1)

            # Competition & Scouting Tags
            tags = []
            if a_team_matches >= 15:
                tags.append(f"A-Takım ({a_team_matches} Maç)")
            elif a_team_matches >= 5:
                tags.append(f"A-Takım Rotasyon ({a_team_matches} Maç)")
            else:
                tags.append("Alt Yapı / A2 Havuzu")

            if is_youth and a_team_matches >= 5:
                tags.append("U21 A-Takım Yeteneği")
            elif is_youth:
                tags.append("U21 Gelişim Adayı")

            if p_meta['diff'] >= 0.8 and a_team_matches >= 5:
                tags.append("Oyun Yönlendirici")
            if p_meta['p90_goals'] >= 0.32 and a_team_matches >= 5:
                tags.append("Skorer Bitirici")
            if p_meta['def'] >= 76.0 and a_team_matches >= 5:
                tags.append("Defansif Çapa")
            if p_meta['phys'] >= 78.0 and a_team_matches >= 5:
                tags.append("Yüksek Kondisyon")
            if 5 <= a_team_matches <= 16 and ovr >= 66.0:
                tags.append("Gizli Cevher")

            explanation = self._generate_scout_verdict(
                p_meta, c_meta, opp_score, need_score, t_score,
                formation=formation, archetype=player_archetype
            )

            candidates.append({
                'player_id': p_meta['player_id'],
                'license_no': p_meta['license_no'],
                'name': p_meta['name'],
                'age': age,
                'pos_cat': p_meta['pos_cat'],
                'prim_pos': p_meta['prim_pos'],
                'current_club': p_meta['club_name'],
                'ovr': ovr,
                'phys': p_meta['phys'],
                'shoot': p_meta['shoot'],
                'tech': p_meta['tech'],
                'def': p_meta['def'],
                'played_matches': total_matches,
                'a_team_matches': a_team_matches,
                'senior_minutes': senior_minutes,
                'competition_factor': comp_factor,
                'recommendation_score': final_score,
                'tactical_fit_pct': round(t_score * 100.0, 1),
                'playing_time_chance_pct': round(opp_score * 100.0, 1),
                'scout_tags': tags,
                'scout_verdict': explanation
            })

        candidates.sort(key=lambda x: x['recommendation_score'], reverse=True)

        # Club Diversity Re-Ranking (Max 2 players from the exact same club in Top-K if pool allows)
        selected = []
        overflow = []
        club_counts = {}
        max_per_club = max(2, top_k // 3)
        for cand in candidates:
            c_src = cand['current_club']
            if club_counts.get(c_src, 0) < max_per_club:
                selected.append(cand)
                club_counts[c_src] = club_counts.get(c_src, 0) + 1
                if len(selected) >= top_k:
                    break
            else:
                overflow.append(cand)

        if len(selected) < top_k:
            selected.extend(overflow[:top_k - len(selected)])

        return selected[:top_k]

    def _generate_scout_verdict(self, p_meta, c_meta, opp_score, need_score, t_score, formation=None, archetype=None):
        """Generates concise, competition-aware scout verdict in Turkish."""
        pos = p_meta['pos_cat']
        age = p_meta['age']
        ovr = p_meta['ovr']
        a_matches = p_meta.get('a_team_matches', 0)
        form_txt = f"{formation} dizilişinde " if formation else ""

        if p_meta['is_youth'] and a_matches >= 5:
            return (
                f"{age} yaşında olmasına rağmen A-Takım seviyesinde {a_matches} maça çıkarak üst lig sertliğini "
                f"kanıtlamış ({ovr} OVR), {c_meta['name']} {form_txt}ilk 11 potansiyeli yüksek genç yetenek."
            )
        elif p_meta['is_youth'] and a_matches < 5:
            return (
                f"{age} yaşındaki oyuncu alt yaş / A2 kategorilerindeki istatistikleriyle öne çıkıyor; "
                f"rekabet seviyesi farkı nedeniyle ({ovr} OVR) A-Takım rotasyonuna kademeli gelişim adayı olarak dahil edilebilir."
            )
        elif pos in ('DF', 'GK') and need_score > 0.58:
            return (
                f"A-Takım seviyesinde {a_matches} maçlık tecrübesi ve {ovr} reytingiyle, kulübün maç başına yediği "
                f"gol ortalamasını ({c_meta.get('goals_against_p90', 1.5)}) aşağı çekecek savunma lideri."
            )
        elif pos in ('FW', 'MF') and p_meta['p90_goals'] >= 0.30:
            return (
                f"A-Takım rekabet seviyesinde 90 dk başına {p_meta['p90_goals']} gol katkısı üreten, "
                f"{form_txt}üçüncü bölgedeki bitiricilik ihtiyacına doğrudan çözüm sunacak skorer profil."
            )
        elif p_meta['diff'] >= 0.8:
            return (
                f"A-Takım maçlarında sahada kaldığı sürede takım averajına (+{p_meta['diff']}) sağladığı "
                f"net katkıyla {form_txt}oyun temposunu yönlendirebilen {ovr} OVR'li merkez profili."
            )
        elif opp_score >= 0.72:
            return (
                f"{c_meta['name']} A-Takım oyun şablonunda ({form_txt.strip() or 'mevcut sistem'}) doğrudan "
                f"ilk 11'e yerleşerek mevki kalitesini yukarı çekecek ({a_matches} A-Takım maçı) olgun performans."
            )
        else:
            return (
                f"A-Takım düzeyinde {a_matches} maç tecrübesiyle takımın taktiksel rotasyonunda "
                f"süreklilik ve rol disiplini sağlayacak tamamlayıcı transfer adayı."
            )

    def recommend_clubs_for_player(self, player_identifier, top_k=5):
        """
        Reciprocal view: Which clubs are optimal for this player's career and playing time?
        """
        p_idx = self._resolve_player_idx(player_identifier)
        p_meta = self.player_meta[p_idx]
        zp_vec = self.zp[p_idx]

        sim_clubs = torch.mv(self.zc, zp_vec).numpy()

        results = []
        for c_idx, c_meta in self.club_meta.items():
            if c_meta['name'] == p_meta.get('club_name'):
                continue

            t_score = float(np.clip((sim_clubs[c_idx] + 1.0) / 2.0, 0.0, 1.0))
            is_super = c_meta['is_super_lig']

            # Tier suitability based on competition-calibrated OVR
            tier_bonus = 0.10 if (is_super and p_meta['ovr'] >= 70.0) else (0.10 if (not is_super and p_meta['ovr'] < 68.0) else 0.0)

            # Opportunity: Does this club have room for this player in its Senior A-Team?
            pos_bench = c_meta.get('avg_ovr', 64.0)
            opp_score = 1.0 / (1.0 + math.exp(-(p_meta['ovr'] - pos_bench) / 5.5))

            suitability = round(float(np.clip((0.45 * t_score + 0.35 * opp_score + tier_bonus) * 100.0, 10.0, 99.0)), 1)

            results.append({
                'club_id': c_meta['club_id'],
                'club_name': c_meta['name'],
                'league_name': c_meta['league_name'],
                'city': c_meta['city'],
                'suitability_score': suitability,
                'playing_time_probability': round(opp_score * 100.0, 1),
                'tactical_match': round(t_score * 100.0, 1)
            })

        results.sort(key=lambda x: x['suitability_score'], reverse=True)
        return results[:top_k]

    def find_similar_players(self, player_identifier, top_k=5, senior_only=True):
        """
        Archetype Twin Finder: Finds players with identical tactical and skill signatures
        using cosine similarity across latent HGNN embeddings and competition tier parity.
        """
        p_idx = self._resolve_player_idx(player_identifier)
        target_p = self.player_meta[p_idx]
        zp_target = self.zp[p_idx]

        sims = torch.mv(self.zp, zp_target).numpy()
        target_is_senior = target_p.get('a_team_matches', 0) >= 5

        results = []
        for idx, pmeta in self.player_meta.items():
            if idx == p_idx:
                continue

            if pmeta['pos_cat'] != target_p['pos_cat']:
                continue

            # If target player is a Senior A-Team player, only match with other Senior A-Team players
            if senior_only and target_is_senior and pmeta.get('a_team_matches', 0) < 5:
                continue

            cos_sim = float(sims[idx])
            # Penalize large OVR disparities so an 82-OVR star is matched with similar-caliber players
            ovr_gap_penalty = abs(target_p['ovr'] - pmeta['ovr']) * 0.008
            adj_sim = cos_sim - ovr_gap_penalty
            sim_pct = round(float(np.clip((adj_sim + 1.0) / 2.0 * 100.0, 0.0, 99.5)), 1)

            results.append({
                'player_id': pmeta['player_id'],
                'license_no': pmeta['license_no'],
                'name': pmeta['name'],
                'current_club': pmeta['club_name'],
                'age': pmeta['age'],
                'pos_cat': pmeta['pos_cat'],
                'prim_pos': pmeta['prim_pos'],
                'ovr': pmeta['ovr'],
                'phys': pmeta['phys'],
                'shoot': pmeta['shoot'],
                'tech': pmeta['tech'],
                'def': pmeta['def'],
                'a_team_matches': pmeta.get('a_team_matches', 0),
                'similarity_pct': sim_pct
            })

        results.sort(key=lambda x: x['similarity_pct'], reverse=True)
        return results[:top_k]


if __name__ == '__main__':
    recommender = ScoutMeRecommender()
    print("Testing ScoutMe Recommender Engine (Competition-Calibrated)...")
    test_recs = recommender.recommend_players_for_club('China Bazaar Gençlik Gücü TSK', target_position='FW', top_k=5)
    for r in test_recs:
        print(
            f"-> {r['name']} ({r['age']}y, {r['current_club']}) | "
            f"Score: {r['recommendation_score']} | OVR: {r['ovr']} | A-Takım Maç: {r['a_team_matches']}"
        )
