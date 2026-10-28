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

# Set to True to show the clickable Folium map under "Geographic location".
ENABLE_MAP_PICKER = False

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
    s["numeric_cols"] = df.select_dtypes(include=[np.number]).columns.tolist()

    # Time
    time_col = next((cols_lower[c] for c in cols_lower if c in TIME_NAMES), None)
    if time_col is not None:
        try:
            ts = pd.to_datetime(df[time_col], errors="coerce").dropna()
            if not ts.empty:
                s["time_start"] = str(ts.min().date())
                s["time_end"] = str(ts.max().date())
        except Exception:
            pass

    # Spatial (values outside valid lat/lon ranges, e.g. projected x/y, are ignored)
    lat_col = next((cols_lower[c] for c in cols_lower if c in LAT_NAMES), None)
    lon_col = next((cols_lower[c] for c in cols_lower if c in LON_NAMES), None)
    if lat_col is not None:
        rng = _numeric_range(df, lat_col, -90, 90)
        if rng:
            s["lat_min"], s["lat_max"], s["lat_mean"] = rng
    if lon_col is not None:
        rng = _numeric_range(df, lon_col, -180, 180)
        if rng:
            s["lon_min"], s["lon_max"], s["lon_mean"] = rng

    # Depth
    depth_col = next((cols_lower[c] for c in cols_lower if c in DEPTH_NAMES), None)
    if depth_col is not None:
        rng = _numeric_range(df, depth_col)
        if rng:
            s["depth_min"], s["depth_max"], _ = rng

    # Abstract
    fmt_name = "TSV" if filename.lower().endswith(".tsv") else "CSV"
    parts = [
        f"This dataset, titled \"{_title_from_filename(filename)}\", contains {s['n_rows']:,} records "
        f"and {s['n_cols']} variables provided in {fmt_name} format."
    ]
    if "time_start" in s:
        parts.append(f"The temporal coverage spans from {s['time_start']} to {s['time_end']}.")
    if "lat_mean" in s and "lon_mean" in s:
        parts.append(
            f"The spatial extent covers latitudes from {s['lat_min']:.3f}°N to "
            f"{s['lat_max']:.3f}°N and longitudes from {s['lon_min']:.3f}°E to "
            f"{s['lon_max']:.3f}°E."
        )
    if "depth_min" in s:
        parts.append(f"Depth ranges from {s['depth_min']:.1f} m to {s['depth_max']:.1f} m.")
    cols_preview = ", ".join(s["columns"][:10])
    if len(s["columns"]) > 10:
        cols_preview += f", and {len(s['columns']) - 10} more"
    parts.append(f"Variables include: {cols_preview}.")
    parts.append(
        f"This dataset was collected within the framework of the {CSMACH1_PROJECT}, "
        f"funded by the {FUNDING_PROGRAM} under Grant Agreement No. {FUNDING_GRANT}."
    )
    s["abstract"] = " ".join(parts)

    # Keywords
    kw = ["cs-mach1", "citizen science", "data"]
    if lat_col is not None or lon_col is not None:
        kw.append("geospatial data")
    if time_col is not None:
        kw.append("time series")
    if depth_col is not None:
        kw.append("oceanography")
    s["keywords"] = kw

    return s, None


def analyse_txt(file_bytes: bytes, filename: str) -> dict:
    """Extract basic info from plain text files for abstract suggestion."""
    text = file_bytes.decode("utf-8", errors="replace")
    n_lines = len([ln for ln in text.splitlines() if ln.strip()])
    abstract = (
        f"This dataset, titled \"{_title_from_filename(filename)}\", is provided as a plain text file "
        f"containing {n_lines:,} lines ({len(text):,} characters). "
        f"It was collected within the framework of the {CSMACH1_PROJECT}, "
        f"funded by the {FUNDING_PROGRAM} under Grant Agreement No. {FUNDING_GRANT}."
    )
    return {"n_lines": n_lines, "abstract": abstract, "keywords": ["cs-mach1", "citizen science", "data"]}


