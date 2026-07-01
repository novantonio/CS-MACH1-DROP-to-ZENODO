"""
cs_mach1_theme.py
------------------
Unified CS-MACH1 branding & Streamlit page-setup helper.

Replaces the per-repo duplicates (CS-MACH1-METEOTRACKER, CS-MACH1-SCUBA,
CORA-vs-WOD) with a single configurable module. Supports multiple style
presets, switchable via a selector rendered on the MAIN page (not the
sidebar), so the same module/CSS can power every CS-MACH1 app while still
letting each one pick its own look.

Usage (top of any Streamlit script, before any other st.* call):

    from cs_mach1_theme import apply_cs_mach1_theme, cs_mach1_footer

    apply_cs_mach1_theme(
        page_title="CS-MACH1 MeteoTracker",
        main_title="🌊 CS-MACH1 MeteoTracker",
        subtitle="Ocean temperature monitoring platform",
        default_theme="Ocean Blue",   # one of THEMES.keys()
    )

    ... your app code ...

    cs_mach1_footer()
"""

import streamlit as st

# ── Theme presets ────────────────────────────────────────────────────────
# Add new presets here. Every app importing this module gets them all,
# and can pick a different default_theme without touching the CSS.
THEMES = {
    "Ocean Blue": {
        "brand": "#00A6D6",
        "hover": "#007EA3",
        "text_muted": "#555555",
    },
    "Deep Sea Dark": {
        "brand": "#3DB5FF",
        "hover": "#1E88C7",
        "text_muted": "#AAAAAA",
    },
    "Scuba Green": {
        "brand": "#0E9F6E",
        "hover": "#0B7A55",
        "text_muted": "#555555",
    },
    "Storm Orange": {
        "brand": "#E07A1F",
        "hover": "#B8610E",
        "text_muted": "#555555",
    },
}

DEFAULT_THEME = "Ocean Blue"


def _build_css(palette: dict) -> str:
    return f"""
<style>
/* ── Header ──────────────────────────────────────────────── */
.cs-main-header {{
    font-size: 34px;
    font-weight: 700;
    color: {palette['brand']};
    margin-bottom: 0px;
}}
.cs-sub-header {{
    font-size: 16px;
    color: {palette['text_muted']};
    margin-bottom: 20px;
}}

/* ── Buttons (all live on the main page, never in the sidebar) ─ */
.stButton>button {{
    background-color: {palette['brand']};
    color: white;
    border-radius: 8px;
    border: none;
}}
.stButton>button:hover {{
    background-color: {palette['hover']};
    color: white;
}}

/* ── Footer ──────────────────────────────────────────────── */
.cs-footer {{
    text-align: center;
    color: grey;
    font-size: 13px;
    margin-top: 2rem;
}}
</style>
"""


def apply_cs_mach1_theme(
    page_title: str = "CS-MACH1",
    page_icon: str = "logo.png",
    main_title: str = "🌊 CS-MACH1",
    subtitle: str = "Ocean temperature monitoring platform",
    logo_path: str = "logo.png",
    logo_width: int = 250,
    layout: str = "wide",
    default_theme: str = DEFAULT_THEME,
    show_theme_picker: bool = True,
) -> str:
    """
    Call once at the top of your Streamlit script (before any other st.* call).
    Sets page config, renders an optional in-page theme selector, injects the
    brand CSS for the chosen palette, then renders the logo and page header.

    Parameters
    ----------
    page_title, page_icon, layout : passed straight to st.set_page_config.
    main_title, subtitle          : heading text shown under the logo.
    logo_path, logo_width         : logo image (path or URL) and width in px.
    default_theme                 : key from THEMES used on first load.
    show_theme_picker             : if True, shows a selectbox (top-right of
                                     the main page) letting the user switch
                                     presets live. Set False to lock the theme.

    Returns
    -------
    The name of the currently active theme (useful if you want to branch
    on it elsewhere in the app, e.g. for a matplotlib color scheme).
    """
    st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)

    if "cs_theme" not in st.session_state:
        st.session_state["cs_theme"] = default_theme
'''
    if show_theme_picker:
        _, picker_col = st.columns([5, 2])
        with picker_col:
            st.session_state["cs_theme"] = st.selectbox(
                "Theme",
                options=list(THEMES.keys()),
                index=list(THEMES.keys()).index(st.session_state["cs_theme"]),
                label_visibility="collapsed",
                key="cs_theme_picker",
            )
'''
    palette = THEMES[st.session_state["cs_theme"]]
    st.markdown(_build_css(palette), unsafe_allow_html=True)

    
    st.markdown(f"<div class='cs-main-header'>{main_title}</div>", unsafe_allow_html=True)
    #st.image(logo_path, width=logo_width)
    st.markdown(f"<div class='cs-sub-header'>{subtitle}</div>", unsafe_allow_html=True)

    return st.session_state["cs_theme"]


def cs_mach1_footer(text: str = "CS-MACH1 Project • Ocean Temperature Monitoring Platform") -> None:
    """Render the standard CS-MACH1 horizontal-rule + footer."""
    st.markdown("---")
    st.markdown(f"<div class='cs-footer'>{text}</div>", unsafe_allow_html=True)
