"""
ScoutMe - Antrenör & Scout Özel Değerlendirme Portalı (4 Adımlı Taktiksel Sihirbaz)
====================================================================================
Modern Aydınlık Spor Analitik (Wyscout / Opta Stili - Beyaz/Açık Gri Zemin,
Zümrüt Yeşili & Lacivert Vurgular) Tasarım Sistemi ile 4 Sayfalı Akış:

1. Sayfa: Teknik Direktör Seçimi & Otomatik Kulüp Eşleşmesi -> Devam Et
2. Sayfa: Görsel Diziliş Seçimi -> Saha Üzerindeki Nokta Butonlarıyla Pozisyon Seçimi
          -> Oyuncu Tipi (Arketip) Seçimi -> Devam Et
3. Sayfa: Kaydırmalı (Carousel) Oyuncu Öneri Kartları -> Aktif Oyuncu Detay Karnesi
          -> "Seç" Butonu
4. Sayfa: Tüm Önerilerin Kart Halinde Gösterimi ("★ SEÇİLEN OYUNCU" İbaresiyle)
          -> Antrenör Puanlama ve Yorum Formu -> Kayıt & GitHub Senkronizasyonu
"""

import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from recommender.recommender_engine import ScoutMeRecommender, normalize_text
from database.github_sync import push_evaluations_to_github, pull_evaluations_from_github_to_db

# =============================================================================
# SAYFA YAPILANDIRMASI
# =============================================================================
st.set_page_config(
    page_title="ScoutMe // Antrenör Değerlendirme Portalı",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================================================================
# MODERN AYDINLIK SPOR ANALİTİK (WYSCOUT / OPTA) CSS TASARIM SİSTEMİ
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

    :root {
        --bg-main: #F8FAFC;
        --bg-card: #FFFFFF;
        --bg-subtle: #F1F5F9;
        --navy-900: #0F172A;
        --navy-800: #1E293B;
        --navy-700: #334155;
        --royal-600: #2563EB;
        --royal-500: #3B82F6;
        --emerald-600: #059669;
        --emerald-500: #10B981;
        --emerald-100: #D1FAE5;
        --amber-500: #F59E0B;
        --amber-100: #FEF3C7;
        --text-main: #0F172A;
        --text-secondary: #475569;
        --text-muted: #64748B;
        --border-light: #E2E8F0;
        --border-mid: #CBD5E1;
    }

    /* Ana Uygulama Zemini */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: var(--bg-main) !important;
        color: var(--text-main) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    [data-testid="stHeader"] {
        background-color: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(8px);
        border-bottom: 1px solid var(--border-light);
    }

    .block-container {
        max-width: 1180px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 4rem !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: var(--navy-900) !important;
        letter-spacing: -0.02em;
    }

    /* Üst Başlık Bandı */
    .portal-topbar {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        color: #FFFFFF;
        border-radius: 16px;
        padding: 20px 28px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
    }
    .portal-brand-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16, 185, 129, 0.2);
        border: 1px solid rgba(16, 185, 129, 0.45);
        color: #6EE7B7;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 4px 10px;
        border-radius: 999px;
        margin-bottom: 6px;
    }
    .portal-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.55rem;
        font-weight: 800;
        color: #FFFFFF !important;
        margin: 0;
        line-height: 1.2;
    }
    .portal-subtitle {
        font-size: 0.85rem;
        color: #CBD5E1;
        margin-top: 3px;
    }

    /* 4 Adımlı Sihirbaz (Stepper) Çubuğu */
    .wizard-stepper {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 26px;
    }
    .step-item {
        background: var(--bg-card);
        border: 1px solid var(--border-light);
        border-radius: 12px;
        padding: 12px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        transition: all 0.2s ease;
    }
    .step-item.active {
        border: 2px solid var(--emerald-500);
        background: linear-gradient(180deg, #FFFFFF 0%, #ECFDF5 100%);
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.14);
    }
    .step-item.completed {
        border: 1px solid #A7F3D0;
        background: #F8FAFC;
    }
    .step-circle {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 800;
        font-size: 0.85rem;
        background: var(--bg-subtle);
        color: var(--text-muted);
        flex-shrink: 0;
    }
    .step-item.active .step-circle {
        background: var(--emerald-500);
        color: #FFFFFF;
        box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.2);
    }
    .step-item.completed .step-circle {
        background: var(--navy-900);
        color: #FFFFFF;
    }
    .step-text-wrap {
        overflow: hidden;
    }
    .step-label-small {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--text-muted);
    }
    .step-item.active .step-label-small {
        color: var(--emerald-600);
    }
    .step-label-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.88rem;
        font-weight: 700;
        color: var(--navy-900);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* 1. Sayfa: Teknik Direktör & Kulüp Kartı */
    .coach-id-card {
        background: var(--bg-card);
        border: 2px solid var(--border-light);
        border-left: 6px solid var(--emerald-500);
        border-radius: 16px;
        padding: 24px 28px;
        margin: 20px 0 26px 0;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
    }
    .coach-id-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 0;
        border-bottom: 1px dashed var(--border-light);
        flex-wrap: wrap;
        gap: 10px;
    }
    .coach-id-row:last-child {
        border-bottom: none;
        padding-bottom: 0;
    }
    .coach-id-label {
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--text-muted);
    }
    .coach-id-value {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.22rem;
        font-weight: 800;
        color: var(--navy-900);
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .league-pill {
        background: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
        font-size: 0.74rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 999px;
    }

    /* 2. Sayfa: Görsel Diziliş Kartları */
    .formation-card-box {
        background: var(--bg-card);
        border: 2px solid var(--border-light);
        border-radius: 14px;
        padding: 12px 10px 10px 10px;
        text-align: center;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        margin-bottom: 6px;
    }
    .formation-card-box.selected {
        border: 2.5px solid var(--emerald-500);
        background: #ECFDF5;
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.18);
        transform: translateY(-2px);
    }
    .formation-card-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.05rem;
        font-weight: 800;
        color: var(--navy-900);
        margin-bottom: 8px;
        letter-spacing: -0.01em;
    }
    .formation-card-box.selected .formation-card-title {
        color: var(--emerald-600);
    }

    /* 2. Sayfa: Büyük İnteraktif Futbol Sahası (Üzerindeki Nokta Butonlar) */
    div[data-testid="stVerticalBlock"]:has(> div .interactive-pitch-anchor) {
        background-color: #15803D !important;
        background-image:
            url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 520' preserveAspectRatio='none'><rect x='14' y='14' width='372' height='492' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='3'/><line x1='14' y1='260' x2='386' y2='260' stroke='rgba(255,255,255,0.85)' stroke-width='2.5'/><circle cx='200' cy='260' r='52' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2.5'/><circle cx='200' cy='260' r='4' fill='rgba(255,255,255,0.9)'/><rect x='95' y='14' width='210' height='82' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2.5'/><rect x='145' y='14' width='110' height='32' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2'/><path d='M 160 96 A 42 42 0 0 0 240 96' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2.2'/><rect x='95' y='424' width='210' height='82' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2.5'/><rect x='145' y='474' width='110' height='32' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2'/><path d='M 160 424 A 42 42 0 0 1 240 424' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2.2'/></svg>"),
            repeating-linear-gradient(0deg, #16A34A 0px, #16A34A 48px, #15803D 48px, #15803D 96px) !important;
        background-size: 100% 100%, 100% 96px !important;
        border: 4px solid #FFFFFF !important;
        border-radius: 18px !important;
        padding: 26px 18px 22px 18px !important;
        box-shadow: 0 16px 36px rgba(15, 23, 42, 0.22) !important;
        max-width: 680px !important;
        margin: 8px auto 18px auto !important;
    }

    /* Saha Üzerindeki Oyuncu Nokta Butonları */
    div[data-testid="stVerticalBlock"]:has(> div .interactive-pitch-anchor) .stButton > button {
        border-radius: 999px !important;
        min-height: 54px !important;
        padding: 6px 14px !important;
        background: #FFFFFF !important;
        color: #0F172A !important;
        border: 3px solid #0F172A !important;
        box-shadow: 0 6px 14px rgba(0, 0, 0, 0.32) !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.78rem !important;
        font-weight: 800 !important;
        transition: all 0.18s ease !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div .interactive-pitch-anchor) .stButton > button p {
        color: #0F172A !important;
        font-weight: 800 !important;
        font-size: 0.78rem !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div .interactive-pitch-anchor) .stButton > button:hover {
        transform: scale(1.08) !important;
        background: #FEF3C7 !important;
        border-color: #F59E0B !important;
        box-shadow: 0 0 0 5px rgba(245, 158, 11, 0.35), 0 8px 18px rgba(0,0,0,0.4) !important;
    }
    /* Seçili Saha Noktası (Primary Button) */
    div[data-testid="stVerticalBlock"]:has(> div .interactive-pitch-anchor) .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%) !important;
        color: #FFFFFF !important;
        border: 3px solid #FFFFFF !important;
        box-shadow: 0 0 0 6px rgba(245, 158, 11, 0.45), 0 10px 22px rgba(0,0,0,0.45) !important;
        transform: scale(1.1) !important;
    }
    div[data-testid="stVerticalBlock"]:has(> div .interactive-pitch-anchor) .stButton > button[kind="primary"] p {
        color: #FFFFFF !important;
    }

    /* 3. Sayfa: Kaydırmalı (Sliding Carousel) Oyuncu Kartları (image2.jpeg Stili) */
    .sliding-card {
        background: #FFFFFF;
        border-radius: 22px;
        overflow: hidden;
        border: 2px solid var(--border-light);
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
        transition: all 0.25s ease;
        text-align: center;
        margin-bottom: 10px;
    }
    .sliding-card.active-slide {
        border: 3px solid var(--royal-600);
        box-shadow: 0 16px 36px rgba(37, 99, 235, 0.20);
        transform: translateY(-6px);
    }
    .sliding-card.inactive-slide {
        opacity: 0.72;
        transform: scale(0.95);
    }
    .sliding-card-top {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        padding: 22px 16px 20px 16px;
        position: relative;
        border-bottom-left-radius: 26px;
        border-bottom-right-radius: 26px;
    }
    .sliding-card.active-slide .sliding-card-top {
        background: linear-gradient(135deg, #059669 0%, #2563EB 100%);
    }
    .sliding-avatar-ring {
        width: 96px;
        height: 96px;
        border-radius: 50%;
        border: 3px solid #FFFFFF;
        padding: 3px;
        margin: 0 auto;
        background: rgba(255,255,255,0.15);
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }
    .sliding-avatar-ring img {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        object-fit: cover;
        background: #FFFFFF;
    }
    .sliding-avatar-initials {
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: #FFFFFF;
        color: var(--navy-900);
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.5rem;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .sliding-card-body {
        padding: 16px 18px 18px 18px;
    }
    .sliding-player-name {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.08rem;
        font-weight: 800;
        color: var(--navy-900);
        margin-bottom: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .sliding-player-desc {
        font-size: 0.8rem;
        color: var(--text-secondary);
        line-height: 1.45;
        min-height: 40px;
        margin-bottom: 10px;
    }
    .sliding-metrics-row {
        display: flex;
        justify-content: center;
        gap: 8px;
        flex-wrap: wrap;
    }
    .sliding-pill-ovr {
        background: var(--navy-900);
        color: #FFFFFF;
        font-size: 0.74rem;
        font-weight: 800;
        padding: 4px 11px;
        border-radius: 999px;
    }
    .sliding-pill-fit {
        background: #ECFDF5;
        color: #059669;
        border: 1px solid #A7F3D0;
        font-size: 0.74rem;
        font-weight: 700;
        padding: 4px 11px;
        border-radius: 999px;
    }

    /* Carousel Nokta Göstergeleri */
    .carousel-dots {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        margin: 10px 0 22px 0;
    }
    .c-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #CBD5E1;
        transition: all 0.2s ease;
    }
    .c-dot.active {
        width: 26px;
        border-radius: 999px;
        background: var(--royal-600);
    }

    /* 3. Sayfa: Aktif Oyuncu Detay Paneli */
    .active-player-showcase {
        background: var(--bg-card);
        border: 2px solid var(--border-light);
        border-top: 5px solid var(--emerald-500);
        border-radius: 18px;
        padding: 24px 28px;
        margin-top: 8px;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
    }

    /* Beceri Çubukları */
    .attr-grid-4 {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin: 14px 0;
    }
    .attr-box {
        background: var(--bg-subtle);
        border: 1px solid var(--border-light);
        border-radius: 12px;
        padding: 12px 14px;
    }
    .attr-head {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 6px;
    }
    .attr-name {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        color: var(--text-secondary);
        letter-spacing: 0.05em;
    }
    .attr-score {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.05rem;
        font-weight: 800;
        color: var(--navy-900);
    }
    .attr-bar-bg {
        width: 100%;
        height: 6px;
        background: #E2E8F0;
        border-radius: 999px;
        overflow: hidden;
    }
    .attr-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #2563EB 0%, #10B981 100%);
        border-radius: 999px;
    }

    /* 4. Sayfa: Tüm Öneriler & Seçilen Kart İbaresi */
    .eval-summary-card {
        background: var(--bg-card);
        border: 2px solid var(--border-light);
        border-radius: 16px;
        padding: 18px 20px;
        position: relative;
        transition: all 0.2s ease;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
        margin-bottom: 12px;
    }
    .eval-summary-card.chosen-card {
        border: 3px solid var(--emerald-500);
        background: linear-gradient(180deg, #ECFDF5 0%, #FFFFFF 45%);
        box-shadow: 0 12px 28px rgba(16, 185, 129, 0.18);
    }
    .chosen-ribbon {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, #059669 0%, #10B981 100%);
        color: #FFFFFF;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.74rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 5px 12px;
        border-radius: 999px;
        margin-bottom: 10px;
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.25);
    }
    .other-ribbon {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: var(--bg-subtle);
        color: var(--text-secondary);
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 5px 12px;
        border-radius: 999px;
        margin-bottom: 10px;
    }

    /* Genel Buton Stilleri */
    .stButton > button,
    .stFormSubmitButton > button {
        border-radius: 10px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.86rem !important;
        padding: 0.6rem 1.2rem !important;
        transition: all 0.18s ease !important;
    }
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"] {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.28) !important;
    }
    .stButton > button[kind="primary"] p,
    .stFormSubmitButton > button[kind="primary"] p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #047857 0%, #059669 100%) !important;
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)


