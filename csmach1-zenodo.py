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

from cs_mach1_theme import apply_cs_mach1_theme, cs_mach1_footer

# Apply CS-MACH1 unified theme
apply_cs_mach1_theme(
    page_title="CS-MACH1 – Dataset Registration",
    page_icon="logo.png",
    main_title="🌊 CS-MACH1 Zenodo Uploader",
    subtitle="Register marine citizen science datasets to the cs-mach1 community",
    logo_width=220,
    layout="centered",
)

# Extra centered logo
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    try:
        st.image("logo.png", width=180)
    except Exception:
        pass  # logo optional

# ─── Constants ────────────────────────────────────────────────────────────────
ZENODO_API_URL   = "https://zenodo.org/api"
ZENODO_COMMUNITY = "https://zenodo.org/communities/cs-mach1/"
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

# Funding badge (kept from original design)
st.markdown(f"""
<div class="funding-badge">
    <b>Project:</b> <a href="{CSMACH1_URL}" target="_blank">{CSMACH1_PROJECT}</a><br>
    <b>Funding:</b> {FUNDING_PROGRAM} — Grant Agreement No.
    <a href="{CORDIS_URL}" target="_blank">{FUNDING_GRANT}</a>
</div>
""", unsafe_allow_html=True)

# Token from secrets only (no UI field)
ZENODO_TOKEN = st.secrets.get("ZENODO_TOKEN", "")
if not ZENODO_TOKEN:
    st.warning(
        "⚠️ No Zenodo token found in `.streamlit/secrets.toml`. "
        "Add `ZENODO_TOKEN = \"your_token\"` to proceed.",
        icon="🔑",
    )

# ─── Helpers: file analysis ───────────────────────────────────────────────────

def detect_separator(raw_bytes: bytes) -> str:
    sample = raw_bytes[:4096].decode("utf-8", errors="replace")
    counts = {",": sample.count(","), ";": sample.count(";"), "\t": sample.count("\t")}
    return max(counts, key=counts.get)


def analyse_csv(file_bytes: bytes, filename: str) -> tuple[dict, str | None]:
    """Parse CSV/TSV, extract structural metadata and build suggested abstract."""
    sep = "\t" if filename.lower().endswith(".tsv") else detect_separator(file_bytes)
    try:
        df = pd.read_csv(io.BytesIO(file_bytes), sep=sep, low_memory=False)
    except Exception as e:
        return {}, f"Could not parse as CSV: {e}"

    s = {}
    cols_lower = {c.lower().strip(): c for c in df.columns}
    s["n_rows"]   = len(df)
    s["n_cols"]   = len(df.columns)
    s["columns"]  = list(df.columns)
    s["numeric_cols"] = df.select_dtypes(include=[np.number]).columns.tolist()

    # Time
    time_col = next((cols_lower[c] for c in cols_lower if c in TIME_NAMES), None)
    if time_col:
        try:
            ts = pd.to_datetime(df[time_col], errors="coerce").dropna()
            if not ts.empty:
                s["time_start"] = str(ts.min().date())
                s["time_end"]   = str(ts.max().date())
        except Exception:
            pass

    # Spatial
    lat_col = next((cols_lower[c] for c in cols_lower if c in LAT_NAMES), None)
    lon_col = next((cols_lower[c] for c in cols_lower if c in LON_NAMES), None)
    if lat_col:
        lv = pd.to_numeric(df[lat_col], errors="coerce").dropna()
        if not lv.empty:
            s["lat_min"]  = float(lv.min())
            s["lat_max"]  = float(lv.max())
            s["lat_mean"] = float(lv.mean())
    if lon_col:
        lv = pd.to_numeric(df[lon_col], errors="coerce").dropna()
        if not lv.empty:
            s["lon_min"]  = float(lv.min())
            s["lon_max"]  = float(lv.max())
            s["lon_mean"] = float(lv.mean())

    # Depth
    depth_col = next((cols_lower[c] for c in cols_lower if c in DEPTH_NAMES), None)
    if depth_col:
        dv = pd.to_numeric(df[depth_col], errors="coerce").dropna()
        if not dv.empty:
            s["depth_min"] = float(dv.min())
            s["depth_max"] = float(dv.max())

    # Abstract
    stem  = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    parts = [
        f"This dataset, titled \"{stem}\", contains {s['n_rows']:,} records "
        f"and {s['n_cols']} variables provided in CSV format."
    ]
    if "time_start" in s:
        parts.append(
            f"The temporal coverage spans from {s['time_start']} to {s['time_end']}."
        )
    if "lat_mean" in s:
        parts.append(
            f"The spatial extent covers latitudes from {s['lat_min']:.3f}°N to "
            f"{s['lat_max']:.3f}°N and longitudes from {s['lon_min']:.3f}°E to "
            f"{s['lon_max']:.3f}°E."
        )
    if "depth_min" in s:
        parts.append(
            f"Depth ranges from {s['depth_min']:.1f} m to {s['depth_max']:.1f} m."
        )
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
    kw = ["polar", "cs-mach1"]
    if lat_col or lon_col: kw.append("geospatial data")
    if time_col:           kw.append("time series")
    if depth_col:          kw.append("oceanography")
    s["keywords"] = kw

    return s, None


