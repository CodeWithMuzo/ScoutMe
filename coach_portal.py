"""
ScoutMe - Antrenör & Scout Özel Değerlendirme Portalı
===================================================
A Takım Teknik Direktörleri ve Scoutlar İçin Sadeleştirilmiş,
Adım Adım Taktiksel Transfer Keşif ve Model Doğrulama Arayüzü.

Akış:
1. Antrenör ve Kulüp Seçimi
2. Tercih Edilen Taktiksel Diziliş
3. Aranan Pozisyon ve Oyuncu Arketipi (Tipi)
4. Modelin Kart Şeklinde Fotoğraflı Önerileri
5. "Futbolcuyu Tanıyor musunuz?" Doğrulama Akışı
   - Evet -> Doğrudan Puanlama
   - Hayır -> Kariyer ve Performans Bilgi Kartı -> Puanlama
6. SQLite coach_evaluations Tablosuna Kayıt & Canlı İsabet Raporu
"""

import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from recommender.recommender_engine import ScoutMeRecommender, normalize_text

# =============================================================================
# SAYFA VE STİL YAPILANDIRMASI
# =============================================================================
st.set_page_config(
    page_title="ScoutMe - Antrenör Değerlendirme Portalı",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom High-End Football UI Styling
st.markdown("""
<style>
    /* Dark Slate & Gold Football Theme */
    .stApp { background-color: #0b0f19; color: #f1f5f9; }
    
    .main-header {
        background: linear-gradient(135deg, #10172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    }
    .main-header h1 {
        font-size: 2.2rem;
        font-weight: 800;
        color: #38bdf8;
        letter-spacing: -0.5px;
        margin-bottom: 6px;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 1.05rem;
    }

    .step-box {
        background: #131b2e;
        border: 1px solid #22304d;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 20px;
    }
    .step-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Player Card Styling */
    .player-card {
        background: #131b2e;
        border: 1px solid #22304d;
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        transition: border-color 0.2s;
    }
    .player-card:hover {
        border-color: #38bdf8;
    }

    .player-photo-container {
        width: 130px;
        height: 160px;
        border-radius: 10px;
        overflow: hidden;
        border: 2px solid #334155;
        background: #1e293b;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .player-photo {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .player-photo-placeholder {
        font-size: 3.5rem;
        color: #64748b;
    }

    .badge-ovr {
        background: #2563eb;
        color: #ffffff;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 1rem;
    }
    .badge-pos {
        background: #334155;
        color: #f1f5f9;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.82rem;
    }
    .badge-fit {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.4);
        color: #34d399;
        font-weight: 800;
        padding: 5px 12px;
        border-radius: 8px;
        font-size: 1.15rem;
    }

    .career-box {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid #3b82f6;
        border-radius: 10px;
        padding: 16px;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .career-title {
        color: #38bdf8;
        font-weight: 700;
        font-size: 0.95rem;
        margin-bottom: 8px;
    }

    .saved-box {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 8px;
        padding: 12px 16px;
        margin-top: 15px;
        color: #6ee7b7;
        font-weight: 600;
        font-size: 0.92rem;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# VERİ & MODEL YÜKLEYİCİLER
# =============================================================================
@st.cache_resource
def get_recommender():
    return ScoutMeRecommender(embeddings_path='data/hgnn_embeddings.pt')

@st.cache_data
def get_coaches_and_clubs():
    conn = sqlite3.connect('data/ktff.db')
    coaches_df = pd.read_sql_query('SELECT id, name, club_name, role FROM coaches ORDER BY name ASC', conn)
    clubs_df = pd.read_sql_query('SELECT id, name, league_name, city FROM clubs ORDER BY league_name DESC, name ASC', conn)
    conn.close()
    return coaches_df, clubs_df

def get_player_full_details(player_id):
    conn = sqlite3.connect('data/ktff.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT 
            p.id, p.name, p.current_club, p.birth_date, p.photo_url,
            s.overall_rating, s.physical_score, s.shooting_score, s.technical_score, s.defending_score,
            s.ci_continuity_index, s.on_pitch_diff_per90, s.p90_goals,
            s.total_played_matches, s.total_goals, s.starter_ratio, s.avg_minutes_played,
            s.goals_conceded_per90, s.clean_sheets, s.age
        FROM players p
        JOIN player_skills s ON p.id = s.player_id
        WHERE p.id = ?
    ''', (player_id,))
    row = cur.fetchone()
    
    # Season stats
    seasons = cur.execute('''
        SELECT season, total_played_matches, starter_matches, goals, yellow_cards, red_cards
        FROM player_season_stats
        WHERE player_id = ?
        ORDER BY season DESC
    ''', (player_id,)).fetchall()
    
    conn.close()
    return row, seasons

def save_evaluation_to_db(coach_name, club_name, player_id, player_name,
                          target_pos, formation, player_type, is_known,
                          model_score, tactical_fit, playing_time,
                          feasibility, decision, note):
    conn = sqlite3.connect('data/ktff.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO coach_evaluations 
        (coach_name, club_name, player_id, player_name, target_position,
         formation, player_type, is_known, model_score, tactical_fit_rating,
         playing_time_rating, feasibility_rating, decision, feedback_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (coach_name, club_name, player_id, player_name, target_pos,
          formation, player_type, is_known, model_score, tactical_fit,
          playing_time, feasibility, decision, note))
    conn.commit()
    conn.close()

def load_evaluations_summary():
    conn = sqlite3.connect('data/ktff.db')
    try:
        df = pd.read_sql_query('SELECT * FROM coach_evaluations ORDER BY id DESC', conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df


recommender = get_recommender()
coaches_df, clubs_df = get_coaches_and_clubs()


# =============================================================================
# BAŞLIK VE ÜST BİLGİ
# =============================================================================
st.markdown("""
<div class="main-header">
    <h1>⚽ SCOUTME | ANTRENÖR TRANSFER DOĞRULAMA PORTALI</h1>
    <p>A Takım Teknik Direktörleri İçin Taktiksel Oyuncu Keşfi & Yapay Zeka Model Değerlendirme Sistemi</p>
</div>
""", unsafe_allow_html=True)

portal_tab1, portal_tab2 = st.tabs(["🎯 Taktiksel Transfer Sihirbazı & Puanlama", "📊 Canlı Model İsabet ve Doğrulama Raporu"])


# =============================================================================
# SEKME 1: 🎯 TAKTİKSEL TRANSFER SİHİRBAZI & PUANLAMA
# =============================================================================
with portal_tab1:
    
    # -------------------------------------------------------------------------
    # ADIM 1: ANTRENÖR & KULÜP BİLGİSİ
    # -------------------------------------------------------------------------
    st.markdown('<div class="step-title">👤 ADIM 1: Antrenör ve Kulüp Kimliği</div>', unsafe_allow_html=True)
    c_col1, c_col2 = st.columns(2)
    
    coach_list = sorted(list(coaches_df['name'].unique()))
    with c_col1:
        selected_coach = st.selectbox(
            "Adınız ve Soyadınız (Teknik Direktör Listesi):",
            ["Misafir Antrenör / Scout"] + coach_list,
            index=coach_list.index("ERDİNÇ BÖREKÇİ") + 1 if "ERDİNÇ BÖREKÇİ" in coach_list else 0
        )
        if selected_coach == "Misafir Antrenör / Scout":
            coach_display_name = st.text_input("Antrenör Adınız:", value="Misafir Teknik Direktör")
        else:
            coach_display_name = selected_coach

    club_names = sorted(list(clubs_df['name']))
    default_club_idx = 0
    if selected_coach != "Misafir Antrenör / Scout":
        c_row = coaches_df[coaches_df['name'] == selected_coach]
        if len(c_row) > 0 and c_row.iloc[0]['club_name'] in club_names:
            default_club_idx = club_names.index(c_row.iloc[0]['club_name'])

    with c_col2:
        selected_club = st.selectbox(
            "Çalıştırdığınız / Temsil Ettiğiniz Kulüp:",
            club_names,
            index=default_club_idx
        )

    st.write("---")

    # -------------------------------------------------------------------------
    # ADIM 2 & 3: DİZİLİŞ & OYUNCU TİPİ SEÇİMİ
    # -------------------------------------------------------------------------
    st.markdown('<div class="step-title">📐 ADIM 2: Tercih Ettiğiniz Diziliş ve Aradığınız Oyuncu Profili</div>', unsafe_allow_html=True)
    
    col_d1, col_d2, col_d3 = st.columns(3)
    
    with col_d1:
        selected_formation = st.selectbox(
            "Oyun Şablonunuz / Dizilişiniz:",
            [
                "4-3-3 (Geniş Kanatlar & Tek Forvet)",
                "4-2-3-1 (Çift Ön Libero & 10 Numara)",
                "4-4-2 (Klasik Çift Forvet & Çizgi Kanatlar)",
                "3-5-2 (3'lü Savunma & İki Forvet)",
                "3-4-3 (3'lü Savunma & Dinamik Kanat Bekler)",
                "4-1-4-1 (Tek Çapa & İki Ofansif 8 Numara)"
            ],
            index=0
        )
        formation_clean = selected_formation.split(" ")[0]

    with col_d2:
        pos_options = {
            "Santrafor / Forvet (FW)": "FW",
            "Kanat Forvet / Açık (Winger - LW/RW)": "FW",
            "Merkez / Ofansif Orta Saha (CM/CAM)": "MF",
            "Defansif Orta Saha / Ön Libero (CDM)": "MF",
            "Stoper / Savunma (CB)": "DF",
            "Bek / Kanat Bek (LB/RB)": "DF",
            "Kaleci (GK)": "GK"
        }
        selected_pos_label = st.selectbox("Aradığınız Pozisyon:", list(pos_options.keys()), index=0)
        target_pos_cat = pos_options[selected_pos_label]

    # Archetype types based on position
    archetype_map = {
        "Santrafor / Forvet (FW)": [
            "Hedef Santrafor (Fizik Güç & Hava Hakimiyeti)",
            "Hızlı / Patlayıcı Kontratak Forveti",
            "Ceza Sahası Bitiricisi (Poacher)",
            "Sahte 9 / Bağlantı Oyuncusu"
        ],
        "Kanat Forvet / Açık (Winger - LW/RW)": [
            "İçeri Kateden Skorer Kanat (Inverted Winger)",
            "Çizgiye İnen Tempolu Kanat & Orta Tehdidi",
            "Pres Gücü Yüksek Çalışkan Kanat"
        ],
        "Merkez / Ofansif Orta Saha (CM/CAM)": [
            "Oyun Kurucu / Metronom (Yüksek Pas & Pozitif Skor Katkısı)",
            "İki Yönlü Dinamo (Box-to-Box)",
            "Yaratıcı 10 Numara / Asistçi"
        ],
        "Defansif Orta Saha / Ön Libero (CDM)": [
            "Defansif Çapa / Top Kapan Kesici",
            "Geriden Oyun Kuran Derin Oyun Kurucu (Regista)"
        ],
        "Stoper / Savunma (CB)": [
            "Hava Hakimiyeti Olan Sert Lider Stoper",
            "Topla Çıkan Modern Pasör Stoper",
            "Hızlı ve Kademe Alan Çabuk Stoper"
        ],
        "Bek / Kanat Bek (LB/RB)": [
            "Hücumcu Bindirmeci Dinamik Bek",
            "Savunma Öncelikli Pozisyonel Bek"
        ],
        "Kaleci (GK)": [
            "Çizgi Kalecisi & Çevik Refleks",
            "Modern Ayaklı Süpürücü Kaleci (Sweeper Keeper)"
        ]
    }

    with col_d3:
        archetypes = archetype_map.get(selected_pos_label, ["Dengeli Oyuncu"])
        selected_archetype = st.selectbox("Aradığınız Oyuncu Tipi (Arketip):", archetypes, index=0)

    # Optional filter: Underdog slider
    with st.expander("⚙️ Gelişmiş Filtreler (Gizli Cevher & Yaş Sınırı)", expanded=False):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            lambda_val = st.slider("Popülarite Cezası (λ) — Gizli Yetenek Arama:", min_value=0.0, max_value=0.50, value=0.20, step=0.05,
                                   help="Yüksek λ değeri tanınmış yıldızlar yerine alt ligdeki yüksek potansiyelli ucuz cevherleri öne çıkarır.")
        with col_f2:
            youth_filter = st.checkbox("Sadece Genç Yetenekler (Yaş ≤ 21)", value=False)

    st.write("")
    run_btn = st.button("🚀 Taktiksel Oyuncu Önerilerini Getir", type="primary", use_container_width=True)

    # =========================================================================
    # ADIM 4 & 5: ÖNERİLER VE İNTERAKTİF DOĞRULAMA AKIŞI
    # =========================================================================
    if run_btn or 'portal_recs' in st.session_state:
        if run_btn:
            # Generate recommendations
            recs = recommender.recommend_players_for_club(
                selected_club,
                target_position=target_pos_cat,
                top_k=4,
                lambda_popularity=lambda_val,
                youth_only=youth_filter
            )
            st.session_state['portal_recs'] = recs
            st.session_state['portal_club'] = selected_club
            st.session_state['portal_coach'] = coach_display_name
            st.session_state['portal_formation'] = formation_clean
            st.session_state['portal_pos'] = target_pos_cat
            st.session_state['portal_archetype'] = selected_archetype

        recs = st.session_state.get('portal_recs', [])
        
        st.write("---")
        st.markdown(f"### 📋 {st.session_state.get('portal_club')} İçin {selected_archetype} Profilli Öneriler")
        st.info("💡 **Antrenör Yönergesi:** Her oyuncuyu inceleyin. Önce futbolcuyu **tanıyıp tanımadığınızı** belirtin. Tanımıyorsanız sistem size oyuncunun kariyer geçmişini özetleyecektir. Ardından modelin önerisini puanlayınız.")

        for idx, p in enumerate(recs, 1):
            p_full, p_seasons = get_player_full_details(p['player_id'])
            
            photo_url = p_full[4] if (p_full and len(p_full) > 4 and p_full[4]) else None
            
            st.markdown(f'<div class="player-card">', unsafe_allow_html=True)
            
            # Card Top Row
            row_c1, row_c2, row_c3 = st.columns([2, 5, 3])
            
            with row_c1:
                if photo_url:
                    st.image(photo_url, width=125, caption=f"KTFF Lisans #{p['license_no']}")
                else:
                    st.markdown("""
                    <div class="player-photo-container">
                        <div class="player-photo-placeholder">👤</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.caption(f"KTFF #{p['license_no']}")

            with row_c2:
                st.markdown(f"""
                <div>
                    <span class="badge-ovr">{p['ovr']} OVR</span>
                    <span class="badge-pos">{p['prim_pos']}</span>
                    <span style="color:#94a3b8; font-size:0.85rem; margin-left:8px;">#{idx} Sıradaki Öneri</span>
                </div>
                <h3 style="color:#ffffff; margin: 4px 0;">{p['name']}</h3>
                <div style="font-size:0.92rem; color:#94a3b8;">
                    <strong>{p['age']} Yaş</strong> &bull; Mevcut Kulüp: <strong style="color:#38bdf8;">{p['current_club']}</strong> &bull; Toplam <strong>{p['played_matches']}</strong> Maç
                </div>
                """, unsafe_allow_html=True)
                
                # 4 Skills meters
                sk1, sk2, sk3, sk4 = st.columns(4)
                sk1.metric("Fizik", p['phys'])
                sk2.metric("Şut", p['shoot'])
                sk3.metric("Teknik", p['tech'])
                sk4.metric("Defans", p['def'])
                
                st.markdown(f'<div style="font-size:0.85rem; color:#cbd5e1; font-style:italic; margin-top:8px;">🤖 <strong>Model Görüşü:</strong> "{p["scout_verdict"]}"</div>', unsafe_allow_html=True)

            with row_c3:
                st.markdown(f"""
                <div style="text-align:right;">
                    <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase;">Taktiksel Uyum Skoru</div>
                    <div class="badge-fit" style="display:inline-block; margin-top:4px;">%{p['tactical_fit_pct']}</div>
                </div>
                <div style="margin-top:15px; font-size:0.85rem;">
                    <div style="display:flex; justify-content:space-between; color:#94a3b8;">
                        <span>İlk 11 Oynama Şansı:</span>
                        <strong style="color:#34d399;">%{p['playing_time_chance_pct']}</strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # İNTERAKTİF DOĞRULAMA AKIŞI: "BU FUTBOLCUYU TANIYOR MUSUNUZ?"
            # -----------------------------------------------------------------
            st.markdown("<hr style='border-color:#1e293b; margin:15px 0;'>", unsafe_allow_html=True)
            
            st.markdown(f"##### ❓ Soru: **{p['name']}** isimli futbolcuyu daha önce ligde izlediniz mi / tanıyor musunuz?")
            
            knows_key = f"knows_{p['player_id']}_{idx}"
            is_known_choice = st.radio(
                "Bilgi Düzeyiniz:",
                ["🟢 Evet, tanıyorum / ligde izledim", "🟡 Hayır, tanımıyorum / ilk defa duyuyorum"],
                horizontal=True,
                key=knows_key
            )
            is_known = 1 if "Evet" in is_known_choice else 0

            # EĞER HAYIRSA: KARİYER BİLGİ KARTINI GÖSTER
            if is_known == 0:
                st.markdown(f"""
                <div class="career-box">
                    <div class="career-title">📖 {p['name']} — Kariyer & Performans Bilgi Notu</div>
                    <div style="font-size:0.88rem; color:#cbd5e1; line-height:1.6;">
                        • <strong>Doğum Tarihi / Yaş:</strong> {p_full[3]} ({p['age']} Yaşında)<br>
                        • <strong>Son 3 Sezon Maç Katılımı:</strong> {p_full[13]} Maçta süre aldı (İlk 11 Başlama Oranı: %{p_full[15]*100:.0f}).<br>
                        • <strong>Skor Katkısı:</strong> Toplam {p_full[14]} gol (90 dk başına {p_full[12]} gol).<br>
                        • <strong>Saha İçi Net Averaj Katkısı (On-Pitch Diff):</strong> Oyuncu sahadayken takımın net gol katkısı: <strong>+{p_full[11]}</strong><br>
                        • <strong>Karakteristik Özellik:</strong> Süreklilik endeksi %{p_full[10]*100:.0f} ile maç kondisyonu yüksek bir profil.
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Season breakdown table
                if p_seasons:
                    season_df = pd.DataFrame(p_seasons, columns=['Sezon', 'Toplam Maç', 'İlk 11', 'Gol', 'Sarı Kart', 'Kırmızı Kart'])
                    st.dataframe(season_df, hide_index=True, use_container_width=True)

            # PUANLAMA FORMU
            st.markdown(f"##### ⭐ Bu Öneriyi Puanlayın:")
            
            with st.form(key=f"coach_eval_form_{p['player_id']}_{idx}"):
                ev_c1, ev_c2, ev_c3 = st.columns(3)
                
                with ev_c1:
                    eval_tac = st.select_slider(
                        "1. Taktiksel Uyum (1 - 5 Yıldız):",
                        options=[1, 2, 3, 4, 5],
                        value=4,
                        help="1: Sistemime hiç uymaz, 3: Orta düzey, 5: Sistemime kusursuz uyum sağlar",
                        key=f"f_tac_{p['player_id']}"
                    )
                with ev_c2:
                    eval_play = st.select_slider(
                        "2. İlk 11 / Süre Verme İsteği (1 - 5):",
                        options=[1, 2, 3, 4, 5],
                        value=4,
                        help="1: Kadroda süre alamaz, 3: Rotasyon oyuncusu, 5: Doğrudan ilk 11 başlar",
                        key=f"f_play_{p['player_id']}"
                    )
                with ev_c3:
                    eval_feas = st.select_slider(
                        "3. Transfer Mantığı & Şartlar (1 - 5):",
                        options=[1, 2, 3, 4, 5],
                        value=4,
                        help="1: Mantıksız / Şartlar imkansız, 3: Mümkün, 5: Çok cazip fırsat",
                        key=f"f_feas_{p['player_id']}"
                    )

                eval_dec = st.radio(
                    "Bu Futbolcu İçin Kararınız:",
                    [
                        "🟢 Kesinlikle Alırım (İlk 11 Hedefi)",
                        "🔵 Rotasyona Alırım (Kadro Derinliği)",
                        "🟡 Scout İzleme Listesine Alırım",
                        "🔴 Pas Geçerim / Uygun Değil"
                    ],
                    index=0,
                    key=f"f_dec_{p['player_id']}"
                )
                
                dec_val_map = {
                    "🟢 Kesinlikle Alırım (İlk 11 Hedefi)": "buy",
                    "🔵 Rotasyona Alırım (Kadro Derinliği)": "rotation",
                    "🟡 Scout İzleme Listesine Alırım": "watchlist",
                    "🔴 Pas Geçerim / Uygun Değil": "reject"
                }

                eval_comment = st.text_input(
                    "Antrenör Olarak Özel Gözleminiz (Opsiyonel):",
                    placeholder="Örn: Pres gücü çok iyi, forvet arkasında aradığımız dinamizmi sağlar...",
                    key=f"f_note_{p['player_id']}"
                )

                submit_eval = st.form_submit_button("💾 Değerlendirmeyi Sisteme Kaydet", type="primary")
                if submit_eval:
                    save_evaluation_to_db(
                        coach_name=st.session_state.get('portal_coach', 'Misafir Antrenör'),
                        club_name=st.session_state.get('portal_club', selected_club),
                        player_id=p['player_id'],
                        player_name=p['name'],
                        target_pos=st.session_state.get('portal_pos', target_pos_cat),
                        formation=st.session_state.get('portal_formation', formation_clean),
                        player_type=st.session_state.get('portal_archetype', selected_archetype),
                        is_known=is_known,
                        model_score=p['recommendation_score'],
                        tactical_fit=eval_tac,
                        playing_time=eval_play,
                        feasibility=eval_feas,
                        decision=dec_val_map[eval_dec],
                        note=eval_comment
                    )
                    st.toast(f"✅ {p['name']} için değerlendirmeniz başarıyla kaydedildi!")
                    st.success(f"Teşekkürler Hocam! **{p['name']}** için verdiğiniz geri bildirim veritabanına işlendi.")

            st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# SEKME 2: 📊 CANLI MODEL İSABETİ & DOĞRULAMA RAPORU
# =============================================================================
with portal_tab2:
    st.subheader("📊 Antrenör Geri Bildirimleri & Model İsabet İstatistikleri")
    st.caption("Teknik direktörlerin verdiği puanlar ve kararlar doğrultusunda modelimizin gerçek dünya isabet analizi.")
    
    all_evals = load_evaluations_summary()
    
    if len(all_evals) == 0:
        st.info("Henüz kaydedilmiş antrenör değerlendirmesi bulunmuyor.")
    else:
        kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
        
        tot_cnt = len(all_evals)
        avg_tac_sc = all_evals['tactical_fit_rating'].mean()
        accepted_cnt = all_evals['decision'].isin(['buy', 'rotation', 'watchlist']).sum()
        acc_rate = (accepted_cnt / tot_cnt) * 100.0
        known_rate = (all_evals['is_known'].sum() / tot_cnt) * 100.0 if 'is_known' in all_evals else 70.0
        
        kpi_c1.metric("Toplam Puanlanan Oyuncu", f"{tot_cnt}")
        kpi_c2.metric("Ortalama Taktik Uyum", f"{avg_tac_sc:.2f} / 5.0", f"%{avg_tac_sc/5*100:.1f} Başarı")
        kpi_c3.metric("Transfer Kabul Oranı", f"%{acc_rate:.1f}", "Alırım + Rotasyon")
        kpi_c4.metric("Ligde Bilinirlik Oranı", f"%{known_rate:.1f}", "Tanınan Oyuncular")

        st.write("---")

        rep_c1, rep_c2 = st.columns(2)
        
        with rep_c1:
            st.subheader("🎯 Antrenör Kararlarının Dağılımı")
            dec_label_map = {
                'buy': 'Kesinlikle Alırım',
                'rotation': 'Rotasyona Alırım',
                'watchlist': 'İzleme Listesi',
                'reject': 'Pas Geçerim'
            }
            mapped_dec = all_evals['decision'].map(dec_label_map).value_counts().reset_index()
            mapped_dec.columns = ['Karar', 'Adet']
            fig_p = px.pie(
                mapped_dec, values='Adet', names='Karar',
                hole=0.45,
                color='Karar',
                color_discrete_map={
                    'Kesinlikle Alırım': '#10b981',
                    'Rotasyona Alırım': '#3b82f6',
                    'İzleme Listesi': '#f59e0b',
                    'Pas Geçerim': '#ef4444'
                }
            )
            fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#f1f5f9'))
            st.plotly_chart(fig_p, use_container_width=True)

        with rep_c2:
            st.subheader("📈 Model Öneri Skoru vs. Antrenör Memnuniyeti")
            fig_sc = px.scatter(
                all_evals, x='model_score', y='tactical_fit_rating',
                color='decision', hover_name='player_name',
                labels={'model_score': 'Model Öneri Skoru (0-100)', 'tactical_fit_rating': 'Antrenör Puanı (1-5)'},
                color_discrete_map={'buy': '#10b981', 'rotation': '#3b82f6', 'watchlist': '#f59e0b', 'reject': '#ef4444'}
            )
            fig_sc.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f1f5f9'),
                xaxis=dict(showgrid=True, gridcolor='#1e293b'),
                yaxis=dict(showgrid=True, gridcolor='#1e293b', dtick=1)
            )
            st.plotly_chart(fig_sc, use_container_width=True)

        st.write("---")

        st.subheader("📑 Son Kaydedilen Değerlendirmeler")
        cols_to_show = ['created_at', 'coach_name', 'club_name', 'player_name', 'target_position', 'formation', 'player_type', 'tactical_fit_rating', 'decision', 'feedback_note']
        existing_cols = [c for c in cols_to_show if c in all_evals.columns]
        
        st.dataframe(all_evals[existing_cols], use_container_width=True, height=350)
        
        csv_out = all_evals.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Antrenör Doğrulama Raporunu İndir (CSV)",
            data=csv_out,
            file_name="scoutme_antrenor_dogrulama_veriseti.csv",
            mime="text/csv"
        )

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 50px; padding: 20px; color: #64748b; font-size: 0.85rem; border-top: 1px solid #1e293b;">
    ScoutMe Yüksek Lisans Tezi &bull; Doğu Akdeniz Üniversitesi (DAÜ / EMU) Bilgisayar Mühendisliği &bull; 2026
</div>
""", unsafe_allow_html=True)
