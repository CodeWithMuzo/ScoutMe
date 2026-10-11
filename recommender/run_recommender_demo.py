"""
ScoutMe Recommender Engine CLI Demo & Comprehensive Showcase
============================================================
Runs comprehensive multi-stakeholder recommendation scenarios for KTFF clubs,
coaches, and scouts, and generates an interactive HTML report.

Scenarios:
1. Süper Lig Contender (China Bazaar GG) -> Striker (FW) Need
2. Title Challenger (Mağusa Türk Gücü) -> Center-Back / Defending (DF) Need
3. Tactical Playmaker Search (Cihangir GSK) -> Midfield (MF) Need
4. Underdog / Hidden Gem Discovery (Log Popularity Penalty in Action)
5. Youth Talent Scouting (16 <= Age <= 21) -> Rising Stars with High Upside
6. Reciprocal Career Path (Club Recommendations for Player)
7. Archetype Twin Finder (Finding Similar Profiles to League Icons)
"""

import os
import json
from recommender.recommender_engine import ScoutMeRecommender


def format_player_summary(p):
    tags_str = ", ".join(p['scout_tags']) if p['scout_tags'] else "Standart Profil"
    return (
        f"  #{p['name']} ({p['pos_cat']} - {p['prim_pos']}, {p['age']} y, {p['current_club']})\n"
        f"     • OVR: {p['ovr']} | [FİZ: {p['phys']} | ŞUT: {p['shoot']} | TEK: {p['tech']} | DEF: {p['def']}]\n"
        f"     • Öneri Skoru: {p['recommendation_score']}/100 | Taktik Uyum: %{p['tactical_fit_pct']} | Oynama Şansı: %{p['playing_time_chance_pct']}\n"
        f"     • Rozetler: [{tags_str}]\n"
        f"     • Scout Görüşü: \"{p['scout_verdict']}\"\n"
    )