def analyse_txt(file_bytes: bytes, filename: str) -> dict:
    """Extract basic info from plain text files for abstract suggestion."""
    try:
        text = file_bytes.decode("utf-8", errors="replace")
    except Exception:
        return {}
    lines       = [l.strip() for l in text.splitlines() if l.strip()]
    n_lines     = len(lines)
    n_chars     = len(text)
    stem        = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    abstract    = (
        f"This dataset, titled \"{stem}\", is provided as a plain text file "
        f"containing {n_lines:,} lines ({n_chars:,} characters). "
        f"It was collected within the framework of the {CSMACH1_PROJECT}, "
        f"funded by the {FUNDING_PROGRAM} under Grant Agreement No. {FUNDING_GRANT}."
    )
    return {"n_lines": n_lines, "abstract": abstract, "keywords": ["polar", "cs-mach1"]}


# ─── Section 1: DOI or upload ─────────────────────────────────────────────────
st.markdown('<div class="section-title">📤 Upload your dataset</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Drop your file here (CSV, NetCDF, TXT, ZIP, PDF, etc.)",
    type=None,
    label_visibility="collapsed",
    help="Any format accepted. CSV/TSV files get smart auto-fill of metadata.",
)

# ─── DOI option ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Or link an existing DOI</div>', unsafe_allow_html=True)

has_doi = st.radio(
    "Select an option", options=["yes", "no"],
    label_visibility="collapsed", horizontal=True,
)

existing_doi    = None
uploaded_file   = None
csv_sugg: dict  = {}
file_ext        = ""

if has_doi == "yes":
    existing_doi = st.text_input("DOI", placeholder="10.5281/zenodo.XXXXXXX")
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
        fmt      = FORMAT_INFO.get(file_ext, {"label": f"{file_ext.upper()} file", "icon": "📁", "parseable": False})

        st.markdown(
            f'<div class="format-badge">'
            f'{fmt["icon"]} <b>Detected format:</b> {fmt["label"]} &nbsp;|&nbsp; '
            f'<b>Size:</b> {uploaded_file.size / 1024:.1f} KB &nbsp;|&nbsp; '
            f'<b>Extension:</b> .{file_ext}'
            f'</div>',
            unsafe_allow_html=True,
        )

        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)

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
                    c1.metric("Rows",         f"{csv_sugg['n_rows']:,}")
                    c2.metric("Columns",      csv_sugg['n_cols'])
                    c3.metric("Numeric vars", len(csv_sugg.get("numeric_cols", [])))
                    if "time_start" in csv_sugg:
                        st.markdown(f"**Time range:** {csv_sugg['time_start']} → {csv_sugg['time_end']}")
                    if "lat_mean" in csv_sugg:
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
            if csv_sugg:
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

# ─── Section 2: User information ──────────────────────────────────────────────
st.markdown('<div class="section-title">Information about the user</div>', unsafe_allow_html=True)

col_first, col_last, col_orcid = st.columns([2, 2, 2])
with col_first:
    author_first = st.text_input("First name", key="author_first_0", placeholder="e.g. Antonio")
with col_last:
    author_last  = st.text_input("Last name",  key="author_last_0",  placeholder="e.g. Novellino")
with col_orcid:
    author_orcid = st.text_input("ORCID",      key="author_orcid_0", placeholder="0000-0000-0000-0000")

