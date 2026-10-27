"""
ScoutMe - Antrenör Değerlendirme Portalı (Mobil Uyumlu 4 Adımlı Sihirbaz)
=========================================================================
1. Adım: Teknik Direktör Seçimi & Otomatik Kulüp Eşleşmesi
2. Adım: Görsel Diziliş -> İnteraktif Saha Üzerinden Mevki -> Oyuncu Tipi Seçimi
3. Adım: Kaydırmalı (Carousel) Oyuncu Kartı & Analitik Özet -> Oyuncu Seçimi
4. Adım: Tüm Öneriler ("★ SEÇİLEN OYUNCU" Vurgulu) -> Puanlama ve Yorum Kaydı
"""

import sqlite3
import pandas as pd
import numpy as np
import streamlit as st
from recommender.recommender_engine import ScoutMeRecommender
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
# MOBİL UYUMLU (RESPONSIVE) & YÜKSEK KONTRASTLI CSS TASARIM SİSTEMİ
# =============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

    :root {
        --bg-main: #F1F5F9;
        --bg-card: #FFFFFF;
        --bg-subtle: #F8FAFC;
        --navy-900: #0F172A;
        --navy-800: #1E293B;
        --navy-700: #334155;
        --royal-600: #2563EB;
        --emerald-600: #059669;
        --emerald-500: #10B981;
        --amber-500: #F59E0B;
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
        background-color: rgba(255, 255, 255, 0.92) !important;
        backdrop-filter: blur(8px);
        border-bottom: 1px solid var(--border-light);
    }

    .block-container {
        max-width: 920px !important;
        padding-top: 1rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: var(--navy-900) !important;
        letter-spacing: -0.02em;
    }

    /* Kompakt Üst Başlık */
    .portal-topbar {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        color: #FFFFFF;
        border-radius: 14px;
        padding: 14px 20px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.12);
    }
    .portal-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.2rem;
        font-weight: 800;
        color: #FFFFFF !important;
        margin: 0;
        line-height: 1.25;
    }
    .portal-step-pill {
        background: rgba(16, 185, 129, 0.22);
        border: 1px solid rgba(110, 231, 183, 0.45);
        color: #6EE7B7;
        padding: 5px 12px;
        border-radius: 999px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.78rem;
        font-weight: 800;
        white-space: nowrap;
    }

    /* 4 Adımlı Stepper Çubuğu (Masaüstü & Mobil Uyumlu) */
    .wizard-stepper {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin-bottom: 18px;
    }
    .step-item {
        background: var(--bg-card);
        border: 1px solid var(--border-light);
        border-radius: 10px;
        padding: 9px 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
    }
    .step-item.active {
        border: 2px solid var(--emerald-500);
        background: #ECFDF5;
        box-shadow: 0 3px 10px rgba(16, 185, 129, 0.14);
    }
    .step-item.completed {
        border: 1px solid #A7F3D0;
        background: #FFFFFF;
    }
    .step-circle {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 800;
        font-size: 0.76rem;
        background: #E2E8F0;
        color: var(--navy-700);
        flex-shrink: 0;
    }
    .step-item.active .step-circle {
        background: var(--emerald-600);
        color: #FFFFFF;
    }
    .step-item.completed .step-circle {
        background: var(--navy-900);
        color: #FFFFFF;
    }
    .step-label-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.8rem;
        font-weight: 700;
        color: var(--navy-900);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Seçim Kutusu (Selectbox) - Belirgin ve Yüksek Kontrastlı */
    div[data-testid="stSelectbox"] label p {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.92rem !important;
        font-weight: 800 !important;
        color: var(--navy-900) !important;
        letter-spacing: 0.01em !important;
    }
    div[data-testid="stSelectbox"] > div > div {
        background-color: #FFFFFF !important;
        border: 2.5px solid var(--emerald-600) !important;
        border-radius: 12px !important;
        min-height: 52px !important;
        box-shadow: 0 4px 14px rgba(5, 150, 105, 0.12) !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        color: var(--navy-900) !important;
        transition: all 0.18s ease !important;
    }
    div[data-testid="stSelectbox"] > div > div:hover,
    div[data-testid="stSelectbox"] > div > div:focus-within {
        border-color: var(--royal-600) !important;
        box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.18) !important;
    }
    div[data-testid="stSelectbox"] svg {
        fill: var(--emerald-600) !important;
        width: 1.35rem !important;
        height: 1.35rem !important;
    }

    /* 1. Sayfa: Teknik Direktör & Kulüp Kartı */
    .page-card {
        background: var(--bg-card);
        border: 1px solid var(--border-light);
        border-radius: 16px;
        padding: 20px 22px;
        margin-bottom: 14px;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
    }
    /* 1. Sayfa: Teknik Direktör Seçim Kutusu Vurgusu (Yalnızca İç Konteyner) */
    div[data-testid="stVerticalBlock"]:has(.coach-select-anchor):not(:has(div[data-testid="stVerticalBlock"] .coach-select-anchor)) {
        background: linear-gradient(180deg, #ECFDF5 0%, #FFFFFF 100%) !important;
        border: 2.5px solid var(--emerald-500) !important;
        border-radius: 16px !important;
        padding: 18px 20px 18px 20px !important;
        margin-bottom: 14px !important;
        box-shadow: 0 8px 22px rgba(5, 150, 105, 0.12) !important;
    }
    .coach-id-card {
        background: var(--bg-card);
        border: 1px solid var(--border-light);
        border-left: 5px solid var(--emerald-500);
        border-radius: 14px;
        padding: 16px 20px;
        margin: 12px 0 18px 0;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
    }
    .coach-id-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid var(--border-light);
        flex-wrap: wrap;
        gap: 8px;
    }
    .coach-id-row:last-child {
        border-bottom: none;
        padding-bottom: 0;
    }
    .coach-id-label {
        font-size: 0.76rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
    }
    .coach-id-value {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.05rem;
        font-weight: 800;
        color: var(--navy-900);
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
    }
    .league-pill {
        background: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 3px 9px;
        border-radius: 999px;
    }

    /* Bölüm Başlık Çubuğu */
    .section-bar {
        background: var(--bg-card);
        border: 1px solid var(--border-light);
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
    }
    .section-bar-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.05rem;
        font-weight: 800;
        color: var(--navy-900);
        margin: 0;
    }
    .section-bar-meta {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-secondary);
        background: var(--bg-subtle);
        border: 1px solid var(--border-light);
        padding: 5px 10px;
        border-radius: 8px;
    }

    /* 2. Sayfa: Görsel Diziliş Kartları */
    .formation-card-box {
        background: var(--bg-card);
        border: 2px solid var(--border-light);
        border-radius: 12px;
        padding: 8px 8px 6px 8px;
        text-align: center;
        margin-bottom: 4px;
    }
    .formation-card-box.selected {
        border: 2.5px solid var(--emerald-500);
        background: #ECFDF5;
        box-shadow: 0 6px 14px rgba(16, 185, 129, 0.16);
    }
    .formation-card-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.95rem;
        font-weight: 800;
        color: var(--navy-900);
        margin-bottom: 4px;
    }
    .formation-card-box.selected .formation-card-title {
        color: var(--emerald-600);
    }

    /* 2. Sayfa: Dizilişin İçine Girme (3B Zoom-In) Animasyonu */
    @keyframes pitchZoomIn {
        0% {
            opacity: 0;
            transform: perspective(900px) scale(0.72) rotateX(14deg) translateY(20px);
        }
        100% {
            opacity: 1;
            transform: perspective(900px) scale(1) rotateX(0deg) translateY(0);
        }
    }

    /* 2. Sayfa: SADECE Dizilişin Arkasındaki Futbol Sahası (Arka Plan Sahasını Engeller) */
    div[data-testid="stVerticalBlock"]:has(.interactive-pitch-anchor):not(:has(div[data-testid="stVerticalBlock"] .interactive-pitch-anchor)) {
        background-color: #15803D !important;
        background-image:
            url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 520' preserveAspectRatio='none'><rect x='14' y='14' width='372' height='492' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='3'/><line x1='14' y1='260' x2='386' y2='260' stroke='rgba(255,255,255,0.85)' stroke-width='2.5'/><circle cx='200' cy='260' r='52' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2.5'/><circle cx='200' cy='260' r='4' fill='rgba(255,255,255,0.9)'/><rect x='95' y='14' width='210' height='82' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2.5'/><rect x='145' y='14' width='110' height='32' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2'/><path d='M 160 96 A 42 42 0 0 0 240 96' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2.2'/><rect x='95' y='424' width='210' height='82' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2.5'/><rect x='145' y='474' width='110' height='32' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2'/><path d='M 160 424 A 42 42 0 0 1 240 424' fill='none' stroke='rgba(255,255,255,0.85)' stroke-width='2.2'/></svg>"),
            repeating-linear-gradient(0deg, #16A34A 0px, #16A34A 48px, #15803D 48px, #15803D 96px) !important;
        background-size: 100% 100%, 100% 96px !important;
        border: 3px solid #FFFFFF !important;
        border-radius: 16px !important;
        padding: 18px 12px 16px 12px !important;
        box-shadow: 0 14px 30px rgba(15, 23, 42, 0.18) !important;
        max-width: 540px !important;
        margin: 8px auto 16px auto !important;
        animation: pitchZoomIn 0.45s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
        transform-origin: center center !important;
    }

    /* Sadece Sahadaki Oyuncu Satırlarının Yatay Kalmasını Sağla */
    div[data-testid="stVerticalBlock"]:has(.interactive-pitch-anchor):not(:has(div[data-testid="stVerticalBlock"] .interactive-pitch-anchor)) [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 8px !important;
    }
    div[data-testid="stVerticalBlock"]:has(.interactive-pitch-anchor):not(:has(div[data-testid="stVerticalBlock"] .interactive-pitch-anchor)) [data-testid="stColumn"] {
        width: auto !important;
        flex: 1 1 0px !important;
        min-width: 0 !important;
        max-width: 120px !important;
    }

    /* Saha Üzerindeki Oyuncu Nokta Butonları */
    div[data-testid="stVerticalBlock"]:has(.interactive-pitch-anchor):not(:has(div[data-testid="stVerticalBlock"] .interactive-pitch-anchor)) .stButton > button {
        border-radius: 999px !important;
        min-height: 44px !important;
        padding: 4px 8px !important;
        background: #FFFFFF !important;
        color: #0F172A !important;
        border: 2.5px solid #0F172A !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.28) !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.76rem !important;
        font-weight: 800 !important;
    }
    div[data-testid="stVerticalBlock"]:has(.interactive-pitch-anchor):not(:has(div[data-testid="stVerticalBlock"] .interactive-pitch-anchor)) .stButton > button p {
        color: #0F172A !important;
        font-weight: 800 !important;
        font-size: 0.76rem !important;
        white-space: nowrap !important;
    }
    div[data-testid="stVerticalBlock"]:has(.interactive-pitch-anchor):not(:has(div[data-testid="stVerticalBlock"] .interactive-pitch-anchor)) .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%) !important;
        color: #FFFFFF !important;
        border: 2.5px solid #FFFFFF !important;
        box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.45), 0 6px 16px rgba(0,0,0,0.4) !important;
        transform: scale(1.06) !important;
    }
    div[data-testid="stVerticalBlock"]:has(.interactive-pitch-anchor):not(:has(div[data-testid="stVerticalBlock"] .interactive-pitch-anchor)) .stButton > button[kind="primary"] p {
        color: #FFFFFF !important;
    }

    /* 3. Sayfa: Birleşik Kaydırmalı Oyuncu Kartı Navigasyonu (Yalnızca İç Konteyner) */
    div[data-testid="stVerticalBlock"]:has(.carousel-nav-anchor):not(:has(div[data-testid="stVerticalBlock"] .carousel-nav-anchor)) [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 8px !important;
    }
    div[data-testid="stVerticalBlock"]:has(.carousel-nav-anchor):not(:has(div[data-testid="stVerticalBlock"] .carousel-nav-anchor)) [data-testid="stColumn"] {
        min-width: 0 !important;
    }

    .unified-player-card {
        background: #FFFFFF;
        border-radius: 18px;
        overflow: hidden;
        border: 2px solid var(--border-light);
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
        margin-bottom: 14px;
    }
    .unified-card-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 55%, #059669 100%);
        color: #FFFFFF;
        padding: 20px 18px 18px 18px;
        text-align: center;
    }
    .sliding-avatar-ring {
        width: 86px;
        height: 86px;
        border-radius: 50%;
        border: 3px solid #FFFFFF;
        padding: 3px;
        margin: 0 auto 10px auto;
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
        font-size: 1.4rem;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .unified-player-name {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.3rem;
        font-weight: 800;
        color: #FFFFFF;
        margin: 0 0 4px 0;
    }
    .unified-player-sub {
        font-size: 0.85rem;
        color: #E2E8F0;
        font-weight: 500;
    }
    .unified-kpi-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        padding: 14px 16px 0 16px;
    }
    .unified-kpi-box {
        background: var(--bg-subtle);
        border: 1px solid var(--border-light);
        border-radius: 12px;
        padding: 10px 8px;
        text-align: center;
    }
    .unified-kpi-label {
        font-size: 0.68rem;
        font-weight: 700;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .unified-kpi-val {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.15rem;
        font-weight: 800;
        color: var(--navy-900);
        margin-top: 2px;
    }
    .unified-body {
        padding: 14px 16px 18px 16px;
    }
    .info-grid-2 {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
        margin-bottom: 12px;
    }
    .info-cell {
        background: var(--bg-subtle);
        border: 1px solid var(--border-light);
        border-radius: 10px;
        padding: 8px 12px;
        font-size: 0.82rem;
    }
    .info-cell span {
        display: block;
        font-size: 0.68rem;
        font-weight: 700;
        color: var(--text-muted);
        text-transform: uppercase;
    }

    /* Beceri Çubukları (Masaüstünde 4, Mobilde 2x2) */
    .attr-grid-4 {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin: 10px 0 12px 0;
    }
    .attr-box {
        background: var(--bg-subtle);
        border: 1px solid var(--border-light);
        border-radius: 10px;
        padding: 9px 11px;
    }
    .attr-head {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 5px;
    }
    .attr-name {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        color: var(--text-secondary);
    }
    .attr-score {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.98rem;
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

    /* Carousel Nokta Göstergeleri */
    .carousel-dots {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 6px;
        margin: 6px 0;
    }
    .c-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #CBD5E1;
    }
    .c-dot.active {
        width: 22px;
        border-radius: 999px;
        background: var(--emerald-600);
    }

    /* 4. Sayfa: Tüm Öneriler & Seçilen Kart İbaresi */
    .eval-summary-card {
        background: var(--bg-card);
        border: 2px solid var(--border-light);
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 8px;
    }
    .eval-summary-card.chosen-card {
        border: 2.5px solid var(--emerald-500);
        background: linear-gradient(180deg, #ECFDF5 0%, #FFFFFF 55%);
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.14);
    }
    .chosen-ribbon {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: var(--emerald-600);
        color: #FFFFFF;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.7rem;
        font-weight: 800;
        text-transform: uppercase;
        padding: 4px 10px;
        border-radius: 999px;
        margin-bottom: 6px;
    }
    .other-ribbon {
        display: inline-flex;
        align-items: center;
        background: var(--bg-subtle);
        border: 1px solid var(--border-light);
        color: var(--text-secondary);
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        padding: 3px 9px;
        border-radius: 999px;
        margin-bottom: 6px;
    }
    .sliding-pill-ovr {
        background: var(--navy-900);
        color: #FFFFFF;
        font-size: 0.74rem;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 999px;
    }
    .sliding-pill-fit {
        background: #ECFDF5;
        color: #059669;
        border: 1px solid #A7F3D0;
        font-size: 0.74rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 999px;
    }

    /* Genel Buton Stilleri */
    .stButton > button,
    .stFormSubmitButton > button {
        border-radius: 10px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.88rem !important;
        min-height: 46px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.18s ease !important;
    }
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"] {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 5px 14px rgba(16, 185, 129, 0.25) !important;
    }
    .stButton > button[kind="primary"] p,
    .stFormSubmitButton > button[kind="primary"] p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* MOBİL EKRANLAR İÇİN ÖZEL KURALLAR (TELEFON GÖRÜNÜMÜ) */
    @media (max-width: 640px) {
        .block-container {
            padding-top: 0.6rem !important;
            padding-left: 0.65rem !important;
            padding-right: 0.65rem !important;
        }
        .portal-topbar {
            padding: 12px 14px;
        }
        .portal-title {
            font-size: 1.02rem;
        }
        .wizard-stepper {
            gap: 5px;
            margin-bottom: 14px;
        }
        .step-item {
            padding: 7px 6px;
            gap: 5px;
        }
        .step-circle {
            width: 20px;
            height: 20px;
            font-size: 0.68rem;
        }
        .step-label-title {
            font-size: 0.7rem;
        }
        .attr-grid-4 {
            grid-template-columns: repeat(2, 1fr);
        }
        .info-grid-2 {
            grid-template-columns: 1fr;
        }
        .coach-id-value {
            font-size: 0.95rem;
        }
        /* Diziliş kartları mobilde 2'li yan yana dizilsin */
        div[data-testid="stVerticalBlock"]:has(.formation-grid-anchor):not(:has(div[data-testid="stVerticalBlock"] .formation-grid-anchor)) [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            gap: 8px !important;
        }
        div[data-testid="stVerticalBlock"]:has(.formation-grid-anchor):not(:has(div[data-testid="stVerticalBlock"] .formation-grid-anchor)) [data-testid="stColumn"] {
            flex: 0 0 calc(50% - 4px) !important;
            width: calc(50% - 4px) !important;
            min-width: calc(50% - 4px) !important;
        }
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
    conn.close()
    return row


@st.cache_resource
def sync_initial_evaluations_from_github():
    try:
        return pull_evaluations_from_github_to_db('data/ktff.db')
    except Exception:
        return 0, 0


def init_evaluation_table():
    conn = sqlite3.connect('data/ktff.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS coach_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coach_name TEXT,
            club_name TEXT,
            player_id INTEGER,
            player_name TEXT,
            target_position TEXT,
            formation TEXT,
            player_type TEXT,
            is_known INTEGER DEFAULT 1,
            model_score REAL,
            tactical_fit_rating INTEGER,
            playing_time_rating INTEGER,
            feasibility_rating INTEGER,
            decision TEXT,
            feedback_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    for col_name, col_type in [
        ("formation", "TEXT"),
        ("player_type", "TEXT"),
        ("is_known", "INTEGER DEFAULT 1")
    ]:
        try:
            cur.execute(f"ALTER TABLE coach_evaluations ADD COLUMN {col_name} {col_type};")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def save_evaluation_to_db(
    coach_name, club_name, player_id, player_name, target_pos,
    formation, player_type, is_known, model_score,
    tactical_fit, playing_time, feasibility, decision, note,
    sync_now=True
):
    conn = sqlite3.connect('data/ktff.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO coach_evaluations (
            coach_name, club_name, player_id, player_name, target_position,
            formation, player_type, is_known, model_score,
            tactical_fit_rating, playing_time_rating, feasibility_rating,
            decision, feedback_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        coach_name, club_name, player_id, player_name, target_pos,
        formation, player_type, is_known, model_score,
        tactical_fit, playing_time, feasibility, decision, note
    ))
    conn.commit()
    conn.close()
    if sync_now:
        return push_evaluations_to_github('data/ktff.db')
    return True, "Kaydedildi"


init_evaluation_table()
sync_initial_evaluations_from_github()
recommender = get_recommender()
coaches_df, clubs_df = get_coaches_and_clubs()


# =============================================================================
# TAKTİK DİZİLİŞLER, SAHA KOORDİNATLARI VE OYUNCU TİPLERİ
# =============================================================================
ARCHETYPE_MAP = {
    "Santrafor / Forvet (FW)": [
        "Hedef Santrafor (Fizik & Hava Hakimiyeti)",
        "Hızlı Kontratak Forveti",
        "Ceza Sahası Bitiricisi (Poacher)",
        "Sahte 9 / Bağlantı Oyuncusu"
    ],
    "Kanat Forvet / Açık (Winger - LW/RW)": [
        "İçeri Kateden Skorer Kanat",
        "Çizgiye İnen Orta & Tempo Kanadı",
        "Pres Gücü Yüksek Çalışkan Kanat"
    ],
    "Merkez / Ofansif Orta Saha (CM/CAM)": [
        "Oyun Kurucu (Pas & Skor Katkısı)",
        "İki Yönlü Dinamo (Box-to-Box)",
        "Yaratıcı 10 Numara"
    ],
    "Defansif Orta Saha / Ön Libero (CDM)": [
        "Defansif Çapa / Top Kapan Kesici",
        "Geriden Oyun Kuran Regista"
    ],
    "Stoper / Savunma (CB)": [
        "Hava Hakimiyeti Olan Sert Stoper",
        "Topla Çıkan Pasör Stoper",
        "Hızlı ve Kademeci Stoper"
    ],
    "Bek / Kanat Bek (LB/RB)": [
        "Hücumcu Bindirmeci Dinamik Bek",
        "Savunma Öncelikli Pozisyonel Bek"
    ],
    "Kaleci (GK)": [
        "Çizgi Kalecisi & Çevik Refleks",
        "Modern Ayaklı Süpürücü Kaleci"
    ]
}

FORMATIONS_SPEC = {
    "4-4-2": {
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
        "rows": [
            [
                ("LW", "SLK", "Sol Kanat Forvet (LW)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 20, 20),
                ("ST", "SNT", "Merkez Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 50, 16),
                ("RW", "SĞK", "Sağ Kanat Forvet (RW)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 80, 20),
            ],
            [
                ("CM_L", "MO", "Sol İç Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 28, 44),
                ("CDM", "DOS", "Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 50, 50),
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
        "rows": [
            [
                ("ST", "SNT", "Merkez Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 50, 16),
            ],
            [
                ("LW", "SLK", "Sol Kanat (LW)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 20, 34),
                ("CAM", "MOO", "10 Numara (CAM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 50, 34),
                ("RW", "SĞK", "Sağ Kanat (RW)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 80, 34),
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
        "rows": [
            [
                ("ST_L", "SNT", "Sol Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 36, 18),
                ("ST_R", "SNT", "Sağ Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 64, 18),
            ],
            [
                ("LWB", "SLKB", "Sol Kanat Bek (LWB)", "DF", "Bek / Kanat Bek (LB/RB)", 14, 42),
                ("CM_L", "MO", "Sol İç Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 33, 44),
                ("CDM", "DOS", "Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 50, 50),
                ("CM_R", "MO", "Sağ İç Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 67, 44),
                ("RWB", "SĞKB", "Sağ Kanat Bek (RWB)", "DF", "Bek / Kanat Bek (LB/RB)", 86, 42),
            ],
            [
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 26, 74),
                ("CB_C", "STP", "Merkez Stoper (CB)", "DF", "Stoper / Savunma (CB)", 50, 75),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 74, 74),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    },
    "3-4-3": {
        "rows": [
            [
                ("LW", "SLK", "Sol Kanat Forvet (LW)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 22, 20),
                ("ST", "SNT", "Merkez Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 50, 16),
                ("RW", "SĞK", "Sağ Kanat Forvet (RW)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 78, 20),
            ],
            [
                ("LM", "SLKB", "Sol Kanat Bek (LM)", "DF", "Bek / Kanat Bek (LB/RB)", 16, 46),
                ("CM_L", "MO", "Sol Merkez Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 39, 47),
                ("CM_R", "MO", "Sağ Merkez Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 61, 47),
                ("RM", "SĞKB", "Sağ Kanat Bek (RM)", "DF", "Bek / Kanat Bek (LB/RB)", 84, 46),
            ],
            [
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 26, 74),
                ("CB_C", "STP", "Merkez Stoper (CB)", "DF", "Stoper / Savunma (CB)", 50, 75),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 74, 74),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    },
    "4-1-4-1": {
        "rows": [
            [
                ("ST", "SNT", "Tek Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 50, 16),
            ],
            [
                ("LM", "SLK", "Sol Kanat (LM)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 16, 38),
                ("CM_L", "MO", "Sol İç Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 38, 39),
                ("CM_R", "MO", "Sağ İç Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 62, 39),
                ("RM", "SĞK", "Sağ Kanat (RM)", "FW", "Kanat Forvet / Açık (Winger - LW/RW)", 84, 38),
            ],
            [
                ("CDM", "DOS", "Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 50, 55),
            ],
            [
                ("LB", "SLB", "Sol Bek (LB)", "DF", "Bek / Kanat Bek (LB/RB)", 16, 74),
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 38, 75),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 62, 75),
                ("RB", "SĞB", "Sağ Bek (RB)", "DF", "Bek / Kanat Bek (LB/RB)", 84, 74),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    },
    "5-3-2": {
        "rows": [
            [
                ("ST_L", "SNT", "Sol Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 36, 18),
                ("ST_R", "SNT", "Sağ Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 64, 18),
            ],
            [
                ("CM_L", "MO", "Sol İç Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 28, 45),
                ("CDM", "DOS", "Merkez Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 50, 48),
                ("CM_R", "MO", "Sağ İç Orta Saha (CM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 72, 45),
            ],
            [
                ("LWB", "SLB", "Sol Kanat Bek (LWB)", "DF", "Bek / Kanat Bek (LB/RB)", 13, 68),
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 32, 74),
                ("CB_C", "STP", "Merkez Stoper (CB)", "DF", "Stoper / Savunma (CB)", 50, 75),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 68, 74),
                ("RWB", "SĞB", "Sağ Kanat Bek (RWB)", "DF", "Bek / Kanat Bek (LB/RB)", 87, 68),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    },
    "4-2-2-2": {
        "rows": [
            [
                ("ST_L", "SNT", "Sol Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 36, 18),
                ("ST_R", "SNT", "Sağ Santrafor (ST)", "FW", "Santrafor / Forvet (FW)", 64, 18),
            ],
            [
                ("CAM_L", "MOO", "Sol Ofansif Orta Saha (CAM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 24, 36),
                ("CAM_R", "MOO", "Sağ Ofansif Orta Saha (CAM)", "MF", "Merkez / Ofansif Orta Saha (CM/CAM)", 76, 36),
            ],
            [
                ("CDM_L", "DOS", "Sol Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 36, 54),
                ("CDM_R", "DOS", "Sağ Ön Libero (CDM)", "MF", "Defansif Orta Saha / Ön Libero (CDM)", 64, 54),
            ],
            [
                ("LB", "SLB", "Sol Bek (LB)", "DF", "Bek / Kanat Bek (LB/RB)", 16, 74),
                ("CB_L", "STP", "Sol Stoper (CB)", "DF", "Stoper / Savunma (CB)", 38, 75),
                ("CB_R", "STP", "Sağ Stoper (CB)", "DF", "Stoper / Savunma (CB)", 62, 75),
                ("RB", "SĞB", "Sağ Bek (RB)", "DF", "Bek / Kanat Bek (LB/RB)", 84, 74),
            ],
            [
                ("GK", "KL", "Kaleci (GK)", "GK", "Kaleci (GK)", 50, 90),
            ]
        ]
    }
}


def render_mini_pitch_svg(formation_key, is_selected=False):
    """Diziliş seçim kartları için kompakt yeşil futbol sahası SVG şeması."""
    spec = FORMATIONS_SPEC[formation_key]
    dot_fill = "#F59E0B" if is_selected else "#FFFFFF"
    dot_stroke = "#0F172A"
    dots_svg = ""
    for row in spec["rows"]:
        for node in row:
            _, _, _, _, _, cx, cy = node
            dots_svg += f'<circle cx="{cx}" cy="{cy * 1.3}" r="5.2" fill="{dot_fill}" stroke="{dot_stroke}" stroke-width="1.8"/>'

    svg = f"""
    <svg viewBox="0 0 100 130" width="100%" height="105" style="border-radius:8px; display:block; margin:0 auto;">
        <rect x="0" y="0" width="100" height="130" rx="6" fill="#15803D"/>
        <rect x="0" y="0" width="100" height="26" fill="#16A34A"/>
        <rect x="0" y="52" width="100" height="26" fill="#16A34A"/>
        <rect x="0" y="104" width="100" height="26" fill="#16A34A"/>
        <rect x="5" y="5" width="90" height="120" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="1.4"/>
        <line x1="5" y1="65" x2="95" y2="65" stroke="rgba(255,255,255,0.85)" stroke-width="1.3"/>
        <circle cx="50" cy="65" r="14" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="1.3"/>
        <rect x="25" y="5" width="50" height="18" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="1.2"/>
        <rect x="25" y="107" width="50" height="18" fill="none" stroke="rgba(255,255,255,0.85)" stroke-width="1.2"/>
        {dots_svg}
    </svg>
    """
    return svg


# =============================================================================
# SESSION STATE BAŞLATMA
# =============================================================================
if 'wizard_step' not in st.session_state:
    st.session_state['wizard_step'] = 1

if 'page2_mode' not in st.session_state:
    st.session_state['page2_mode'] = 'gallery'

if 'selected_coach' not in st.session_state:
    default_coach = "ERDİNÇ BÖREKÇİ" if "ERDİNÇ BÖREKÇİ" in list(coaches_df['name']) else coaches_df.iloc[0]['name']
    st.session_state['selected_coach'] = default_coach

if 'selected_formation' not in st.session_state:
    st.session_state['selected_formation'] = "4-3-3"

if 'selected_node' not in st.session_state:
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
    <h1 class="portal-title">⚽ ScoutMe Antrenör Portalı</h1>
    <span class="portal-step-pill">Adım {curr_step} / 4</span>
</div>
""")

step_titles = [
    (1, "Antrenör"),
    (2, "Taktik & Mevki"),
    (3, "Adaylar"),
    (4, "Değerlendirme")
]

stepper_html = '<div class="wizard-stepper">'
for s_num, s_title in step_titles:
    cls = "active" if s_num == curr_step else ("completed" if s_num < curr_step else "")
    icon_txt = "✓" if s_num < curr_step else str(s_num)
    stepper_html += f"""
    <div class="step-item {cls}">
        <div class="step-circle">{icon_txt}</div>
        <div class="step-label-title">{s_title}</div>
    </div>
    """
stepper_html += '</div>'
render_html(stepper_html)


# =============================================================================
# 1. SAYFA: TEKNİK DİREKTÖR SEÇİMİ & OTOMATİK KULÜP BİLGİSİ
# =============================================================================
if curr_step == 1:
    render_html("""
    <div class="page-card">
        <h2 style="margin:0 0 4px 0; font-size:1.25rem;">Teknik Direktör Seçimi</h2>
        <p style="color:#475569; font-size:0.88rem; margin:0;">
            Listeden isminizi seçiniz; görev yaptığınız kulüp otomatik olarak eşleştirilir.
        </p>
    </div>
    """)

    coach_options = sorted(list(coaches_df['name'].unique()))
    current_coach_idx = (
        coach_options.index(st.session_state['selected_coach'])
        if st.session_state['selected_coach'] in coach_options else 0
    )

    coach_box = st.container()
    with coach_box:
        render_html('<div class="coach-select-anchor"></div>')
        chosen_coach = st.selectbox(
            "👤 TEKNİK DİREKTÖR SEÇİNİZ (İsminize Tıklayın)",
            options=coach_options,
            index=current_coach_idx,
            key="page1_coach_select"
        )
    st.session_state['selected_coach'] = chosen_coach

    c_row = coaches_df[coaches_df['name'] == chosen_coach]
    auto_club_name = c_row.iloc[0]['club_name'] if len(c_row) > 0 else clubs_df.iloc[0]['name']
    auto_role = c_row.iloc[0]['role'] if len(c_row) > 0 else "Teknik Direktör"

    club_info_row = clubs_df[clubs_df['name'] == auto_club_name]
    auto_league = club_info_row.iloc[0]['league_name'] if len(club_info_row) > 0 else "KTFF"
    auto_city = club_info_row.iloc[0]['city'] if len(club_info_row) > 0 else ""

    st.session_state['selected_club'] = auto_club_name

    render_html(f"""
    <div class="coach-id-card">
        <div class="coach-id-row">
            <div class="coach-id-label">Teknik Direktör</div>
            <div class="coach-id-value">
                <span>👤 {chosen_coach}</span>
                <span class="league-pill" style="background:#ECFDF5; color:#059669; border-color:#A7F3D0;">{auto_role}</span>
            </div>
        </div>
        <div class="coach-id-row">
            <div class="coach-id-label">Kulüp & Lig</div>
            <div class="coach-id-value">
                <span>🛡️ {auto_club_name}</span>
                <span class="league-pill">{auto_league}{f' • {auto_city}' if auto_city else ''}</span>
            </div>
        </div>
    </div>
    """)

    if st.button("Devam Et →", type="primary", use_container_width=True, key="btn_page1_next"):
        st.session_state['wizard_step'] = 2
        st.session_state['page2_mode'] = 'gallery'
        st.rerun()


# =============================================================================
# 2. SAYFA: 2 AŞAMALI DİZİLİŞ GALERİSİ -> ZOOM-IN SAHA & OYUNCU TİPİ SEÇİMİ
# =============================================================================
elif curr_step == 2:
    page2_mode = st.session_state.get('page2_mode', 'gallery')
    active_form = st.session_state.get('selected_formation', '4-3-3')

    # -------------------------------------------------------------------------
    # AŞAMA 1: İLK GÖRÜNÜM (YALNIZCA DİZİLİŞ GALERİSİ)
    # -------------------------------------------------------------------------
    if page2_mode == 'gallery':
        render_html(f"""
        <div class="section-bar">
            <h2 class="section-bar-title">Diziliş Seçiniz</h2>
            <div class="section-bar-meta">
                👤 {st.session_state.get('selected_coach')} &bull; 🛡️ {st.session_state.get('selected_club')}
            </div>
        </div>
        """)

        formation_keys = list(FORMATIONS_SPEC.keys())

        form_grid_container = st.container()
        with form_grid_container:
            render_html('<div class="formation-grid-anchor"></div>')
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
                        if st.button(
                            f"{f_key} Seç →",
                            key=f"select_form_{f_key}",
                            type="primary" if is_sel else "secondary",
                            use_container_width=True
                        ):
                            st.session_state['selected_formation'] = f_key
                            first_node = FORMATIONS_SPEC[f_key]["rows"][0][0]
                            st.session_state['selected_node'] = first_node
                            st.session_state['selected_archetype'] = ARCHETYPE_MAP[first_node[4]][0]
                            st.session_state['page2_mode'] = 'pitch'
                            st.rerun()

        st.write("")
        if st.button("← Antrenör Seçimine Dön", use_container_width=True, key="btn_page2_back_to_p1"):
            st.session_state['wizard_step'] = 1
            st.rerun()

    # -------------------------------------------------------------------------
    # AŞAMA 2: ZOOM-IN SAHA İÇİ POZİSYON VE OYUNCU TİPİ SEÇİMİ
    # -------------------------------------------------------------------------
    else:
        form_spec = FORMATIONS_SPEC[active_form]
        current_node = st.session_state.get('selected_node')

        all_nodes_in_form = [n for r in form_spec["rows"] for n in r]
        valid_node_ids = [n[0] for n in all_nodes_in_form]
        if not current_node or current_node[0] not in valid_node_ids:
            current_node = all_nodes_in_form[0]
            st.session_state['selected_node'] = current_node

        render_html(f"""
        <div class="section-bar">
            <h2 class="section-bar-title">📐 {active_form} — Mevki Noktasına Dokunun</h2>
            <div class="section-bar-meta">Seçili: <strong>{current_node[2]}</strong></div>
        </div>
        """)

        if st.button("🔄 Dizilişi Değiştir", key="btn_change_formation"):
            st.session_state['page2_mode'] = 'gallery'
            st.rerun()

        pitch_container = st.container()
        with pitch_container:
            render_html('<div class="interactive-pitch-anchor"></div>')
            render_html(
                '<div style="text-align:center; color:rgba(255,255,255,0.92); font-size:0.7rem; font-weight:800; letter-spacing:0.08em; margin-bottom:8px;">'
                f'⬆️ HÜCUM YÖNÜ ({active_form}) ⬆️</div>'
            )

            for r_idx, row_nodes in enumerate(form_spec["rows"]):
                target_cols = st.columns(len(row_nodes))
                for c_i, node_tuple in enumerate(row_nodes):
                    node_id, short_code, full_lbl, pos_cat, sub_lbl, cx, cy = node_tuple
                    is_active_dot = (current_node[0] == node_id)
                    dot_label = f"★ {short_code}" if is_active_dot else short_code
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
                    render_html('<div style="height:8px;"></div>')

            render_html(
                '<div style="text-align:center; color:rgba(255,255,255,0.92); font-size:0.7rem; font-weight:800; letter-spacing:0.08em; margin-top:6px;">'
                '⬇️ KALE ⬇️</div>'
            )

        sel_node_id, sel_short, sel_full_name, sel_pos_cat, sel_sub_label, _, _ = st.session_state['selected_node']
        available_archetypes = ARCHETYPE_MAP.get(sel_sub_label, ["Dengeli Oyuncu"])
        if st.session_state.get('selected_archetype') not in available_archetypes:
            st.session_state['selected_archetype'] = available_archetypes[0]

        render_html(f"""
        <div class="section-bar" style="border-left:4px solid #10B981;">
            <h2 class="section-bar-title">Oyuncu Tipi Seçiniz</h2>
            <div class="section-bar-meta">🎯 {sel_full_name}</div>
        </div>
        """)

        arch_cols = st.columns(min(2, len(available_archetypes)))
        for a_i, arch_name in enumerate(available_archetypes):
            is_arch_sel = (st.session_state.get('selected_archetype') == arch_name)
            with arch_cols[a_i % len(arch_cols)]:
                if st.button(
                    f"{'✓ ' if is_arch_sel else ''}{arch_name}",
                    key=f"arch_btn_{a_i}_{sel_node_id}",
                    type="primary" if is_arch_sel else "secondary",
                    use_container_width=True
                ):
                    st.session_state['selected_archetype'] = arch_name
                    st.rerun()

        st.write("")
        nav_c1, nav_c2 = st.columns([1, 2])
        with nav_c1:
            if st.button("← Dizilişlere Dön", use_container_width=True, key="btn_page2_back"):
                st.session_state['page2_mode'] = 'gallery'
                st.rerun()
        with nav_c2:
            if st.button("Devam Et (Önerileri Getir) →", type="primary", use_container_width=True, key="btn_page2_next"):
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
# 3. SAYFA: KAYDIRMALI (CAROUSEL) BİRLEŞİK OYUNCU KARTI & SEÇİM
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
    <div class="section-bar">
        <h2 class="section-bar-title">Önerilen Oyuncular ({c_idx + 1} / {n_recs})</h2>
        <div class="section-bar-meta">
            📐 {st.session_state.get('selected_formation')} &bull; 🎯 {sel_node[2]}
        </div>
    </div>
    """)

    # Üst Kaydırma (Carousel) Navigasyon Barı (Mobilde de Yatay Kalır)
    carousel_nav = st.container()
    with carousel_nav:
        render_html('<div class="carousel-nav-anchor"></div>')
        nav_l, nav_mid, nav_r = st.columns([1.2, 2.6, 1.2])
        with nav_l:
            if st.button("❮ Önceki", key="carousel_prev_btn", use_container_width=True):
                st.session_state['carousel_idx'] = (c_idx - 1) % n_recs
                st.rerun()
        with nav_mid:
            dots_html = '<div class="carousel-dots">'
            for d_i in range(n_recs):
                d_cls = "active" if d_i == c_idx else ""
                dots_html += f'<div class="c-dot {d_cls}"></div>'
            dots_html += '</div>'
            render_html(dots_html)
        with nav_r:
            if st.button("Sonraki ❯", key="carousel_next_btn", use_container_width=True):
                st.session_state['carousel_idx'] = (c_idx + 1) % n_recs
                st.rerun()

    # Birleşik Oyuncu Kartı
    active_p = recs[c_idx]
    p_full = get_player_full_details(active_p['player_id'])
    photo_url = p_full[4] if (p_full and len(p_full) > 4 and p_full[4]) else None
    initials = "".join([w[0] for w in active_p['name'].split()[:2]]) if active_p['name'] else "OY"

    avatar_html = (
        f'<img src="{photo_url}" alt="{active_p["name"]}"/>'
        if photo_url
        else f'<div class="sliding-avatar-initials">{initials}</div>'
    )

    tot_matches_3y = p_full[13] if p_full else active_p['played_matches']
    starter_pct = (p_full[15] * 100.0) if p_full else 0.0
    tot_goals_3y = p_full[14] if p_full else 0
    net_diff_val = p_full[11] if p_full else 0.0

    render_html(f"""
    <div class="unified-player-card">
        <div class="unified-card-header">
            <div class="sliding-avatar-ring">{avatar_html}</div>
            <h3 class="unified-player-name">{active_p['name']}</h3>
            <div class="unified-player-sub">
                {active_p['current_club']} &bull; {active_p['age']} Yaş &bull; {active_p['prim_pos']}
            </div>
        </div>

        <div class="unified-kpi-row">
            <div class="unified-kpi-box">
                <div class="unified-kpi-label">Genel Reyting</div>
                <div class="unified-kpi-val">{active_p['ovr']} OVR</div>
            </div>
            <div class="unified-kpi-box">
                <div class="unified-kpi-label">Taktik Uyum</div>
                <div class="unified-kpi-val" style="color:#059669;">%{active_p['tactical_fit_pct']}</div>
            </div>
            <div class="unified-kpi-box">
                <div class="unified-kpi-label">İlk 11 Şansı</div>
                <div class="unified-kpi-val" style="color:#2563EB;">%{active_p['playing_time_chance_pct']}</div>
            </div>
        </div>

        <div class="unified-body">
            <div class="attr-grid-4">
                <div class="attr-box">
                    <div class="attr-head"><span class="attr-name">Fiziksel</span><span class="attr-score">{active_p['phys']:.0f}</span></div>
                    <div class="attr-bar-bg"><div class="attr-bar-fill" style="width:{min(100, max(0, active_p['phys']))}%;"></div></div>
                </div>
                <div class="attr-box">
                    <div class="attr-head"><span class="attr-name">Şut</span><span class="attr-score">{active_p['shoot']:.0f}</span></div>
                    <div class="attr-bar-bg"><div class="attr-bar-fill" style="width:{min(100, max(0, active_p['shoot']))}%;"></div></div>
                </div>
                <div class="attr-box">
                    <div class="attr-head"><span class="attr-name">Teknik</span><span class="attr-score">{active_p['tech']:.0f}</span></div>
                    <div class="attr-bar-bg"><div class="attr-bar-fill" style="width:{min(100, max(0, active_p['tech']))}%;"></div></div>
                </div>
                <div class="attr-box">
                    <div class="attr-head"><span class="attr-name">Defans</span><span class="attr-score">{active_p['def']:.0f}</span></div>
                    <div class="attr-bar-bg"><div class="attr-bar-fill" style="width:{min(100, max(0, active_p['def']))}%;"></div></div>
                </div>
            </div>

            <div class="info-grid-2">
                <div class="info-cell">
                    <span>Maç & İlk 11 İstikrarı</span>
                    <strong>{tot_matches_3y} Maç ({active_p.get('a_team_matches', 0)} A-Takım | İlk 11: %{starter_pct:.0f})</strong>
                </div>
                <div class="info-cell">
                    <span>Skor & Saha İçi Katkı</span>
                    <strong>{tot_goals_3y} Gol ({net_diff_val:+.2f} Maç Başı Averaj)</strong>
                </div>
            </div>

            <div style="background:#ECFDF5; border-left:4px solid #059669; border-radius:8px; padding:10px 14px; font-size:0.84rem; color:#065F46;">
                <strong>Scout Notu:</strong> {active_p['scout_verdict']}
            </div>
        </div>
    </div>
    """)

    b_col1, b_col2 = st.columns([1, 2])
    with b_col1:
        if st.button("← Mevki Değiştir", use_container_width=True, key="btn_page3_back"):
            st.session_state['page2_mode'] = 'pitch'
            st.session_state['wizard_step'] = 2
            st.rerun()
    with b_col2:
        if st.button(
            "✓ Bu Oyuncuyu Seç ve Değerlendir →",
            type="primary",
            use_container_width=True,
            key="btn_page3_select_player"
        ):
            st.session_state['selected_player_id'] = active_p['player_id']
            st.session_state['wizard_step'] = 4
            st.rerun()


# =============================================================================
# 4. SAYFA: TÜM ÖNERİLER ("★ SEÇİLEN OYUNCU" VURGULU) & DEĞERLENDİRME FORMU
# =============================================================================
elif curr_step == 4:
    recs = st.session_state.get('portal_recs', [])
    chosen_pid = st.session_state.get('selected_player_id')
    sel_node = st.session_state.get('selected_node')

    render_html(f"""
    <div class="section-bar">
        <h2 class="section-bar-title">Önerilen Adayları Değerlendirin</h2>
        <div class="section-bar-meta">
            👤 {st.session_state.get('selected_coach')} &bull; 🛡️ {st.session_state.get('selected_club')}
        </div>
    </div>
    """)

    with st.form(key="page4_all_evaluations_form"):
        for idx, p in enumerate(recs, 1):
            is_chosen = (p['player_id'] == chosen_pid)
            card_cls = "chosen-card" if is_chosen else ""
            ribbon_html = (
                '<div class="chosen-ribbon">★ SEÇİLEN OYUNCU</div>'
                if is_chosen
                else f'<div class="other-ribbon">ADAY #{idx}</div>'
            )

            render_html(f"""
            <div class="eval-summary-card {card_cls}">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
                    <div>
                        {ribbon_html}
                        <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:1.1rem; font-weight:800; color:#0F172A;">
                            {p['name']}
                        </div>
                        <div style="font-size:0.82rem; color:#475569;">
                            {p['current_club']} &bull; {p['age']} Yaş &bull; {p['prim_pos']}
                        </div>
                    </div>
                    <div style="display:flex; gap:6px; align-items:center;">
                        <span class="sliding-pill-fit">%{p['tactical_fit_pct']} Uyum</span>
                        <span class="sliding-pill-ovr">{p['ovr']} OVR</span>
                    </div>
                </div>
            </div>
            """)

            r_col1, r_col2, r_col3 = st.columns(3)
            default_rating = 5 if is_chosen else 4
            default_dec_idx = 0 if is_chosen else 1

            with r_col1:
                st.select_slider(
                    "Taktik Uyum (1–5)",
                    options=[1, 2, 3, 4, 5],
                    value=default_rating,
                    key=f"p4_tac_{p['player_id']}"
                )
            with r_col2:
                st.select_slider(
                    "İlk 11 Şansı (1–5)",
                    options=[1, 2, 3, 4, 5],
                    value=default_rating,
                    key=f"p4_play_{p['player_id']}"
                )
            with r_col3:
                st.select_slider(
                    "Transfer Mantığı (1–5)",
                    options=[1, 2, 3, 4, 5],
                    value=default_rating,
                    key=f"p4_feas_{p['player_id']}"
                )

            k_col1, k_col2 = st.columns(2)
            with k_col1:
                st.selectbox(
                    "Transfer Kararınız",
                    options=[
                        "Kesinlikle Alırım (İlk 11)",
                        "Rotasyona Alırım",
                        "İzleme Listesine Alırım",
                        "Uygun Değil"
                    ],
                    index=default_dec_idx,
                    key=f"p4_dec_{p['player_id']}"
                )
            with k_col2:
                st.radio(
                    "Oyuncuyu tanıyor musunuz?",
                    options=["Evet", "Hayır"],
                    horizontal=True,
                    key=f"p4_known_{p['player_id']}"
                )

            st.text_input(
                "Kısa Yorum / Not (İsteğe Bağlı)",
                placeholder="Örn: Sistemimize uygun, fiziksel temposu yeterli...",
                key=f"p4_note_{p['player_id']}"
            )

            render_html('<hr style="border:none; border-top:1px solid #E2E8F0; margin:10px 0 16px 0;"/>')

        general_feedback = st.text_area(
            "Genel Değerlendirme Notunuz (İsteğe Bağlı)",
            placeholder="Önerilerin genel isabeti hakkındaki görüşünüz...",
            height=70,
            key="p4_general_comment"
        )

        submit_all = st.form_submit_button(
            "✓ Değerlendirmeyi Kaydet",
            type="primary",
            use_container_width=True
        )

        if submit_all:
            dec_val_map = {
                "Kesinlikle Alırım (İlk 11)": "buy",
                "Rotasyona Alırım": "rotation",
                "İzleme Listesine Alırım": "watchlist",
                "Uygun Değil": "reject"
            }

            for i_rec, p in enumerate(recs):
                pid = p['player_id']
                is_chosen = (pid == chosen_pid)
                tac_val = st.session_state.get(f"p4_tac_{pid}", 4)
                play_val = st.session_state.get(f"p4_play_{pid}", 4)
                feas_val = st.session_state.get(f"p4_feas_{pid}", 4)
                dec_lbl = st.session_state.get(f"p4_dec_{pid}", "Rotasyona Alırım")
                known_lbl = st.session_state.get(f"p4_known_{pid}", "Evet")
                note_txt = st.session_state.get(f"p4_note_{pid}", "").strip()

                prefix_tag = "[SEÇİLEN OYUNCU] " if is_chosen else ""
                combined_note = f"{prefix_tag}{note_txt}"
                if general_feedback.strip() and is_chosen:
                    combined_note = f"{combined_note} | Genel Not: {general_feedback.strip()}".strip(" |")

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

            st.success("✓ Değerlendirmeniz başarıyla kaydedildi! Katkınız için teşekkür ederiz.")
            st.balloons()

    f_nav1, f_nav2 = st.columns(2)
    with f_nav1:
        if st.button("← Aday Kartlarına Dön", use_container_width=True, key="btn_page4_back3"):
            st.session_state['wizard_step'] = 3
            st.rerun()
    with f_nav2:
        if st.button("🔄 Yeni Mevki / Diziliş Seç", use_container_width=True, key="btn_page4_back2"):
            st.session_state['page2_mode'] = 'gallery'
            st.session_state['wizard_step'] = 2
            st.rerun()