def generate_html_report(showcase_data, output_path='scoutme_recommender_report.html'):
    """Generates a responsive modern HTML report with cards and badges."""
    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScoutMe - Çok Paydaşlı Öneri Motoru Vitrini</title>
    <style>
        :root {{
            --bg: #0b0f19;
            --surface: #131b2e;
            --surface-hover: #1b2640;
            --border: #22304d;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent-green: #10b981;
            --accent-blue: #3b82f6;
            --accent-gold: #f59e0b;
            --accent-purple: #8b5cf6;
            --accent-red: #ef4444;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background-color: var(--bg); color: var(--text-primary); padding: 30px 20px; line-height: 1.5; }}
        .container {{ max-width: 1300px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 40px; padding: 25px; background: linear-gradient(135deg, #131b2e 0%, #1e293b 100%); border-radius: 16px; border: 1px solid var(--border); }}
        .header h1 {{ font-size: 2.2rem; font-weight: 800; color: #38bdf8; margin-bottom: 8px; letter-spacing: -0.5px; }}
        .header p {{ color: var(--text-secondary); font-size: 1.05rem; }}
        .badge-bar {{ display: flex; justify-content: center; gap: 15px; margin-top: 15px; flex-wrap: wrap; }}
        .stat-pill {{ background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); color: #38bdf8; padding: 5px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }}
        
        .section-title {{ font-size: 1.4rem; font-weight: 700; margin: 35px 0 15px 0; color: #f8fafc; border-left: 4px solid var(--accent-blue); padding-left: 12px; display: flex; align-items: center; justify-content: space-between; }}
        .section-desc {{ color: var(--text-secondary); font-size: 0.92rem; margin-bottom: 18px; margin-top: -8px; }}
        
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; }}
        .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: transform 0.2s, border-color 0.2s; position: relative; }}
        .card:hover {{ transform: translateY(-3px); border-color: #3b82f6; background: var(--surface-hover); }}
        
        .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }}
        .player-name {{ font-size: 1.15rem; font-weight: 700; color: #ffffff; }}
        .player-meta {{ font-size: 0.85rem; color: var(--text-secondary); margin-top: 2px; }}
        .score-box {{ text-align: center; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 10px; padding: 6px 12px; }}
        .score-val {{ font-size: 1.4rem; font-weight: 800; color: var(--accent-green); line-height: 1; }}
        .score-label {{ font-size: 0.65rem; text-transform: uppercase; color: #6ee7b7; font-weight: 700; letter-spacing: 0.5px; }}

        .ovr-pill {{ display: inline-block; background: #2563eb; color: #fff; font-weight: 800; padding: 3px 8px; border-radius: 6px; font-size: 0.85rem; margin-right: 6px; }}
        .pos-badge {{ display: inline-block; background: #334155; color: #e2e8f0; font-weight: 700; padding: 3px 8px; border-radius: 6px; font-size: 0.82rem; }}

        .skills-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 14px 0; background: rgba(0, 0, 0, 0.25); padding: 10px; border-radius: 8px; }}
        .skill-item {{ text-align: center; }}
        .skill-num {{ font-size: 1.05rem; font-weight: 700; color: #f1f5f9; }}
        .skill-name {{ font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; }}

        .progress-block {{ margin-bottom: 12px; }}
        .progress-label {{ display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 4px; }}
        .progress-bar-bg {{ background: #1e293b; height: 6px; border-radius: 3px; overflow: hidden; }}
        .progress-bar-fill {{ height: 100%; border-radius: 3px; }}
        .fill-blue {{ background: linear-gradient(90deg, #3b82f6, #60a5fa); }}
        .fill-green {{ background: linear-gradient(90deg, #10b981, #34d399); }}

        .tags-container {{ display: flex; gap: 6px; flex-wrap: wrap; margin: 12px 0 10px 0; }}
        .tag {{ font-size: 0.72rem; font-weight: 600; padding: 2px 8px; border-radius: 4px; background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.35); color: #c4b5fd; }}
        .tag.gem {{ background: rgba(245, 158, 11, 0.15); border-color: rgba(245, 158, 11, 0.4); color: #fbbf24; }}
        .tag.youth {{ background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.4); color: #6ee7b7; }}

        .scout-verdict {{ font-size: 0.82rem; color: #cbd5e1; background: rgba(30, 41, 59, 0.7); border-left: 3px solid var(--accent-gold); padding: 8px 10px; border-radius: 0 6px 6px 0; font-style: italic; margin-top: 10px; }}

        .twin-card {{ display: flex; justify-content: space-between; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; }}
        .twin-name {{ font-weight: 700; font-size: 0.95rem; color: #fff; }}
        .twin-sub {{ font-size: 0.8rem; color: var(--text-secondary); }}
        .twin-pct {{ font-size: 1.1rem; font-weight: 800; color: #38bdf8; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SCOUTME | ÇOK PAYDAŞLI KARŞILIKLI ÖNERİ MOTORU</h1>
            <p>Heterojen Graf Sinir Ağı (HGNN) & Sentetik Spor Analitiği Tabanlı Futbolcu ve Kulüp Eşleştirme Vitrini</p>
            <div class="badge-bar">
                <span class="stat-pill">2.404 Futbolcu Graf Düğümü</span>
                <span class="stat-pill">30 A Takım Kulübü</span>
                <span class="stat-pill">36 A Takım Teknik Direktörü</span>
                <span class="stat-pill">4 Scout Arketipi</span>
                <span class="stat-pill">Karşılıklı Sıralama (Reciprocal RecSys)</span>
                <span class="stat-pill">Logaritmik Popülarite Cezası</span>
            </div>
        </div>
"""

    for section in showcase_data['sections']:
        html += f"""
        <div class="section-title">
            <span>{section['title']}</span>
            <span style="font-size:0.85rem; font-weight:500; color:var(--text-secondary);">{section.get('badge', '')}</span>
        </div>
        <div class="section-desc">{section['desc']}</div>
        """

        if section['type'] == 'players':
            html += '<div class="grid">'
            for p in section['items']:
                tags_html = ""
                for t in p['scout_tags']:
                    cls = "tag"
                    if "Gizli" in t or "Cevher" in t:
                        cls += " gem"
                    elif "Genç" in t:
                        cls += " youth"
                    tags_html += f'<span class="{cls}">{t}</span>'

                html += f"""
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div>
                                <span class="ovr-pill">{p['ovr']}</span>
                                <span class="pos-badge">{p['prim_pos']}</span>
                            </div>
                            <div class="player-name" style="margin-top:6px;">{p['name']}</div>
                            <div class="player-meta">{p['age']} Yaş &bull; {p['current_club']}</div>
                        </div>
                        <div class="score-box">
                            <div class="score-val">{p['recommendation_score']}</div>
                            <div class="score-label">Öneri Skoru</div>
                        </div>
                    </div>

                    <div class="skills-row">
                        <div class="skill-item">
                            <div class="skill-num">{p['phys']}</div>
                            <div class="skill-name">Fizik</div>
                        </div>
                        <div class="skill-item">
                            <div class="skill-num">{p['shoot']}</div>
                            <div class="skill-name">Şut</div>
                        </div>
                        <div class="skill-item">
                            <div class="skill-num">{p['tech']}</div>
                            <div class="skill-name">Teknik</div>
                        </div>
                        <div class="skill-item">
                            <div class="skill-num">{p['def']}</div>
                            <div class="skill-name">Defans</div>
                        </div>
                    </div>

                    <div class="progress-block">
                        <div class="progress-label">
                            <span>Taktiksel Sistem Uyumu</span>
                            <span style="font-weight:700; color:#60a5fa;">%{p['tactical_fit_pct']}</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill fill-blue" style="width: {p['tactical_fit_pct']}%;"></div>
                        </div>
                    </div>

                    <div class="progress-block">
                        <div class="progress-label">
                            <span>İlk 11 Oynama & Süre Alma Olasılığı</span>
                            <span style="font-weight:700; color:#34d399;">%{p['playing_time_chance_pct']}</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill fill-green" style="width: {p['playing_time_chance_pct']}%;"></div>
                        </div>
                    </div>

                    <div class="tags-container">{tags_html}</div>

                    <div class="scout-verdict">
                        "{p['scout_verdict']}"
                    </div>
                </div>
                """
            html += '</div>'

        elif section['type'] == 'twins':
            html += '<div style="max-width:800px; margin: 0 auto;">'
            for item in section['items']:
                html += f"""
                <div class="twin-card">
                    <div>
                        <div class="twin-name">{item['name']} <span class="pos-badge" style="font-size:0.75rem; margin-left:6px;">{item['prim_pos']}</span></div>
                        <div class="twin-sub">{item['age']} Yaş &bull; {item['current_club']} &bull; OVR: {item['ovr']}</div>
                    </div>
                    <div style="text-align:right;">
                        <div class="twin-pct">%{item['similarity_pct']}</div>
                        <div style="font-size:0.7rem; color:var(--text-secondary); text-transform:uppercase;">Taktiksel Eşleşme</div>
                    </div>
                </div>
                """
            html += '</div>'

        elif section['type'] == 'clubs':
            html += '<div class="grid">'
            for c in section['items']:
                html += f"""
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="player-name">{c['club_name']}</div>
                            <div class="player-meta">{c['league_name']} &bull; {c['city']}</div>
                        </div>
                        <div class="score-box">
                            <div class="score-val">{c['suitability_score']}</div>
                            <div class="score-label">Uygunluk</div>
                        </div>
                    </div>
                    <div class="progress-block" style="margin-top:12px;">
                        <div class="progress-label">
                            <span>Oyuncu İçin Oynama Fırsatı</span>
                            <span style="font-weight:700; color:#34d399;">%{c['playing_time_probability']}</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill fill-green" style="width: {c['playing_time_probability']}%;"></div>
                        </div>
                    </div>
                    <div class="progress-block">
                        <div class="progress-label">
                            <span>Taktiksel Kimya</span>
                            <span style="font-weight:700; color:#60a5fa;">%{c['tactical_match']}</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill fill-blue" style="width: {c['tactical_match']}%;"></div>
                        </div>
                    </div>
                </div>
                """
            html += '</div>'

    html += """
        <div style="text-align:center; margin-top:50px; padding:20px; color:var(--text-secondary); font-size:0.85rem; border-top: 1px solid var(--border);">
            ScoutMe Yüksek Lisans Tez Projesi &bull; Doğu Akdeniz Üniversitesi (DAÜ / EMU) Bilgisayar Mühendisliği &bull; 2026
        </div>
    </div>
</body>
</html>
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[REPORT] Interactive showcase HTML report saved to: {output_path}")


def main():
    print("=" * 65)
    print("      SCOUTME MULTI-STAKEHOLDER RECOMMENDATION ENGINE DEMO")
    print("=" * 65)

    rec = ScoutMeRecommender()
    showcase = {'sections': []}

    # =========================================================================
    # SCENARIO 1: China Bazaar GG (Süper Lig Zirve Takımı) -> Forvet (FW) Arayışı
    # =========================================================================
    club_name = 'China Bazaar Gençlik Gücü TSK'
    print(f"\n[SENARYO 1] {club_name} İçin Forvet (FW) Transfer Önerileri:")
    fw_recs = rec.recommend_players_for_club(club_name, target_position='FW', top_k=4)
    for p in fw_recs:
        print(format_player_summary(p))

    showcase['sections'].append({
        'title': f'{club_name} — Forvet (FW) Transfer Önerileri',
        'desc': 'Zirve yarışı veren Süper Lig ekibinin ofansif bitiricilik ve skor katkısını maksimize edecek hedef santrafor önerileri.',
        'badge': 'Süper Lig &bull; Forvet',
        'type': 'players',
        'items': fw_recs
    })

    # =========================================================================
    # SCENARIO 2: Mağusa Türk Gücü -> Stoper / Savunma (DF) Arayışı
    # =========================================================================
    club_name = 'Mağusa Türk Gücü'
    print(f"\n[SENARYO 2] {club_name} İçin Defans (DF) Transfer Önerileri:")
    df_recs = rec.recommend_players_for_club(club_name, target_position='DF', top_k=4)
    for p in df_recs:
        print(format_player_summary(p))

    showcase['sections'].append({
        'title': f'{club_name} — Defans (DF) Takviye Önerileri',
        'desc': 'Şampiyonluk yarışında savunma güvenliği ve kalesini gole kapatma başarısını yükseltecek stoper ve lider savunmacı adayları.',
        'badge': 'Süper Lig &bull; Savunma',
        'type': 'players',
        'items': df_recs
    })

    # =========================================================================
    # SCENARIO 3: Cihangir GSK -> Oyun Kurucu & Metronom (MF) Arayışı
    # =========================================================================
    club_name = 'Cihangir GSK'
    print(f"\n[SENARYO 3] {club_name} İçin Orta Saha (MF) Transfer Önerileri:")
    mf_recs = rec.recommend_players_for_club(club_name, target_position='MF', top_k=4)
    for p in mf_recs:
        print(format_player_summary(p))

    showcase['sections'].append({
        'title': f'{club_name} — Orta Saha / Oyun Kurucu (MF) Önerileri',
        'desc': 'Saha içi pozitif skor averajı katkısı (On-Pitch Differential) ve teknik pas vizyonu yüksek merkez orta saha önerileri.',
        'badge': 'Süper Lig &bull; Orta Saha',
        'type': 'players',
        'items': mf_recs
    })

    # =========================================================================
    # SCENARIO 4: Gizli Cevher Keşfi (Underdog / Hidden Gems with High Lambda)
    # =========================================================================
    club_name = 'Düzkaya KOSK'
    print(f"\n[SENARYO 4] {club_name} (1. Lig) — Gizli Cevher & Düşük Maliyetli Oyuncular (Lambda=0.45):")
    gem_recs = rec.recommend_players_for_club(club_name, top_k=4, lambda_popularity=0.45)
    for p in gem_recs:
        print(format_player_summary(p))

    showcase['sections'].append({
        'title': f'{club_name} (1. Lig) — Gizli Cevherler (Underdog Discovery)',
        'desc': 'Yüksek popülarite cezası (Lambda=0.45) uygulanarak ligin çok bilinen yıldızları yerine radar altı kalmış, yüksek potansiyelli ve bütçe dostu oyuncuların keşfi.',
        'badge': '1. Lig &bull; Gizli Cevher',
        'type': 'players',
        'items': gem_recs
    })

    # =========================================================================
    # SCENARIO 5: Genç Yetenek Avı (Youth Scouting: 16 <= Age <= 21)
    # =========================================================================
    club_name = 'Alsancak Yeşilova SK'
    print(f"\n[SENARYO 5] {club_name} İçin Genç Yetenekler (Youth Scouting, Age <= 21):")
    youth_recs = rec.recommend_players_for_club(club_name, youth_only=True, top_k=4)
    for p in youth_recs:
        print(format_player_summary(p))

    showcase['sections'].append({
        'title': f'{club_name} — Geleceğin Yıldızları (Youth Scouting: Yaş ≤ 21)',
        'desc': 'APROPOS gelişim eğrisine göre önümüzdeki 2-3 sezonda en yüksek piyasa değeri ve taktiksel sıçrama potansiyeline sahip genç yetenekler.',
        'badge': 'Genç Yetenekler (U21)',
        'type': 'players',
        'items': youth_recs
    })

    # =========================================================================
    # SCENARIO 6: Kariyer Planlama (Futbolcu İçin En Uygun Kulüpler)
    # =========================================================================
    player_target = 'OUSMANE DIABY'
    print(f"\n[SENARYO 6] {player_target} İçin Kariyer ve Oynama Süresi En Uygun Kulüpler:")
    club_recs = rec.recommend_clubs_for_player(player_target, top_k=4)
    for c in club_recs:
        print(f"  • {c['club_name']} ({c['league_name']}) | Uygunluk: {c['suitability_score']}/100 | Oynama Şansı: %{c['playing_time_probability']}")

    showcase['sections'].append({
        'title': f'{player_target} İçin En Uygun Kulüpler (Kariyer & Oynama Şansı)',
        'desc': 'Çift taraflı (reciprocal) model uyarınca oyuncunun düzenli süre alabileceği ve vitrine çıkabileceği en uygun kulüp rotaları.',
        'badge': 'Kariyer Planlaması',
        'type': 'clubs',
        'items': club_recs
    })

    # =========================================================================
    # SCENARIO 7: Arketip İkiz Bulucu (Archetype Twin Search)
    # =========================================================================
    twin_search_player = 'ZİHNİ TEMELCİ'
    print(f"\n[SENARYO 7] '{twin_search_player}' Profiline Benzer Arketip İkizler:")
    twins = rec.find_similar_players(twin_search_player, top_k=4)
    for tw in twins:
        print(f"  • {tw['name']} ({tw['age']} y, {tw['current_club']}) | Eşleşme: %{tw['similarity_pct']} | OVR: {tw['ovr']}")

    showcase['sections'].append({
        'title': f"'{twin_search_player}' Profiline Benzer Taktiksel İkizler",
        'desc': 'HGNN latent uzayında kosinüs benzerliği kullanılarak hem savunma güvenliği hem duran top golcülüğü olan benzer savunma liderlerinin keşfi.',
        'badge': 'Arketip İkiz Bulucu',
        'type': 'twins',
        'items': twins
    })

    # Generate HTML
    generate_html_report(showcase, output_path='scoutme_recommender_report.html')
    print("\n[SUCCESS] Tüm senaryolar başarıyla çalıştırıldı ve görsel rapor oluşturuldu!")


if __name__ == '__main__':
    main()
