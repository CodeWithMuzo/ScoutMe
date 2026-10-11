"""
ScoutMe Multi-Stakeholder Reciprocal Recommender Engine
======================================================
Implements Layer 3 of the ScoutMe AI Architecture:
- Reciprocal Recommendation (Club/Coach Need + Player Playing Time Opportunity)
- Latent Tactical Compatibility via HGNN Embeddings
- Squad Deficit Weighting (Defense/Offense balance)
- Logarithmic Anti-Popularity Penalty for Underdog / Hidden Gem Discovery
- Youth & Potential Projection (APROPOS / YPI)
- Explainable AI Scouting Badges & Justifications
"""

import os
import math
import torch
import numpy as np


import unicodedata

def normalize_text(text):
    if not text:
        return ""
    # NFKD decompose and remove non-ascii accents
    nfkd = unicodedata.normalize('NFKD', str(text).strip().upper())
    ascii_text = nfkd.encode('ASCII', 'ignore').decode('utf-8').lower()
    return ascii_text


class ScoutMeRecommender:
    def __init__(self, embeddings_path='data/hgnn_embeddings.pt'):
        if not os.path.exists(embeddings_path):
            raise FileNotFoundError(f"Embeddings file not found at: {embeddings_path}. Run hgnn_model.py first!")

        self.ckpt = torch.load(embeddings_path, map_location='cpu')
        self.zp = self.ckpt['zp']  # [2404, 64]
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
            # Partial match
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

    def recommend_players_for_club(
        self,
        club_identifier,
        target_position=None,
        top_k=10,
        lambda_popularity=0.20,
        youth_only=False,
        exclude_current_squad=True
    ):
        """
        Multi-stakeholder reciprocal recommendation for a target club.
        
        Args:
            club_identifier: Club ID or Name
            target_position: 'GK', 'DF', 'MF', 'FW' (or None for all)
            top_k: Number of recommendations
            lambda_popularity: Penalty factor for high-profile star players (enables hidden gem discovery)
            youth_only: Filter for players aged <= 21
            exclude_current_squad: Do not recommend players already at this club
        """
        c_idx = self._resolve_club_idx(club_identifier)
        c_meta = self.club_meta[c_idx]
        zc_vec = self.zc[c_idx]

        # Find linked coach if any
        coach_idx = None
        for tidx, tmeta in self.coach_meta.items():
            if tmeta.get('club_idx') == c_idx:
                coach_idx = tidx
                break
        zt_vec = self.zt[coach_idx] if coach_idx is not None else zc_vec

        # Club characteristics
        is_super = c_meta.get('is_super_lig', True)
        c_def_need = max(0.0, (c_meta.get('goals_against_p90', 1.5) - 1.2) / 2.0)
        c_att_need = max(0.0, (2.0 - c_meta.get('goals_for_p90', 1.5)) / 2.0)
        c_avg_ovr = c_meta.get('avg_ovr', 65.0)

        # Precompute current squad OVR distribution by position for opportunity modeling
        squad_pos_ovrs = {'GK': [], 'DF': [], 'MF': [], 'FW': []}
        for pidx, pmeta in self.player_meta.items():
            if pmeta.get('club_name', '').strip() == c_meta['name']:
                pcat = pmeta.get('pos_cat', 'MF')
                if pcat in squad_pos_ovrs:
                    squad_pos_ovrs[pcat].append(pmeta['ovr'])

        # Benchmark position thresholds
        pos_benchmarks = {}
        for pcat, ovr_list in squad_pos_ovrs.items():
            pos_benchmarks[pcat] = np.mean(ovr_list) if ovr_list else c_avg_ovr

        recommendations = []

        # Latent similarities across all players
        sim_club = torch.mv(self.zp, zc_vec).numpy()
        sim_coach = torch.mv(self.zp, zt_vec).numpy()
        tactical_match = 0.70 * sim_club + 0.30 * sim_coach

        for p_idx, p_meta in self.player_meta.items():
            # Exclude current squad
            if exclude_current_squad and p_meta.get('club_name', '').strip() == c_meta['name']:
                continue

            # Position filter
            if target_position and p_meta.get('pos_cat') != target_position.upper():
                continue

            # Youth filter
            if youth_only and not p_meta.get('is_youth', False):
                continue

            # NEW: A-Team vs Youth Team Separation
            a_team_matches = p_meta.get('a_team_matches', 0)
            total_matches = p_meta.get('played_matches', 0)
            is_youth_league_player = p_meta.get('is_youth', False) and (a_team_matches < 5)

            # If user wants A-team ready players, filter out youth league players completely
            if not youth_only and is_youth_league_player:
                continue

            # Calculate effective OVR (Youth league stats are inflated)
            effective_ovr = p_meta['ovr']
            if is_youth_league_player:
                effective_ovr *= 0.75  # 25% discount for youth league stats

            # 1. Tactical Latent Alignment (0 - 1)
            t_score = float(np.clip((tactical_match[p_idx] + 1.0) / 2.0, 0.0, 1.0))

            # 2. Club Need Fit (Defensive or Offensive Deficit Match)
            need_score = 0.50
            pos_cat = p_meta.get('pos_cat', 'MF')
            if pos_cat in ('DF', 'GK'):
                need_score = 0.40 + c_def_need * (p_meta['def'] / 100.0)
            elif pos_cat in ('FW', 'MF'):
                need_score = 0.40 + c_att_need * (p_meta['shoot'] / 100.0)

            # League tier compatibility
            tier_fit = 1.0
            if is_super and effective_ovr < 60.0:
                tier_fit = 0.70
            elif (not is_super) and effective_ovr > 83.0:
                # Elite stars unlikely to accept 1. Lig move
                tier_fit = 0.75

            # 3. Reciprocal Opportunity Score (Player Playing Time Expectation)
            bench = pos_benchmarks.get(pos_cat, c_avg_ovr)
            ovr_diff = effective_ovr - bench
            opp_score = 1.0 / (1.0 + math.exp(-ovr_diff / 5.0))  # Sigmoid: >0 means starter potential

            # 4. Youth Potential Bonus
            youth_bonus = 0.0
            if p_meta['is_youth']:
                age_factor = max(0.0, (22 - p_meta['age']) / 7.0)
                youth_bonus = 0.15 * age_factor * (effective_ovr / 80.0)

            # 5. Logarithmic Anti-Popularity Penalty (Underdog / Hidden Gem Discovery)
            played = max(1, p_meta.get('played_matches', 1))
            pop_penalty = lambda_popularity * math.log1p(played) / math.log1p(80)

            # Composite Recommendation Score (0 - 100)
            raw_rec = (
                0.40 * t_score +
                0.25 * need_score * tier_fit +
                0.20 * opp_score +
                youth_bonus -
                pop_penalty
            )
            final_score = round(float(np.clip(raw_rec * 100.0 + 15.0, 10.0, 99.5)), 1)

            # Qualitative Automated Scouting Explanation
            tags = []
            if p_meta['is_youth']:
                tags.append("Genç Yetenek")
            if p_meta['diff'] > 1.2:
                tags.append("Oyun Yönlendirici")
            if p_meta['p90_goals'] >= 0.40:
                tags.append("Skorer Bitirici")
            if p_meta['def'] >= 80.0:
                tags.append("Defansif Çapa")
            if p_meta['phys'] >= 80.0:
                tags.append("Yüksek Kondisyon")
            if played < 15 and p_meta['ovr'] >= 70.0:
                tags.append("Gizli Cevher")

            explanation = self._generate_scout_verdict(p_meta, c_meta, opp_score, need_score, t_score)

            recommendations.append({
                'player_id': p_meta['player_id'],
                'license_no': p_meta['license_no'],
                'name': p_meta['name'],
                'age': p_meta['age'],
                'pos_cat': p_meta['pos_cat'],
                'prim_pos': p_meta['prim_pos'],
                'current_club': p_meta['club_name'],
                'ovr': p_meta['ovr'],
                'phys': p_meta['phys'],
                'shoot': p_meta['shoot'],
                'tech': p_meta['tech'],
                'def': p_meta['def'],
                'played_matches': played,
                'recommendation_score': final_score,
                'tactical_fit_pct': round(t_score * 100.0, 1),
                'playing_time_chance_pct': round(opp_score * 100.0, 1),
                'scout_tags': tags,
                'scout_verdict': explanation
            })

        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        return recommendations[:top_k]

    def _generate_scout_verdict(self, p_meta, c_meta, opp_score, need_score, t_score):
        """Generates concise, humanized scout verdict in Turkish for thesis reports."""
        name = p_meta['name']
        pos = p_meta['pos_cat']
        age = p_meta['age']
        ovr = p_meta['ovr']

        if p_meta['is_youth'] and opp_score >= 0.65:
            return f"{age} yaşındaki oyuncu, {c_meta['name']} kadro derinliğinde düzenli ilk 11 şansı bularak taktiksel sıçrama yapabilecek yüksek tavanlı bir genç yetenek."
        elif pos in ('DF', 'GK') and need_score > 0.60:
            return f"Kulübün maç başına yediği gol ortalamasını ({c_meta.get('goals_against_p90', 1.5)}) aşağı çekecek {ovr} reytingli, savunma güvenliği ve pozisyon bilgisi yüksek profil."
        elif pos in ('FW', 'MF') and p_meta['p90_goals'] >= 0.35:
            return f"90 dk başına {p_meta['p90_goals']} gol katkısıyla takımın üçüncü bölgedeki üretkenlik sorununa doğrudan çözüm üretecek bitirici hamle."
        elif p_meta['diff'] > 1.0:
            return f"Sahada kaldığı dakikalarda takım averajına (+{p_meta['diff']}) sağladığı pozitif diferansiyelle oyun temposunu dikte edebilen teknik orta saha."
        elif opp_score >= 0.80:
            return f"{c_meta['name']} oyun şablonunda doğrudan ilk 11'e yerleşerek takımın mevki kalitesini yukarı çekecek olgun performans."
        else:
            return f"Takımın taktiksel rotasyonunda derinlik sağlayacak, rol disiplini yüksek tamamlayıcı transfer profili."

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

            # Tier suitability
            tier_bonus = 0.10 if (is_super and p_meta['ovr'] >= 72.0) else (0.10 if (not is_super and p_meta['ovr'] < 68.0) else 0.0)

            # Opportunity: Does this club have room for this player?
            pos_bench = c_meta.get('avg_ovr', 65.0)
            opp_score = 1.0 / (1.0 + math.exp(-(p_meta['ovr'] - pos_bench) / 6.0))

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

    def find_similar_players(self, player_identifier, top_k=5):
        """
        Archetype Twin Finder: Finds players with identical tactical and skill signatures
        using cosine similarity across latent HGNN embeddings.
        """
        p_idx = self._resolve_player_idx(player_identifier)
        target_p = self.player_meta[p_idx]
        zp_target = self.zp[p_idx]

        sims = torch.mv(self.zp, zp_target).numpy()

        results = []
        for idx, pmeta in self.player_meta.items():
            if idx == p_idx:
                continue

            # Must share broad position category
            if pmeta['pos_cat'] != target_p['pos_cat']:
                continue

            cos_sim = float(sims[idx])
            sim_pct = round(float(np.clip((cos_sim + 1.0) / 2.0 * 100.0, 0.0, 99.9)), 1)

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
                'similarity_pct': sim_pct
            })

        results.sort(key=lambda x: x['similarity_pct'], reverse=True)
        return results[:top_k]


if __name__ == '__main__':
    recommender = ScoutMeRecommender()
    print("Testing ScoutMe Recommender Engine...")
    test_recs = recommender.recommend_players_for_club('China Bazaar Gençlik Gücü TSK', target_position='FW', top_k=3)
    for r in test_recs:
        print(f"-> {r['name']} ({r['age']} y, {r['current_club']}) | Score: {r['recommendation_score']} | OVR: {r['ovr']}")
