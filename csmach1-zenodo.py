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
    bbox: dict | None = None,
    resource_type: str = "dataset",
    project_doi: str = "",
) -> dict:
    """Build metadata for the Zenodo Deposits API.

    Zenodo locations are points only: for an Area deployment `lat_val`/`lon_val` are the
    centre of the box and the box corners are stated in the place text and in the notes.
    """
    if bbox:
        place = (
            f"Bounding box: SW ({bbox['sw_lat']:.4f}°N, {bbox['sw_lon']:.4f}°E) – "
            f"NE ({bbox['ne_lat']:.4f}°N, {bbox['ne_lon']:.4f}°E) ({spatial} deployment)"
        )
    else:
        place = f"{lat_val:.4f}°N, {lon_val:.4f}°E ({spatial} deployment)"

    metadata = {
        "title": title.strip(),
        "upload_type": resource_type,
        "description": text_to_html(abstract_text or description_text or title),
        "creators": creators,
        "publication_date": date.today().isoformat(),
        "access_right": "open",
        "license": lic,
        "communities": [{"identifier": ZENODO_COMMUNITY}],
        "locations": [{"lat": float(lat_val), "lon": float(lon_val), "place": place}],
    }

    # How the data were collected
    if (description_text or "").strip():
        metadata["method"] = text_to_html(description_text)

    # Project / deployment / ROR / Project DOI go into the (plain-text) notes field
    notes = []
    if (proj or "").strip():
        notes.append(f"Project: {proj.strip()}")
    if (project_doi or "").strip():
        notes.append(f"Project DOI/CORDIS Reference: {project_doi.strip()}")
    notes.append(f"Spatial deployment: {spatial}")
    if bbox:
        notes.append(
            f"Bounding box (WGS84): SW {bbox['sw_lat']:.4f}, {bbox['sw_lon']:.4f}; "
            f"NE {bbox['ne_lat']:.4f}, {bbox['ne_lon']:.4f}"
        )
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

def _is_new_map_event(sig) -> bool:
    """Map events persist across reruns; only react to each one once so typed values are not overwritten."""
    if st.session_state.get("_map_event_sig") == sig:
        return False
    st.session_state["_map_event_sig"] = sig
    return True


def _base_map(center: list, zoom: int):
    """Folium map in Web Mercator (EPSG:3857) with the project's base layers."""
    import folium

    m = folium.Map(location=center, zoom_start=zoom, tiles=None)
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
    return m


def _add_csv_extent(m, csv_sugg: dict) -> None:
    import folium

    if all(k in csv_sugg for k in ("lat_min", "lat_max", "lon_min", "lon_max")):
        folium.Rectangle(
            bounds=[[csv_sugg["lat_min"], csv_sugg["lon_min"]], [csv_sugg["lat_max"], csv_sugg["lon_max"]]],
            color="#1a4f8a", weight=1.5, fill=True, fill_opacity=0.07,
            tooltip="Dataset spatial extent (from file)",
        ).add_to(m)


def render_point_picker(csv_sugg: dict) -> None:
    """Click on the map to set a single representative point (Fixed deployment)."""
    import folium
    from streamlit_folium import st_folium

    st.markdown(
        '<div class="map-hint">🗺️ Click on the map to set the position, '
        'or type the coordinates in the fields below.</div>',
        unsafe_allow_html=True,
    )
    clat, clon = st.session_state.lat_input, st.session_state.lon_input

    m = _base_map([clat, clon], 4)
    folium.Marker(
        location=[clat, clon],
        tooltip=f"Selected: {clat:.4f}°N, {clon:.4f}°E",
        icon=folium.Icon(color="blue", icon="tint", prefix="fa"),
    ).add_to(m)
    _add_csv_extent(m, csv_sugg)

    result = st_folium(m, use_container_width=True, height=380,
                       returned_objects=["last_clicked"], key="point_map")

    clicked = (result or {}).get("last_clicked")
    if clicked and _is_new_map_event(("click", clicked["lat"], clicked["lng"])):
        st.session_state.lat_input = round(clamp(clicked["lat"], -90, 90), 4)
        st.session_state.lon_input = round(clamp(clicked["lng"], -180, 180), 4)
        st.rerun()