# ═════════════════════════════════════════════════════════════════════════════
# Helpers: ROR / ORCID
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def get_rors(affiliation: str) -> list:
    """Search the ROR registry for organisations matching a free-text affiliation."""
    try:
        resp = requests.get(
            "https://api.ror.org/v2/organizations",
            params={"query": affiliation},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("items") or []
    except Exception as e:
        print(f"Error getting RORs for {affiliation}: {e}")
        return []


def ror_display_name(item: dict) -> str:
    names = item.get("names") or []
    for n in names:
        if "ror_display" in n.get("types", []):
            return n["value"]
    return names[0]["value"] if names else item.get("id", "Unknown")


def ror_location(item: dict) -> str:
    locations = item.get("locations") or []
    if not locations:
        return ""
    g = locations[0].get("geonames_details", {})
    return ", ".join(x for x in (g.get("name"), g.get("country_name")) if x)


def verify_orcid(orcid: str) -> tuple[bool, str]:
    orcid = normalize_orcid(orcid)
    if not ORCID_PATTERN.match(orcid):
        return False, f"Invalid ORCID format ({orcid}). Expected: 0000-0000-0000-0000"
    try:
        response = requests.get(
            f"https://pub.orcid.org/v3.0/{orcid}/person",
            headers={"Accept": "application/json"},
            timeout=15,
        )
    except requests.RequestException as e:
        return False, f"Could not reach ORCID to verify {orcid}: {e}"

    if response.status_code == 200:
        return True, ""
    if response.status_code == 404:
        return False, f"ORCID {orcid} doesn't exist"
    return False, f"Error verifying ORCID {orcid}: {response.text[:200]}"


# ═════════════════════════════════════════════════════════════════════════════
# Helpers: Zenodo
# ═════════════════════════════════════════════════════════════════════════════

def build_creators(primary: dict, colls: list) -> list:
    """Build creator metadata for the Zenodo Deposits API."""
    creators = []
    for author in [primary] + (colls or []):
        first = (author.get("first") or "").strip()
        last = (author.get("last") or "").strip()
        if not first and not last:
            continue

        creator = {"name": f"{last}, {first}" if first and last else last or first}

        orcid = normalize_orcid(author.get("orcid") or "")
        if orcid:
            creator["orcid"] = orcid

        affiliation = (author.get("affil") or "").strip()
        if affiliation:
            creator["affiliation"] = affiliation

        creators.append(creator)
    return creators


def build_metadata(
    title: str,
    abstract_text: str,
    description_text: str,
    creators: list,
    spatial: str,
    proj: str,
    kw: list,
    lat_val: float,
    lon_val: float,
    lic: str,
    author_ror: str | None = None,
    scoop_concept_url: str = "",
    resource_type: str = "dataset",
) -> dict:
    """Build metadata for the Zenodo Deposits API."""
    metadata = {
        "title": title.strip(),
        "upload_type": resource_type,
        "description": text_to_html(abstract_text or description_text or title),
        "creators": creators,
        "publication_date": date.today().isoformat(),
        "access_right": "open",
        "license": lic,
        "communities": [{"identifier": ZENODO_COMMUNITY}],
        "locations": [{
            "lat": float(lat_val),
            "lon": float(lon_val),
            "place": f"{lat_val:.4f}°N, {lon_val:.4f}°E ({spatial} deployment)",
        }],
    }

    # How the data were collected
    if (description_text or "").strip():
        metadata["method"] = text_to_html(description_text)

    # Project / deployment / ROR go into the (plain-text) notes field
    notes = []
    if (proj or "").strip():
        notes.append(f"Project: {proj.strip()}")
    notes.append(f"Spatial deployment: {spatial}")
    if author_ror:
        notes.append(f"First author affiliation ROR: {author_ror}")
    metadata["notes"] = "\n".join(notes)

    clean_keywords = [k.strip() for k in (kw or []) if isinstance(k, str) and k.strip()]
    if clean_keywords:
        metadata["keywords"] = clean_keywords

    if (scoop_concept_url or "").strip():
        metadata["related_identifiers"] = [{
            "identifier": scoop_concept_url.strip(),
            "relation": "isDescribedBy",
            "scheme": "url",
        }]

    return metadata


def create_deposition(token: str, metadata: dict) -> dict | None:
    """Create an unpublished deposition."""
    try:
        response = requests.post(
            f"{ZENODO_DEPOSITIONS_URL}/",
            headers=auth_headers(token, json_body=True),
            json={"metadata": metadata},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        show_request_error("creating Zenodo deposition", exc)
        return None


def upload_file_to_deposition(token: str, deposition: dict, file_bytes: bytes, filename: str) -> dict | None:
    """Upload a file to a deposition (bucket API, with legacy files endpoint as fallback)."""
    try:
        bucket_url = (deposition.get("links") or {}).get("bucket")
        if bucket_url:
            response = requests.put(
                f"{bucket_url}/{quote(filename)}",
                headers=auth_headers(token),
                data=file_bytes,
                timeout=600,
            )
        else:
            response = requests.post(
                f"{ZENODO_DEPOSITIONS_URL}/{deposition['id']}/files",
                headers=auth_headers(token),
                data={"name": filename},
                files={"file": (filename, file_bytes, "application/octet-stream")},
                timeout=600,
            )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        show_request_error("uploading file to Zenodo", exc)
        return None


def publish_deposition(token: str, deposition_id) -> dict | None:
    """Publish the deposition (the community is already set in its metadata)."""
    try:
        response = requests.post(
            f"{ZENODO_DEPOSITIONS_URL}/{deposition_id}/actions/publish",
            headers=auth_headers(token),
            timeout=120,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        show_request_error("publishing Zenodo deposition", exc)
        return None


def parse_record_id(doi_or_url: str) -> str:
    match = re.search(r"zenodo\.(\d+)", doi_or_url or "", flags=re.IGNORECASE)
    if match:
        return match.group(1)
    if (doi_or_url or "").strip().isdigit():
        return doi_or_url.strip()
    raise ValueError("This does not look like a Zenodo DOI (expected 10.5281/zenodo.XXXXXXX).")


def get_record(token: str, doi: str) -> tuple[dict, str]:
    """Fetch an existing Zenodo record from its DOI. Returns (json, record_id)."""
    record_id = parse_record_id(doi)
    response = requests.get(
        f"{ZENODO_RECORDS_URL}/{record_id}",
        headers=auth_headers(token) if token else {},
        timeout=60,
    )
    response.raise_for_status()
    return response.json(), record_id


def add_existing_doi_to_community(token: str, record_id: str) -> dict:
    """Request inclusion of an already-published record in the cs-mach1 community."""
    community = requests.get(f"{ZENODO_COMMUNITIES_URL}/{ZENODO_COMMUNITY}", headers=auth_headers(token), timeout=60)
    community.raise_for_status()
    community_uuid = community.json()["id"]

    response = requests.post(
        f"{ZENODO_RECORDS_URL}/{record_id}/communities",
        headers=auth_headers(token, json_body=True),
        json={"communities": [{"id": community_uuid}]},
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    errors = body.get("errors") or []
    if errors:
        raise ValueError(f"Zenodo could not add the record to the community: {errors}")
    return body


def notify(json_resp: dict, email: str, added_to_community: bool, mode: str) -> None:
    """Send the confirmation email without letting a mail failure hide the success message."""
    try:
        send_email(json_resp, email, added_to_community, ZENODO_COMMUNITY, mode=mode)
    except Exception as exc:
        st.warning(f"Your record was saved, but the confirmation email could not be sent: {exc}")


# ═════════════════════════════════════════════════════════════════════════════
# Optional map picker
# ═════════════════════════════════════════════════════════════════════════════

def render_map_picker(csv_sugg: dict) -> None:
    import folium
    from streamlit_folium import st_folium

    st.markdown(
        '<div class="map-hint">🗺️ Click on the map to set the representative coordinates, '
        'or type them in the fields below. If the dataset covers an area, use the centroid.</div>',
        unsafe_allow_html=True,
    )
    clat, clon = st.session_state.lat_input, st.session_state.lon_input

    m = folium.Map(location=[clat, clon], zoom_start=4, tiles=None)
    folium.TileLayer(tiles="CartoDB positron", name="CartoDB Positron",
                     overlay=False, control=True, show=True).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Esri Ocean", overlay=False, control=True,
    ).add_to(m)
    folium.TileLayer(
        tiles="https://tiles.emodnet-bathymetry.eu/wmts/1.0.0/mean_multicolour/default/web_mercator/{z}/{y}/{x}.png",
        attr="© EMODnet Bathymetry", name="EMODnet Bathymetry",
        overlay=False, control=True, show=False,
    ).add_to(m)
    folium.LayerControl().add_to(m)
    folium.Marker(
        location=[clat, clon],
        tooltip=f"Selected: {clat:.4f}°N, {clon:.4f}°E",
        icon=folium.Icon(color="blue", icon="tint", prefix="fa"),
    ).add_to(m)

    if all(k in csv_sugg for k in ("lat_min", "lat_max", "lon_min", "lon_max")):
        folium.Rectangle(
            bounds=[[csv_sugg["lat_min"], csv_sugg["lon_min"]], [csv_sugg["lat_max"], csv_sugg["lon_max"]]],
            color="#1a4f8a", weight=1.5, fill=True, fill_opacity=0.07,
            tooltip="Dataset spatial extent (from CSV)",
        ).add_to(m)

    result = st_folium(m, use_container_width=True, height=380,
                       returned_objects=["last_clicked"], key="location_map")

    clicked = (result or {}).get("last_clicked")
    if clicked:
        new_lat, new_lon = round(clicked["lat"], 4), round(clicked["lng"], 4)
        if new_lat != clat or new_lon != clon:
            st.session_state.lat_input = max(-90.0, min(90.0, new_lat))
            st.session_state.lon_input = max(-180.0, min(180.0, ((new_lon + 180) % 360) - 180))
            st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# UI
# ═════════════════════════════════════════════════════════════════════════════

# Funding badge
st.markdown(f"""
<div class="funding-badge">
    <b>Project:</b> <a href="{CSMACH1_URL}" target="_blank">{CSMACH1_PROJECT}</a><br>
    <b>Funding:</b> {FUNDING_PROGRAM} — Grant Agreement No.
    <a href="{CORDIS_URL}" target="_blank">{FUNDING_GRANT}</a>
</div>
""", unsafe_allow_html=True)

# Token from secrets only (no UI field)
ZENODO_TOKEN = get_zenodo_token()
if not ZENODO_TOKEN:
    st.warning(
        "⚠️ No Zenodo token found in `.streamlit/secrets.toml`. "
        "Add `ZENODO_TOKEN = \"your_token\"` to proceed.",
        icon="🔑",
    )

# Defaults for values used at submit time
st.session_state.setdefault("lat_input", DEFAULT_LAT)
st.session_state.setdefault("lon_input", DEFAULT_LON)

existing_doi = None
uploaded_file = None
csv_sugg: dict = {}

author_first = author_last = author_orcid = author_affil = ""
selected_ror_id = None
collaborators: list[dict] = []
project_name = description = record_title = abstract = scoop_concept_url = ""
spatial_deployment = "Fixed"
license_choice = LICENSES[0]
keywords: list[str] = []

# ─── DOI option / upload ──────────────────────────────────────────────────────
section("Upload a new record or link an existing DOI")

st.write("Do you already have a Zenodo DOI?")
has_doi = st.radio(
    "Do you already have a Zenodo DOI?", options=["no", "yes"],
    label_visibility="collapsed", horizontal=True,
)
link_existing = has_doi == "yes"

if link_existing:
    existing_doi = st.text_input("DOI", placeholder="10.5281/zenodo.XXXXXXX").strip()
    st.info("ℹ️ The existing record will be linked to the cs-mach1 community via the Zenodo API.")
else:
    st.markdown("**Upload your dataset**")
    uploaded_file = st.file_uploader(
        "Drop your file here", type=None,
        label_visibility="collapsed",
        help="Any format accepted. Recommended: CSV, NetCDF, ZIP, PDF, TXT.",
    )

    if uploaded_file is not None:
        file_ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else "unknown"
        fmt = FORMAT_INFO.get(file_ext, {"label": f"{file_ext.upper()} file", "icon": "📁", "parseable": False})

        st.markdown(
            f'<div class="format-badge">'
            f'{fmt["icon"]} <b>Detected format:</b> {fmt["label"]} &nbsp;|&nbsp; '
            f'<b>Size:</b> {uploaded_file.size / 1024:.1f} KB &nbsp;|&nbsp; '
            f'<b>Extension:</b> .{file_ext}'
            f'</div>',
            unsafe_allow_html=True,
        )

        file_bytes = uploaded_file.getvalue()
        parseable = fmt.get("parseable", False)

        if parseable == "csv":
            with st.spinner("Analysing CSV to suggest metadata…"):
                csv_sugg, err = analyse_csv(file_bytes, uploaded_file.name)
            if err:
                st.warning(f"⚠️ {err}")
            elif csv_sugg:
                st.markdown(
                    '<div class="autofill-badge">✨ <b>Auto-fill active:</b> '
                    'Fields below have been pre-filled from the CSV. '
                    'Review and adjust as needed.</div>',
                    unsafe_allow_html=True,
                )
                with st.expander("📋 CSV quick summary", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Rows", f"{csv_sugg['n_rows']:,}")
                    c2.metric("Columns", csv_sugg["n_cols"])
                    c3.metric("Numeric vars", len(csv_sugg.get("numeric_cols", [])))
                    if "time_start" in csv_sugg:
                        st.markdown(f"**Time range:** {csv_sugg['time_start']} → {csv_sugg['time_end']}")
                    if "lat_mean" in csv_sugg and "lon_mean" in csv_sugg:
                        st.markdown(
                            f"**Spatial extent:** lat [{csv_sugg['lat_min']:.3f}, {csv_sugg['lat_max']:.3f}] · "
                            f"lon [{csv_sugg['lon_min']:.3f}, {csv_sugg['lon_max']:.3f}]"
                        )
                    if "depth_min" in csv_sugg:
                        st.markdown(f"**Depth range:** {csv_sugg['depth_min']:.1f} – {csv_sugg['depth_max']:.1f} m")
                    st.markdown(
                        "**Columns:** " + ", ".join(f"`{c}`" for c in csv_sugg["columns"][:15])
                        + ("…" if len(csv_sugg["columns"]) > 15 else "")
                    )

        elif parseable == "txt":
            with st.spinner("Reading text file…"):
                csv_sugg = analyse_txt(file_bytes, uploaded_file.name)
            st.markdown(
                '<div class="autofill-badge">📄 <b>Text file detected:</b> '
                f'{csv_sugg.get("n_lines", "?")} lines — abstract pre-filled from filename.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info(
                f"ℹ️ Format **{fmt['label']}** detected. "
                "Metadata cannot be extracted automatically — please fill in the fields below manually."
            )

        # Apply the CSV centroid once per new file, so manual edits are not overwritten on reruns
        file_sig = (uploaded_file.name, uploaded_file.size)
        if st.session_state.get("autofill_sig") != file_sig:
            st.session_state.autofill_sig = file_sig
            if "lat_mean" in csv_sugg and "lon_mean" in csv_sugg:
                st.session_state.lat_input = round(csv_sugg["lat_mean"], 4)
                st.session_state.lon_input = round(csv_sugg["lon_mean"], 4)

# ─── Sections 2–6: only for new uploads ───────────────────────────────────────
if not link_existing:

    # Section 2: Contact person
    section("Contact person for the data published")

    col_first, col_last, col_orcid = st.columns([2, 2, 2])
    with col_first:
        author_first = st.text_input("First name", key="author_first_0", placeholder="e.g. First Name")
    with col_last:
        author_last = st.text_input("Last name", key="author_last_0", placeholder="e.g. Last Name")
    with col_orcid:
        author_orcid = st.text_input("ORCID", key="author_orcid_0", placeholder="0000-0000-0000-0000")
        if author_orcid.strip():
            st.markdown(f"[See ORCID profile](https://orcid.org/{normalize_orcid(author_orcid)})")

    author_affil = st.text_input(
        "Affiliation", key="author_affil_0", placeholder="e.g. ETT|DEDAGroup S.p.A."
    ).strip()

    if author_affil:
        matches = get_rors(author_affil)
        if matches:
            by_id = {item["id"]: item for item in matches}
            labels = {None: "Use my original affiliation"}
            for item in matches:
                loc = ror_location(item)
                labels[item["id"]] = f"{ror_display_name(item)} ({loc})" if loc else ror_display_name(item)

            choice = st.radio(
                "Did you mean one of these organizations?",
                options=list(labels),
                format_func=labels.get,
            )

            if choice:
                selected_ror = by_id[choice]
                selected_ror_id = selected_ror["id"]
                st.info(f"**Selected organization**\n\n**ROR:** {selected_ror_id}")

                other_names = [n["value"] for n in selected_ror.get("names", [])]
                if len(other_names) > 1:
                    st.caption("**Other names:**")
                    for name in other_names:
                        st.caption(f"• {name}")

                # Zenodo stores affiliation as free text: use the official name
                author_affil = ror_display_name(selected_ror)

    # Collaborators
    st.session_state.setdefault("num_collaborators", 0)
    if st.button("＋ Add another collaborator"):
        st.session_state.num_collaborators += 1

    for i in range(st.session_state.num_collaborators):
        st.markdown(f"*Collaborator {i + 1}*")
        ca, cb, cc, cd = st.columns([2, 2, 2, 3])
        with ca:
            cfirst = st.text_input("First name", key=f"coll_first_{i}", placeholder="First name")
        with cb:
            clast = st.text_input("Last name", key=f"coll_last_{i}", placeholder="Last name")
        with cc:
            corcid = st.text_input("ORCID", key=f"coll_orcid_{i}", placeholder="0000-0000-0000-0000")
            if corcid.strip():
                st.markdown(f"[See ORCID profile](https://orcid.org/{normalize_orcid(corcid)})")
        with cd:
            caffil = st.text_input("Affiliation", key=f"coll_affil_{i}", placeholder="Institution")

        collaborators.append({"first": cfirst, "last": clast, "orcid": corcid, "affil": caffil})

    # Section 3: Project
    section("Information about the project")
    project_name = st.text_input("Project's name", placeholder="e.g. CS-MACH1 ")

    # Section 4: Measurement description
    section("Description of the measurement")
    description = st.text_area(
        "Describe how you collected the dataset",
        placeholder="Describe the collection method, instrumentation used, time period…",
        height=90,
    )
    spatial_deployment = st.radio(
        "Specify the spatial deployment of the device",
        options=["Fixed", "Area", "Trajectory"],
        horizontal=True,
    )

    # Section 5: Metadata + abstract
    section("Additional metadata")

    col_title, col_license = st.columns([3, 2])
    with col_title:
        record_title = st.text_input("Dataset title *", placeholder="Title of the dataset on Zenodo")
    with col_license:
        license_choice = st.selectbox("License", options=LICENSES, index=0)

    abstract = st.text_area(
        "Abstract",
        value=csv_sugg.get("abstract", ""),
        placeholder="Provide a description of the dataset for the record…",
        height=180,
        help="Auto-filled from file analysis when possible. Please review and complete.",
    )

    keywords_raw = st.text_input(
        "Keywords (comma-separated)",
        value=", ".join(csv_sugg.get("keywords", [])),
        placeholder="citizen science, oceanography, temperature, in situ, …",
    )
    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]

    scoop_concept_url = st.text_input(
        label="Sensor Concept [SCOOP] URL (optional)",
        placeholder="https://www.scoop-ocean.org/catalogue/SCOOP94/wave-gauge",
        help=(
            "Optional. Enter the URL of the corresponding SCOOP concept "
            "(e.g. https://www.scoop-ocean.org/catalogue/SCOOP94/wave-gauge)."
        ),
    ).strip()
    if scoop_concept_url.lower().startswith(("http://", "https://")):
        st.markdown(f"[See SCOOP concept]({scoop_concept_url})")

    # Section 6: Location
    section("Geographic location")

    if ENABLE_MAP_PICKER:
        render_map_picker(csv_sugg)

    col_lat, col_lon = st.columns(2)
    with col_lat:
        lat = st.number_input(
            "Latitude (°N)", min_value=-90.0, max_value=90.0,
            step=0.0001, format="%.4f", key="lat_input",
        )
    with col_lon:
        lon = st.number_input(
            "Longitude (°E)", min_value=-180.0, max_value=180.0,
            step=0.0001, format="%.4f", key="lon_input",
        )

# ─── Preview of a pre-existing record ─────────────────────────────────────────
if link_existing and existing_doi:
    try:
        json_resp, record_id = get_record(ZENODO_TOKEN, existing_doi)
        meta = json_resp.get("metadata", {})

        title = meta.get("title", "-")
        doi = json_resp.get("doi", existing_doi)
        rec_abstract = meta.get("description", "No abstract available.")

        authors = []
        for c in meta.get("creators", []):
            po = c.get("person_or_org", {})
            authors.append(po.get("name", "Unknown") if po else c.get("name", "Unknown"))

        with st.container(border=True):
            st.markdown("**Record to be linked:**")
            st.write(f"Record ID: {record_id}")
            st.write(f"DOI: {doi}")
            st.markdown(f"**Title**\n\n{title}")

            st.markdown("**Authors**")
            if authors:
                for a in authors:
                    st.write(f"• {a}")
            else:
                st.write("-")

            st.markdown("**Abstract**")
            # Zenodo descriptions are (sanitised) HTML
            st.markdown(rec_abstract, unsafe_allow_html=True)

            record_url = json_resp.get("links", {}).get("self_html") or json_resp.get("links", {}).get("latest_html")
            if record_url:
                st.link_button("Open record on Zenodo", record_url, use_container_width=True)
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Zenodo HTTP error: {e.response.status_code} — {e.response.text}")
    except ValueError as e:
        st.error(f"❌ {e}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")

# ─── Contact email + GDPR ─────────────────────────────────────────────────────
email_addrs = st.text_input("Contact email address", placeholder="e.g. your.email@institution.edu").strip()

try:
    with open("gdpr.txt", "r", encoding="utf-8") as f:
        st.caption(f.read())
except FileNotFoundError:
    pass

# ─── Submit ───────────────────────────────────────────────────────────────────
st.markdown("---")
submit = st.button(
    "🚀 Register dataset to cs-mach1 community",
    type="primary",
    use_container_width=True,
)

if submit:
    errors = []
    if not ZENODO_TOKEN:
        errors.append("Zenodo token missing from secrets.toml.")
    if not email_addrs:
        errors.append("Please provide a contact email address.")
    elif not EMAIL_PATTERN.match(email_addrs):
        errors.append("Please provide a valid contact email address.")

    if link_existing:
        if not existing_doi:
            errors.append("Please enter the existing dataset DOI.")
    else:
        if not uploaded_file:
            errors.append("Please upload a dataset file.")
        if not (author_first.strip() or author_last.strip()):
            errors.append("Please enter at least the first author's name.")
        if not record_title.strip():
            errors.append("Please provide a dataset title.")
        if not (abstract.strip() or description.strip()):
            errors.append("Please provide an abstract (or a description of the measurement).")
        if scoop_concept_url and not scoop_concept_url.lower().startswith(("http://", "https://")):
            errors.append("The SCOOP URL must start with http:// or https://.")

        orcids_to_check = [("the first author", author_orcid)] + [
            (f"collaborator {i + 1}", c["orcid"]) for i, c in enumerate(collaborators)
        ]
        for who, orcid in orcids_to_check:
            if orcid.strip():
                valid, msg = verify_orcid(orcid)
                if not valid:
                    errors.append(f"ORCID of {who}: {msg}")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    with st.spinner("Uploading to Zenodo…"):
        try:
            if link_existing:
                json_resp, record_id = get_record(ZENODO_TOKEN, existing_doi)
                add_existing_doi_to_community(ZENODO_TOKEN, record_id)
                view_url = f"https://zenodo.org/records/{record_id}"

                notify(json_resp, email_addrs, True, "community_success")

                st.markdown(f"""
                <div class="success-box">
                    ✅ <b>Record linked to the cs-mach1 community!</b><br>
                    Record ID: <code>{record_id}</code><br>
                    <a href="{view_url}" target="_blank" rel="noopener noreferrer">
                    🔗 View public submission on Zenodo (read-only) →</a>
                </div>""", unsafe_allow_html=True)
                st.caption(
                    "This link opens the public, read-only record page. "
                    "No login session is shared — visitors cannot edit the record from this link."
                )

            else:
                primary_author = {
                    "first": author_first, "last": author_last,
                    "orcid": author_orcid, "affil": author_affil,
                }
                creators = build_creators(primary_author, collaborators)

                metadata = build_metadata(
                    title=record_title,
                    abstract_text=abstract,
                    description_text=description,
                    creators=creators,
                    spatial=spatial_deployment,
                    proj=project_name,
                    kw=keywords,
                    lat_val=st.session_state.lat_input,
                    lon_val=st.session_state.lon_input,
                    lic=license_choice,
                    author_ror=selected_ror_id,
                    scoop_concept_url=scoop_concept_url,
                )

                draft_info = create_deposition(ZENODO_TOKEN, metadata)
                if not draft_info:
                    st.stop()
                record_id = draft_info["id"]
                st.info(f"📝 Draft created (ID: {record_id})")

                if not upload_file_to_deposition(
                    ZENODO_TOKEN, draft_info, uploaded_file.getvalue(), uploaded_file.name
                ):
                    st.stop()
                st.info(f"📂 File '{uploaded_file.name}' uploaded.")

                json_resp = publish_deposition(ZENODO_TOKEN, record_id)
                if not json_resp:
                    st.stop()

                doi_out = json_resp.get("doi", "n/a")
                view_url = f"https://zenodo.org/records/{record_id}"

                # The community is part of the deposition metadata, so it is submitted on publish
                notify(json_resp, email_addrs, True, "upload_success")

                st.markdown(f"""
                <div class="success-box">
                    ✅ <b>Dataset published to the cs-mach1 community!</b><br>
                    DOI: <code>{doi_out}</code><br>
                    Record ID: <code>{record_id}</code><br>
                    <a href="{view_url}" target="_blank" rel="noopener noreferrer">
                    🔗 View public submission on Zenodo (read-only) →</a>
                </div>""", unsafe_allow_html=True)
                st.caption(
                    "This link opens the public, read-only record page — anyone who opens it "
                    "sees the published version without being logged in, so it cannot be edited from there."
                )
                st.balloons()

        except requests.exceptions.HTTPError as e:
            st.error(f"❌ Zenodo HTTP error: {e.response.status_code} — {e.response.text}")
        except ValueError as e:
            st.error(f"❌ {e}")
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")

# ─── Footer ───────────────────────────────────────────────────────────────────
cs_mach1_footer("CS-MACH1 Zenodo Uploader • Marine Citizen Science Data Horizon")
