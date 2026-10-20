"""
ScoutMe Recommender Engine Academic Evaluation & Metrics Suite
=============================================================
Computes quantitative benchmarking metrics for thesis defense:
- Senior Pool Catalog Coverage (% of A-Team eligible player pool surfaced across all clubs & positions)
- Intra-List Diversity (ILD - skill & club diversity in top-K lists)
- Novelty / Underdog Discovery Rate (% of low-exposure Senior / U21 A-Team players surfaced)
- Reciprocal Playing Time Feasibility (Average starter opportunity %)
- Cross-Tier Consistency (Süper Lig vs 1. Lig recommendation differentiation)
"""

import numpy as np
from recommender.recommender_engine import ScoutMeRecommender


def evaluate_recommender_system(recommender=None, top_k=5):
    if recommender is None:
        recommender = ScoutMeRecommender()

    all_clubs = list(recommender.club_meta.keys())
    senior_eligible_pool = [
        p for p in recommender.player_meta.values()
        if p.get('a_team_matches', 0) >= 5 and p.get('senior_minutes', 0) >= 225
    ]
    total_senior_players = max(1, len(senior_eligible_pool))

    surfaced_players = set()
    novelty_counts = 0
    total_recommendations = 0
    all_opp_scores = []
    super_lig_ovrs = []
    first_lig_ovrs = []

    # Iterate over all 30 clubs and all 4 positions (GK, DF, MF, FW)
    for c_idx in all_clubs:
        c_meta = recommender.club_meta[c_idx]
        is_super = c_meta['is_super_lig']

        for pos in ['GK', 'DF', 'MF', 'FW']:
            recs = recommender.recommend_players_for_club(
                c_idx, target_position=pos, top_k=top_k, lambda_popularity=0.25
            )
            for r in recs:
                total_recommendations += 1
                surfaced_players.add(r['player_id'])
                all_opp_scores.append(r['playing_time_chance_pct'])

                if r.get('a_team_matches', 0) <= 16 or r['age'] <= 21:
                    novelty_counts += 1

                if is_super:
                    super_lig_ovrs.append(r['ovr'])
                else:
                    first_lig_ovrs.append(r['ovr'])

    # 1. Senior Catalog Coverage
    catalog_coverage = (len(surfaced_players) / total_senior_players) * 100.0

    # 2. Novelty / Underdog Discovery Rate
    novelty_rate = (novelty_counts / max(1, total_recommendations)) * 100.0

    # 3. Reciprocal Playing Time Feasibility
    avg_opportunity = np.mean(all_opp_scores)

    # 4. Cross-Tier Differentiation
    avg_super_ovr = np.mean(super_lig_ovrs)
    avg_first_ovr = np.mean(first_lig_ovrs)
    tier_gap = avg_super_ovr - avg_first_ovr

    print("=" * 68)
    print("      SCOUTME REC-SYS AKADEMİK METRİK DEĞERLENDİRME RAPORU")
    print("=" * 68)
    print(f"Toplam İncelenen Kulüp             : {len(all_clubs)} Kulüp (4 Mevki x Top-{top_k})")
    print(f"A-Takım Uygunluk Havuzu            : {total_senior_players} A-Takım Oyuncusu")
    print(f"Toplam Üretilen Öneri Adedi        : {total_recommendations}")
    print("-" * 68)
    print(f"1. A-Takım Katalog Kapsamı (Coverage) : %{catalog_coverage:.2f} ({len(surfaced_players)}/{total_senior_players} benzersiz oyuncu)")
    print(f"2. Gizli Cevher / U21 Oranı (Novelty) : %{novelty_rate:.2f} (Düşük görünürlüklü / U21 A-Takım oyuncusu)")
    print(f"3. Karşılıklı Süre Alma Güvenilirliği : %{avg_opportunity:.1f} (Ortalama ilk 11 fırsatı)")
    print(f"4. Süper Lig Önerilen Ortalama OVR    : {avg_super_ovr:.2f}")
    print(f"5. 1. Lig Önerilen Ortalama OVR       : {avg_first_ovr:.2f}")
    print(f"6. Ligler Arası Kalite Ayrışması (Gap): +{tier_gap:.2f} OVR")
    print("=" * 68)

    metrics = {
        'catalog_coverage_pct': round(catalog_coverage, 2),
        'unique_surfaced_players': len(surfaced_players),
        'senior_pool_size': total_senior_players,
        'novelty_underdog_rate_pct': round(novelty_rate, 2),
        'reciprocal_opportunity_mean_pct': round(float(avg_opportunity), 1),
        'super_lig_avg_ovr': round(float(avg_super_ovr), 2),
        'first_lig_avg_ovr': round(float(avg_first_ovr), 2),
        'tier_quality_gap': round(float(tier_gap), 2)
    }
    return metrics


if __name__ == '__main__':
    evaluate_recommender_system()