def render_bbox_picker(csv_sugg: dict) -> None:
    """Draw a rectangle on the Mercator map to set the bounding box (Area deployment)."""
    import folium
    from folium.plugins import Draw
    from streamlit_folium import st_folium

    st.markdown(
        '<div class="map-hint">🗺️ Use the rectangle tool (left of the map) to draw the bounding box, '
        'or type the corner coordinates in the fields below.</div>',
        unsafe_allow_html=True,
    )
    ne_lat, ne_lon = st.session_state.ne_lat_input, st.session_state.ne_lon_input
    sw_lat, sw_lon = st.session_state.sw_lat_input, st.session_state.sw_lon_input
    valid = ne_lat > sw_lat and ne_lon > sw_lon

    m = _base_map([(ne_lat + sw_lat) / 2, (ne_lon + sw_lon) / 2], 5)
    if valid:
        folium.Rectangle(
            bounds=[[sw_lat, sw_lon], [ne_lat, ne_lon]],
            color="#1a4f8a", weight=2, fill=True, fill_opacity=0.15,
            tooltip=f"SW {sw_lat:.4f}, {sw_lon:.4f} · NE {ne_lat:.4f}, {ne_lon:.4f}",
        ).add_to(m)
        m.fit_bounds([[sw_lat, sw_lon], [ne_lat, ne_lon]])
    _add_csv_extent(m, csv_sugg)

    Draw(
        export=False,
        draw_options={"polyline": False, "polygon": False, "circle": False,
                      "marker": False, "circlemarker": False, "rectangle": True},
        edit_options={"edit": False, "remove": False},
    ).add_to(m)

    result = st_folium(m, use_container_width=True, height=420,
                       returned_objects=["last_active_drawing"], key="bbox_map")

    drawing = (result or {}).get("last_active_drawing")
    geometry = (drawing or {}).get("geometry") or {}
    if geometry.get("type") == "Polygon":
        ring = geometry["coordinates"][0]
        lons = [pt[0] for pt in ring]
        lats = [pt[1] for pt in ring]
        sig = ("draw", round(min(lats), 6), round(max(lats), 6), round(min(lons), 6), round(max(lons), 6))
        if _is_new_map_event(sig):
            st.session_state.sw_lat_input = round(clamp(min(lats), -90, 90), 4)
            st.session_state.ne_lat_input = round(clamp(max(lats), -90, 90), 4)
            st.session_state.sw_lon_input = round(clamp(min(lons), -180, 180), 4)
            st.session_state.ne_lon_input = round(clamp(max(lons), -180, 180), 4)
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
st.session_state.setdefault("sw_lat_input", round(DEFAULT_LAT - DEFAULT_BOX_HALF, 4))
st.session_state.setdefault("sw_lon_input", round(DEFAULT_LON - DEFAULT_BOX_HALF, 4))
st.session_state.setdefault("ne_lat_input", round(DEFAULT_LAT + DEFAULT_BOX_HALF, 4))
st.session_state.setdefault("ne_lon_input", round(DEFAULT_LON + DEFAULT_BOX_HALF, 4))

existing_doi = None
uploaded_file = None
csv_sugg: dict = {}

author_first = author_last = author_orcid = author_affil = ""
selected_ror_id = None
collaborators: list[dict] = []
project_name = project_doi = description = record_title = abstract = scoop_concept_url = ""
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
                        st.markdown(f"**Depth range:** {csv_sugg['depth_min']:.1f} m → {csv_sugg['depth_max']:.1f} m")

        elif parseable == "txt":
            csv_sugg = analyse_txt(file_bytes, uploaded_file.name)
            st.markdown(
                '<div class="autofill-badge">✨ <b>Auto-fill active:</b> '
                'Abstract pre-filled from text file stats.</div>',
                unsafe_allow_html=True,
            )

# ─── First Author section ─────────────────────────────────────────────────────
section("First Author")
col1, col2 = st.columns(2)
with col1:
    author_first = st.text_input("First name *", placeholder="Jane")
