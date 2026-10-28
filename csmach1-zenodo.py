"""
CS-MACH1 Zenodo Community Dataset Registration
Streamlit app — EU-CS-MACH1 community upload with smart CSV/TXT pre-fill and optional map picker.
Project: CS-MACH1 (https://cs-mach1.eu/)
Funding: https://cordis.europa.eu/project/id/101214613
"""

from __future__ import annotations

import html
import io
import re
from datetime import date
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests
import streamlit as st

from cs_mach1_theme import apply_cs_mach1_theme, cs_mach1_footer
from email_service import send_email

# Unified CS-MACH1 theme (must run before any other Streamlit call)
apply_cs_mach1_theme(
    page_title="CS-MACH1 – Dataset Registration",
    page_icon="logo.png",
    main_title="CS-MACH1 Zenodo Uploader",
    subtitle="Register marine citizen science datasets to the cs-mach1 community",
    logo_width=220,
    layout="centered",
)

# ─── Constants ────────────────────────────────────────────────────────────────
ZENODO_API_URL = "https://zenodo.org/api"
ZENODO_DEPOSITIONS_URL = f"{ZENODO_API_URL}/deposit/depositions"
ZENODO_RECORDS_URL = f"{ZENODO_API_URL}/records"
ZENODO_COMMUNITIES_URL = f"{ZENODO_API_URL}/communities"
ZENODO_COMMUNITY = "cs-mach1"

CSMACH1_PROJECT = "CS MACH1 – MArine Citizen science data Horizon"
CSMACH1_URL = "https://cs-mach1.eu/"
CORDIS_ID = "101214613"
CORDIS_URL = f"https://cordis.europa.eu/project/id/{CORDIS_ID}"
FUNDING_PROGRAM = "European Union's Horizon Europe research and innovation programme"
FUNDING_GRANT = "101214613"

DEFAULT_LAT = 44.5  # °N
DEFAULT_LON = 9.5   # °E

# Interactive Web-Mercator map (click for a point, draw a rectangle for a box).
# Set to False to use the coordinate fields only.
ENABLE_MAP_PICKER = True

# "Fixed" -> single point; "Area" -> bounding box (moving devices: box covering the whole track)
SPATIAL_OPTIONS = ["Fixed", "Area"]
DEFAULT_BOX_HALF = 0.5  # degrees around the default point for the initial box

LICENSES = ["cc-by-4.0", "cc0-1.0", "cc-by-sa-4.0", "mit", "apache-2.0"]

# Format registry
FORMAT_INFO = {
    "csv":     {"label": "CSV (Comma-Separated Values)",      "icon": "📊", "parseable": "csv"},
    "tsv":     {"label": "TSV (Tab-Separated Values)",        "icon": "📊", "parseable": "csv"},
    "txt":     {"label": "Plain text",                        "icon": "📄", "parseable": "txt"},
    "nc":      {"label": "NetCDF (Network Common Data Form)", "icon": "🌊", "parseable": False},
    "nc4":     {"label": "NetCDF-4",                          "icon": "🌊", "parseable": False},
    "hdf5":    {"label": "HDF5",                              "icon": "🗄️", "parseable": False},
    "h5":      {"label": "HDF5",                              "icon": "🗄️", "parseable": False},
    "json":    {"label": "JSON",                              "icon": "🔣", "parseable": False},
    "geojson": {"label": "GeoJSON",                           "icon": "🗺️", "parseable": False},
    "shp":     {"label": "Shapefile",                         "icon": "🗺️", "parseable": False},
    "mat":     {"label": "MATLAB data file",                  "icon": "🔢", "parseable": False},
    "zip":     {"label": "ZIP archive",                       "icon": "🗜️", "parseable": False},
    "tar":     {"label": "TAR archive",                       "icon": "🗜️", "parseable": False},
    "gz":      {"label": "GZip compressed",                   "icon": "🗜️", "parseable": False},
    "pdf":     {"label": "PDF document",                      "icon": "📑", "parseable": False},
    "xlsx":    {"label": "Excel spreadsheet",                 "icon": "📊", "parseable": False},
    "xls":     {"label": "Excel spreadsheet (legacy)",        "icon": "📊", "parseable": False},
}

