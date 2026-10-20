"""
ScoutMe - Antrenör & Scout Özel Değerlendirme Portalı (Swiss Pitch Minimal)
==========================================================================
Stitch MCP "Swiss Pitch Minimal" Tasarım Sistemi (Siyah & Beyaz Monokrom)
ile Sadeleştirilmiş Taktiksel Transfer Keşif ve Model Doğrulama Arayüzü.

Tasarım Spesifikasyonu (Stitch Asset: assets/cff8c06daa384d6da7d971ba084df414):
- Zemin (Canvas Base): #FFFFFF (Saf Beyaz)
- Yapısal Yüzeyler (Surfaces): #FAFAFA, #F4F4F5
- İnce Çizgiler (Hairlines): 1px solid #E4E4E7, #D4D4D8
- Birincil Mürekkep (Primary Ink): #09090B, #000000 (Keskin Siyah)
- İkincil Metin (Muted Metadata): #71717A
- Tipografi: Space Grotesk (Başlıklar, Metrikler, Etiketler) & Inter (Gövde)
"""

import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from recommender.recommender_engine import ScoutMeRecommender, normalize_text

# =============================================================================
# SAYFA VE STITCH "SWISS PITCH MINIMAL" STİL YAPILANDIRMASI
# =============================================================================
st.set_page_config(
    page_title="SCOUTME // Antrenör Değerlendirme Portalı",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');

    /* =========================================================================
       STITCH DESIGN SYSTEM: SWISS PITCH MINIMAL (PURE BLACK & WHITE)
       ========================================================================= */
    :root {
        --bg-canvas: #FFFFFF;
        --surface-low: #FAFAFA;
        --surface-mid: #F4F4F5;
        --border-hairline: #E4E4E7;
        --border-strong: #D4D4D8;
        --ink-primary: #09090B;
        --ink-black: #000000;
        --ink-secondary: #3F3F46;
        --ink-muted: #71717A;
    }

    /* Ana Uygulama Zemini */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: var(--bg-canvas) !important;
        color: var(--ink-primary) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    [data-testid="stHeader"] {
        background-color: var(--bg-canvas) !important;
        border-bottom: 1px solid var(--border-hairline);
    }

    .block-container {
        max-width: 1180px !important;
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
    }

    /* Genel Tipografi Sıfırlama */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: var(--ink-primary) !important;
        letter-spacing: -0.02em;
    }

    p, span, label, div {
        color: var(--ink-primary);
    }

    /* Üst Mimari Başlık (Swiss Header) */
    .swiss-header {
        background: var(--bg-canvas);
        border-top: 3px solid var(--ink-black);
        border-bottom: 1px solid var(--border-hairline);
        padding: 20px 0 18px 0;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        flex-wrap: wrap;
        gap: 12px;
    }
    .swiss-brand-tag {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--ink-muted);
        margin-bottom: 4px;
    }
    .swiss-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.85rem;
        font-weight: 700;
        color: var(--ink-black);
        letter-spacing: -0.03em;
        margin: 0;
        line-height: 1.15;
    }
    .swiss-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 0.88rem;
        color: var(--ink-muted);
        margin-top: 4px;
    }
    .swiss-meta-badge {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        background: var(--surface-mid);
        color: var(--ink-primary);
        border: 1px solid var(--border-hairline);
        padding: 6px 12px;
    }

    /* Bölüm Başlıkları */
    .section-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        color: var(--ink-black);
        padding-bottom: 8px;
        border-bottom: 1px solid var(--ink-black);
        margin-bottom: 16px;
        margin-top: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .section-header span.step-num {
        background: var(--ink-black);
        color: #FFFFFF;
        padding: 2px 7px;
        font-size: 0.68rem;
        margin-right: 8px;
    }

    /* Streamlit Form ve Girdi Kontrolleri (Monokrom) */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"] {
        background-color: var(--bg-canvas) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 0px !important;
        color: var(--ink-primary) !important;
        box-shadow: none !important;
    }
    div[data-baseweb="select"] > div:focus-within,
    div[data-baseweb="input"] > div:focus-within {
        border-color: var(--ink-black) !important;
    }
    div[data-baseweb="select"] span,
    input[type="text"] {
        color: var(--ink-primary) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
    }

    /* Açılır Menü Listesi */
    ul[data-testid="stSelectboxVirtualDropdown"],
    div[data-baseweb="popover"] {
        background-color: var(--bg-canvas) !important;
        border: 1px solid var(--ink-black) !important;
        border-radius: 0px !important;
    }
    li[role="option"] {
        background-color: var(--bg-canvas) !important;
        color: var(--ink-primary) !important;
    }
    li[role="option"]:hover, li[aria-selected="true"] {
        background-color: var(--surface-mid) !important;
        color: var(--ink-black) !important;
        font-weight: 600;
    }

    /* Etiketler (Labels) */
    [data-testid="stWidgetLabel"] p {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 0.74rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: var(--ink-secondary) !important;
    }

    /* Butonlar (Keskin Siyah & Beyaz) */
    .stButton > button,
    .stFormSubmitButton > button,
    .stDownloadButton > button {
        background-color: var(--ink-black) !important;
        color: #FFFFFF !important;
        border: 1px solid var(--ink-black) !important;
        border-radius: 0px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        padding: 0.65rem 1.25rem !important;
        transition: all 0.15s ease !important;
        box-shadow: none !important;
    }
    .stButton > button p,
    .stFormSubmitButton > button p,
    .stDownloadButton > button p {
        color: #FFFFFF !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover,
    .stFormSubmitButton > button:hover,
    .stDownloadButton > button:hover {
        background-color: #27272A !important;
        border-color: #27272A !important;
        color: #FFFFFF !important;
    }

    /* Sekmeler (Tabs) */
    button[data-baseweb="tab"] {
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: var(--ink-muted) !important;
        padding: 10px 20px !important;
        border-radius: 0px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--ink-black) !important;
        background-color: var(--surface-low) !important;
        border-bottom: 2px solid var(--ink-black) !important;
    }
    div[data-baseweb="tab-highlight"] {
        background-color: var(--ink-black) !important;
    }

    /* Expander ve Form Konteynerleri */
    [data-testid="stExpander"] {
        background-color: var(--surface-low) !important;
        border: 1px solid var(--border-hairline) !important;
        border-radius: 0px !important;
    }
    [data-testid="stForm"] {
        background-color: var(--surface-low) !important;
        border: 1px solid var(--border-hairline) !important;
        border-radius: 0px !important;
        padding: 18px !important;
    }

    /* Oyuncu Kartı (Swiss Monochrome Card) */
    .swiss-card-header {
        background: var(--surface-low);
        border: 1px solid var(--border-hairline);
        border-top: 2px solid var(--ink-black);
        padding: 14px 18px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 22px;
    }
    .swiss-rank-tag {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        background: var(--ink-black);
        color: #FFFFFF;
        padding: 4px 9px;
    }
    .swiss-player-name {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--ink-black);
        letter-spacing: -0.02em;
        margin: 0 10px;
    }
    .swiss-pos-tag {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        border: 1px solid var(--border-strong);
        background: #FFFFFF;
        color: var(--ink-secondary);
        padding: 3px 8px;
    }
    .swiss-ovr-badge {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.95rem;
        font-weight: 700;
        background: var(--ink-black);
        color: #FFFFFF;
        padding: 5px 12px;
        letter-spacing: -0.01em;
    }
    .swiss-fit-badge {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.85rem;
        font-weight: 700;
        background: #FFFFFF;
        color: var(--ink-black);
        border: 1px solid var(--ink-black);
        padding: 4px 10px;
    }

    /* Fotoğraf Çerçevesi */
    .swiss-photo-box {
        width: 115px;
        height: 142px;
        border: 1px solid var(--border-strong);
        background: var(--surface-low);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }
    .swiss-photo-box img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        filter: grayscale(100%) contrast(1.08);
    }
    .swiss-photo-initials {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--ink-muted);
    }

    /* Yatay Beceri Çubukları (Monochrome Attribute Matrix) */
    .skill-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin: 12px 0;
    }
    .skill-cell {
        background: var(--surface-low);
        border: 1px solid var(--border-hairline);
        padding: 8px 10px;
    }
    .skill-top {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 6px;
    }
    .skill-label {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: var(--ink-muted);
    }
    .skill-val {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.95rem;
        font-weight: 700;
        color: var(--ink-black);
        font-variant-numeric: tabular-nums;
    }
    .skill-track {
        width: 100%;
        height: 4px;
        background: var(--border-hairline);
    }
    .skill-fill {
        height: 100%;
        background: var(--ink-black);
    }

    /* Scout Raporu Not Kutusu */
    .swiss-verdict-box {
        background: var(--surface-low);
        border-left: 2px solid var(--ink-black);
        padding: 10px 14px;
        font-size: 0.86rem;
        color: var(--ink-secondary);
        margin-top: 8px;
    }

    /* Kariyer Bilgi Kartı */
    .swiss-career-sheet {
        background: var(--surface-low);
        border: 1px solid var(--ink-black);
        padding: 14px 18px;
        margin: 12px 0;
    }
    .swiss-career-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.76rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--ink-black);
        margin-bottom: 8px;
        border-bottom: 1px solid var(--border-hairline);
        padding-bottom: 6px;
    }

    /* KPI Kutuları */
    .swiss-kpi {
        background: var(--surface-low);
        border: 1px solid var(--border-hairline);
        border-top: 2px solid var(--ink-black);
        padding: 16px;
    }
    .swiss-kpi-label {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--ink-muted);
    }
    .swiss-kpi-value {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--ink-black);
        margin-top: 4px;
        font-variant-numeric: tabular-nums;
    }
    .swiss-kpi-sub {
        font-size: 0.76rem;
        color: var(--ink-muted);
        margin-top: 2px;
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
# MİMARİ ÜST BAŞLIK (SWISS PITCH MINIMAL HEADER)
# =============================================================================
st.markdown("""
<div class="swiss-header">
    <div>
        <div class="swiss-brand-tag">SCOUTME // MULTI-STAKEHOLDER RECSYS</div>
        <h1 class="swiss-title">ANTRENÖR DEĞERLENDİRME PORTALI</h1>
        <div class="swiss-subtitle">A Takım Teknik Direktörleri İçin Taktiksel Oyuncu Keşif ve Doğrulama Arayüzü</div>
    </div>
    <div class="swiss-meta-badge">KTFF 2026–2027 VERİ TABANI</div>
</div>
""", unsafe_allow_html=True)

portal_tab1, portal_tab2 = st.tabs([
    "01 // TAKTİKSEL TRANSFER SİHİRBAZI",
    "02 // DOĞRULAMA METRİKLERİ & İSABET RAPORU"
])


# =============================================================================
# SEKME 1: 01 // TAKTİKSEL TRANSFER SİHİRBAZI
# =============================================================================
with portal_tab1:

    # -------------------------------------------------------------------------
    # ADIM 01 & 02: KOMPAKT YAPILANDIRMA IZGARASI
    # -------------------------------------------------------------------------
    st.markdown('<div class="section-header"><div><span class="step-num">01</span>ANTRENÖR, KULÜP VE TAKTİKSEL PROFİL SEÇİMİ</div><span>PARAMETRE GİRİŞİ</span></div>', unsafe_allow_html=True)

    c_col1, c_col2 = st.columns(2)
    coach_list = sorted(list(coaches_df['name'].unique()))
    with c_col1:
        selected_coach = st.selectbox(
            "TEKNİK DİREKTÖR / DEĞERLENDİRİCİ",
            ["Misafir Antrenör / Scout"] + coach_list,
            index=coach_list.index("ERDİNÇ BÖREKÇİ") + 1 if "ERDİNÇ BÖREKÇİ" in coach_list else 0
        )
        if selected_coach == "Misafir Antrenör / Scout":
            coach_display_name = st.text_input("ADINIZ VE SOYADINIZ", value="Misafir Teknik Direktör")
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
            "KULÜP",
            club_names,
            index=default_club_idx
        )

    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        selected_formation = st.selectbox(
            "TAKTİK DİZİLİŞ",
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
        selected_pos_label = st.selectbox("ARANAN MEVKİ", list(pos_options.keys()), index=0)
        target_pos_cat = pos_options[selected_pos_label]

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
            "Oyun Kurucu / Metronom (Yüksek Pas & Skor Katkısı)",
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
        selected_archetype = st.selectbox("OYUNCU ARKETİPİ", archetypes, index=0)

    with st.expander("GELİŞMİŞ FİLTRELER (GİZLİ YETENEK KATSAYISI & U21 FİLTRESİ)", expanded=False):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            lambda_val = st.slider(
                "POPÜLARİTE CEZASI (λ)",
                min_value=0.0, max_value=0.50, value=0.20, step=0.05,
                help="Yüksek λ değeri tanınmış oyuncular yerine alt ligdeki yüksek potansiyelli oyuncuları öne çıkarır."
            )
        with col_f2:
            st.write("")
            youth_filter = st.checkbox("YALNIZCA U21 GENÇ YETENEKLERİ LİSTELE (YAŞ ≤ 21)", value=False)

    run_btn = st.button("TAKTİKSEL OYUNCU ÖNERİLERİNİ LİSTELE →", type="primary", use_container_width=True)

    # =========================================================================
    # ADIM 02: ÖNERİ KARTLARI VE DOĞRULAMA AKIŞI
    # =========================================================================
    if run_btn or 'portal_recs' in st.session_state:
        if run_btn:
            recs = recommender.recommend_players_for_club(
                selected_club,
                target_position=target_pos_cat,
                top_k=4,
                lambda_popularity=lambda_val,
                youth_only=youth_filter,
                formation=formation_clean,
                sub_position_label=selected_pos_label,
                player_archetype=selected_archetype,
                coach_identifier=coach_display_name
            )
            st.session_state['portal_recs'] = recs
            st.session_state['portal_club'] = selected_club
            st.session_state['portal_coach'] = coach_display_name
            st.session_state['portal_formation'] = formation_clean
            st.session_state['portal_pos'] = target_pos_cat
            st.session_state['portal_archetype'] = selected_archetype

        recs = st.session_state.get('portal_recs', [])

        st.markdown(
            f'<div class="section-header" style="margin-top:28px;">'
            f'<div><span class="step-num">02</span>{st.session_state.get("portal_club")} // ÖNERİLEN ADAYLAR ({len(recs)})</div>'
            f'<span>{st.session_state.get("portal_formation")} • {st.session_state.get("portal_archetype")}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        for idx, p in enumerate(recs, 1):
            p_full, p_seasons = get_player_full_details(p['player_id'])
            photo_url = p_full[4] if (p_full and len(p_full) > 4 and p_full[4]) else None
            initials = "".join([w[0] for w in p['name'].split()[:2]]) if p['name'] else "OY"

            # Kart Üst Şeridi
            st.markdown(f"""
            <div class="swiss-card-header">
                <div style="display:flex; align-items:center; flex-wrap:wrap; gap:6px;">
                    <span class="swiss-rank-tag">ADAY #{idx:02d}</span>
                    <span class="swiss-player-name">{p['name']}</span>
                    <span class="swiss-pos-tag">{p['prim_pos']}</span>
                    <span style="font-size:0.78rem; color:#71717A; margin-left:6px;">LİSANS #{p['license_no']}</span>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span class="swiss-fit-badge">UYUM %{p['tactical_fit_pct']}</span>
                    <span class="swiss-pos-tag">İLK 11 ŞANSI %{p['playing_time_chance_pct']}</span>
                    <span class="swiss-ovr-badge">{p['ovr']} OVR</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Kart Gövdesi
            body_c1, body_c2 = st.columns([1.4, 8.6])
            with body_c1:
                if photo_url:
                    st.markdown(f"""
                    <div class="swiss-photo-box">
                        <img src="{photo_url}" alt="{p['name']}" />
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="swiss-photo-box">
                        <div class="swiss-photo-initials">{initials}</div>
                        <div style="font-size:0.65rem; color:#71717A; margin-top:4px;">#{p['license_no']}</div>
                    </div>
                    """, unsafe_allow_html=True)

            with body_c2:
                tags_html = " &bull; ".join([f"<span style='font-family:Space Grotesk; font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; border:1px solid #D4D4D8; padding:2px 6px; background:#FAFAFA;'>{t}</span>" for t in p.get('scout_tags', [])])
                st.markdown(f"""
                <div style="font-size:0.86rem; color:#3F3F46; margin-bottom:6px; display:flex; justify-content:space-between; flex-wrap:wrap;">
                    <div><strong>{p['age']} YAŞ</strong> &nbsp;|&nbsp; KULÜP: <strong>{p['current_club']}</strong> &nbsp;|&nbsp; A-TAKIM MAÇ: <strong>{p.get('a_team_matches', 0)}</strong> <span style="color:#71717A;">(Toplam: {p['played_matches']})</span></div>
                    <div>{tags_html}</div>
                </div>
                <div class="skill-grid">
                    <div class="skill-cell">
                        <div class="skill-top"><span class="skill-label">FİZİKSEL</span><span class="skill-val">{p['phys']:.0f}</span></div>
                        <div class="skill-track"><div class="skill-fill" style="width:{min(100, max(0, p['phys']))}%;"></div></div>
                    </div>
                    <div class="skill-cell">
                        <div class="skill-top"><span class="skill-label">ŞUT</span><span class="skill-val">{p['shoot']:.0f}</span></div>
                        <div class="skill-track"><div class="skill-fill" style="width:{min(100, max(0, p['shoot']))}%;"></div></div>
                    </div>
                    <div class="skill-cell">
                        <div class="skill-top"><span class="skill-label">TEKNİK</span><span class="skill-val">{p['tech']:.0f}</span></div>
                        <div class="skill-track"><div class="skill-fill" style="width:{min(100, max(0, p['tech']))}%;"></div></div>
                    </div>
                    <div class="skill-cell">
                        <div class="skill-top"><span class="skill-label">DEFANS</span><span class="skill-val">{p['def']:.0f}</span></div>
                        <div class="skill-track"><div class="skill-fill" style="width:{min(100, max(0, p['def']))}%;"></div></div>
                    </div>
                </div>
                <div class="swiss-verdict-box">
                    <strong style="font-family:'Space Grotesk', sans-serif; font-size:0.74rem; text-transform:uppercase; letter-spacing:0.06em; color:#000000;">MODEL GEREKÇESİ //</strong> {p["scout_verdict"]}
                </div>
                """, unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # ADIM 03: BİLİNİRLİK KONTROLÜ & PUANLAMA FORMU
            # -----------------------------------------------------------------
            knows_key = f"knows_{p['player_id']}_{idx}"
            is_known_choice = st.radio(
                f"{p['name']} İSİMLİ OYUNCUYU DAHA ÖNCE LİGDE İZLEDİNİZ Mİ?",
                ["Evet, oyuncuyu tanıyorum", "Hayır, tanımıyorum (Kariyer karnesini göster)"],
                horizontal=True,
                key=knows_key
            )
            is_known = 1 if "Evet" in is_known_choice else 0

            if is_known == 0 and p_full:
                st.markdown(f"""
                <div class="swiss-career-sheet">
                    <div class="swiss-career-title">{p['name']} — RESMİ KTFF PERFORMANS ÖZETİ</div>
                    <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; font-size:0.82rem; color:#3F3F46;">
                        <div><span style="color:#71717A; font-size:0.72rem; text-transform:uppercase; display:block;">DOĞUM TARİHİ</span><strong>{p_full[3] or '-'} ({p['age']} Yaş)</strong></div>
                        <div><span style="color:#71717A; font-size:0.72rem; text-transform:uppercase; display:block;">SON 3 SEZON KATILIM</span><strong>{p_full[13]} Maç (İlk 11: %{p_full[15]*100:.0f})</strong></div>
                        <div><span style="color:#71717A; font-size:0.72rem; text-transform:uppercase; display:block;">SKOR ÜRETİMİ</span><strong>{p_full[14]} Gol ({p_full[12]} Gol/90dk)</strong></div>
                        <div><span style="color:#71717A; font-size:0.72rem; text-transform:uppercase; display:block;">SAHA İÇİ NET AVERAJ</span><strong>{p_full[11]:+.2f} / 90dk (CI: %{p_full[10]*100:.0f})</strong></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if p_seasons:
                    season_df = pd.DataFrame(p_seasons, columns=['Sezon', 'Toplam Maç', 'İlk 11', 'Gol', 'Sarı Kart', 'Kırmızı Kart'])
                    st.dataframe(season_df, hide_index=True, use_container_width=True)

            with st.form(key=f"coach_eval_form_{p['player_id']}_{idx}"):
                ev_c1, ev_c2, ev_c3 = st.columns(3)

                with ev_c1:
                    eval_tac = st.select_slider(
                        "01. TAKTİKSEL UYUM (1–5)",
                        options=[1, 2, 3, 4, 5],
                        value=4,
                        key=f"f_tac_{p['player_id']}"
                    )
                with ev_c2:
                    eval_play = st.select_slider(
                        "02. İLK 11 / SÜRE ŞANSI (1–5)",
                        options=[1, 2, 3, 4, 5],
                        value=4,
                        key=f"f_play_{p['player_id']}"
                    )
                with ev_c3:
                    eval_feas = st.select_slider(
                        "03. TRANSFER MANTIĞI (1–5)",
                        options=[1, 2, 3, 4, 5],
                        value=4,
                        key=f"f_feas_{p['player_id']}"
                    )

                eval_dec = st.radio(
                    "TRANSFER KARARINIZ",
                    [
                        "Kesinlikle Alırım (İlk 11 Hedefi)",
                        "Rotasyona Alırım (Kadro Derinliği)",
                        "Scout İzleme Listesine Alırım",
                        "Pas Geçerim / Uygun Değil"
                    ],
                    horizontal=True,
                    index=0,
                    key=f"f_dec_{p['player_id']}"
                )

                dec_val_map = {
                    "Kesinlikle Alırım (İlk 11 Hedefi)": "buy",
                    "Rotasyona Alırım (Kadro Derinliği)": "rotation",
                    "Scout İzleme Listesine Alırım": "watchlist",
                    "Pas Geçerim / Uygun Değil": "reject"
                }

                form_b1, form_b2 = st.columns([7, 3])
                with form_b1:
                    eval_comment = st.text_input(
                        "TEKNİK NOT (OPSİYONEL)",
                        placeholder="Örn: Pres disiplini ve fizik kalitesi sistemimize uygun...",
                        key=f"f_note_{p['player_id']}"
                    )
                with form_b2:
                    st.write("")
                    submit_eval = st.form_submit_button("DEĞERLENDİRMEYİ KAYDET →", type="primary", use_container_width=True)

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
                    st.toast(f"Kaydedildi: {p['name']}")
                    st.markdown(
                        f"<div style='border:1px solid #09090B; background:#FFFFFF; padding:10px 14px; font-size:0.84rem; font-weight:600;'>"
                        f"✓ {p['name']} için değerlendirmeniz veritabanına kaydedildi.</div>",
                        unsafe_allow_html=True
                    )


# =============================================================================
# SEKME 2: 02 // DOĞRULAMA METRİKLERİ & İSABET RAPORU
# =============================================================================
with portal_tab2:
    st.markdown('<div class="section-header"><div><span class="step-num">01</span>SAHA DOĞRULAMA METRİKLERİ (HUMAN-IN-THE-LOOP)</div><span>CANLI VERİTABANI ÖZETİ</span></div>', unsafe_allow_html=True)

    all_evals = load_evaluations_summary()

    if len(all_evals) == 0:
        st.info("Henüz kaydedilmiş antrenör değerlendirmesi bulunmuyor.")
    else:
        tot_cnt = len(all_evals)
        avg_tac_sc = all_evals['tactical_fit_rating'].mean()
        accepted_cnt = all_evals['decision'].isin(['buy', 'rotation', 'watchlist']).sum()
        acc_rate = (accepted_cnt / tot_cnt) * 100.0
        known_rate = (all_evals['is_known'].sum() / tot_cnt) * 100.0 if 'is_known' in all_evals else 70.0

        kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
        with kpi_c1:
            st.markdown(f"""
            <div class="swiss-kpi">
                <div class="swiss-kpi-label">TOPLAM DEĞERLENDİRME</div>
                <div class="swiss-kpi-value">{tot_cnt}</div>
                <div class="swiss-kpi-sub">Kayıtlı Antrenör Oyu</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_c2:
            st.markdown(f"""
            <div class="swiss-kpi">
                <div class="swiss-kpi-label">ORTALAMA TAKTİK UYUM</div>
                <div class="swiss-kpi-value">{avg_tac_sc:.2f} <span style="font-size:1rem; color:#71717A;">/ 5.0</span></div>
                <div class="swiss-kpi-sub">%{avg_tac_sc/5*100:.1f} Memnuniyet</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_c3:
            st.markdown(f"""
            <div class="swiss-kpi">
                <div class="swiss-kpi-label">TRANSFER KABUL ORANI</div>
                <div class="swiss-kpi-value">%{acc_rate:.1f}</div>
                <div class="swiss-kpi-sub">İlk 11 + Rotasyon + İzleme</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_c4:
            st.markdown(f"""
            <div class="swiss-kpi">
                <div class="swiss-kpi-label">LİG BİLİNİRLİK ORANI</div>
                <div class="swiss-kpi-value">%{known_rate:.1f}</div>
                <div class="swiss-kpi-sub">Tanınan Oyuncu Oranı</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="section-header" style="margin-top:28px;"><div><span class="step-num">02</span>KARAR DAĞILIMI VE MODEL KORELASYONU</div><span>MONOKROM ANALİTİK</span></div>', unsafe_allow_html=True)

        rep_c1, rep_c2 = st.columns(2)

        with rep_c1:
            dec_label_map = {
                'buy': 'Kesinlikle Alırım',
                'rotation': 'Rotasyona Alırım',
                'watchlist': 'İzleme Listesi',
                'reject': 'Uygun Değil'
            }
            mapped_dec = all_evals['decision'].map(dec_label_map).value_counts().reset_index()
            mapped_dec.columns = ['Karar', 'Adet']
            fig_bar = px.bar(
                mapped_dec, x='Karar', y='Adet', text='Adet',
                color='Karar',
                color_discrete_map={
                    'Kesinlikle Alırım': '#09090B',
                    'Rotasyona Alırım': '#3F3F46',
                    'İzleme Listesi': '#71717A',
                    'Uygun Değil': '#D4D4D8'
                }
            )
            fig_bar.update_layout(
                title=dict(text="ANTRENÖR KARAR DAĞILIMI", font=dict(family="Space Grotesk", size=13, color="#09090B")),
                paper_bgcolor='#FFFFFF', plot_bgcolor='#FAFAFA',
                font=dict(family="Inter", color='#09090B', size=12),
                showlegend=False,
                margin=dict(l=20, r=20, t=45, b=20),
                height=320,
                xaxis=dict(title="", showgrid=False, linecolor='#E4E4E7'),
                yaxis=dict(title="Oy Sayısı", showgrid=True, gridcolor='#E4E4E7', dtick=1)
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with rep_c2:
            fig_sc = px.scatter(
                all_evals, x='model_score', y='tactical_fit_rating',
                hover_name='player_name',
                labels={'model_score': 'Model Öneri Skoru (0–100)', 'tactical_fit_rating': 'Antrenör Puanı (1–5)'}
            )
            fig_sc.update_traces(marker=dict(size=10, color='#09090B', line=dict(width=1, color='#FFFFFF')))
            fig_sc.update_layout(
                title=dict(text="MODEL SKORU VS. ANTRENÖR PUANI", font=dict(family="Space Grotesk", size=13, color="#09090B")),
                paper_bgcolor='#FFFFFF', plot_bgcolor='#FAFAFA',
                font=dict(family="Inter", color='#09090B', size=12),
                margin=dict(l=20, r=20, t=45, b=20),
                height=320,
                xaxis=dict(showgrid=True, gridcolor='#E4E4E7', linecolor='#E4E4E7'),
                yaxis=dict(showgrid=True, gridcolor='#E4E4E7', linecolor='#E4E4E7', dtick=1, range=[0.5, 5.5])
            )
            st.plotly_chart(fig_sc, use_container_width=True)

        st.markdown('<div class="section-header" style="margin-top:20px;"><div><span class="step-num">03</span>KAYITLI DEĞERLENDİRME TABLOSU</div><span>SQLITE KAYITLARI</span></div>', unsafe_allow_html=True)
        cols_to_show = ['created_at', 'coach_name', 'club_name', 'player_name', 'target_position', 'formation', 'player_type', 'tactical_fit_rating', 'decision', 'feedback_note']
        existing_cols = [c for c in cols_to_show if c in all_evals.columns]
        st.dataframe(all_evals[existing_cols], use_container_width=True, height=320)

        csv_out = all_evals.to_csv(index=False).encode('utf-8')
        st.download_button(
            "DOĞRULAMA VERİ SETİNİ İNDİR (CSV) →",
            data=csv_out,
            file_name="scoutme_antrenor_dogrulama_veriseti.csv",
            mime="text/csv"
        )

# Footer
st.markdown("""
<div style="display:flex; justify-content:space-between; margin-top:48px; padding-top:16px; color:#71717A; font-size:0.75rem; border-top:1px solid #E4E4E7; font-family:'Space Grotesk', sans-serif; text-transform:uppercase; letter-spacing:0.06em;">
    <span>SCOUTME // YÜKSEK LİSANS TEZ PROJESİ</span>
    <span>DOĞU AKDENİZ ÜNİVERSİTESİ (DAÜ / EMU) BİLGİSAYAR MÜHENDİSLİĞİ • 2026</span>
</div>
""", unsafe_allow_html=True)
