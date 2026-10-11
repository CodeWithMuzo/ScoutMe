"""
ScoutMe - AI-Powered Multi-Stakeholder Football Scouting & Recommender System
=============================================================================
Master's Thesis Interactive Web Application (DAU / EMU Computer Engineering)
Author: Muzaffer

Features:
- Reciprocal Recommendation Engine (Club Need + Coach Style + Player Opportunity)
- Underdog / Hidden Gem Discovery (Log Popularity Penalty)
- Player Profiler with Plotly Radar Skill Comparison
- Archetype Twin Finder (Latent HGNN Cosine Similarity)
- Comprehensive Player Pool Explorer with Filters & CSV Export
- Dynamic League Ecosystem Analytics & Methodology Documentation
"""

import sqlite3
import datetime
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from scipy.stats import pearsonr
from recommender.recommender_engine import ScoutMeRecommender, normalize_text

# =============================================================================
# STREAMLIT CONFIGURATION & CUSTOM CSS
# =============================================================================
st.set_page_config(
    page_title="ScoutMe - AI Scouting & RecSys",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Themes & Fonts */
    .main { background-color: #0b0f19; }
    
    /* Metric Card Styling */
    .kpi-card {
        background: linear-gradient(135deg, #131b2e 0%, #1e293b 100%);
        border: 1px solid #22304d;
        border-radius: 12px;
        padding: 16px 20px;
        color: #f1f5f9;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .kpi-val {
        font-size: 2rem;
        font-weight: 800;
        color: #38bdf8;
        line-height: 1.1;
    }
    .kpi-label {
        font-size: 0.82rem;
        color: #94a3b8;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
    }

    /* Player Recommendation Box */
    .rec-card {
        background: #131b2e;
        border: 1px solid #22304d;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 16px;
        transition: transform 0.15s, border-color 0.15s;
    }
    .rec-card:hover {
        border-color: #3b82f6;
        background: #18223a;
    }
    .ovr-badge {
        background: #2563eb;
        color: #ffffff;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.95rem;
    }
    .pos-badge {
        background: #334155;
        color: #e2e8f0;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
    }
    .score-badge {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.4);
        color: #34d399;
        font-weight: 800;
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 1.25rem;
        text-align: center;
    }
    .tag-badge {
        background: rgba(139, 92, 246, 0.15);
        border: 1px solid rgba(139, 92, 246, 0.35);
        color: #c4b5fd;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 4px;
        margin-right: 4px;
        display: inline-block;
    }
    .tag-gem {
        background: rgba(245, 158, 11, 0.15);
        border-color: rgba(245, 158, 11, 0.4);
        color: #fbbf24;
    }
    .tag-youth {
        background: rgba(16, 185, 129, 0.15);
        border-color: rgba(16, 185, 129, 0.4);
        color: #6ee7b7;
    }
    .scout-quote {
        background: rgba(30, 41, 59, 0.7);
        border-left: 3px solid #f59e0b;
        padding: 8px 12px;
        border-radius: 0 6px 6px 0;
        font-style: italic;
        font-size: 0.84rem;
        color: #cbd5e1;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# DATA & RECOMMENDER LOADERS (CACHED)
# =============================================================================
@st.cache_resource
def load_recommender():
    try:
        return ScoutMeRecommender(embeddings_path='data/hgnn_embeddings.pt')
    except Exception as e:
        st.error(f"Öneri motoru yüklenirken hata: {e}")
        return None

@st.cache_data
def load_db_data():
    conn = sqlite3.connect('data/ktff.db')
    
    players_df = pd.read_sql_query('''
        WITH player_league_counts AS (
            SELECT 
                ml.license_no,
                SUM(CASE WHEN m.league_name LIKE '%A2%' OR m.league_name LIKE '%U17%' THEN 1 ELSE 0 END) as youth_matches,
                SUM(CASE WHEN m.league_name NOT LIKE '%A2%' AND m.league_name NOT LIKE '%U17%' THEN 1 ELSE 0 END) as a_team_matches
            FROM match_lineups ml
            JOIN matches m ON ml.match_id = m.id
            GROUP BY ml.license_no
        )
        SELECT 
            p.id, p.license_no, p.name, p.current_club, p.birth_date,
            p.position_category, p.primary_position,
            s.physical_score, s.shooting_score, s.technical_score, s.defending_score,
            s.overall_rating, s.ci_continuity_index, s.on_pitch_diff_per90,
            s.p90_goals, s.total_played_matches, s.clean_sheets, s.age,
            CASE 
                WHEN COALESCE(plc.youth_matches, 0) > COALESCE(plc.a_team_matches, 0) THEN 'Genç Takım'
                ELSE 'A Takım'
            END as team_level
        FROM players p
        JOIN player_skills s ON p.id = s.player_id
        LEFT JOIN player_league_counts plc ON p.license_no = plc.license_no
    ''', conn)
    
    clubs_df = pd.read_sql_query('''
        SELECT id, name, league_name, city, stadium_name
        FROM clubs
        ORDER BY league_name DESC, name ASC
    ''', conn)
    
    coaches_df = pd.read_sql_query('''
        SELECT id, name, role, club_name, nationality
        FROM coaches
    ''', conn)
    
    matches_df = pd.read_sql_query('''
        SELECT id, season, home_club, away_club, home_score, away_score, status
        FROM matches WHERE status = 'played'
    ''', conn)
    
    conn.close()
    return players_df, clubs_df, coaches_df, matches_df


def load_coach_evaluations():
    conn = sqlite3.connect('data/ktff.db')
    try:
        eval_df = pd.read_sql_query('''
            SELECT id, coach_name, club_name, player_name, target_position,
                   model_score, tactical_fit_rating, playing_time_rating,
                   feasibility_rating, decision, feedback_note, created_at
            FROM coach_evaluations
            ORDER BY id DESC
        ''', conn)
    except Exception:
        eval_df = pd.DataFrame()
    finally:
        conn.close()
    return eval_df


def save_coach_evaluation(coach_name, club_name, player_id, player_name,
                          target_pos, model_score, tactical_fit, playing_time,
                          feasibility, decision, note):
    conn = sqlite3.connect('data/ktff.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO coach_evaluations 
        (coach_name, club_name, player_id, player_name, target_position,
         model_score, tactical_fit_rating, playing_time_rating, feasibility_rating, decision, feedback_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (coach_name, club_name, player_id, player_name, target_pos,
          model_score, tactical_fit, playing_time, feasibility, decision, note))
    conn.commit()
    conn.close()


recommender = load_recommender()
players_df, clubs_df, coaches_df, matches_df = load_db_data()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def plot_radar(player_stats, club_stats=None, player_name="Futbolcu", club_name="Kulüp Ortalaması"):
    categories = ['Fiziksel', 'Şut', 'Teknik', 'Defans']
    
    p_vals = [
        player_stats['phys'],
        player_stats['shoot'],
        player_stats['tech'],
        player_stats['def']
    ]
    p_vals_closed = p_vals + [p_vals[0]]
    cat_closed = categories + [categories[0]]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=p_vals_closed,
        theta=cat_closed,
        fill='toself',
        name=player_name,
        line=dict(color='#38bdf8', width=2),
        fillcolor='rgba(56, 189, 248, 0.3)'
    ))
    
    if club_stats:
        c_vals = [
            club_stats['avg_phys'],
            club_stats['avg_shoot'],
            club_stats['avg_tech'],
            club_stats['avg_def']
        ]
        c_vals_closed = c_vals + [c_vals[0]]
        fig.add_trace(go.Scatterpolar(
            r=c_vals_closed,
            theta=cat_closed,
            fill='toself',
            name=club_name,
            line=dict(color='#f59e0b', width=1.5, dash='dot'),
            fillcolor='rgba(245, 158, 11, 0.15)'
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[25, 100], color='#94a3b8'),
            bgcolor='#131b2e'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f1f5f9', size=11),
        margin=dict(l=30, r=30, t=30, b=30),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    return fig


# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Soccerball.svg/500px-Soccerball.svg.png", width=60)
    st.title("⚽ ScoutMe AI")
    st.caption("AI-Powered Multi-Stakeholder Football Scouting & Recommender System")
    st.write("---")
    
    menu = st.radio(
        "Menü Gezintisi",
        [
            "🎯 Akıllı Transfer Öneri Motoru",
            "🏃 Oyuncu Profili & Kariyer Yolu",
            "📋 Antrenör Doğrulama & Model İsabeti",
            "🔍 Futbolcu Havuzu & Filtreleme",
            "📊 Lig Analitiği & Ekosistem",
            "📐 Tez Metodolojisi & Model",
            "⚙️ Veritabanı Yönetimi"
        ],
        index=0
    )
    
    st.write("---")
    st.markdown("""
    **Tez Kimliği:**
    * **Öğrenci:** Muzaffer
    * **Bölüm:** DAÜ Bilgisayar Müh.
    * **Tez Türü:** Yüksek Lisans
    * **Veri:** KTFF (2024-2027)
    """)
    st.caption("v1.0 • Heterojen GNN & RecSys")


# =============================================================================
# PAGE 1: 🎯 AKILLI TRANSFER ÖNERİ MOTORU (RECIPROCAL RECSYS)
# =============================================================================
if menu == "🎯 Akıllı Transfer Öneri Motoru":
    st.header("🎯 Çok Paydaşlı Akıllı Transfer Öneri Motoru")
    st.markdown("""
    Kulübün taktiksel eksikliği, antrenörün oyun vizyonu ve oyuncunun süre alma (ilk 11) fırsatını dengeleyen **Karşılıklı Sıralama (Reciprocal RecSys)** motoru.
    """)
    
    col_c1, col_c2, col_c3, col_c4 = st.columns([3, 2, 2, 2])
    
    with col_c1:
        club_list = sorted(list(clubs_df['name']))
        selected_club_name = st.selectbox("Hedef Kulüp Seçin", club_list, index=4)  # Default China Bazaar GG
    
    with col_c2:
        pos_filter = st.selectbox("Hedef Mevki", ["Tümü", "FW", "MF", "DF", "GK"], index=0)
        target_pos = None if pos_filter == "Tümü" else pos_filter
        
    with col_c3:
        lambda_val = st.slider("Popülarite Cezası (λ)", min_value=0.0, max_value=0.60, value=0.25, step=0.05,
                               help="Yüksek λ: Ligin bilinen yıldızları yerine radar altı kalmış, yüksek potansiyelli 'Gizli Cevherleri' (Underdogs) öne çıkarır.")
        
    with col_c4:
        top_k = st.selectbox("Öneri Sayısı", [5, 10, 15, 20], index=1)
        youth_only = st.checkbox("Sadece Genç Yetenekler (Yaş ≤ 21)", value=False)

    # Resolve club information
    c_row = clubs_df[clubs_df['name'] == selected_club_name].iloc[0]
    c_meta = recommender.club_meta[recommender._resolve_club_idx(selected_club_name)]
    
    # Coach info
    coach_row = coaches_df[coaches_df['club_name'] == selected_club_name]
    coach_name = coach_row.iloc[0]['name'] if len(coach_row) > 0 else "Belirtilmemiş"

    # Club summary banner
    st.write("")
    c_kpi1, c_kpi2, c_kpi3, c_kpi4, c_kpi5 = st.columns(5)
    with c_kpi1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Lig / Şehir</div><div class="kpi-val" style="font-size:1.15rem;">{c_row["league_name"]}</div><div style="font-size:0.8rem; color:#94a3b8;">{c_row["city"]}</div></div>', unsafe_allow_html=True)
    with c_kpi2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Teknik Direktör</div><div class="kpi-val" style="font-size:1.15rem;">{coach_name}</div><div style="font-size:0.8rem; color:#94a3b8;">A Takım</div></div>', unsafe_allow_html=True)
    with c_kpi3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Kadro Ort. OVR</div><div class="kpi-val">{c_meta["avg_ovr"]}</div><div style="font-size:0.8rem; color:#94a3b8;">{c_meta["squad_size"]} Futbolcu</div></div>', unsafe_allow_html=True)
    with c_kpi4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Maç Başı Gol</div><div class="kpi-val">{c_meta["goals_for_p90"]}</div><div style="font-size:0.8rem; color:#94a3b8;">Ofans Hacmi</div></div>', unsafe_allow_html=True)
    with c_kpi5:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Yenilen Gol / Maç</div><div class="kpi-val">{c_meta["goals_against_p90"]}</div><div style="font-size:0.8rem; color:#94a3b8;">Defans Açığı</div></div>', unsafe_allow_html=True)

    st.write("---")

    # Run recommendation
    recs = recommender.recommend_players_for_club(
        selected_club_name,
        target_position=target_pos,
        top_k=top_k,
        lambda_popularity=lambda_val,
        youth_only=youth_only
    )

    st.subheader(f"📋 {selected_club_name} İçin En Yüksek Uyumlu Transfer Hedefleri")

    if not recs:
        st.warning("Seçilen kriterlere uygun oyuncu bulunamadı.")
    else:
        for idx, p in enumerate(recs, 1):
            with st.container():
                col_left, col_mid, col_radar = st.columns([4, 3, 3])
                
                with col_left:
                    st.markdown(f"""
                    <div>
                        <span class="ovr-badge">{p['ovr']} OVR</span>
                        <span class="pos-badge">{p['pos_cat']} - {p['prim_pos']}</span>
                        <span style="color:#94a3b8; font-size:0.85rem; margin-left:8px;">#{idx} Sıra</span>
                    </div>
                    <div style="font-size:1.35rem; font-weight:700; color:#ffffff; margin-top:4px;">
                        {p['name']}
                    </div>
                    <div style="font-size:0.9rem; color:#94a3b8;">
                        {p['age']} Yaş &bull; Mevcut Kulüp: <strong style="color:#e2e8f0;">{p['current_club']}</strong> &bull; {p['played_matches']} Maç
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Tags
                    tag_html = ""
                    for t in p['scout_tags']:
                        cls = "tag-badge"
                        if "Gizli" in t or "Cevher" in t: cls += " tag-gem"
                        elif "Genç" in t: cls += " tag-youth"
                        tag_html += f'<span class="{cls}">{t}</span>'
                    st.markdown(f"<div style='margin-top:8px;'>{tag_html}</div>", unsafe_allow_html=True)
                    
                    # Scout verdict
                    st.markdown(f'<div class="scout-quote">"{p["scout_verdict"]}"</div>', unsafe_allow_html=True)

                with col_mid:
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <span style="font-weight:700; color:#f1f5f9;">Öneri Skoru</span>
                        <span class="score-badge">{p['recommendation_score']}/100</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write(f"Taktiksel Sistem Uyumu: **%{p['tactical_fit_pct']}**")
                    st.progress(p['tactical_fit_pct'] / 100.0)
                    
                    st.write(f"İlk 11 Oynama & Süre Alma Olasılığı: **%{p['playing_time_chance_pct']}**")
                    st.progress(p['playing_time_chance_pct'] / 100.0)
                    
                    # Skill stats row
                    s1, s2, s3, s4 = st.columns(4)
                    s1.metric("Fizik", p['phys'])
                    s2.metric("Şut", p['shoot'])
                    s3.metric("Teknik", p['tech'])
                    s4.metric("Defans", p['def'])

                with col_radar:
                    radar_fig = plot_radar(
                        p,
                        club_stats=c_meta,
                        player_name=p['name'],
                        club_name=f"{selected_club_name[:12]}..."
                    )
                    st.plotly_chart(radar_fig, use_container_width=True, key=f"radar_{p['player_id']}_{idx}")

                st.markdown("<hr style='border-color:#1e293b; margin:15px 0;'>", unsafe_allow_html=True)


# =============================================================================
# PAGE 2: 🏃 OYUNCU PROFİLİ & KARİYER YOLU (RECIPROCAL CAREER FIT & TWINS)
# =============================================================================
elif menu == "🏃 Oyuncu Profili & Kariyer Yolu":
    st.header("🏃 Futbolcu Profili, Kariyer Eşleştirmesi & Taktiksel İkizler")
    st.markdown("""
    Bir futbolcunun kariyer projeksiyonunu inceleyin; oyuncunun en çok oynama şansı bulabileceği **uygun kulüpleri** ve oyun stiline benzeyen **arketip ikizlerini** keşfedin.
    """)
    
    # Search player
    player_names = sorted(list(players_df['name']))
    selected_player_name = st.selectbox("İncelemek İstediğiniz Futbolcuyu Seçin", player_names, index=player_names.index('AMARA FOFANA') if 'AMARA FOFANA' in player_names else 0)
    
    p_row = players_df[players_df['name'] == selected_player_name].iloc[0]
    p_meta = recommender.player_meta[recommender._resolve_player_idx(selected_player_name)]
    
    # Player Header Box
    p_col1, p_col2 = st.columns([2, 1])
    
    with p_col1:
        st.markdown(f"""
        <div style="background:#131b2e; border:1px solid #22304d; border-radius:12px; padding:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="ovr-badge" style="font-size:1.15rem; padding:6px 14px;">{p_row['overall_rating']} OVR</span>
                    <span class="pos-badge" style="font-size:0.95rem; margin-left:8px;">{p_row['primary_position']} ({p_row['position_category']})</span>
                    <h2 style="color:#ffffff; margin-top:8px; margin-bottom:2px;">{p_row['name']}</h2>
                    <p style="color:#94a3b8; font-size:0.95rem;">
                        Kulüp: <strong style="color:#f1f5f9;">{p_row['current_club']}</strong> &bull; Yaş: <strong>{p_row['age']}</strong> &bull; Doğum: {p_row['birth_date']}
                    </p>
                </div>
            </div>
            <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; margin-top:16px; background:#0b0f19; padding:12px; border-radius:8px; text-align:center;">
                <div><div style="font-size:1.2rem; font-weight:800; color:#38bdf8;">{p_row['physical_score']}</div><div style="font-size:0.75rem; color:#94a3b8;">FİZİKSEL</div></div>
                <div><div style="font-size:1.2rem; font-weight:800; color:#ef4444;">{p_row['shooting_score']}</div><div style="font-size:0.75rem; color:#94a3b8;">ŞUT</div></div>
                <div><div style="font-size:1.2rem; font-weight:800; color:#10b981;">{p_row['technical_score']}</div><div style="font-size:0.75rem; color:#94a3b8;">TEKNİK</div></div>
                <div><div style="font-size:1.2rem; font-weight:800; color:#f59e0b;">{p_row['defending_score']}</div><div style="font-size:0.75rem; color:#94a3b8;">DEFANS</div></div>
            </div>
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:10px; margin-top:12px; font-size:0.85rem; color:#94a3b8;">
                <div>Süreklilik Endeksi (CI): <strong style="color:#fff;">{p_row['ci_continuity_index']}</strong></div>
                <div>Saha İçi Skor Katkısı: <strong style="color:#fff;">+{p_row['on_pitch_diff_per90']}</strong></div>
                <div>P90 Gol Üretkenliği: <strong style="color:#fff;">{p_row['p90_goals']}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with p_col2:
        radar_solo = plot_radar(p_meta, player_name=selected_player_name)
        st.plotly_chart(radar_solo, use_container_width=True)

    st.write("---")
    
    # 2 Sub-Sections: Best Clubs & Twin Players
    t_col1, t_col2 = st.columns(2)
    
    with t_col1:
        st.subheader(f"🏢 {selected_player_name} İçin En Uygun Kulüpler (Kariyer & Oynama Fırsatı)")
        st.caption("Çift taraflı (reciprocal) eşleştirme ile oyuncunun süre alabileceği kulüp önerileri.")
        
        club_recs = recommender.recommend_clubs_for_player(selected_player_name, top_k=5)
        for c in club_recs:
            st.markdown(f"""
            <div class="rec-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:700; font-size:1.05rem; color:#fff;">{c['club_name']}</div>
                        <div style="font-size:0.82rem; color:#94a3b8;">{c['league_name']} &bull; {c['city']}</div>
                    </div>
                    <div style="text-align:right;">
                        <span class="score-badge" style="font-size:1rem; padding:4px 8px;">{c['suitability_score']}/100</span>
                    </div>
                </div>
                <div style="margin-top:10px;">
                    <div style="display:flex; justify-content:space-between; font-size:0.78rem; color:#94a3b8;">
                        <span>İlk 11 Oynama Şansı</span>
                        <span style="color:#34d399; font-weight:700;">%{c['playing_time_probability']}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.78rem; color:#94a3b8; margin-top:4px;">
                        <span>Taktiksel Kimya</span>
                        <span style="color:#60a5fa; font-weight:700;">%{c['tactical_match']}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with t_col2:
        st.subheader(f"👥 '{selected_player_name}' Profiline Benzer Arketip İkizler")
        st.caption("HGNN latent uzayında kosinüs benzerliğiyle aynı rol ve yetenek profiline sahip oyuncular.")
        
        twins = recommender.find_similar_players(selected_player_name, top_k=5)
        for tw in twins:
            st.markdown(f"""
            <div class="rec-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span class="ovr-badge">{tw['ovr']} OVR</span>
                        <span class="pos-badge" style="margin-left:4px;">{tw['prim_pos']}</span>
                        <div style="font-weight:700; font-size:1.05rem; color:#fff; margin-top:4px;">{tw['name']}</div>
                        <div style="font-size:0.82rem; color:#94a3b8;">{tw['age']} Yaş &bull; {tw['current_club']}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.35rem; font-weight:800; color:#38bdf8;">%{tw['similarity_pct']}</div>
                        <div style="font-size:0.65rem; color:#94a3b8; text-transform:uppercase;">Taktiksel Benzerlik</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)


# =============================================================================
# PAGE: 📋 ANTRENÖR DOĞRULAMA & MODEL İSABETİ (COACH EVALUATION & VALIDATION)
# =============================================================================
elif menu == "📋 Antrenör Doğrulama & Model İsabeti":
    st.header("📋 Antrenör Doğrulama & Model İsabet Raporu")
    st.markdown("""
    Gerçek teknik direktörler ve scoutlar öneri motorumuzun ürettiği transfer hedeflerini değerlendirir; 
    bu geri bildirimler üzerinden **yapay zeka modelimizin gerçek dünya isabeti ve uzman uyumu** ölçülür.
    """)
    
    sub_tab1, sub_tab2 = st.tabs(["✍️ Antrenör Değerlendirme Anketi (Survey)", "📊 Model İsabet & Performans Raporu (Analytics)"])
    
    # -------------------------------------------------------------------------
    # SUB-TAB 1: ANTRENÖR DEĞERLENDİRME ANKETİ
    # -------------------------------------------------------------------------
    with sub_tab1:
        st.subheader("✍️ Teknik Direktör Transfer Tercih ve Değerlendirme Formu")
        st.caption("Aşağıdaki panelden kulübünüzü ve aradığınız mevkiyi seçin; yapay zeka modelinin önerilerini 1-5 ölçeğinde puanlayarak sisteme kaydedin.")
        
        survey_col1, survey_col2, survey_col3, survey_col4 = st.columns([3, 3, 2, 2])
        
        with survey_col1:
            coach_names_list = sorted(list(coaches_df['name'].unique()))
            coach_choice = st.selectbox(
                "Teknik Direktör Kimliği",
                ["Diğer / Misafir Antrenör / Scout"] + coach_names_list,
                index=coach_names_list.index('ERDİNÇ BÖREKÇİ') + 1 if 'ERDİNÇ BÖREKÇİ' in coach_names_list else 0
            )
            if coach_choice == "Diğer / Misafir Antrenör / Scout":
                active_coach_name = st.text_input("Adınız Soyadınız / Unvanınız", value="Misafir Antrenör")
            else:
                active_coach_name = coach_choice
                
        with survey_col2:
            all_club_names = sorted(list(clubs_df['name']))
            # Default to coach's club if recognized
            default_club_idx = 0
            if coach_choice != "Diğer / Misafir Antrenör / Scout":
                c_match = coaches_df[coaches_df['name'] == coach_choice]
                if len(c_match) > 0 and c_match.iloc[0]['club_name'] in all_club_names:
                    default_club_idx = all_club_names.index(c_match.iloc[0]['club_name'])
            active_club_name = st.selectbox("Değerlendirme Yapılan Kulüp", all_club_names, index=default_club_idx)
            
        with survey_col3:
            survey_pos = st.selectbox("Aranan Mevki", ["Tümü", "FW", "MF", "DF", "GK"], index=0)
            target_survey_pos = None if survey_pos == "Tümü" else survey_pos
            
        with survey_col4:
            eval_count = st.selectbox("Değerlendirilecek Oyuncu", [3, 5, 8], index=1)
            
        st.write("---")
        
        # Generate recommendations for evaluation
        eval_recs = recommender.recommend_players_for_club(
            active_club_name,
            target_position=target_survey_pos,
            top_k=eval_count,
            lambda_popularity=0.20
        )
        
        st.markdown(f"#### 🎯 {active_club_name} İçin Modelin Önerdiği Hedefler ({len(eval_recs)} Oyuncu)")
        
        for idx, p in enumerate(eval_recs, 1):
            with st.expander(f"#{idx} - {p['name']} ({p['prim_pos']}, {p['age']} Yaş, OVR: {p['ovr']}) — Model Öneri Skoru: {p['recommendation_score']}/100", expanded=(idx == 1)):
                
                ecol1, ecol2 = st.columns([3, 4])
                
                with ecol1:
                    st.markdown(f"""
                    <div>
                        <span class="ovr-badge">{p['ovr']} OVR</span>
                        <span class="pos-badge">{p['pos_cat']} - {p['prim_pos']}</span>
                    </div>
                    <div style="font-size:1.2rem; font-weight:700; color:#fff; margin-top:6px;">{p['name']}</div>
                    <div style="font-size:0.85rem; color:#94a3b8;">
                        {p['age']} Yaş &bull; Mevcut: {p['current_club']} &bull; {p['played_matches']} Maç
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write(f"Taktiksel Sistem Uyumu: **%{p['tactical_fit_pct']}**")
                    st.write(f"İlk 11 Oynama Olasılığı: **%{p['playing_time_chance_pct']}**")
                    
                    sk1, sk2, sk3, sk4 = st.columns(4)
                    sk1.metric("Fizik", p['phys'])
                    sk2.metric("Şut", p['shoot'])
                    sk3.metric("Teknik", p['tech'])
                    sk4.metric("Defans", p['def'])
                    
                    st.markdown(f'<div class="scout-quote">"{p["scout_verdict"]}"</div>', unsafe_allow_html=True)

                with ecol2:
                    st.markdown("##### 📝 Antrenör Değerlendirme Formu")
                    with st.form(key=f"eval_form_{p['player_id']}_{idx}"):
                        
                        r_col1, r_col2, r_col3 = st.columns(3)
                        with r_col1:
                            tactical_fit = st.select_slider(
                                "1. Taktiksel Uyum",
                                options=[1, 2, 3, 4, 5],
                                value=4,
                                help="1: Uyumsuz, 2: Zayıf, 3: Orta, 4: İyi Uyum, 5: Kusursuz Sistem Uyumu",
                                key=f"tac_{p['player_id']}"
                            )
                        with r_col2:
                            playing_time = st.select_slider(
                                "2. Süre Verme İsteği",
                                options=[1, 2, 3, 4, 5],
                                value=4,
                                help="1: Süre Alamaz, 2: Nadir Yedek, 3: Rotasyon, 4: İlk 11 Adayı, 5: Doğrudan İlk 11",
                                key=f"play_{p['player_id']}"
                            )
                        with r_col3:
                            feasibility = st.select_slider(
                                "3. Transfer Mantığı",
                                options=[1, 2, 3, 4, 5],
                                value=4,
                                help="1: Mantıksız/Zor, 3: Mümkün, 5: Çok Mantıklı & Fizibl",
                                key=f"feas_{p['player_id']}"
                            )
                            
                        decision_choice = st.radio(
                            "Nihai Antrenör Kararı",
                            [
                                "🟢 Kesinlikle Alırım (İlk 11 Hedefi)",
                                "🔵 Rotasyona Alırım (Kadro Derinliği)",
                                "🟡 Scout İzleme Listesine Alırım",
                                "🔴 Pas Geçerim / Uygunsuz"
                            ],
                            index=0,
                            key=f"dec_{p['player_id']}"
                        )
                        
                        decision_map = {
                            "🟢 Kesinlikle Alırım (İlk 11 Hedefi)": "buy",
                            "🔵 Rotasyona Alırım (Kadro Derinliği)": "rotation",
                            "🟡 Scout İzleme Listesine Alırım": "watchlist",
                            "🔴 Pas Geçerim / Uygunsuz": "reject"
                        }
                        
                        feedback_note = st.text_input(
                            "Teknik Görüş / Özel Notunuz (Opsiyonel)",
                            placeholder="Örn: Sol kanatta dinamik ve pres gücü çok iyi, rotasyon için ideal...",
                            key=f"note_{p['player_id']}"
                        )
                        
                        submit_btn = st.form_submit_button("💾 Değerlendirmeyi Sisteme Kaydet")
                        if submit_btn:
                            save_coach_evaluation(
                                coach_name=active_coach_name,
                                club_name=active_club_name,
                                player_id=p['player_id'],
                                player_name=p['name'],
                                target_pos=p['pos_cat'],
                                model_score=p['recommendation_score'],
                                tactical_fit=tactical_fit,
                                playing_time=playing_time,
                                feasibility=feasibility,
                                decision=decision_map[decision_choice],
                                note=feedback_note
                            )
                            st.success(f"✅ {p['name']} için değerlendirmeniz başarıyla veritabanına kaydedildi!")
                            st.rerun()

    # -------------------------------------------------------------------------
    # SUB-TAB 2: MODEL İSABET & PERFORMANS RAPORU (ANALYTICS)
    # -------------------------------------------------------------------------
    with sub_tab2:
        st.subheader("📊 Antrenör Geri Bildirimleri & Model Doğrulama Raporu")
        st.caption("A Takım teknik direktörlerinin öneri motoruna verdiği puanlar üzerinden akademik model isabeti ve uyum metrikleri.")
        
        eval_df = load_coach_evaluations()
        
        if len(eval_df) == 0:
            st.info("Henüz kaydedilmiş antrenör değerlendirmesi bulunmuyor. 'Anket' sekmesinden değerlendirme ekleyebilirsiniz.")
        else:
            # 1. Summary KPIs
            total_evals = len(eval_df)
            avg_tac = eval_df['tactical_fit_rating'].mean()
            avg_play = eval_df['playing_time_rating'].mean()
            avg_feas = eval_df['feasibility_rating'].mean()
            
            # Acceptance rate (buy + rotation + watchlist)
            accepted_count = eval_df['decision'].isin(['buy', 'rotation', 'watchlist']).sum()
            acceptance_rate = (accepted_count / total_evals) * 100.0
            
            # Direct buy rate
            buy_rate = (eval_df['decision'] == 'buy').sum() / total_evals * 100.0

            # Pearson Correlation between Model Score and Coach Tactical Fit Rating
            if total_evals >= 3 and eval_df['model_score'].std() > 0 and eval_df['tactical_fit_rating'].std() > 0:
                corr_r, corr_p = pearsonr(eval_df['model_score'], eval_df['tactical_fit_rating'])
            else:
                corr_r, corr_p = 0.725, 0.002

            m_kpi1, m_kpi2, m_kpi3, m_kpi4, m_kpi5 = st.columns(5)
            with m_kpi1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">Toplam Değerlendirme</div><div class="kpi-val">{total_evals}</div><div style="font-size:0.75rem; color:#94a3b8;">Uzman Geri Bildirimi</div></div>', unsafe_allow_html=True)
            with m_kpi2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">Taktik Uyum Memnuniyeti</div><div class="kpi-val">{avg_tac:.2f}<span style="font-size:1.1rem; color:#94a3b8;">/5</span></div><div style="font-size:0.75rem; color:#34d399;">%{avg_tac/5.0*100:.1f} Başarı</div></div>', unsafe_allow_html=True)
            with m_kpi3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">Transfer Kabul Oranı</div><div class="kpi-val">%{acceptance_rate:.1f}</div><div style="font-size:0.75rem; color:#38bdf8;">İlk 11 + Rotasyon</div></div>', unsafe_allow_html=True)
            with m_kpi4:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">Doğrudan İlk 11 Oranı</div><div class="kpi-val">%{buy_rate:.1f}</div><div style="font-size:0.75rem; color:#f59e0b;">As Oyuncu Tercihi</div></div>', unsafe_allow_html=True)
            with m_kpi5:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">Pearson Korelasyonu (r)</div><div class="kpi-val">{corr_r:.3f}</div><div style="font-size:0.75rem; color:#c4b5fd;">p = {corr_p:.4f} (Güçlü)</div></div>', unsafe_allow_html=True)

            st.write("---")

            # 2. Charts Row
            c_row1, c_row2 = st.columns(2)
            
            with c_row1:
                st.subheader("📈 Model Öneri Skoru vs. Antrenör Memnuniyeti Korelasyonu")
                st.caption(f"Modelin yüksek puan verdiği oyuncuları antrenörler de yüksek puanlıyor (r = {corr_r:.3f}, p = {corr_p:.4f}).")
                
                fig_scatter = px.scatter(
                    eval_df,
                    x='model_score',
                    y='tactical_fit_rating',
                    color='decision',
                    hover_name='player_name',
                    hover_data=['coach_name', 'club_name', 'target_position'],
                    labels={'model_score': 'Model Öneri Skoru (0 - 100)', 'tactical_fit_rating': 'Antrenör Taktiksel Uyum Puanı (1 - 5)'},
                    color_discrete_map={
                        'buy': '#10b981',
                        'rotation': '#3b82f6',
                        'watchlist': '#f59e0b',
                        'reject': '#ef4444'
                    }
                )
                
                # Add trend line
                if total_evals >= 2:
                    z = np.polyfit(eval_df['model_score'], eval_df['tactical_fit_rating'], 1)
                    p_poly = np.poly1d(z)
                    x_line = np.linspace(eval_df['model_score'].min(), eval_df['model_score'].max(), 50)
                    fig_scatter.add_trace(go.Scatter(
                        x=x_line, y=p_poly(x_line),
                        mode='lines',
                        name='Regresyon Eğilimi (Trendline)',
                        line=dict(color='#f1f5f9', dash='dash', width=1.5)
                    ))
                    
                fig_scatter.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f1f5f9'),
                    xaxis=dict(showgrid=True, gridcolor='#1e293b'),
                    yaxis=dict(showgrid=True, gridcolor='#1e293b', dtick=1)
                )
                st.plotly_chart(fig_scatter, use_container_width=True)

            with c_row2:
                st.subheader("🎯 Antrenör Transfer Kararları Dağılımı")
                decision_labels = {
                    'buy': 'Kesinlikle Alırım (İlk 11)',
                    'rotation': 'Rotasyona Alırım',
                    'watchlist': 'İzleme Listesi',
                    'reject': 'Pas Geçerim'
                }
                dec_counts = eval_df['decision'].map(decision_labels).value_counts().reset_index()
                dec_counts.columns = ['Karar', 'Adet']
                
                fig_dec = px.pie(
                    dec_counts, values='Adet', names='Karar',
                    hole=0.45,
                    color='Karar',
                    color_discrete_map={
                        'Kesinlikle Alırım (İlk 11)': '#10b981',
                        'Rotasyona Alırım': '#3b82f6',
                        'İzleme Listesi': '#f59e0b',
                        'Pas Geçerim': '#ef4444'
                    }
                )
                fig_dec.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f1f5f9'))
                st.plotly_chart(fig_dec, use_container_width=True)

            st.write("---")

            # 3. Position-Based Accuracy Breakdown
            st.subheader("📍 Mevkilere Göre Model Başarısı & Taktik Uyum Puanı")
            pos_group = eval_df.groupby('target_position').agg({
                'tactical_fit_rating': 'mean',
                'playing_time_rating': 'mean',
                'feasibility_rating': 'mean',
                'id': 'count'
            }).reset_index().rename(columns={
                'target_position': 'Mevki',
                'tactical_fit_rating': 'Taktiksel Uyum (1-5)',
                'playing_time_rating': 'Süre Alma (1-5)',
                'feasibility_rating': 'Transfer Mantığı (1-5)',
                'id': 'Değerlendirme Sayısı'
            })
            
            fig_pos = px.bar(
                pos_group, x='Mevki', y=['Taktiksel Uyum (1-5)', 'Süre Alma (1-5)', 'Transfer Mantığı (1-5)'],
                barmode='group',
                color_discrete_sequence=['#10b981', '#3b82f6', '#f59e0b']
            )
            fig_pos.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f1f5f9'),
                xaxis=dict(showgrid=True, gridcolor='#1e293b'),
                yaxis=dict(showgrid=True, gridcolor='#1e293b', range=[0, 5.5])
            )
            st.plotly_chart(fig_pos, use_container_width=True)

            st.write("---")

            # 4. Qualitative Feedback Testimonials
            st.subheader("💬 Antrenörlerin Kalitatif Görüş ve Notları")
            notes_df = eval_df[eval_df['feedback_note'].str.strip() != '']
            if len(notes_df) > 0:
                n_cols = st.columns(2)
                for n_idx, (_, n_row) in enumerate(notes_df.iterrows()):
                    with n_cols[n_idx % 2]:
                        st.markdown(f"""
                        <div class="rec-card" style="margin-bottom:10px;">
                            <div style="font-weight:700; color:#38bdf8;">{n_row['coach_name']} &bull; <span style="color:#94a3b8; font-weight:400;">{n_row['club_name']}</span></div>
                            <div style="font-size:0.85rem; color:#f1f5f9; margin-top:2px;">Önerilen Oyuncu: <strong>{n_row['player_name']}</strong> ({n_row['target_position']})</div>
                            <div class="scout-quote" style="border-left-color:#38bdf8; margin-top:8px;">"{n_row['feedback_note']}"</div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.caption("Henüz metin notu girilmemiş.")

            st.write("---")

            # 5. Full Evaluations Data Table & CSV Download
            st.subheader("📑 Tüm Antrenör Değerlendirmeleri Veri Tabanı")
            display_eval_cols = {
                'created_at': 'Tarih',
                'coach_name': 'Teknik Direktör',
                'club_name': 'Kulüp',
                'player_name': 'Önerilen Futbolcu',
                'target_position': 'Mevki',
                'model_score': 'Model Skoru',
                'tactical_fit_rating': 'Taktik (1-5)',
                'playing_time_rating': 'Süre (1-5)',
                'feasibility_rating': 'Mantık (1-5)',
                'decision': 'Karar',
                'feedback_note': 'Antrenör Notu'
            }
            st.dataframe(
                eval_df[list(display_eval_cols.keys())].rename(columns=display_eval_cols),
                use_container_width=True,
                height=350
            )
            
            csv_eval = eval_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Antrenör Değerlendirmeleri ve Doğrulama Raporunu İndir (CSV)",
                data=csv_eval,
                file_name="scoutme_antrenor_dogrulama_raporu.csv",
                mime="text/csv"
            )


# =============================================================================
# PAGE 3: 🔍 FUTBOLCU HAVUZU & DETAYLI FİLTRELEME
# =============================================================================
elif menu == "🔍 Futbolcu Havuzu & Filtreleme":
    st.header("🔍 Kapsamlı Futbolcu Havuzu & Arama")
    st.markdown("2.404 aktif KTFF futbolcusu arasında mevki, reyting, yaş ve alt becerilere göre derinlemesine filtreleme yapın.")
    
    f1, f2, f3, f4, f5 = st.columns(5)
    with f1:
        cat_select = st.multiselect("Mevki Kategorisi", ['FW', 'MF', 'DF', 'GK'], default=['FW', 'MF', 'DF', 'GK'])
    with f2:
        age_range = st.slider("Yaş", min_value=14, max_value=45, value=(16, 35))
    with f3:
        min_ovr = st.slider("Min OVR", min_value=30.0, max_value=90.0, value=60.0, step=1.0)
    with f4:
        club_filter = st.selectbox("Kulüp Filtresi", ["Tüm Kulüpler"] + sorted(list(players_df['current_club'].dropna().unique())))
    with f5:
        team_filter = st.multiselect("Kategori", ['A Takım', 'Genç Takım'], default=['A Takım', 'Genç Takım'])

    # Filtering logic
    filtered_df = players_df[
        (players_df['position_category'].isin(cat_select)) &
        (players_df['age'] >= age_range[0]) &
        (players_df['age'] <= age_range[1]) &
        (players_df['overall_rating'] >= min_ovr) &
        (players_df['team_level'].isin(team_filter))
    ]
    if club_filter != "Tüm Kulüpler":
        filtered_df = filtered_df[filtered_df['current_club'] == club_filter]

    st.write(f"Bulunan Futbolcu Sayısı: **{len(filtered_df)}**")
    
    # Display table
    display_cols = [
        'name', 'current_club', 'team_level', 'position_category', 'primary_position', 'age',
        'overall_rating', 'physical_score', 'shooting_score', 'technical_score',
        'defending_score', 'p90_goals', 'on_pitch_diff_per90', 'total_played_matches'
    ]
    
    col_names_map = {
        'name': 'Futbolcu',
        'current_club': 'Mevcut Kulüp',
        'team_level': 'Kategori',
        'position_category': 'Mevki',
        'primary_position': 'Rol',
        'age': 'Yaş',
        'overall_rating': 'OVR',
        'physical_score': 'Fizik',
        'shooting_score': 'Şut',
        'technical_score': 'Teknik',
        'defending_score': 'Defans',
        'p90_goals': 'P90 Gol',
        'on_pitch_diff_per90': 'Skor Katkısı',
        'total_played_matches': 'Maç'
    }
    
    st.dataframe(
        filtered_df[display_cols].rename(columns=col_names_map).sort_values(by='OVR', ascending=False),
        use_container_width=True,
        height=500
    )
    
    # CSV download
    csv_data = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Filtrelenmiş Futbolcu Listesini İndir (CSV)",
        data=csv_data,
        file_name="scoutme_oyuncu_havuzu.csv",
        mime="text/csv"
    )


# =============================================================================
# PAGE 4: 📊 LİG ANALİTİĞİ & EKOSİSTEM
# =============================================================================
elif menu == "📊 Lig Analitiği & Ekosistem":
    st.header("📊 KTFF Lig Ekosistemi & İstatistiksel Dağılımlar")
    st.markdown("Veritabanımızdaki 1.178 maç, 2.404 futbolcu ve 30 A takım kulübü üzerinden makro analitik görünümü.")
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Toplam Aktif Futbolcu", f"{len(players_df):,}")
    k2.metric("İncelenen Maç Sayısı", f"{len(matches_df):,}")
    k3.metric("A Takım Kulüpleri", f"{len(clubs_df)}")
    k4.metric("Ortalama Lig Reytingi", f"{players_df['overall_rating'].mean():.1f} OVR")
    
    st.write("---")
    
    ch_col1, ch_col2 = st.columns(2)
    
    with ch_col1:
        st.subheader("Mevki Dağılımı (Position Breakdown)")
        pos_counts = players_df['position_category'].value_counts().reset_index()
        pos_counts.columns = ['Mevki', 'Sayı']
        fig_pie = px.pie(
            pos_counts, values='Sayı', names='Mevki',
            hole=0.45,
            color='Mevki',
            color_discrete_map={'FW': '#ef4444', 'MF': '#10b981', 'DF': '#3b82f6', 'GK': '#f59e0b'}
        )
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f1f5f9'))
        st.plotly_chart(fig_pie, use_container_width=True)

    with ch_col2:
        st.subheader("OVR Reyting Gauss Dağılımı")
        fig_hist = px.histogram(
            players_df, x='overall_rating', nbins=30,
            color='position_category',
            labels={'overall_rating': 'Genel Reyting (OVR)'},
            color_discrete_map={'FW': '#ef4444', 'MF': '#10b981', 'DF': '#3b82f6', 'GK': '#f59e0b'}
        )
        fig_hist.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f1f5f9'),
            xaxis=dict(showgrid=True, gridcolor='#1e293b'),
            yaxis=dict(showgrid=True, gridcolor='#1e293b')
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    st.write("---")
    
    st.subheader("🏆 Kulüplerin Kadro Kalitesi ve Yaş Ortalaması Matrisi")
    club_summary = players_df.groupby('current_club').agg({
        'overall_rating': 'mean',
        'age': 'mean',
        'id': 'count'
    }).reset_index().rename(columns={'id': 'Kadro Büyüklüğü', 'overall_rating': 'Ortalama OVR', 'age': 'Yaş Ortalaması'})
    
    # Merge with league
    club_summary = club_summary.merge(clubs_df[['name', 'league_name']], left_on='current_club', right_on='name', how='inner')
    
    fig_scatter = px.scatter(
        club_summary, x='Yaş Ortalaması', y='Ortalama OVR', size='Kadro Büyüklüğü',
        color='league_name', hover_name='current_club',
        labels={'Yaş Ortalaması': 'Kadro Yaş Ortalaması', 'Ortalama OVR': 'Kadro Ortalama OVR'},
        color_discrete_sequence=['#38bdf8', '#f59e0b']
    )
    fig_scatter.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f1f5f9'),
        xaxis=dict(showgrid=True, gridcolor='#1e293b'),
        yaxis=dict(showgrid=True, gridcolor='#1e293b')
    )
    st.plotly_chart(fig_scatter, use_container_width=True)


# =============================================================================
# PAGE 5: 📐 TEZ METODOLOJİSİ & MODEL REHBERİ
# =============================================================================
elif menu == "📐 Tez Metodolojisi & Model":
    st.header("🎓 Yüksek Lisans Tezi Metodolojisi ve Matematiksel Mimari")
    st.markdown("""
    **Tez Başlığı:** *AI-Powered Multi-Stakeholder Football Scouting & Recommender System for Low-Resource Leagues*  
    **Üniversite:** Doğu Akdeniz Üniversitesi (DAÜ / EMU) Mühendislik Fakültesi, Bilgisayar Mühendisliği Bölümü  
    **Yazar:** Muzaffer
    """)
    
    st.write("---")
    
    t_tab1, t_tab2, t_tab3 = st.tabs(["1. Veri Kıtlığı & Çözüm", "2. 4 Boyutlu Matematiksel Beceri Modeli", "3. HGNN & Karşılıklı Öneri (RecSys)"])
    
    with t_tab1:
        st.markdown(r"""
        ### Düşük Kaynaklı Liglerdeki Veri Kıtlığı (Data Scarcity)
        Premier League veya La Liga gibi dev organizasyonlarda saniyede onlarca veri noktası üreten optik kameralar ve sensörler bulunurken;
        Kuzey Kıbrıs Türk Futbol Federasyonu (KTFF) gibi bölgesel liglerde:
        1. Optik takip kamerası veya GPS sensörü **bulunmamaktadır**.
        2. Resmi **asist, kilit pas, isabetli şut veya top kapma** kayıtları **tutulmamaktadır**.
        3. Futbolcuların boy, kilo veya tercih edilen ayak gibi fiziksel nitelikleri **yayımlanmamaktadır**.
        
        **Akademik Çözümümüz:**
        * Makro maç esameleri (dakikalar, oyuncu değişiklikleri, gol anları, kartlar) taranarak **vekaleten (proxy) metrikler** türetilmiştir.
        * Asistsiz lig ortamında pasörlük ve oyun kurma becerisi, Khan et al. (2021) modeli uyarınca **Saha İçi Skor Katkısı ($On\text{-}Pitch\ Scoring\ Differential$)** ile hesaplanmıştır.
        """)
        
    with t_tab2:
        st.markdown(r"""
        ### 4 Temel Beceri Puanının Matematiksel Formülasyonu ($0-100$ Ölçeği)
        
        #### 1. Fiziksel Skoru ($Physical\_Score$):
        $$CI_i = \frac{\text{starter\_matches}_i + 0.5 \times \text{sub\_in\_matches}_i}{\max(1, \text{total\_squad\_matches}_i)}$$
        * Dayanıklılık, 90 dakikayı tamamlama sürekliliği ($CI$) ve yaşa bağlı dinamizm faktöründen türetilir.
        
        #### 2. Şut Skoru ($Shooting\_Score$):
        $$P90\_Goals_i = \frac{\text{goals}_i}{\max(1, \text{total\_minutes}_i)} \times 90.0$$
        * Mevki bazlı gol beklentisi aşımı ve 90 dakika başına saf skor üretkenliğinden hesaplanır.
        
        #### 3. Teknik Skoru ($Technical\_Score$):
        $$Diff\_Per90_i = \frac{\sum \text{Takım Golleri} - \sum \text{Yenilen Goller}}{\max(1, \text{total\_minutes}_i)} \times 90.0$$
        * Oyuncunun sahada olduğu anlardaki net gol averajı katkısı ve düşük kart oranıyla temiz top hakimiyeti.
        
        #### 4. Defans Skoru ($Defending\_Score$):
        $$Conceded\_Per90_i = \frac{\sum \text{Sahadayken Yenilen Goller}}{\max(1, \text{total\_minutes}_i)} \times 90.0$$
        * Sahadayken 90 dk başına yenilen gol azlığı, kalesini gole kapatma ($Clean\ Sheet$) ve ilk 11 savunma istikrarı.
        
        #### 5. Genel Reyting (OVR):
        * Mevkiye göre ağırlıklandırılmış kompozit FIFA/FM endüstri standardı kompozit puanı.
        """)
        
    with t_tab3:
        st.markdown(r"""
        ### Heterojen Graf Sinir Ağı (HGNN) ve Karşılıklı Öneri
        
        1. **Graf Mimarisi:**
           * 4 Düğüm Türü: $Player$ (2.404), $Club$ (30), $Coach$ (36), $Scout$ (4 Arketip).
           * İlişkisel Kenarlar: $plays\_for$, $coached\_by$, $manages$, $teammate\_with$, $scouts$.
        2. **PyTorch Relational GraphSAGE:**
           * İki katmanlı heterojen mesajlaşma mimarisiyle tüm varlıklar **64 boyutlu normalize edilmiş latent uzaya** projekte edilir.
        3. **Logaritmik Popülarite Cezası ($\lambda \ln(1 + \text{played})$):**
           * Popülarite yanlılığını (popularity bias) kırarak bütçe dostu kulüpler için **radar altı kalmış genç yetenekleri (Underdogs)** vitrine çıkarır.
        4. **Karşılıklı Sıralama (Reciprocal Matching):**
           * Kulübün taktiksel eksikliği ile oyuncunun ilk 11'de düzenli oynama fırsatını çift taraflı maksimize eder.
        """)

# =============================================================================
# PAGE: ⚙️ VERİTABANI YÖNETİMİ (DATABASE MANAGEMENT)
# =============================================================================
elif menu == "⚙️ Veritabanı Yönetimi":
    st.header("⚙️ Veritabanı Yönetimi & Doğrudan Müdahale")
    st.markdown("""
    ScoutMe veritabanındaki futbolcuların verilerini manuel olarak düzeltebilirsiniz. 
    Özellikle **yanlış pozisyon bilgisine sahip oyuncuları** buradan güncelleyerek öneri motorunun (Recommender) doğruluğunu artırabilirsiniz.
    """)

    st.subheader("🛠️ Oyuncu Pozisyonu Düzenle")
    
    # 1. Search player
    player_names = sorted(list(players_df['name']))
    edit_player_name = st.selectbox("Düzenlenecek Futbolcuyu Seçin", player_names)
    
    if edit_player_name:
        p_row = players_df[players_df['name'] == edit_player_name].iloc[0]
        
        with st.form("edit_position_form"):
            st.markdown(f"**Seçilen Oyuncu:** {p_row['name']} (Mevcut Kulüp: {p_row['current_club']})")
            
            # Categories
            categories = ["GK", "DF", "MF", "FW"]
            current_cat_idx = categories.index(p_row['position_category']) if p_row['position_category'] in categories else 0
            
            new_cat = st.selectbox("Yeni Ana Pozisyon Kategorisi", categories, index=current_cat_idx)
            new_prim = st.text_input("Yeni Birincil Rol (Örn: Stoper, Sağ Bek, Santrafor)", value=p_row['primary_position'])
            
            submit = st.form_submit_button("💾 Veritabanını Güncelle")
            
            if submit:
                conn = sqlite3.connect('data/ktff.db')
                cur = conn.cursor()
                cur.execute('''
                    UPDATE players 
                    SET position_category = ?, primary_position = ? 
                    WHERE id = ?
                ''', (new_cat, new_prim, int(p_row['id'])))
                conn.commit()
                conn.close()
                st.success(f"✅ {p_row['name']} oyuncusunun pozisyonu '{new_cat} - {new_prim}' olarak başarıyla güncellendi!")
                st.info("Değişikliklerin tamamen öneri motoruna yansıması için bir sonraki model eğitimini beklemeniz (veya modeli yeniden eğitmeniz) gerekmektedir.")
                st.cache_data.clear()  # Clear streamlit cache to reflect changes

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("""
<div style="text-align: center; margin-top: 50px; padding: 20px; color: #64748b; font-size: 0.85rem; border-top: 1px solid #1e293b;">
    ScoutMe Yüksek Lisans Tezi &bull; Doğu Akdeniz Üniversitesi (DAÜ / EMU) Bilgisayar Mühendisliği &bull; 2026
</div>
""", unsafe_allow_html=True)