author_affil = st.text_input(
    "Affiliation", key="author_affil_0",
    placeholder="e.g. EMODnet Physics / OGS – National Institute of Oceanography and Applied Geophysics",
)

if "num_collaborators" not in st.session_state:
    st.session_state.num_collaborators = 0

if st.button("＋ Add another collaborator"):
    st.session_state.num_collaborators += 1

collaborators = []
for i in range(st.session_state.num_collaborators):
    st.markdown(f"*Collaborator {i + 1}*")
    ca, cb, cc, cd = st.columns([2, 2, 2, 3])
    with ca:
        cfirst = st.text_input("First name",  key=f"coll_first_{i}",  placeholder="First name")
    with cb:
        clast  = st.text_input("Last name",   key=f"coll_last_{i}",   placeholder="Last name")
    with cc:
        corcid = st.text_input("ORCID",       key=f"coll_orcid_{i}",  placeholder="0000-0000-0000-0000")
    with cd:
        caffil = st.text_input("Affiliation", key=f"coll_affil_{i}",  placeholder="Institution")
    collaborators.append({"first": cfirst, "last": clast, "orcid": corcid, "affil": caffil})

# ─── Section 3: Project ───────────────────────────────────────────────────────
st.markdown('<div class="section-title">Information about the project</div>', unsafe_allow_html=True)

project_name = st.text_input(
    "Project's name", placeholder="e.g. cs-mach1, MyArctic2024…",
)

# ─── Section 4: Measurement description ──────────────────────────────────────
st.markdown('<div class="section-title">Description of the measurement</div>', unsafe_allow_html=True)

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

# ─── Section 5: Metadata + abstract ──────────────────────────────────────────
st.markdown('<div class="section-title">Additional metadata</div>', unsafe_allow_html=True)

default_abstract = csv_sugg.get("abstract", "")
abstract = st.text_area(
    "Abstract / Description for Zenodo",
    value=default_abstract,
    placeholder="Provide a description of the dataset for the Zenodo record…",
    height=180,
    help="Auto-filled from file analysis when possible. Please review and complete.",
)

col_title, col_license = st.columns([3, 2])
with col_title:
    record_title = st.text_input("Dataset title *", placeholder="Title of the dataset on Zenodo")
with col_license:
    license_choice = st.selectbox(
        "License",
        options=["cc-by-4.0", "cc0-1.0", "cc-by-sa-4.0", "mit", "apache-2.0"],
        index=0,
    )

default_kw   = ", ".join(csv_sugg.get("keywords", []))
keywords_raw = st.text_input(
    "Keywords (comma-separated)",
    value=default_kw,
    placeholder="polar, oceanography, temperature, Arctic…",
)
keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]

# ─── Section 6: Location picker (Folium mini-map) ────────────────────────────
st.markdown('<div class="section-title">Geographic location</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="map-hint">🗺️ Click on the map to set the representative coordinates, '
    'or type them in the fields below. '
    'If the dataset covers an area, use the centroid.</div>',
    unsafe_allow_html=True,
)

# Session state defaults (pre-filled from CSV centroid if available)
if "sel_lat" not in st.session_state:
    st.session_state.sel_lat = round(csv_sugg.get("lat_mean", DEFAULT_LAT), 4)
if "sel_lon" not in st.session_state:
    st.session_state.sel_lon = round(csv_sugg.get("lon_mean", DEFAULT_LON), 4)

# Update defaults when a new CSV is loaded and has spatial info
if csv_sugg.get("lat_mean") is not None:
    st.session_state.sel_lat = round(csv_sugg["lat_mean"], 4)
    st.session_state.sel_lon = round(csv_sugg["lon_mean"], 4)

# Folium mini-map
_clat = st.session_state.sel_lat
_clon = st.session_state.sel_lon

m = folium.Map(location=[_clat, _clon], zoom_start=4, tiles=None)
folium.TileLayer(
    tiles="CartoDB positron", name="CartoDB Positron",
    overlay=False, control=True, show=True,
).add_to(m)
folium.TileLayer(
    tiles=(
        "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}"
    ),
    attr="Esri", name="Esri Ocean", overlay=False, control=True,
).add_to(m)
folium.TileLayer(
    tiles=(
        "https://tiles.emodnet-bathymetry.eu/wmts/1.0.0/"
        "mean_multicolour/default/web_mercator/{z}/{y}/{x}.png"
    ),
    attr="© EMODnet Bathymetry",
    name="EMODnet Bathymetry",
    overlay=False, control=True, show=False,
).add_to(m)
folium.LayerControl().add_to(m)

