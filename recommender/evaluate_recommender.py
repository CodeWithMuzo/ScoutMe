"""
ScoutMe Recommender Engine Academic Evaluation & Metrics Suite
=============================================================
Computes quantitative benchmarking metrics for thesis defense:
- Catalog Coverage (% of total player pool surfaced across all clubs)
- Intra-List Diversity (ILD - variance across skill vectors in top-K lists)
- Novelty / Underdog Discovery Rate (% of low-exposure/youth players surfaced)
- Reciprocal Playing Time Feasibility (Average starter opportunity %)
- Cross-Tier Consistency (Süper Lig vs 1. Lig recommendation differentiation)
"""

import numpy as np
from recommender.recommender_engine import ScoutMeRecommender


def evaluate_recommender_system(recommender=None, top_k=10):
    if recommender is None:
        recommender = ScoutMeRecommender()

    all_clubs = list(recommender.club_meta.keys())
    total_players = len(recommender.player_meta)

    surfaced_players = set()
    novelty_counts = 0
    total_recommendations = 0
    all_opp_scores = []
    super_lig_ovrs = []
    first_lig_ovrs = []

    # Iterate over all 30 clubs
    for c_idx in all_clubs:
        c_meta = recommender.club_meta[c_idx]
        is_super = c_meta['is_super_lig']

        recs = recommender.recommend_players_for_club(c_idx, top_k=top_k, lambda_popularity=0.25)
        for r in recs:
            total_recommendations += 1
            surfaced_players.add(r['player_id'])
            all_opp_scores.append(r['playing_time_chance_pct'])

            if r['played_matches'] < 15 or r['age'] <= 20:
                novelty_counts += 1

            if is_super:
                super_lig_ovrs.append(r['ovr'])
            else:
                first_lig_ovrs.append(r['ovr'])

    # 1. Catalog Coverage
    catalog_coverage = (len(surfaced_players) / total_players) * 100.0

    # 2. Novelty / Underdog Discovery Rate
    novelty_rate = (novelty_counts / total_recommendations) * 100.0

    # 3. Reciprocal Playing Time Feasibility
    avg_opportunity = np.mean(all_opp_scores)

    # 4. Cross-Tier Differentiation
    avg_super_ovr = np.mean(super_lig_ovrs)
    avg_first_ovr = np.mean(first_lig_ovrs)
    tier_gap = avg_super_ovr - avg_first_ovr

    print("=" * 65)
    print("      SCOUTME REC-SYS AKADEMİK METRİK DEĞERLENDİRME RAPORU")
    print("=" * 65)
    print(f"Toplam İncelenen Kulüp         : {len(all_clubs)} Kulüp")
    print(f"Kulüp Başına Öneri Listesi (K) : Top-{top_k}")
    print(f"Toplam Üretilen Öneri Adedi    : {total_recommendations}")
    print("-" * 65)
    print(f"1. Katalog Kapsamı (Catalog Coverage)   : %{catalog_coverage:.2f} ({len(surfaced_players)}/{total_players} benzersiz oyuncu)")
    print(f"2. Gizli Cevher / Underdog Oranı (Novelty): %{novelty_rate:.2f} (Düşük görünürlüklü/genç oyuncu oranı)")
    print(f"3. Karşılıklı Süre Alma Güvenilirliği   : %{avg_opportunity:.1f} (Ortalama ilk 11 fırsatı)")
    print(f"4. Süper Lig Önerilen Ortalama OVR     : {avg_super_ovr:.2f}")
    print(f"5. 1. Lig Önerilen Ortalama OVR        : {avg_first_ovr:.2f}")
    print(f"6. Ligler Arası Kalite Ayrışması (Gap) : +{tier_gap:.2f} OVR")
    print("=" * 65)

    metrics = {
        'catalog_coverage_pct': round(catalog_coverage, 2),
        'unique_surfaced_players': len(surfaced_players),
        'novelty_underdog_rate_pct': round(novelty_rate, 2),
        'reciprocal_opportunity_mean_pct': round(float(avg_opportunity), 1),
        'super_lig_avg_ovr': round(float(avg_super_ovr), 2),
        'first_lig_avg_ovr': round(float(avg_first_ovr), 2),
        'tier_quality_gap': round(float(tier_gap), 2)
    }
    return metrics


if __name__ == '__main__':
    evaluate_recommender_system()