with col2:
    author_last = st.text_input("Last name *", placeholder="Doe")

author_orcid = st.text_input("ORCID iD", placeholder="0000-0002-1825-0097")
if author_orcid.strip():
    clean_orcid = normalize_orcid(author_orcid)
    if ORCID_PATTERN.match(clean_orcid):
        st.caption(f"🔗 [See ORCID profile](https://orcid.org/{clean_orcid})")

author_affil = st.text_input("Affiliation", placeholder="University of Genoa")
if author_affil.strip():
    rors = get_rors(author_affil)
    if rors:
        options = {item["id"]: f"{ror_display_name(item)} ({ror_location(item)})" for item in rors[:5]}
        selected_ror_id = st.selectbox("Matching ROR Organisation", options=list(options.keys()), format_func=lambda x: options[x])

# ─── Project & Funding Details ───────────────────────────────────────────────
section("Project & Funding Details")
project_name = st.text_input("Project Name", value=CSMACH1_PROJECT)
project_doi = st.text_input(
    "Project DOI / CORDIS Reference",
    placeholder="10.3030/101214613 or https://cordis.europa.eu/project/id/101214613",
    help="Enter the project DOI or CORDIS reference link"
)
if project_doi.strip():
    doi_val = project_doi.strip()
    if doi_val.isdigit() or doi_val.startswith("10."):
        proj_url = f"https://cordis.europa.eu/project/id/{doi_val}" if doi_val.isdigit() else f"https://doi.org/{doi_val}"
    else:
        proj_url = doi_val
    st.caption(f"🔗 [View Project / CORDIS Record]({proj_url})")

# ─── Metadata Details ─────────────────────────────────────────────────────────
section("Dataset Details")
default_title = _title_from_filename(uploaded_file.name) if uploaded_file else ""
record_title = st.text_input("Dataset Title *", value=default_title, placeholder="Marine observation data…")

default_abstract = csv_sugg.get("abstract", "")
abstract = st.text_area("Abstract / Summary *", value=default_abstract, height=120, placeholder="Describe the dataset contents, purpose, and coverage…")
description = st.text_area("Methods / Description (optional)", height=90, placeholder="Describe how data were collected, instruments used, processing steps…")

# ─── Spatial Coverage ─────────────────────────────────────────────────────────
section("Spatial Coverage")
spatial_deployment = st.selectbox("Spatial deployment type", options=SPATIAL_OPTIONS)

if ENABLE_MAP_PICKER:
    if spatial_deployment == "Fixed":
        render_point_picker(csv_sugg)
    else:
        render_bbox_picker(csv_sugg)

if spatial_deployment == "Fixed":
    c1, c2 = st.columns(2)
    with c1:
        lat_val = st.number_input("Latitude (°N)", value=float(st.session_state.lat_input), format="%.4f", min_value=-90.0, max_value=90.0)
    with c2:
        lon_val = st.number_input("Longitude (°E)", value=float(st.session_state.lon_input), format="%.4f", min_value=-180.0, max_value=180.0)
    bbox = None
else:
    c1, c2 = st.columns(2)
    with c1:
        sw_lat = st.number_input("SW Latitude (°N)", value=float(st.session_state.sw_lat_input), format="%.4f", min_value=-90.0, max_value=90.0)
        ne_lat = st.number_input("NE Latitude (°N)", value=float(st.session_state.ne_lat_input), format="%.4f", min_value=-90.0, max_value=90.0)
    with c2:
        sw_lon = st.number_input("SW Longitude (°E)", value=float(st.session_state.sw_lon_input), format="%.4f", min_value=-180.0, max_value=180.0)
        ne_lon = st.number_input("NE Longitude (°E)", value=float(st.session_state.ne_lon_input), format="%.4f", min_value=-180.0, max_value=180.0)
    
    bbox = {"sw_lat": sw_lat, "sw_lon": sw_lon, "ne_lat": ne_lat, "ne_lon": ne_lon}
    lat_val = round((sw_lat + ne_lat) / 2, 4)
    lon_val = round((sw_lon + ne_lon) / 2, 4)