folium.Marker(
    location=[_clat, _clon],
    tooltip=f"Selected: {_clat:.4f}°N, {_clon:.4f}°E",
    icon=folium.Icon(color="blue", icon="tint", prefix="fa"),
).add_to(m)

# Bounding box from CSV if available
if "lat_min" in csv_sugg and "lon_min" in csv_sugg:
    folium.Rectangle(
        bounds=[
            [csv_sugg["lat_min"], csv_sugg["lon_min"]],
            [csv_sugg["lat_max"], csv_sugg["lon_max"]],
        ],
        color="#1a4f8a", weight=1.5, fill=True, fill_opacity=0.07,
        tooltip="Dataset spatial extent (from CSV)",
    ).add_to(m)

map_result = st_folium(
    m,
    use_container_width=True,
    height=380,
    returned_objects=["last_clicked"],
    key="location_map",
)

# Process map click → update session state and rerun
if map_result and map_result.get("last_clicked"):
    clicked = map_result["last_clicked"]
    new_lat  = round(clicked["lat"], 4)
    new_lon  = round(clicked["lng"], 4)
    if new_lat != st.session_state.sel_lat or new_lon != st.session_state.sel_lon:
        st.session_state.sel_lat = new_lat
        st.session_state.sel_lon = new_lon
        st.rerun()

# Editable coordinate fields (synced with map)
_lat_key = f"lat_input_{st.session_state.sel_lat}"
_lon_key = f"lon_input_{st.session_state.sel_lon}"

col_lat, col_lon = st.columns(2)
with col_lat:
    lat = st.number_input(
        "Latitude (°N)",
        value=st.session_state.sel_lat,
        min_value=-90.0, max_value=90.0,
        step=0.0001, format="%.4f",
        key=_lat_key,
    )
with col_lon:
    lon = st.number_input(
        "Longitude (°E)",
        value=st.session_state.sel_lon,
        min_value=-180.0, max_value=180.0,
        step=0.0001, format="%.4f",
        key=_lon_key,
    )

# Sync manual edits back to session state
if lat != st.session_state.sel_lat or lon != st.session_state.sel_lon:
    st.session_state.sel_lat = lat
    st.session_state.sel_lon = lon

st.caption(f"📍 Selected point: **{st.session_state.sel_lat:.4f}°N, {st.session_state.sel_lon:.4f}°E**")

# ─── Zenodo helpers ───────────────────────────────────────────────────────────

def build_creators(primary: dict, colls: list) -> list:
    """Build InvenioRDM creators list from author dicts."""
    result = []
    all_authors = [primary] + colls
    for a in all_authors:
        first = a.get("first", "").strip()
        last  = a.get("last",  "").strip()
        if not (first or last):
            continue
        full_name = f"{last}, {first}" if last and first else (last or first)
        creator = {
            "person_or_org": {
                "type":        "personal",
                "name":        full_name,
                "given_name":  first,
                "family_name": last,
            }
        }
        if a.get("orcid"):
            creator["person_or_org"]["identifiers"] = [
                {"scheme": "orcid", "identifier": a["orcid"]}
            ]
        if a.get("affil"):
            creator["affiliations"] = [{"name": a["affil"]}]
        result.append(creator)
    return result