def render_html(html_str: str):
    """Satır başı girintileri ve boş satırları temizleyerek Markdown'ın HTML'i kod bloğu olarak göstermesini engeller."""
    cleaned = "\n".join(line.strip() for line in html_str.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


# =============================================================================
# VERİ VE MODEL YÜKLEYİCİLER
# =============================================================================
@st.cache_resource
def get_recommender():
    return ScoutMeRecommender(embeddings_path='data/hgnn_embeddings.pt')


@st.cache_data
def get_coaches_and_clubs():
    conn = sqlite3.connect('data/ktff.db')
    coaches_df = pd.read_sql_query(
        'SELECT id, name, club_name, role FROM coaches ORDER BY name ASC', conn
    )
    clubs_df = pd.read_sql_query(
        'SELECT id, name, league_name, city FROM clubs ORDER BY league_name DESC, name ASC', conn
    )
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


@st.cache_resource
def init_remote_evaluations_if_cloud():
    """Restores evaluations from GitHub 'evaluations-data' branch on cloud container boot."""
    import os
    if os.name != 'nt':
        try:
            pull_evaluations_from_github_to_db()
        except Exception:
            pass
    return True


init_remote_evaluations_if_cloud()


def save_evaluation_to_db(coach_name, club_name, player_id, player_name,
                          target_pos, formation, player_type, is_known,
                          model_score, tactical_fit, playing_time,
                          feasibility, decision, note, sync_now=True):
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
    if sync_now:
        push_evaluations_to_github()


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
# TAKTİK DİZİLİŞLER, SAHA KOORDİNATLARI VE OYUNCU TİPLERİ (ARKETİPLER)
# =============================================================================
ARCHETYPE_MAP = {
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

# Her diziliş için:
# - rows: İnteraktif saha üzerinde yukarıdan aşağıya (Hücum -> Kaleci) tıklanabilir nokta butonları
#   Her düğüm: (node_id, kısa_kod, tam_etiket, pos_cat, sub_pos_label, svg_x, svg_y)
FORMATIONS_SPEC = {
    "4-4-2": {
        "subtitle": "Klasik Çift Santrafor & Dengeli Dörtlü Hatlar",
        "rows": [
            [
                ("ST_L", "SNT", "Sol Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 36, 18),
                ("ST_R", "SNT", "Sağ Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 64, 18),
            ],
            [
                ("LM", "SLK", "Sol Kanat (LM)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 16, 44),
                ("CM_L", "MO", "Sol Merkez Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 38, 46),
                ("CM_R", "MO", "Sağ Merkez Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 62, 46),
                ("RM", "SĞK", "Sağ Kanat (RM)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 84, 44),
            ],
            [
                ("LB", "SLB", "Sol Bek (LB)", "DF", "Bek / Kanat Bek (LB/RB)", 16, 72),
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 38, 74),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 62, 74),
                ("RB", "SĞB", "Sağ Bek (RB)", "DF", "Bek / Kanat Bek (LB/RB)", 84, 72),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    },
    "4-3-3": {
        "subtitle": "Geniş Kanat Forvetler & Üçlü Merkez Üçgeni",
        "rows": [
            [
                ("LW", "SLK", "Sol Kanat Forvet (LW)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 20, 20),
                ("ST", "SNT", "Merkez Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 50, 16),
                ("RW", "SĞK", "Sağ Kanat Forvet (RW)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 80, 20),
            ],
            [
                ("CM_L", "MO", "Sol İç Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 28, 44),
                ("CDM", "DOS", "Defansif Orta Saha / Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 50, 50),
                ("CM_R", "MO", "Sağ İç Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 72, 44),
            ],
            [
                ("LB", "SLB", "Sol Bek (LB)", "DF", "Bek / Kanat Bek (LB/RB)", 16, 72),
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 38, 74),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 62, 74),
                ("RB", "SĞB", "Sağ Bek (RB)", "DF", "Bek / Kanat Bek (LB/RB)", 84, 72),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    },
    "4-2-3-1": {
        "subtitle": "Çift Ön Libero, 10 Numara & Tek Santrafor",
        "rows": [
            [
                ("ST", "SNT", "Merkez Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 50, 16),
            ],
            [
                ("LW", "SLK", "Sol Açık / Kanat (LW)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 20, 34),
                ("CAM", "MOO", "Ofansif Orta Saha / 10 Numara (CAM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 50, 34),
                ("RW", "SĞK", "Sağ Açık / Kanat (RW)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 80, 34),
            ],
            [
                ("CDM_L", "DOS", "Sol Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 36, 53),
                ("CDM_R", "DOS", "Sağ Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 64, 53),
            ],
            [
                ("LB", "SLB", "Sol Bek (LB)", "DF", "Bek / Kanat Bek (LB/RB)", 16, 73),
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 38, 75),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 62, 75),
                ("RB", "SĞB", "Sağ Bek (RB)", "DF", "Bek / Kanat Bek (LB/RB)", 84, 73),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    },
    "3-5-2": {
        "subtitle": "Üçlü Stoper Hattı, Dinamik Kanat Bekler & Çift Forvet",
        "rows": [
            [
                ("ST_L", "SNT", "Sol Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 36, 18),
                ("ST_R", "SNT", "Sağ Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 64, 18),
            ],
            [
                ("LWB", "SLKB", "Sol Kanat Bek (LWB)", "DF", "Bek / Kanat Bek (LB/RB)", 14, 44),
                ("CM_L", "MO", "Sol Merkez Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 32, 44),
                ("CDM", "DOS", "Merkez Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 50, 48),
                ("CM_R", "MO", "Sağ Merkez Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 68, 44),
                ("RWB", "SĞKB", "Sağ Kanat Bek (RWB)", "DF", "Bek / Kanat Bek (LB/RB)", 86, 44),
            ],
            [
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 26, 73),
                ("CB_C", "STP", "Merkez Lider Stoper (CB)", "DF", "Stoper / Savunma (CB)", 50, 75),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 74, 73),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    },
    "3-4-3": {
        "subtitle": "Üçlü Savunma, Dörtlü Orta Blok & Üçlü Hücum Hattı",
        "rows": [
            [
                ("LW", "SLK", "Sol Kanat Forvet (LW)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 22, 20),
                ("ST", "SNT", "Merkez Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 50, 17),
                ("RW", "SĞK", "Sağ Kanat Forvet (RW)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 78, 20),
            ],
            [
                ("LM", "SLKB", "Sol Kanat Bek (LM)", "DF", "Bek / Kanat Bek (LB/RB)", 15, 46),
                ("CM_L", "MO", "Sol Merkez Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 38, 46),
                ("CM_R", "MO", "Sağ Merkez Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 62, 46),
                ("RM", "SĞKB", "Sağ Kanat Bek (RM)", "DF", "Bek / Kanat Bek (LB/RB)", 85, 46),
            ],
            [
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 26, 73),
                ("CB_C", "STP", "Merkez Stoper (CB)", "DF", "Stoper / Savunma (CB)", 50, 75),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 74, 73),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    },
    "4-1-4-1": {
        "subtitle": "Tek Defansif Çapa & Dörtlü Ofansif Orta Saha",
        "rows": [
            [
                ("ST", "SNT", "Tek Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 50, 16),
            ],
            [
                ("LM", "SLK", "Sol Kanat (LM)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 16, 38),
                ("CM_L", "MO", "Sol Ofansif 8 Numara (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 38, 38),
                ("CM_R", "MO", "Sağ Ofansif 8 Numara (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 62, 38),
                ("RM", "SĞK", "Sağ Kanat (RM)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 84, 38),
            ],
            [
                ("CDM", "DOS", "Defansif Çapa / Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 50, 56),
            ],
            [
                ("LB", "SLB", "Sol Bek (LB)", "DF", "Bek / Kanat Bek (LB/RB)", 16, 74),
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 38, 76),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 62, 76),
                ("RB", "SĞB", "Sağ Bek (RB)", "DF", "Bek / Kanat Bek (LB/RB)", 84, 74),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    },
    "4-5-1": {
        "subtitle": "Kalabalık Beşli Orta Saha Bloğu & Tek Santrafor",
        "rows": [
            [
                ("ST", "SNT", "Merkez Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 50, 17),
            ],
            [
                ("LM", "SLK", "Sol Kanat (LM)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 14, 43),
                ("CM_L", "MO", "Sol İç Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 32, 43),
                ("CDM", "DOS", "Merkez Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 50, 45),
                ("CM_R", "MO", "Sağ İç Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 68, 43),
                ("RM", "SĞK", "Sağ Kanat (RM)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 86, 43),
            ],
            [
                ("LB", "SLB", "Sol Bek (LB)", "DF", "Bek / Kanat Bek (LB/RB)", 16, 73),
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 38, 75),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 62, 75),
                ("RB", "SĞB", "Sağ Bek (RB)", "DF", "Bek / Kanat Bek (LB/RB)", 84, 73),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    },
    "5-3-2": {
        "subtitle": "Beşli Savunma Hattı, Üçlü Merkez & Çift Santrafor",
        "rows": [
            [
                ("ST_L", "SNT", "Sol Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 36, 18),
                ("ST_R", "SNT", "Sağ Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 64, 18),
            ],
            [
                ("CM_L", "MO", "Sol Merkez Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 26, 45),
                ("CDM", "DOS", "Merkez Orta Saha / Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 50, 44),
                ("CM_R", "MO", "Sağ Merkez Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 74, 45),
            ],
            [
                ("LWB", "SLB", "Sol Kanat Bek (LWB)", "DF", "Bek / Kanat Bek (LB/RB)", 12, 71),
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 31, 74),
                ("CB_C", "STP", "Merkez Stoper (CB)", "DF", "Stoper / Savunma (CB)", 50, 75),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 69, 74),
                ("RWB", "SĞB", "Sağ Kanat Bek (RWB)", "DF", "Bek / Kanat Bek (LB/RB)", 88, 71),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    },
}


def render_mini_pitch_svg(formation_key, is_selected=False):
    """
    image1.jpeg referansındaki gibi yeşil futbol sahası ve beyaz oyuncu noktalarından oluşan SVG üretir.
    """
    spec = FORMATIONS_SPEC[formation_key]
    dots_svg = ""
    for row in spec["rows"]:
        for node_id, short_code, full_lbl, pos_cat, sub_lbl, cx, cy in row:
            dot_fill = "#FEF08A" if is_selected else "#FFFFFF"
            dots_svg += (
                f'<circle cx="{cx * 1.6:.1f}" cy="{cy * 2.1:.1f}" r="8.5" '
                f'fill="{dot_fill}" stroke="#0F172A" stroke-width="1.5" '
                f'filter="drop-shadow(0px 2px 2px rgba(0,0,0,0.35))"/>'
            )

    svg = f"""
    <svg viewBox="0 0 160 210" width="100%" style="max-width:155px; border-radius:8px; display:block; margin:0 auto;">
        <defs>
            <linearGradient id="pitchGrad_{formation_key}" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#16A34A"/>
                <stop offset="50%" stop-color="#15803D"/>
                <stop offset="100%" stop-color="#166534"/>
            </linearGradient>
        </defs>
        <rect x="0" y="0" width="160" height="210" rx="6" fill="url(#pitchGrad_{formation_key})"/>
        <rect x="7" y="7" width="146" height="196" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="1.6"/>
        <line x1="7" y1="105" x2="153" y2="105" stroke="rgba(255,255,255,0.85)" stroke-width="1.4"/>
        <circle cx="80" cy="105" r="22" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="1.4"/>
        <rect x="38" y="7" width="84" height="32" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="1.4"/>
        <rect x="58" y="7" width="44" height="13" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="1.2"/>
        <path d="M 64 39 A 16 16 0 0 0 96 39" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="1.3"/>
        <rect x="38" y="171" width="84" height="32" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="1.4"/>
        <rect x="58" y="190" width="44" height="13" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="1.2"/>
        <path d="M 64 171 A 16 16 0 0 1 96 171" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="1.3"/>
        {dots_svg}
    </svg>
    """
    return svg


# =============================================================================
# SESSION STATE BAŞLATMA (4 SAYFALI SİHİRBAZ)
# =============================================================================
if 'wizard_step' not in st.session_state:
    st.session_state['wizard_step'] = 1

if 'selected_coach' not in st.session_state:
    default_coach = "ERDİNÇ BÖREKÇİ" if "ERDİNÇ BÖREKÇİ" in list(coaches_df['name']) else coaches_df.iloc[0]['name']
    st.session_state['selected_coach'] = default_coach

if 'selected_formation' not in st.session_state:
    st.session_state['selected_formation'] = "4-3-3"

if 'selected_node' not in st.session_state:
    # Varsayılan: 4-3-3 Merkez Santrafor (ST)
    st.session_state['selected_node'] = ("ST", "SNT", "Merkez Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 50, 16)

if 'selected_archetype' not in st.session_state:
    st.session_state['selected_archetype'] = ARCHETYPE_MAP["Santrafor / Forvet (FW)"][0]

if 'carousel_idx' not in st.session_state:
    st.session_state['carousel_idx'] = 0

if 'selected_player_id' not in st.session_state:
    st.session_state['selected_player_id'] = None


# =============================================================================
# ÜST BAR & 4 ADIMLI STEPPER GÖSTERGESİ
# =============================================================================
curr_step = st.session_state['wizard_step']

render_html(f"""
<div class="portal-topbar">
    <div>
        <div class="portal-brand-badge">⚽ SCOUTME // TAKTİKSEL KARAR DESTEK SİSTEMİ</div>
        <h1 class="portal-title">ANTRENÖR DEĞERLENDİRME PORTALI</h1>
        <div class="portal-subtitle">KTFF 2026–2027 Sezonu A-Takım Teknik Direktörleri İçin 4 Adımlı Transfer Keşif ve Doğrulama Sihirbazı</div>
    </div>
    <div style="text-align:right;">
        <span style="background:rgba(255,255,255,0.14); border:1px solid rgba(255,255,255,0.25); padding:7px 14px; border-radius:10px; font-family:'Plus Jakarta Sans',sans-serif; font-size:0.8rem; font-weight:700; color:#FFFFFF;">
            ADIM {curr_step} / 4
        </span>
    </div>
</div>
""")

step_titles = [
    (1, "1. SAYFA", "Teknik Direktör & Kulüp"),
    (2, "2. SAYFA", "Diziliş, Mevki & Oyuncu Tipi"),
    (3, "3. SAYFA", "Kaydırmalı Oyuncu Önerileri"),
    (4, "4. SAYFA", "Tüm Öneriler & Değerlendirme")
]

stepper_html = '<div class="wizard-stepper">'
for s_num, s_small, s_title in step_titles:
    cls = "active" if s_num == curr_step else ("completed" if s_num < curr_step else "")
    icon_txt = "✓" if s_num < curr_step else str(s_num)
    stepper_html += f"""
    <div class="step-item {cls}">
        <div class="step-circle">{icon_txt}</div>
        <div class="step-text-wrap">
            <div class="step-label-small">{s_small}</div>
            <div class="step-label-title">{s_title}</div>
        </div>
    </div>
    """
stepper_html += '</div>'
render_html(stepper_html)


# =============================================================================
# 1. SAYFA: TEKNİK DİREKTÖR SEÇİMİ & OTOMATİK KULÜP BİLGİSİ
# =============================================================================
if curr_step == 1:
    left_sp, center_col, right_sp = st.columns([1.2, 7.6, 1.2])
    with center_col:
        render_html("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:18px; padding:28px 32px; box-shadow:0 8px 24px rgba(15,23,42,0.04);">
            <div style="font-size:0.76rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#059669; margin-bottom:4px;">
                1. SAYFA // KİMLİK DOĞRULAMA
            </div>
            <h2 style="margin:0 0 6px 0; font-size:1.45rem;">Teknik Direktör Seçimi</h2>
            <p style="color:#64748B; font-size:0.9rem; margin:0;">
                Lütfen aşağıdaki listeden isminizi seçiniz. Görev yaptığınız kulüp bilgisi resmi KTFF kayıtlarından otomatik olarak eşleştirilecektir.
            </p>
        </div>
        """)

        st.write("")
        coach_options = sorted(list(coaches_df['name'].unique()))
        current_coach_idx = (
            coach_options.index(st.session_state['selected_coach'])
            if st.session_state['selected_coach'] in coach_options else 0
        )

        chosen_coach = st.selectbox(
            "TEKNİK DİREKTÖR SEÇİNİZ",
            options=coach_options,
            index=current_coach_idx,
            key="page1_coach_select"
        )
        st.session_state['selected_coach'] = chosen_coach

        # Seçilen teknik direktörün kulübünü otomatik bul (listeden seçilmez)
        c_row = coaches_df[coaches_df['name'] == chosen_coach]
        auto_club_name = c_row.iloc[0]['club_name'] if len(c_row) > 0 else clubs_df.iloc[0]['name']
        auto_role = c_row.iloc[0]['role'] if len(c_row) > 0 else "Teknik Direktör"

        club_info_row = clubs_df[clubs_df['name'] == auto_club_name]
        auto_league = club_info_row.iloc[0]['league_name'] if len(club_info_row) > 0 else "KTFF"
        auto_city = club_info_row.iloc[0]['city'] if len(club_info_row) > 0 else ""

        st.session_state['selected_club'] = auto_club_name

        # Altta Teknik Direktör ve Otomatik Kulüp Gösterimi
        render_html(f"""
        <div class="coach-id-card">
            <div class="coach-id-row">
                <div class="coach-id-label">TEKNİK DİREKTÖR:</div>
                <div class="coach-id-value">
                    <span>👤 {chosen_coach}</span>
                    <span class="league-pill" style="background:#ECFDF5; color:#059669; border-color:#A7F3D0;">{auto_role}</span>
                </div>
            </div>
            <div class="coach-id-row">
                <div class="coach-id-label">KULÜP:</div>
                <div class="coach-id-value">
                    <span>🛡️ {auto_club_name}</span>
                    <span class="league-pill">{auto_league} • {auto_city}</span>
                </div>
            </div>
        </div>
        """)

        if st.button("Devam Et →", type="primary", use_container_width=True, key="btn_page1_next"):
            st.session_state['wizard_step'] = 2
            st.rerun()


# =============================================================================
# 2. SAYFA: GÖRSEL DİZİLİŞ SEÇİMİ -> SAHA ÜZERİNDE NOKTA BUTONLARLA POZİSYON SEÇİMİ
#           -> OYUNCU TİPİ SEÇİMİ -> DEVAM ET
# =============================================================================
elif curr_step == 2:
    render_html(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:16px; padding:18px 24px; margin-bottom:18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div>
            <div style="font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#059669;">
                2. SAYFA // TAKTİKSEL KURGU & MEVKİ SEÇİMİ
            </div>
            <h2 style="margin:2px 0 0 0; font-size:1.35rem;">Hangi Dizilişi Tercih Edersiniz?</h2>
        </div>
        <div style="font-size:0.85rem; color:#475569; background:#F1F5F9; padding:8px 14px; border-radius:10px; font-weight:600;">
            👤 <strong>{st.session_state.get('selected_coach')}</strong> &nbsp;|&nbsp; 🛡️ <strong>{st.session_state.get('selected_club')}</strong>
        </div>
    </div>
    """)

    # -------------------------------------------------------------------------
    # AŞAMA 2.1: GÖRSEL DİZİLİŞ GALERİSİ (image1.jpeg Stili Yeşil Sahalar)
    # -------------------------------------------------------------------------
    formation_keys = list(FORMATIONS_SPEC.keys())
    active_form = st.session_state.get('selected_formation', '4-3-3')

    for row_start in range(0, len(formation_keys), 4):
        f_cols = st.columns(4)
        for idx_in_row, f_key in enumerate(formation_keys[row_start:row_start + 4]):
            is_sel = (f_key == active_form)
            sel_cls = "selected" if is_sel else ""
            svg_html = render_mini_pitch_svg(f_key, is_selected=is_sel)
            with f_cols[idx_in_row]:
                render_html(f"""
                <div class="formation-card-box {sel_cls}">
                    <div class="formation-card-title">{f_key}</div>
                    {svg_html}
                </div>
                """)
                btn_lbl = f"✓ {f_key} Seçili" if is_sel else f"{f_key} Seç"
                if st.button(
                    btn_lbl,
                    key=f"select_form_{f_key}",
                    type="primary" if is_sel else "secondary",
                    use_container_width=True
                ):
                    st.session_state['selected_formation'] = f_key
                    # Yeni diziliş seçildiğinde varsayılan olarak ilk hücum noktasını seç
                    first_node = FORMATIONS_SPEC[f_key]["rows"][0][0]
                    st.session_state['selected_node'] = first_node
                    st.session_state['selected_archetype'] = ARCHETYPE_MAP[first_node[4]][0]
                    st.rerun()

    st.write("")

    # -------------------------------------------------------------------------
    # AŞAMA 2.2: SEÇİLEN DİZİLİŞ ÜZERİNDEKİ NOKTALARIN BUTON HALİNE GELMESİ
    # -------------------------------------------------------------------------
    active_form = st.session_state.get('selected_formation', '4-3-3')
    form_spec = FORMATIONS_SPEC[active_form]
    current_node = st.session_state.get('selected_node')

    # Eğer current_node bu dizilişte yoksa ilk noktaya sıfırla
    all_nodes_in_form = [n for r in form_spec["rows"] for n in r]
    valid_node_ids = [n[0] for n in all_nodes_in_form]
    if not current_node or current_node[0] not in valid_node_ids:
        current_node = all_nodes_in_form[0]
        st.session_state['selected_node'] = current_node

    render_html(f"""
    <div style="text-align:center; margin:16px 0 8px 0;">
        <span style="background:#ECFDF5; color:#059669; border:1px solid #A7F3D0; font-size:0.75rem; font-weight:800; padding:4px 12px; border-radius:999px; text-transform:uppercase; letter-spacing:0.06em;">
            ADIM 2A // SAHA ÜZERİNDEN POZİSYON SEÇİMİ ({active_form})
        </span>
        <h3 style="margin:8px 0 4px 0; font-size:1.2rem;">
            {active_form} Dizilişi Üzerindeki Oyuncu Noktasına Tıklayarak Pozisyon Seçiniz
        </h3>
        <p style="color:#64748B; font-size:0.85rem; margin:0;">
            Aşağıdaki saha üzerindeki her nokta tıklanabilir bir pozisyon butonudur. Transfer aradığınız mevki noktasına tıklayınız.
        </p>
    </div>
    """)

    # Yeşil Futbol Sahası Konteyneri (Üzerindeki Noktalar Gerçek Buton!)
    pitch_container = st.container()
    with pitch_container:
        render_html('<div class="interactive-pitch-anchor"></div>')
        render_html(
            f'<div style="text-align:center; color:rgba(255,255,255,0.92); font-family:Plus Jakarta Sans,sans-serif; font-size:0.76rem; font-weight:800; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:10px;">'
            f'⬆️ RAKİP KALE // {active_form} TAKTİK SAHASI ⬆️</div>'
        )

        for r_idx, row_nodes in enumerate(form_spec["rows"]):
            n_cnt = len(row_nodes)
            if n_cnt == 1:
                cols = st.columns([2.2, 2.6, 2.2])
                target_cols = [cols[1]]
            elif n_cnt == 2:
                cols = st.columns([1.0, 2.5, 0.8, 2.5, 1.0])
                target_cols = [cols[1], cols[3]]
            elif n_cnt == 3:
                cols = st.columns([0.5, 2.5, 2.5, 2.5, 0.5])
                target_cols = [cols[1], cols[2], cols[3]]
            elif n_cnt == 4:
                target_cols = st.columns(4)
            else:
                target_cols = st.columns(n_cnt)

            for c_i, node_tuple in enumerate(row_nodes):
                node_id, short_code, full_lbl, pos_cat, sub_lbl, cx, cy = node_tuple
                is_active_dot = (current_node[0] == node_id)
                dot_label = f"★ {short_code}" if is_active_dot else f"⚪ {short_code}"
                with target_cols[c_i]:
                    if st.button(
                        dot_label,
                        key=f"pitch_dot_{active_form}_{node_id}",
                        type="primary" if is_active_dot else "secondary",
                        help=full_lbl,
                        use_container_width=True
                    ):
                        st.session_state['selected_node'] = node_tuple
                        st.session_state['selected_archetype'] = ARCHETYPE_MAP[sub_lbl][0]
                        st.rerun()

            if r_idx < len(form_spec["rows"]) - 1:
                render_html('<div style="height:14px;"></div>')

        render_html(
            '<div style="text-align:center; color:rgba(255,255,255,0.92); font-family:Plus Jakarta Sans,sans-serif; font-size:0.74rem; font-weight:800; letter-spacing:0.1em; text-transform:uppercase; margin-top:8px;">'
            '⬇️ KENDİ KALEMİZ ⬇️</div>'
        )

    # -------------------------------------------------------------------------
    # AŞAMA 2.3: POZİSYON SEÇİLDİKTEN SONRA OYUNCU TİPİ (ARKETİP) SEÇİMİ
    # -------------------------------------------------------------------------
    sel_node_id, sel_short, sel_full_name, sel_pos_cat, sel_sub_label, _, _ = st.session_state['selected_node']
    available_archetypes = ARCHETYPE_MAP.get(sel_sub_label, ["Dengeli Oyuncu"])
    if st.session_state.get('selected_archetype') not in available_archetypes:
        st.session_state['selected_archetype'] = available_archetypes[0]

    render_html(f"""
    <div style="background:#FFFFFF; border:2px solid #10B981; border-radius:16px; padding:20px 24px; margin:16px 0; box-shadow:0 8px 24px rgba(16,185,129,0.08);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:8px;">
            <div>
                <span style="background:#FEF3C7; color:#B45309; border:1px solid #FDE68A; font-size:0.73rem; font-weight:800; padding:4px 10px; border-radius:999px; text-transform:uppercase;">
                    SEÇİLEN SAHA NOKTASI: {sel_full_name}
                </span>
                <h3 style="margin:8px 0 2px 0; font-size:1.18rem;">Bu Pozisyon İçin Aradığınız Oyuncu Tipini Seçiniz</h3>
            </div>
            <div style="font-size:0.82rem; color:#475569;">
                Kategori: <strong>{sel_sub_label}</strong>
            </div>
        </div>
    </div>
    """)

    arch_cols = st.columns(len(available_archetypes))
    for a_i, arch_name in enumerate(available_archetypes):
        is_arch_sel = (st.session_state.get('selected_archetype') == arch_name)
        with arch_cols[a_i]:
            if st.button(
                f"{'✓ ' if is_arch_sel else ''}{arch_name}",
                key=f"arch_btn_{a_i}_{sel_node_id}",
                type="primary" if is_arch_sel else "secondary",
                use_container_width=True
            ):
                st.session_state['selected_archetype'] = arch_name
                st.rerun()

    with st.expander("⚙️ İsteğe Bağlı Gelişmiş Keşif Filtreleri (Popülarite & U21 Filtresi)", expanded=False):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            lambda_val = st.slider(
                "Gizli Yetenek / Popülarite Cezası (λ)",
                min_value=0.0, max_value=0.50,
                value=st.session_state.get('lambda_val', 0.20),
                step=0.05
            )
            st.session_state['lambda_val'] = lambda_val
        with f_col2:
            st.write("")
            youth_filter = st.checkbox(
                "Yalnızca U21 Genç Yetenekleri Listele (Yaş ≤ 21)",
                value=st.session_state.get('youth_filter', False)
            )
            st.session_state['youth_filter'] = youth_filter

    st.write("")
    nav_c1, nav_c2 = st.columns([3, 7])
    with nav_c1:
        if st.button("← 1. Sayfaya Dön", use_container_width=True, key="btn_page2_back"):
            st.session_state['wizard_step'] = 1
            st.rerun()
    with nav_c2:
        if st.button("Devam Et (Oyuncu Önerilerini Getir) →", type="primary", use_container_width=True, key="btn_page2_next"):
            recs = recommender.recommend_players_for_club(
                st.session_state['selected_club'],
                target_position=sel_pos_cat,
                top_k=5,
                lambda_popularity=st.session_state.get('lambda_val', 0.20),
                youth_only=st.session_state.get('youth_filter', False),
                formation=active_form,
                sub_position_label=sel_sub_label,
                player_archetype=st.session_state['selected_archetype'],
                coach_identifier=st.session_state['selected_coach']
            )
            st.session_state['portal_recs'] = recs
            st.session_state['carousel_idx'] = 0
            st.session_state['selected_player_id'] = recs[0]['player_id'] if recs else None
            st.session_state['wizard_step'] = 3
            st.rerun()


# =============================================================================
# 3. SAYFA: KAYDIRMALI (CAROUSEL) OYUNCU ÖNERİ KARTLARI + AKTİF OYUNCU DETAYI
#           + EN ALTTA "SEÇ" BUTONU
# =============================================================================
elif curr_step == 3:
    recs = st.session_state.get('portal_recs', [])
    if not recs:
        sel_node = st.session_state['selected_node']
        recs = recommender.recommend_players_for_club(
            st.session_state.get('selected_club', clubs_df.iloc[0]['name']),
            target_position=sel_node[3],
            top_k=5,
            lambda_popularity=st.session_state.get('lambda_val', 0.20),
            youth_only=st.session_state.get('youth_filter', False),
            formation=st.session_state.get('selected_formation', '4-3-3'),
            sub_position_label=sel_node[4],
            player_archetype=st.session_state.get('selected_archetype'),
            coach_identifier=st.session_state.get('selected_coach')
        )
        st.session_state['portal_recs'] = recs

    n_recs = len(recs)
    c_idx = st.session_state.get('carousel_idx', 0) % max(1, n_recs)
    st.session_state['carousel_idx'] = c_idx

    sel_node = st.session_state['selected_node']
    render_html(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:16px; padding:16px 24px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
        <div>
            <div style="font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#2563EB;">
                3. SAYFA // KAYDIRMALI ADAY KEŞFİ ({c_idx + 1} / {n_recs})
            </div>
            <h2 style="margin:2px 0 0 0; font-size:1.32rem;">Önerilen Oyuncu Kartları</h2>
        </div>
        <div style="font-size:0.82rem; color:#475569; background:#F1F5F9; padding:8px 14px; border-radius:10px; font-weight:600;">
            📐 <strong>{st.session_state.get('selected_formation')}</strong> &nbsp;•&nbsp;
            🎯 <strong>{sel_node[2]}</strong> &nbsp;•&nbsp;
            ⚡ <strong>{st.session_state.get('selected_archetype')}</strong>
        </div>
    </div>
    """)

    # -------------------------------------------------------------------------
    # KAYDIRMALI KARTLAR (SLIDING CARDS CAROUSEL - image2.jpeg Stili)
    # -------------------------------------------------------------------------
    prev_idx = (c_idx - 1) % n_recs
    next_idx = (c_idx + 1) % n_recs

    nav_left_col, card_col_1, card_col_2, card_col_3, nav_right_col = st.columns([0.8, 2.8, 3.2, 2.8, 0.8])

    with nav_left_col:
        render_html('<div style="height:115px;"></div>')
        if st.button("❮", key="carousel_prev_btn", help="Önceki Oyuncuya Kaydır", use_container_width=True):
            st.session_state['carousel_idx'] = (c_idx - 1) % n_recs
            st.rerun()

    visible_slots = [
        (prev_idx, card_col_1, False),
        (c_idx, card_col_2, True),
        (next_idx, card_col_3, False)
    ]

    for slot_pos, (p_i, col_obj, is_center) in enumerate(visible_slots):
        cand = recs[p_i]
        p_full_slot, _ = get_player_full_details(cand['player_id'])
        photo_url_slot = p_full_slot[4] if (p_full_slot and len(p_full_slot) > 4 and p_full_slot[4]) else None
        initials_slot = "".join([w[0] for w in cand['name'].split()[:2]]) if cand['name'] else "OY"

        avatar_html = (
            f'<img src="{photo_url_slot}" alt="{cand["name"]}"/>'
            if photo_url_slot
            else f'<div class="sliding-avatar-initials">{initials_slot}</div>'
        )
        slide_cls = "active-slide" if is_center else "inactive-slide"
        rank_badge = f"★ AKTİF KART (#{p_i + 1})" if is_center else f"ADAY #{p_i + 1}"

        with col_obj:
            render_html(f"""
            <div class="sliding-card {slide_cls}">
                <div class="sliding-card-top">
                    <div style="font-size:0.68rem; font-weight:800; color:rgba(255,255,255,0.9); letter-spacing:0.08em; text-transform:uppercase; margin-bottom:8px;">
                        {rank_badge}
                    </div>
                    <div class="sliding-avatar-ring">
                        {avatar_html}
                    </div>
                </div>
                <div class="sliding-card-body">
                    <div class="sliding-player-name">{cand['name']}</div>
                    <div class="sliding-player-desc">
                        <strong>{cand['current_club']}</strong><br/>
                        {cand['age']} Yaş &bull; {cand['prim_pos']} &bull; {cand.get('a_team_matches', 0)} A-Takım Maçı
                    </div>
                    <div class="sliding-metrics-row">
                        <span class="sliding-pill-ovr">{cand['ovr']} OVR</span>
                        <span class="sliding-pill-fit">%{cand['tactical_fit_pct']} Uyum</span>
                    </div>
                </div>
            </div>
            """)

            if not is_center:
                if st.button(
                    f"İncele (#{p_i + 1})",
                    key=f"jump_slide_{slot_pos}_{p_i}",
                    use_container_width=True
                ):
                    st.session_state['carousel_idx'] = p_i
                    st.rerun()
            else:
                render_html(
                    '<div style="text-align:center; font-size:0.76rem; font-weight:800; color:#059669; padding:6px 0;">'
                    '▼ DETAYLAR AŞAĞIDA GÖSTERİLİYOR ▼</div>'
                )

    with nav_right_col:
        render_html('<div style="height:115px;"></div>')
        if st.button("❯", key="carousel_next_btn", help="Sonraki Oyuncuya Kaydır", use_container_width=True):
            st.session_state['carousel_idx'] = (c_idx + 1) % n_recs
            st.rerun()

    # Carousel Nokta Göstergeleri (Pagination Dots)
    dots_html = '<div class="carousel-dots">'
    for d_i in range(n_recs):
        d_cls = "active" if d_i == c_idx else ""
        dots_html += f'<div class="c-dot {d_cls}"></div>'
    dots_html += '</div>'
    render_html(dots_html)

    # -------------------------------------------------------------------------
    # KAYDIRMA KİMDEYSE ALTTA O OYUNCUYA AİT DETAYLI BİLGİLER
    # -------------------------------------------------------------------------
    active_p = recs[c_idx]
    p_full, p_seasons = get_player_full_details(active_p['player_id'])

    tags_badges = " ".join([
        f'<span style="background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE; font-size:0.74rem; font-weight:700; padding:4px 10px; border-radius:999px; display:inline-block; margin-right:6px;">{t}</span>'
        for t in active_p.get('scout_tags', [])
    ])

    birth_str = p_full[3] if (p_full and p_full[3]) else "-"
    tot_matches_3y = p_full[13] if p_full else active_p['played_matches']
    starter_pct = (p_full[15] * 100.0) if p_full else 0.0
    tot_goals_3y = p_full[14] if p_full else 0
    p90_goals_val = p_full[12] if p_full else 0.0
    net_diff_val = p_full[11] if p_full else 0.0
    ci_val = (p_full[10] * 100.0) if p_full else 0.0

    render_html(f"""
    <div class="active-player-showcase">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px; border-bottom:1px solid #E2E8F0; padding-bottom:14px; margin-bottom:14px;">
            <div>
                <div style="font-size:0.74rem; font-weight:800; color:#059669; text-transform:uppercase; letter-spacing:0.08em;">
                    AKTİF OYUNCU ANALİTİK KARNESİ // ADAY #{c_idx + 1}
                </div>
                <h2 style="margin:4px 0 6px 0; font-size:1.55rem;">
                    {active_p['name']}
                    <span style="font-size:0.9rem; font-weight:600; color:#64748B;">(Lisans #{active_p['license_no']})</span>
                </h2>
                <div>{tags_badges}</div>
            </div>
            <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:12px; padding:8px 14px; text-align:center;">
                    <div style="font-size:0.68rem; font-weight:700; color:#64748B; text-transform:uppercase;">TAKTİK UYUM</div>
                    <div style="font-size:1.2rem; font-weight:800; color:#059669;">%{active_p['tactical_fit_pct']}</div>
                </div>
                <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:12px; padding:8px 14px; text-align:center;">
                    <div style="font-size:0.68rem; font-weight:700; color:#64748B; text-transform:uppercase;">İLK 11 ŞANSI</div>
                    <div style="font-size:1.2rem; font-weight:800; color:#2563EB;">%{active_p['playing_time_chance_pct']}</div>
                </div>
                <div style="background:#0F172A; color:#FFFFFF; border-radius:12px; padding:8px 16px; text-align:center;">
                    <div style="font-size:0.68rem; font-weight:700; color:#94A3B8; text-transform:uppercase;">GENEL REYTİNG</div>
                    <div style="font-size:1.25rem; font-weight:800; color:#FFFFFF;">{active_p['ovr']} OVR</div>
                </div>
            </div>
        </div>

        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:14px 16px; margin-bottom:14px; font-size:0.85rem;">
            <div><span style="color:#64748B; font-size:0.72rem; font-weight:700; display:block;">MEVCUT KULÜP & MEVKİ</span><strong>{active_p['current_club']} ({active_p['prim_pos']})</strong></div>
            <div><span style="color:#64748B; font-size:0.72rem; font-weight:700; display:block;">DOĞUM TARİHİ & YAŞ</span><strong>{birth_str} ({active_p['age']} Yaş)</strong></div>
            <div><span style="color:#64748B; font-size:0.72rem; font-weight:700; display:block;">KTFF MAÇ & SÜREKLİLİK</span><strong>{tot_matches_3y} Maç (İlk 11: %{starter_pct:.0f} | CI: %{ci_val:.0f})</strong></div>
            <div><span style="color:#64748B; font-size:0.72rem; font-weight:700; display:block;">SKOR & SAHA İÇİ ETKİ</span><strong>{tot_goals_3y} Gol ({p90_goals_val} Gol/90 | {net_diff_val:+.2f} Averaj)</strong></div>
        </div>

        <div class="attr-grid-4">
            <div class="attr-box">
                <div class="attr-head"><span class="attr-name">FİZİKSEL GÜÇ</span><span class="attr-score">{active_p['phys']:.0f}</span></div>
                <div class="attr-bar-bg"><div class="attr-bar-fill" style="width:{min(100, max(0, active_p['phys']))}%;"></div></div>
            </div>
            <div class="attr-box">
                <div class="attr-head"><span class="attr-name">ŞUT & BİTİRİCİLİK</span><span class="attr-score">{active_p['shoot']:.0f}</span></div>
                <div class="attr-bar-bg"><div class="attr-bar-fill" style="width:{min(100, max(0, active_p['shoot']))}%;"></div></div>
            </div>
            <div class="attr-box">
                <div class="attr-head"><span class="attr-name">TEKNİK & PAS</span><span class="attr-score">{active_p['tech']:.0f}</span></div>
                <div class="attr-bar-bg"><div class="attr-bar-fill" style="width:{min(100, max(0, active_p['tech']))}%;"></div></div>
            </div>
            <div class="attr-box">
                <div class="attr-head"><span class="attr-name">DEFANSİF KATKI</span><span class="attr-score">{active_p['def']:.0f}</span></div>
                <div class="attr-bar-bg"><div class="attr-bar-fill" style="width:{min(100, max(0, active_p['def']))}%;"></div></div>
            </div>
        </div>

        <div style="background:#ECFDF5; border-left:4px solid #059669; border-radius:8px; padding:12px 16px; font-size:0.88rem; color:#065F46; margin-top:10px;">
            <strong>🧠 YAPAY ZEKA SCOUT GEREKÇESİ:</strong> {active_p['scout_verdict']}
        </div>
    </div>
    """)

    if p_seasons:
        with st.expander(f"📊 {active_p['name']} — Sezon Bazlı Resmi KTFF İstatistik Tablosu", expanded=False):
            season_df = pd.DataFrame(
                p_seasons,
                columns=['Sezon', 'Toplam Maç', 'İlk 11 Başlangıç', 'Gol', 'Sarı Kart', 'Kırmızı Kart']
            )
            st.dataframe(season_df, hide_index=True, use_container_width=True)

    st.write("")
    # En Altta "Seç" Butonu
    b_col1, b_col2 = st.columns([2.8, 7.2])
    with b_col1:
        if st.button("← 2. Sayfaya Dön (Diziliş/Mevki)", use_container_width=True, key="btn_page3_back"):
            st.session_state['wizard_step'] = 2
            st.rerun()
    with b_col2:
        if st.button(
            f"✓ SEÇ ({active_p['name']} İsimli Oyuncuyu Seç ve 4. Sayfaya Geç) →",
            type="primary",
            use_container_width=True,
            key="btn_page3_select_player"
        ):
            st.session_state['selected_player_id'] = active_p['player_id']
            st.session_state['wizard_step'] = 4
            st.rerun()


# =============================================================================
# 4. SAYFA: YAPILAN TÜM ÖNERİLER KART HALİNDE ("SEÇİLEN" İBARESİYLE)
#           VE ANTRENÖRLERDEN PUANLAMA & YORUM ALANI
# =============================================================================
elif curr_step == 4:
    recs = st.session_state.get('portal_recs', [])
    chosen_pid = st.session_state.get('selected_player_id')
    sel_node = st.session_state.get('selected_node')

    render_html(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:16px; padding:18px 24px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
        <div>
            <div style="font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#059669;">
                4. SAYFA // TÜM ÖNERİLERİN DEĞERLENDİRİLMESİ & MODEL DOĞRULAMA
            </div>
            <h2 style="margin:2px 0 0 0; font-size:1.35rem;">Yapılan Tüm Öneriler, Puanlama ve Antrenör Yorumu</h2>
            <div style="font-size:0.85rem; color:#64748B; margin-top:2px;">
                3. sayfada seçtiğiniz oyuncu <strong>"★ SEÇİLEN OYUNCU"</strong> ibaresiyle vurgulanmıştır. Lütfen yapılan öneriler için puanlama ve yorumunuzu giriniz.
            </div>
        </div>
        <div style="font-size:0.82rem; color:#475569; background:#F1F5F9; padding:8px 14px; border-radius:10px; font-weight:600;">
            👤 <strong>{st.session_state.get('selected_coach')}</strong> &nbsp;|&nbsp;
            🛡️ <strong>{st.session_state.get('selected_club')}</strong> &nbsp;|&nbsp;
            📐 <strong>{st.session_state.get('selected_formation')}</strong>
        </div>
    </div>
    """)

    # -------------------------------------------------------------------------
    # TÜM ÖNERİLERİN KART HALİNDE GÖSTERİMİ + PUANLAMA FORMU
    # -------------------------------------------------------------------------
    with st.form(key="page4_all_evaluations_form"):
        for idx, p in enumerate(recs, 1):
            is_chosen = (p['player_id'] == chosen_pid)
            card_cls = "chosen-card" if is_chosen else ""
            ribbon_html = (
                '<div class="chosen-ribbon">★ SEÇİLEN OYUNCU (TERCİHİNİZ)</div>'
                if is_chosen
                else f'<div class="other-ribbon">ÖNERİLEN ADAY #{idx}</div>'
            )

            render_html(f"""
            <div class="eval-summary-card {card_cls}">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div>
                        {ribbon_html}
                        <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:1.22rem; font-weight:800; color:#0F172A;">
                            {p['name']}
                            <span style="font-size:0.85rem; font-weight:600; color:#475569; margin-left:6px;">
                                ({p['age']} Yaş • {p['current_club']} • {p['prim_pos']})
                            </span>
                        </div>
                        <div style="font-size:0.82rem; color:#475569; margin-top:4px;">
                            {p['scout_verdict']}
                        </div>
                    </div>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <span class="sliding-pill-fit" style="font-size:0.8rem;">Uyum: %{p['tactical_fit_pct']}</span>
                        <span class="sliding-pill-ovr" style="font-size:0.85rem;">{p['ovr']} OVR</span>
                    </div>
                </div>
            </div>
            """)

            r_col1, r_col2, r_col3, r_col4 = st.columns([2.2, 2.2, 2.2, 3.4])
            default_rating = 5 if is_chosen else 4
            default_dec_idx = 0 if is_chosen else 1

            with r_col1:
                st.select_slider(
                    f"Taktiksel Uyum (1–5)",
                    options=[1, 2, 3, 4, 5],
                    value=default_rating,
                    key=f"p4_tac_{p['player_id']}"
                )
            with r_col2:
                st.select_slider(
                    f"İlk 11 / Süre Şansı (1–5)",
                    options=[1, 2, 3, 4, 5],
                    value=default_rating,
                    key=f"p4_play_{p['player_id']}"
                )
            with r_col3:
                st.select_slider(
                    f"Transfer Mantığı (1–5)",
                    options=[1, 2, 3, 4, 5],
                    value=default_rating,
                    key=f"p4_feas_{p['player_id']}"
                )
            with r_col4:
                st.selectbox(
                    f"Transfer Kararı & Bilinirlik",
                    options=[
                        "Kesinlikle Alırım (İlk 11 Hedefi)",
                        "Rotasyona Alırım (Kadro Derinliği)",
                        "Scout İzleme Listesine Alırım",
                        "Pas Geçerim / Uygun Değil"
                    ],
                    index=default_dec_idx,
                    key=f"p4_dec_{p['player_id']}"
                )

            k_col1, k_col2 = st.columns([3.5, 6.5])
            with k_col1:
                st.radio(
                    f"{p['name']} isimli oyuncuyu tanıyor musunuz?",
                    options=["Evet, tanıyorum", "Hayır, tanımıyorum"],
                    horizontal=True,
                    key=f"p4_known_{p['player_id']}"
                )
            with k_col2:
                st.text_input(
                    f"{p['name']} İçin Antrenör Yorumu / Teknik Not",
                    placeholder="Örn: Sistemimize ve aradığımız role çok uygun, fizik kalitesi yeterli...",
                    key=f"p4_note_{p['player_id']}"
                )

            render_html('<hr style="border:none; border-top:1px solid #E2E8F0; margin:12px 0 20px 0;"/>')

        general_feedback = st.text_area(
            "GENEL DEĞERLENDİRME & ÖNERİ SİSTEMİ HAKKINDA YORUMUNUZ (OPSİYONEL)",
            placeholder="Yapılan önerilerin genel isabeti, seçtiğiniz oyuncu hakkındaki genel görüşünüz...",
            height=80,
            key="p4_general_comment"
        )

        submit_all = st.form_submit_button(
            "✓ TÜM PUANLAMA VE YORUMLARI KAYDET →",
            type="primary",
            use_container_width=True
        )

        if submit_all:
            dec_val_map = {
                "Kesinlikle Alırım (İlk 11 Hedefi)": "buy",
                "Rotasyona Alırım (Kadro Derinliği)": "rotation",
                "Scout İzleme Listesine Alırım": "watchlist",
                "Pas Geçerim / Uygun Değil": "reject"
            }

            for i_rec, p in enumerate(recs):
                pid = p['player_id']
                is_chosen = (pid == chosen_pid)
                tac_val = st.session_state.get(f"p4_tac_{pid}", 4)
                play_val = st.session_state.get(f"p4_play_{pid}", 4)
                feas_val = st.session_state.get(f"p4_feas_{pid}", 4)
                dec_lbl = st.session_state.get(f"p4_dec_{pid}", "Rotasyona Alırım (Kadro Derinliği)")
                known_lbl = st.session_state.get(f"p4_known_{pid}", "Evet, tanıyorum")
                note_txt = st.session_state.get(f"p4_note_{pid}", "").strip()

                prefix_tag = "[SEÇİLEN OYUNCU] " if is_chosen else ""
                combined_note = f"{prefix_tag}{note_txt}"
                if general_feedback.strip() and is_chosen:
                    combined_note = f"{combined_note} | Genel Not: {general_feedback.strip()}".strip(" |")

                # Son kayıtta GitHub senkronizasyonunu tetikle
                is_last = (i_rec == len(recs) - 1)
                save_evaluation_to_db(
                    coach_name=st.session_state.get('selected_coach', 'Teknik Direktör'),
                    club_name=st.session_state.get('selected_club', ''),
                    player_id=pid,
                    player_name=p['name'],
                    target_pos=sel_node[3] if sel_node else p['pos_cat'],
                    formation=st.session_state.get('selected_formation', '4-3-3'),
                    player_type=st.session_state.get('selected_archetype', ''),
                    is_known=1 if "Evet" in known_lbl else 0,
                    model_score=p['recommendation_score'],
                    tactical_fit=tac_val,
                    playing_time=play_val,
                    feasibility=feas_val,
                    decision=dec_val_map.get(dec_lbl, "rotation"),
                    note=combined_note,
                    sync_now=is_last
                )

            st.success("✓ Değerlendirmeleriniz ve yorumlarınız başarıyla veritabanına kaydedildi! Katkınız için teşekkür ederiz.")
            st.balloons()

    # Alt Navigasyon Butonları
    f_nav1, f_nav2, f_nav3 = st.columns([3, 4, 3])
    with f_nav1:
        if st.button("← 3. Sayfaya Dön (Kaydırmalı Kartlar)", use_container_width=True, key="btn_page4_back3"):
            st.session_state['wizard_step'] = 3
            st.rerun()
    with f_nav2:
        if st.button("🔄 Farklı Diziliş / Mevki İçin Yeni Arama Yap (2. Sayfa)", use_container_width=True, key="btn_page4_back2"):
            st.session_state['wizard_step'] = 2
            st.rerun()
    with f_nav3:
        if st.button("👤 Teknik Direktör Değiştir (1. Sayfa)", use_container_width=True, key="btn_page4_back1"):
            st.session_state['wizard_step'] = 1
            st.rerun()

    # İsteğe Bağlı: Canlı Veritabanı Özeti Expander
    with st.expander("📊 Kayıtlı Antrenör Değerlendirmeleri & Doğrulama Özeti", expanded=False):
        all_evals = load_evaluations_summary()
        if len(all_evals) == 0:
            st.info("Henüz kaydedilmiş değerlendirme bulunmuyor.")
        else:
            tot_cnt = len(all_evals)
            avg_tac = all_evals['tactical_fit_rating'].mean()
            acc_cnt = all_evals['decision'].isin(['buy', 'rotation', 'watchlist']).sum()
            acc_rate = (acc_cnt / tot_cnt) * 100.0

            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Değerlendirme", f"{tot_cnt} Oy")
            m2.metric("Ortalama Taktik Uyum", f"{avg_tac:.2f} / 5.0")
            m3.metric("Transfer Kabul Oranı", f"%{acc_rate:.1f}")

            cols_to_show = [
                'created_at', 'coach_name', 'club_name', 'player_name',
                'target_position', 'formation', 'player_type',
                'tactical_fit_rating', 'decision', 'feedback_note'
            ]
            existing_cols = [c for c in cols_to_show if c in all_evals.columns]
            st.dataframe(all_evals[existing_cols], use_container_width=True, height=260)


# Alt Bilgi (Footer)
render_html("""
<div style="display:flex; justify-content:space-between; margin-top:44px; padding-top:16px; color:#64748B; font-size:0.75rem; border-top:1px solid #E2E8F0; font-weight:600;">
    <span>SCOUTME // YÜKSEK LİSANS TEZ PROJESİ</span>
    <span>DOĞU AKDENİZ ÜNİVERSİTESİ (DAÜ / EMU) BİLGİSAYAR MÜHENDİSLİĞİ • 2026</span>
</div>
""")
