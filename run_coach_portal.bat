@echo off
title ScoutMe Coach Evaluation Portal (Swiss Monochrome)
echo ScoutMe Antrenor ve Scout Degerlendirme Portali baslatiliyor...
echo Tarayiciniz otomatik olarak acilacaktir (Varsayilan Port: 8502)
echo.
cd /d "%~dp0"
set PYTHONPATH=%cd%
streamlit run coach_portal.py --server.port 8502 --theme.base "light" --theme.primaryColor "#09090B" --theme.backgroundColor "#FFFFFF" --theme.secondaryBackgroundColor "#FAFAFA" --theme.textColor "#09090B"
pause