def build_metadata(title, abstract_text, description_text, creators,
                   spatial, proj, kw, lat_val, lon_val, lic):
    desc_parts = []
    if abstract_text.strip():
        desc_parts.append(abstract_text.strip())
    if description_text.strip():
        desc_parts.append(f"Collection method: {description_text.strip()}")
    desc_parts.append(f"Spatial deployment: {spatial}.")
    desc_parts.append(
        f"Representative coordinates: {lat_val:.4f}°N, {lon_val:.4f}°E."
    )
    desc_parts.append(
        f"Project: {proj or CSMACH1_PROJECT}. "
        f"Funded by the {FUNDING_PROGRAM} under Grant Agreement No. {FUNDING_GRANT}."
    )

    metadata = {
        "title":         title,
        "description":   "\n\n".join(desc_parts),
        "resource_type": {"id": "dataset"},
        "creators":      creators,
        "rights":        [{"id": lic}],
        "communities":   [{"id": ZENODO_COMMUNITY}],
        "funding": [
            {
                "funder": {
                    "name":       "European Commission",
                    "scheme":     "doi",
                    "identifier": "10.13039/501100000780",
                },
                "award": {
                    "title":       {"en": CSMACH1_PROJECT},
                    "number":      FUNDING_GRANT,
                    "identifiers": [{"scheme": "url", "identifier": CORDIS_URL}],
                },
            }
        ],
    }
    if kw:
        metadata["subjects"] = [{"subject": k} for k in kw]
    return metadata


def create_draft(token, metadata):
    r = requests.post(
        f"{ZENODO_API_URL}/records",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        json={"metadata": metadata},
    )
    r.raise_for_status()
    return r.json()


def upload_file_to_draft(token, record_id, file_bytes, filename):
    requests.post(
        f"{ZENODO_API_URL}/records/{record_id}/draft/files",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        json=[{"key": filename}],
    ).raise_for_status()
    requests.put(
        f"{ZENODO_API_URL}/records/{record_id}/draft/files/{filename}/content",
        headers={"Content-Type": "application/octet-stream", "Authorization": f"Bearer {token}"},
        data=file_bytes,
    ).raise_for_status()
    r = requests.post(
        f"{ZENODO_API_URL}/records/{record_id}/draft/files/{filename}/commit",
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r.json()


def publish_draft(token, record_id):
    r = requests.post(
        f"{ZENODO_API_URL}/records/{record_id}/draft/actions/publish",
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r.json()


def add_existing_doi_to_community(token, doi):
    r = requests.get(
        f"{ZENODO_API_URL}/records",
        params={"q": f"doi:{doi}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    hits = r.json().get("hits", {}).get("hits", [])
    if not hits:
        raise ValueError(f"No record found for DOI: {doi}")
    record_id = hits[0]["id"]
    requests.post(
        f"{ZENODO_API_URL}/communities/{ZENODO_COMMUNITY}/records",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        json={"records": [{"id": str(record_id)}]},
    ).raise_for_status()
    return record_id


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
    if has_doi == "yes" and not existing_doi:
        errors.append("Please enter the existing dataset DOI.")
    if has_doi == "no" and not uploaded_file:
        errors.append("Please upload a dataset file.")
    if not (author_first or author_last):
        errors.append("Please enter at least the first author's name.")
    if has_doi == "no" and not record_title:
        errors.append("Please provide a dataset title.")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    primary_author = {
        "first": author_first, "last": author_last,
        "orcid": author_orcid, "affil": author_affil,
    }
    creators = build_creators(primary_author, collaborators)

    with st.spinner("Uploading to Zenodo…"):
        try:
            if has_doi == "yes":
                record_id = add_existing_doi_to_community(ZENODO_TOKEN, existing_doi)
                view_url   = f"https://zenodo.org/records/{record_id}"
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
                metadata = build_metadata(
                    title=record_title,
                    abstract_text=abstract,
                    description_text=description,
                    creators=creators,
                    spatial=spatial_deployment,
                    proj=project_name,
                    kw=keywords,
                    lat_val=st.session_state.sel_lat,
                    lon_val=st.session_state.sel_lon,
                    lic=license_choice,
                )

                draft_info = create_draft(ZENODO_TOKEN, metadata)
                record_id  = draft_info["id"]
                st.info(f"📝 Draft created (ID: {record_id})")

                file_bytes_upload = uploaded_file.read()
                upload_file_to_draft(ZENODO_TOKEN, record_id, file_bytes_upload, uploaded_file.name)
                st.info(f"📂 File '{uploaded_file.name}' uploaded.")

                published = publish_draft(ZENODO_TOKEN, record_id)
                doi_out   = published.get("doi", "n/a")
                view_url  = f"https://zenodo.org/records/{record_id}"

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
from cs_mach1_theme import cs_mach1_footer
cs_mach1_footer("CS-MACH1 Zenodo Uploader • Marine Citizen Science Data Horizon")