# Column name patterns
LAT_NAMES = {"lat", "latitude", "lat_deg", "latitude_deg", "ylat", "y"}
LON_NAMES = {"lon", "longitude", "long", "lon_deg", "longitude_deg", "xlon", "x"}
TIME_NAMES = {"time", "date", "datetime", "timestamp", "date_time", "time_utc", "date_utc"}
DEPTH_NAMES = {"depth", "depth_m", "pressure", "pres", "z"}

ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ─── CSS ──────────────────────────────────────────────────────────────────────
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
        background: #f4f6f8; border: 1px solid #d0dce8;
        border-radius: 6px; padding: 10px 14px; font-size: 0.9rem; margin: 8px 0 4px 0;
    }
    .autofill-badge {
        background: #fffbea; border-left: 4px solid #f0a500;
        padding: 8px 12px; border-radius: 4px;
        font-size: 0.82rem; color: #6b4c00; margin-bottom: 10px;
    }
    .map-hint {
        background: #f0f7ff; border-left: 3px solid #1a4f8a;
        padding: 6px 12px; border-radius: 4px;
        font-size: 0.82rem; color: #1a4f8a; margin-bottom: 6px;
    }
    .success-box {
        background: #eafaf1; border: 1px solid #27ae60;
        border-radius: 6px; padding: 16px; color: #1e8449;
    }
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# Helpers: generic
# ═════════════════════════════════════════════════════════════════════════════

def section(title: str) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def expand_range(lo: float, hi: float, limit: float, min_span: float = 0.01) -> tuple[float, float]:
    """Make sure a min/max pair spans at least `min_span` degrees and stays within ±limit."""
    if hi - lo < min_span:
        lo, hi = lo - min_span / 2, hi + min_span / 2
    return round(clamp(lo, -limit, limit), 4), round(clamp(hi, -limit, limit), 4)


def normalize_orcid(value: str) -> str:
    """Return the bare ORCID iD (0000-0000-0000-0000) from an iD or a full URL."""
    value = (value or "").strip()
    value = re.sub(r"^https?://(www\.)?orcid\.org/", "", value, flags=re.IGNORECASE)
    return value.rstrip("/")


def text_to_html(text: str) -> str:
    """Escape plain text and convert blank lines / newlines to HTML for Zenodo."""
    paragraphs = [p.strip() for p in (text or "").split("\n\n") if p.strip()]
    return "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs)


def get_zenodo_token() -> str:
    try:
        return st.secrets.get("ZENODO_TOKEN", "")
    except Exception:  # no secrets.toml at all
        return ""


def auth_headers(token: str, json_body: bool = False) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def show_request_error(action: str, exc: requests.RequestException) -> None:
    details = ""
    if getattr(exc, "response", None) is not None:
        details = exc.response.text[:2000]
    st.error(f"Error {action}: {exc}\n{details}")


# ═════════════════════════════════════════════════════════════════════════════
# Helpers: file analysis
# ═════════════════════════════════════════════════════════════════════════════

def detect_separator(raw_bytes: bytes) -> str:
    sample = raw_bytes[:4096].decode("utf-8", errors="replace")
    counts = {",": sample.count(","), ";": sample.count(";"), "\t": sample.count("\t")}
    return max(counts, key=counts.get)


def _numeric_range(df: pd.DataFrame, col: str, lo: float | None = None, hi: float | None = None):
    """Return (min, max, mean) of a numeric column, ignoring values outside [lo, hi]."""
    vals = pd.to_numeric(df[col], errors="coerce").dropna()
    if lo is not None:
        vals = vals[vals >= lo]
    if hi is not None:
        vals = vals[vals <= hi]
    if vals.empty:
        return None
    return float(vals.min()), float(vals.max()), float(vals.mean())


def _title_from_filename(filename: str) -> str:
    return filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()


def analyse_csv(file_bytes: bytes, filename: str) -> tuple[dict, str | None]:
    """Parse CSV/TSV, extract structural metadata and build a suggested abstract."""
    sep = "\t" if filename.lower().endswith(".tsv") else detect_separator(file_bytes)
    try:
        df = pd.read_csv(io.BytesIO(file_bytes), sep=sep, low_memory=False)
    except Exception as e:
        return {}, f"Could not parse as CSV: {e}"

    s: dict = {}
    cols_lower = {str(c).lower().strip(): c for c in df.columns}
    s["n_rows"] = len(df)
    s["n_cols"] = len(df.columns)
    s["columns"] = [str(c) for c in df.columns]
    s["numeric_cols"] =
