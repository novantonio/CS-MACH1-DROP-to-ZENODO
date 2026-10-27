"""
CS-MACH1 Zenodo Community Dataset Registration
Streamlit app — EU-CS-MACH1 community upload with smart CSV/TXT pre-fill and map picker.
Project: CS-MACH1 (https://cs-mach1.eu/)
Funding: https://cordis.europa.eu/project/id/101214613
"""

import io
import streamlit as st
import requests
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from datetime import date

from cs_mach1_theme import apply_cs_mach1_theme, cs_mach1_footer
from email_service import send_email
import re


# Apply CS-MACH1 unified theme
apply_cs_mach1_theme(
    page_title="CS-MACH1 – Dataset Registration",
    page_icon="logo.png",
    main_title="CS-MACH1 Zenodo Uploader",
    subtitle="Register marine citizen science datasets to the cs-mach1 community",
    logo_width=220,
    layout="centered"
)


# ─── Constants ────────────────────────────────────────────────────────────────
ZENODO_API_URL   = "https://zenodo.org/api"
ZENODO_COMMUNITY = "cs-mach1"
CSMACH1_PROJECT  = "CS MACH1 – MArine Citizen science data Horizon"
CSMACH1_URL      = "https://cs-mach1.eu/"
CORDIS_ID        = "101214613"
CORDIS_URL       = f"https://cordis.europa.eu/project/id/{CORDIS_ID}"
FUNDING_PROGRAM  = "European Union's Horizon Europe research and innovation programme"
FUNDING_GRANT    = "101214613"

# Default coordinates for map (Arctic / North Atlantic focus)
DEFAULT_LAT = 70.0   # °N
DEFAULT_LON = -10.0  # °E

# Format registry
FORMAT_INFO = {
    "csv":     {"label": "CSV (Comma-Separated Values)",       "icon": "📊", "parseable": "csv"},
    "tsv":     {"label": "TSV (Tab-Separated Values)",         "icon": "📊", "parseable": "csv"},
    "txt":     {"label": "Plain text",                         "icon": "📄", "parseable": "txt"},
    "nc":      {"label": "NetCDF (Network Common Data Form)",  "icon": "🌊", "parseable": False},
    "nc4":     {"label": "NetCDF-4",                           "icon": "🌊", "parseable": False},
    "hdf5":    {"label": "HDF5",                               "icon": "🗄️", "parseable": False},
    "h5":      {"label": "HDF5",                               "icon": "🗄️", "parseable": False},
    "json":    {"label": "JSON",                               "icon": "🔣", "parseable": False},
    "geojson": {"label": "GeoJSON",                            "icon": "🗺️", "parseable": False},
    "shp":     {"label": "Shapefile",                          "icon": "🗺️", "parseable": False},
    "mat":     {"label": "MATLAB data file",                   "icon": "🔢", "parseable": False},
    "zip":     {"label": "ZIP archive",                        "icon": "🗜️", "parseable": False},
    "tar":     {"label": "TAR archive",                        "icon": "🗜️", "parseable": False},
    "gz":      {"label": "GZip compressed",                    "icon": "🗜️", "parseable": False},
    "pdf":     {"label": "PDF document",                       "icon": "📑", "parseable": False},
    "xlsx":    {"label": "Excel spreadsheet",                  "icon": "📊", "parseable": False},
    "xls":     {"label": "Excel spreadsheet (legacy)",         "icon": "📊", "parseable": False},
}

# Column name patterns
LAT_NAMES   = {"lat", "latitude", "lat_deg", "latitude_deg", "ylat", "y"}
LON_NAMES   = {"lon", "longitude", "long", "lon_deg", "longitude_deg", "xlon", "x"}
TIME_NAMES  = {"time", "date", "datetime", "timestamp", "date_time", "time_utc", "date_utc"}
DEPTH_NAMES = {"depth", "depth_m", "pressure", "pres", "z"}

# ─── CSS ──────────────────────────────────────────────────────────────────────
#st.image(logo_path, width=logo_width)
st.markdown("""
<style>
    .cs-mach1-header {
        display: flex; align-items: center; gap: 16px;
        padding: 12px 0 24px 0;
        border-bottom: 2px solid #1a4f8a; margin-bottom: 28px;
    }
    .cs-mach1-title    { color: #1a4f8a; font-size: 1.6rem; font-weight: 700; }
    .cs-mach1-subtitle { color: #555; font-size: 0.85rem; }
    .section-title {
        font-size: 1rem; font-weight: 700; color: #1a4f8a;
        text-transform: uppercase; letter-spacing: 0.05em;
        border-bottom: 1px solid #cce0f5;
        padding-bottom: 4px; margin-top: 28px; margin-bottom: 12px;
    }
    .funding-badge {
        background: #eaf3fb; border-left: 4px solid #1a4f8a;
        padding: 10px 14px; border-radius: 4px;
        font-size: 0.82rem; color: #333; margin-bottom: 16px;
    }
    .format-badge {