# ─── Additional Metadata ──────────────────────────────────────────────────────
section("Additional Metadata & License")
default_kw = ", ".join(csv_sugg.get("keywords", ["cs-mach1", "citizen science", "data"]))
keywords_input = st.text_input("Keywords (comma separated)", value=default_kw)
keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

license_choice = st.selectbox("License", options=LICENSES, index=0)
scoop_concept_url = st.text_input("Related SCOOP Concept URL (optional)", placeholder="https://zenodo.org/record/...")

# ─── Submitter Contact ────────────────────────────────────────────────────────
section("Submitter Contact")
submitter_email = st.text_input("Email address for confirmation notification", placeholder="name@example.com")

# ─── Submission Action ────────────────────────────────────────────────────────
section("Register & Publish")

if st.button("🚀 Register Dataset to Zenodo", type="primary"):
    # Validation checks
    errors = []
    if not ZENODO_TOKEN:
        errors.append("Zenodo API token is missing in Streamlit secrets.")
    if not link_existing and not uploaded_file:
        errors.append("Please upload a file or choose to link an existing DOI.")
    if not author_first or not author_last:
        errors.append("First Author first name and last name are required.")
    if not record_title:
        errors.append("Dataset title is required.")
    if not abstract:
        errors.append("Abstract is required.")
    if submitter_email and not EMAIL_PATTERN.match(submitter_email.strip()):
        errors.append("Please provide a valid email address.")

    if errors:
        for err in errors:
            st.error(err)
    else:
        with st.spinner("Processing registration with Zenodo…"):
            primary_author = {
                "first": author_first,
                "last": author_last,
                "orcid": author_orcid,
                "affil": author_affil,
            }
            creators = build_creators(primary_author, collaborators)

            if link_existing:
                try:
                    record_json, record_id = get_record(ZENODO_TOKEN, existing_doi)
                    add_existing_doi_to_community(ZENODO_TOKEN, record_id)
                    st.markdown(
                        f"""
                        <div class="success-box">
                            <h3>✅ Successfully Linked!</h3>
                            <p>Record <b>{record_id}</b> has been successfully linked to the <b>{ZENODO_COMMUNITY}</b> community.</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if submitter_email:
                        notify(record_json, submitter_email, added_to_community=True, mode="link")
                except Exception as exc:
                    st.error(f"Error linking existing DOI: {exc}")
            else:
                metadata = build_metadata(
                    title=record_title,
                    abstract_text=abstract,
                    description_text=description,
                    creators=creators,
                    spatial=spatial_deployment,
                    proj=project_name,
                    kw=keywords,
                    lat_val=lat_val,
                    lon_val=lon_val,
                    lic=license_choice,
                    author_ror=selected_ror_id,
                    scoop_concept_url=scoop_concept_url,
                    bbox=bbox,
                    project_doi=project_doi,
                )
                dep = create_deposition(ZENODO_TOKEN, metadata)
                if dep:
                    file_bytes = uploaded_file.getvalue()
                    filename = uploaded_file.name
                    uploaded_file_resp = upload_file_to_deposition(ZENODO_TOKEN, dep, file_bytes, filename)
                    if uploaded_file_resp:
                        pub_resp = publish_deposition(ZENODO_TOKEN, dep["id"])
                        if pub_resp:
                            doi = pub_resp.get("doi", "Unknown DOI")
                            concept_doi = pub_resp.get("conceptdoi", "")
                            st.markdown(
                                f"""
                                <div class="success-box">
                                    <h3>🎉 Successfully Published!</h3>
                                    <p>Your dataset has been successfully registered and published on Zenodo and added to the <b>{ZENODO_COMMUNITY}</b> community.</p>
                                    <p><b>DOI:</b> <a href="https://doi.org/{doi}" target="_blank">{doi}</a></p>
                                    {f"<p><b>Concept DOI:</b> <a href='https://doi.org/{concept_doi}' target='_blank'>{concept_doi}</a></p>" if concept_doi else ""}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            if submitter_email:
                                notify(pub_resp, submitter_email, added_to_community=True, mode="create")

cs_mach1_footer()
