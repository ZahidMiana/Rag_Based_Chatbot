"""
frontend/app.py
DocuMind AI — Streamlit frontend
Matches the design shown in UI screenshots: dark navy theme, sidebar nav,
login split-panel, dashboard, chat, upload, my-documents, admin panel.
"""

from __future__ import annotations

import sys
import os
import uuid
import time
from datetime import datetime
from typing import Optional

import streamlit as st

# Ensure project root is on sys.path so `frontend.api_client` resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from frontend.api_client import APIClient, get_client  # noqa: E402

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════
C = {
    "bg":       "#080D18",
    "sidebar":  "#0C1220",
    "card":     "#111827",
    "border":   "#1F2E45",
    "accent":   "#3B82F6",
    "accent2":  "#2563EB",
    "text":     "#E8EDF5",
    "muted":    "#8B9AB4",
    "success":  "#22C55E",
    "warning":  "#F59E0B",
    "danger":   "#EF4444",
    "dim":      "#4B5E7A",
}

FILE_ICON = {
    "pdf":  ("🔴", "#EF4444"),
    "docx": ("🔵", "#3B82F6"),
    "doc":  ("🔵", "#3B82F6"),
    "csv":  ("🟢", "#22C55E"),
    "xlsx": ("🟢", "#22C55E"),
    "xls":  ("🟢", "#22C55E"),
    "txt":  ("⚪", "#8B9AB4"),
    "md":   ("🟣", "#8B5CF6"),
}


def _file_icon(filename: str) -> tuple[str, str]:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    return FILE_ICON.get(ext, ("📄", "#8B9AB4"))


# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════

def inject_css() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Reset ───────────────────────────────────────────── */
*,*::before,*::after{{box-sizing:border-box}}
html,body,[class*="css"]{{font-family:'Inter',sans-serif!important}}

/* ── Hide Streamlit chrome ──────────────────────────── */
#MainMenu,footer,header,.stDeployButton{{visibility:hidden!important;display:none!important}}

/* ── App background ─────────────────────────────────── */
.stApp{{background-color:{C["bg"]}!important;color:{C["text"]}!important}}
[data-testid="stAppViewContainer"]{{background-color:{C["bg"]}!important}}
[data-testid="stMain"]{{background-color:{C["bg"]}!important}}

/* ── Sidebar ─────────────────────────────────────────── */
[data-testid="stSidebar"]{{background-color:{C["sidebar"]}!important;border-right:1px solid{C["border"]}!important}}
[data-testid="stSidebar"] .stButton>button{{background-color:transparent!important;color:{C["muted"]}!important;border:none!important;text-align:left!important;padding:9px 12px!important;border-radius:8px!important;font-size:14px!important;font-weight:500!important;width:100%!important;transition:all .15s}}
[data-testid="stSidebar"] .stButton>button:hover{{background-color:{C["card"]}!important;color:{C["text"]}!important}}

/* ── Typography ──────────────────────────────────────── */
h1,h2,h3,h4,h5,h6{{color:{C["text"]}!important;font-weight:700!important}}
p,span,label,div{{color:{C["text"]}}}

/* ── Text inputs ─────────────────────────────────────── */
.stTextInput>label{{color:{C["muted"]}!important;font-size:13px!important;font-weight:500!important;margin-bottom:4px!important}}
.stTextInput>div>div>input{{background-color:{C["card"]}!important;border:1px solid{C["border"]}!important;color:{C["text"]}!important;border-radius:8px!important;padding:10px 14px!important;font-size:14px!important}}
.stTextInput>div>div>input:focus{{border-color:{C["accent"]}!important;box-shadow:0 0 0 3px rgba(59,130,246,.15)!important;outline:none!important}}
.stTextInput>div>div>input::placeholder{{color:{C["dim"]}!important}}

/* ── Textarea ────────────────────────────────────────── */
.stTextArea>label{{color:{C["muted"]}!important;font-size:13px!important;font-weight:500!important}}
.stTextArea>div>div>textarea{{background-color:{C["card"]}!important;border:1px solid{C["border"]}!important;color:{C["text"]}!important;border-radius:8px!important}}
.stTextArea>div>div>textarea:focus{{border-color:{C["accent"]}!important}}

/* ── Primary buttons ─────────────────────────────────── */
.stButton>button{{background-color:{C["accent"]}!important;color:#fff!important;border:none!important;border-radius:8px!important;font-weight:600!important;font-size:14px!important;padding:10px 20px!important;transition:background-color .2s!important;letter-spacing:.01em!important;cursor:pointer!important}}
.stButton>button:hover{{background-color:{C["accent2"]}!important}}
.stButton>button:active{{transform:scale(.98)!important}}

/* ── Tabs ────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"]{{background-color:{C["card"]}!important;border-radius:10px!important;padding:4px!important;gap:2px!important;border:1px solid{C["border"]}!important}}
.stTabs [data-baseweb="tab"]{{background-color:transparent!important;color:{C["muted"]}!important;border-radius:8px!important;font-weight:500!important;font-size:14px!important;padding:8px 24px!important;border:none!important}}
.stTabs [aria-selected="true"]{{background-color:{C["accent"]}!important;color:#fff!important}}
.stTabs [data-baseweb="tab-highlight"]{{display:none!important}}
.stTabs [data-baseweb="tab-border"]{{display:none!important}}

/* ── Checkbox ────────────────────────────────────────── */
.stCheckbox>label>span{{color:{C["muted"]}!important;font-size:13px!important}}

/* ── Selectbox ───────────────────────────────────────── */
.stSelectbox>label{{color:{C["muted"]}!important;font-size:13px!important}}
.stSelectbox [data-baseweb="select"]>div{{background-color:{C["card"]}!important;border:1px solid{C["border"]}!important;border-radius:8px!important;color:{C["text"]}!important}}

/* ── File uploader ───────────────────────────────────── */
[data-testid="stFileUploader"]{{background-color:{C["card"]}!important;border:2px dashed{C["border"]}!important;border-radius:12px!important;transition:border-color .2s}}
[data-testid="stFileUploader"]:hover{{border-color:{C["accent"]}!important}}
[data-testid="stFileUploaderDropzone"]{{background-color:transparent!important}}
.stFileUploader label{{color:{C["muted"]}!important}}

/* ── Progress ────────────────────────────────────────── */
.stProgress>div>div{{background-color:{C["border"]}!important;border-radius:4px!important}}
.stProgress>div>div>div{{background-color:{C["accent"]}!important;border-radius:4px!important}}

/* ── Metrics ─────────────────────────────────────────── */
[data-testid="stMetric"]{{background-color:{C["card"]}!important;border:1px solid{C["border"]}!important;border-radius:12px!important;padding:20px!important}}
[data-testid="stMetricLabel"]>div{{color:{C["muted"]}!important;font-size:12px!important;text-transform:uppercase!important;letter-spacing:.05em!important}}
[data-testid="stMetricValue"]>div{{color:{C["text"]}!important;font-size:28px!important;font-weight:700!important}}

/* ── Dataframe ───────────────────────────────────────── */
[data-testid="stDataFrame"]{{background-color:{C["card"]}!important;border:1px solid{C["border"]}!important;border-radius:12px!important}}
.stDataFrame thead tr th{{background-color:{C["sidebar"]}!important;color:{C["muted"]}!important;font-size:11px!important;text-transform:uppercase!important;letter-spacing:.08em!important;padding:12px 16px!important;border-bottom:1px solid{C["border"]}!important}}
.stDataFrame tbody tr td{{color:{C["text"]}!important;font-size:13px!important;padding:12px 16px!important;border-bottom:1px solid{C["border"]}!important}}
.stDataFrame tbody tr:hover td{{background-color:{C["sidebar"]}!important}}

/* ── Expander ────────────────────────────────────────── */
.stExpander{{border:1px solid{C["border"]}!important;border-radius:8px!important;background-color:{C["card"]}!important}}
.stExpander summary{{color:{C["muted"]}!important;font-weight:500!important}}

/* ── Alert / info ────────────────────────────────────── */
.stAlert{{border-radius:8px!important}}

/* ── Chat messages ───────────────────────────────────── */
[data-testid="stChatMessage"]{{background-color:{C["card"]}!important;border:1px solid{C["border"]}!important;border-radius:12px!important;margin-bottom:8px!important}}

/* ── Chat input ──────────────────────────────────────── */
[data-testid="stChatInput"]{{background-color:{C["card"]}!important;border:1px solid{C["border"]}!important;border-radius:12px!important}}
[data-testid="stChatInputTextArea"]{{background-color:transparent!important;color:{C["text"]}!important}}
[data-testid="stChatInputTextArea"]::placeholder{{color:{C["dim"]}!important}}

/* ── Scrollbar ───────────────────────────────────────── */
::-webkit-scrollbar{{width:6px;height:6px}}
::-webkit-scrollbar-track{{background:{C["bg"]}}}
::-webkit-scrollbar-thumb{{background:{C["border"]};border-radius:3px}}
::-webkit-scrollbar-thumb:hover{{background:{C["dim"]}}}

/* ── Spinner ─────────────────────────────────────────── */
.stSpinner>div>div{{border-top-color:{C["accent"]}!important}}

/* ── Toast ───────────────────────────────────────────── */
[data-testid="stToast"]{{background-color:{C["card"]}!important;border:1px solid{C["border"]}!important;color:{C["text"]}!important}}

/* ── Divider ─────────────────────────────────────────── */
hr{{border-color:{C["border"]}!important}}

/* ── Horizontal radio (for filter tabs) ─────────────── */
.stRadio>div{{flex-direction:row!important;gap:8px!important;flex-wrap:wrap}}
.stRadio>label{{color:{C["muted"]}!important;font-size:13px!important}}
.stRadio [data-baseweb="radio"]>div:first-child{{background-color:{C["card"]}!important;border-color:{C["border"]}!important}}

/* ── Column gap fix ──────────────────────────────────── */
[data-testid="column"]{{padding:4px 8px!important}}
</style>
""",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SHARED HTML HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _badge(text: str, kind: str = "user") -> str:
    colors = {
        "admin":      (f"rgba(59,130,246,.2)",  C["accent"]),
        "user":       (f"rgba(139,154,180,.15)", C["muted"]),
        "ready":      (f"rgba(34,197,94,.15)",   C["success"]),
        "processing": (f"rgba(245,158,11,.15)",  C["warning"]),
        "failed":     (f"rgba(239,68,68,.15)",   C["danger"]),
        "active":     (f"rgba(34,197,94,.15)",   C["success"]),
        "inactive":   (f"rgba(239,68,68,.15)",   C["danger"]),
    }
    bg, fg = colors.get(kind.lower(), (f"rgba(139,154,180,.15)", C["muted"]))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 10px;'
        f'border-radius:20px;font-size:11px;font-weight:700;'
        f'letter-spacing:.05em;text-transform:uppercase;display:inline-block">'
        f"{text}</span>"
    )


def _stat_card(
    label: str, value: str, icon: str, trend: Optional[str] = None, trend_up: bool = True
) -> str:
    trend_color = C["success"] if trend_up else C["danger"]
    trend_html = (
        f'<div style="font-size:12px;color:{trend_color};margin-top:4px">{trend}</div>'
        if trend else ""
    )
    return f"""
<div style="background:{C["card"]};border:1px solid{C["border"]};border-radius:12px;
     padding:20px;height:100%;min-height:110px">
  <div style="font-size:12px;color:{C["muted"]};text-transform:uppercase;
       letter-spacing:.08em;margin-bottom:10px">{icon}&nbsp; {label}</div>
  <div style="font-size:30px;font-weight:800;color:{C["text"]};line-height:1">{value}</div>
  {trend_html}
</div>"""


def _section_header(title: str, action_label: str = "", action_page: str = "") -> str:
    action_html = ""
    if action_label:
        action_html = (
            f'<span style="color:{C["accent"]};font-size:13px;cursor:pointer">'
            f"{action_label}</span>"
        )
    return f"""
<div style="display:flex;justify-content:space-between;align-items:center;
     margin:24px 0 16px">
  <h2 style="font-size:18px;font-weight:600;color:{C["text"]};margin:0">{title}</h2>
  {action_html}
</div>"""


def _page_header(title: str, subtitle: str = "") -> None:
    sub = f'<p style="color:{C["muted"]};margin:2px 0 0">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div style="margin-bottom:24px">'
        f'<h1 style="font-size:28px;font-weight:700;color:{C["text"]};margin:0">{title}</h1>'
        f"{sub}</div>",
        unsafe_allow_html=True,
    )


def _empty_state(message: str, icon: str = "📭") -> None:
    st.markdown(
        f"""<div style="background:{C["card"]};border:1px solid{C["border"]};
border-radius:12px;padding:48px;text-align:center">
  <div style="font-size:40px;margin-bottom:16px">{icon}</div>
  <p style="color:{C["muted"]};margin:0;font-size:15px">{message}</p>
</div>""",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

def _nav_button(icon: str, label: str, page_key: str) -> None:
    """Render a sidebar nav item. Active ones show as blue pill via CSS override."""
    is_active = st.session_state.get("current_page") == page_key
    if is_active:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;'
            f'border-radius:8px;background:{C["accent"]};margin:2px 4px 2px;'
            f'cursor:pointer">'
            f'<span style="font-size:16px">{icon}</span>'
            f'<span style="color:#fff;font-weight:600;font-size:14px">{label}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        if st.button(f"{icon}  {label}", key=f"nav_{page_key}", use_container_width=True):
            st.session_state["current_page"] = page_key
            # Reset chat state when switching away from chat
            if page_key != "chat":
                st.session_state.pop("chat_session_id", None)
            st.rerun()


def render_sidebar(client: APIClient) -> None:
    user = st.session_state.get("user", {})
    username = user.get("username", "User")
    role = user.get("role", "user")

    with st.sidebar:
        # ── Logo ──────────────────────────────────────────────
        st.markdown(
            f"""<div style="padding:20px 16px 14px;display:flex;align-items:center;
gap:10px;border-bottom:1px solid{C["border"]}">
  <div style="width:36px;height:36px;background:linear-gradient(135deg,#3B82F6,#6366F1);
       border-radius:8px;display:flex;align-items:center;justify-content:center;
       font-size:18px">📄</div>
  <span style="color:{C["text"]};font-weight:700;font-size:15px">DocuMind AI</span>
</div>""",
            unsafe_allow_html=True,
        )

        # ── User card ──────────────────────────────────────────
        role_bg = "rgba(59,130,246,.2)" if role == "admin" else "rgba(139,154,180,.15)"
        role_fg = C["accent"] if role == "admin" else C["muted"]
        initial = username[0].upper() if username else "U"
        st.markdown(
            f"""<div style="margin:12px 8px;padding:12px;background:{C["card"]};
border:1px solid{C["border"]};border-radius:10px">
  <div style="display:flex;align-items:center;gap:10px">
    <div style="width:36px;height:36px;background:linear-gradient(135deg,#3B82F6,#6366F1);
         border-radius:50%;display:flex;align-items:center;justify-content:center;
         color:#fff;font-weight:700;font-size:14px;flex-shrink:0">{initial}</div>
    <div>
      <div style="color:{C["text"]};font-weight:600;font-size:14px">{username}</div>
      <span style="background:{role_bg};color:{role_fg};font-size:10px;font-weight:700;
            padding:2px 8px;border-radius:4px;text-transform:uppercase">{role}</span>
    </div>
  </div>
</div>""",
            unsafe_allow_html=True,
        )

        # ── Navigation ─────────────────────────────────────────
        st.markdown('<div style="padding:0 4px;margin-top:4px">', unsafe_allow_html=True)

        _nav_button("💬", "Chat", "chat")
        _nav_button("⬆️", "Upload", "upload")
        _nav_button("📁", "My Documents", "my_documents")
        _nav_button("📊", "Dashboard", "dashboard")
        if role == "admin":
            _nav_button("⚙️", "Admin Panel", "admin")

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Spacer + Logout ────────────────────────────────────
        st.markdown('<div style="height:32px"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="border-top:1px solid{C["border"]};padding:12px 4px 4px">',
            unsafe_allow_html=True,
        )
        if st.button("🔴  Logout", key="sidebar_logout", use_container_width=True):
            client.logout()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: LOGIN / REGISTER
# ══════════════════════════════════════════════════════════════════════════════

def page_login(client: APIClient) -> None:
    # Hide sidebar on login
    st.markdown(
        '<style>[data-testid="stSidebar"]{display:none!important}</style>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1.2, 1], gap="large")

    # ── Left: Branding panel ────────────────────────────────────────────────
    with col_left:
        st.markdown(
            f"""<div style="background:linear-gradient(180deg,#0C1526 0%,{C["bg"]} 100%);
min-height:88vh;border-radius:16px;display:flex;flex-direction:column;
justify-content:center;align-items:center;text-align:center;padding:48px 40px">

  <div style="width:64px;height:64px;background:linear-gradient(135deg,#3B82F6,#6366F1);
       border-radius:14px;display:flex;align-items:center;justify-content:center;
       font-size:34px;margin-bottom:20px">📄</div>

  <h2 style="color:{C["text"]};font-size:22px;font-weight:700;margin:0 0 28px">
    DocuMind AI</h2>

  <!-- Doc illustration mock -->
  <div style="background:{C["card"]};border:1px solid{C["border"]};border-radius:14px;
       padding:24px 32px;margin-bottom:32px;width:260px">
    <div style="background:{C["accent"]};border-radius:8px;height:8px;width:80%;
         margin:0 auto 10px"></div>
    <div style="background:{C["border"]};border-radius:4px;height:6px;width:100%;
         margin-bottom:8px"></div>
    <div style="background:{C["border"]};border-radius:4px;height:6px;width:70%;
         margin-bottom:8px"></div>
    <div style="background:{C["border"]};border-radius:4px;height:6px;width:85%;
         margin-bottom:20px"></div>
    <div style="display:flex;gap:8px">
      <div style="background:{C["sidebar"]};border:1px solid{C["border"]};
           border-radius:6px;padding:8px 14px;font-size:11px;color:{C["muted"]}">PDF</div>
      <div style="background:{C["sidebar"]};border:1px solid{C["border"]};
           border-radius:6px;padding:8px 14px;font-size:11px;color:{C["muted"]}">DOCX</div>
      <div style="background:{C["sidebar"]};border:1px solid{C["border"]};
           border-radius:6px;padding:8px 14px;font-size:11px;color:{C["muted"]}">TXT</div>
    </div>
  </div>

  <h1 style="color:{C["text"]};font-size:26px;font-weight:700;margin:0 0 14px">
    Chat with your documents.</h1>
  <p style="color:{C["muted"]};font-size:14px;line-height:1.7;max-width:320px;margin:0">
    Powered by AI. Upload PDFs, ask questions, and get instant summaries with our
    neural processing engine.</p>

</div>
<div style="color:{C["dim"]};font-size:11px;letter-spacing:.12em;margin-top:12px;
     text-align:center">V1.0.0 &bull; ENTERPRISE READY</div>""",
            unsafe_allow_html=True,
        )

    # ── Right: Auth forms ────────────────────────────────────────────────────
    with col_right:
        st.markdown('<div style="padding:48px 8px 0">', unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["  Login  ", "  Register  "])

        # ── Login tab ──────────────────────────────────────────
        with tab_login:
            st.markdown(
                f"""<div style="margin-bottom:28px">
  <h2 style="font-size:24px;font-weight:700;color:{C["text"]};margin:0 0 4px">
    Welcome back</h2>
  <p style="color:{C["muted"]};font-size:14px;margin:0">
    Enter your credentials to access your documents</p>
</div>""",
                unsafe_allow_html=True,
            )

            login_email = st.text_input(
                "Email Address", placeholder="name@company.com", key="li_email"
            )
            login_pass = st.text_input(
                "Password", type="password", placeholder="••••••••", key="li_pass"
            )

            col_cb, col_fp = st.columns([1, 1])
            with col_cb:
                st.checkbox("Remember me for 30 days", key="li_remember")
            with col_fp:
                st.markdown(
                    f'<div style="text-align:right;padding-top:4px">'
                    f'<span style="color:{C["accent"]};font-size:13px;cursor:pointer">'
                    f"Forgot password?</span></div>",
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            if st.button("Login to Dashboard", use_container_width=True, key="li_btn"):
                if not login_email or not login_pass:
                    st.error("Please fill in all fields.")
                else:
                    with st.spinner("Signing in…"):
                        data, err = client.login(login_email, login_pass)
                    if err:
                        st.error(f"Login failed: {err}")
                    else:
                        _do_login(client, data)

            st.markdown(
                f"""<div style="display:flex;align-items:center;gap:12px;
margin:20px 0;color:{C["dim"]};font-size:12px">
  <div style="flex:1;height:1px;background:{C["border"]}"></div>
  OR CONTINUE WITH
  <div style="flex:1;height:1px;background:{C["border"]}"></div>
</div>""",
                unsafe_allow_html=True,
            )

            gc, ghc = st.columns(2)
            with gc:
                if st.button("🟣  Google", use_container_width=True, key="li_google"):
                    st.info("OAuth not configured in this deployment.")
            with ghc:
                if st.button("⚫  GitHub", use_container_width=True, key="li_github"):
                    st.info("OAuth not configured in this deployment.")

            st.markdown(
                f'<p style="color:{C["dim"]};font-size:11px;text-align:center;'
                f'margin-top:20px">By continuing you agree to DocuMind AI\'s '
                f'<span style="color:{C["accent"]}">Terms of Service</span> and '
                f'<span style="color:{C["accent"]}">Privacy Policy</span></p>',
                unsafe_allow_html=True,
            )

        # ── Register tab ───────────────────────────────────────
        with tab_register:
            st.markdown(
                f"""<div style="margin-bottom:28px">
  <h2 style="font-size:24px;font-weight:700;color:{C["text"]};margin:0 0 4px">
    Create account</h2>
  <p style="color:{C["muted"]};font-size:14px;margin:0">
    Start your AI-powered document journey</p>
</div>""",
                unsafe_allow_html=True,
            )

            reg_user = st.text_input("Username", placeholder="johndoe", key="reg_user")
            reg_email = st.text_input(
                "Email Address", placeholder="name@company.com", key="reg_email"
            )
            reg_pass = st.text_input(
                "Password", type="password", placeholder="Min 8 characters", key="reg_pass"
            )
            reg_confirm = st.text_input(
                "Confirm Password", type="password", placeholder="Repeat your password", key="reg_confirm"
            )

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            if st.button("Create Account", use_container_width=True, key="reg_btn"):
                if not all([reg_user, reg_email, reg_pass, reg_confirm]):
                    st.error("Please fill in all fields.")
                elif reg_pass != reg_confirm:
                    st.error("Passwords do not match.")
                elif len(reg_pass) < 8:
                    st.error("Password must be at least 8 characters.")
                else:
                    with st.spinner("Creating account…"):
                        r_data, r_err = client.register(reg_user, reg_email, reg_pass)
                    if r_err:
                        st.error(f"Registration failed: {r_err}")
                    else:
                        st.success("Account created! Signing you in…")
                        time.sleep(0.8)
                        l_data, l_err = client.login(reg_email, reg_pass)
                        if l_err:
                            st.error(f"Auto-login failed: {l_err}")
                        else:
                            _do_login(client, l_data)

        st.markdown("</div>", unsafe_allow_html=True)


def _do_login(client: APIClient, token_data: dict) -> None:
    """Store tokens, fetch user info, transition to dashboard."""
    st.session_state["access_token"] = token_data["access_token"]
    st.session_state["refresh_token"] = token_data["refresh_token"]
    user, _ = client.get_me()
    st.session_state["user"] = user or {}
    st.session_state["authenticated"] = True
    st.session_state["current_page"] = "dashboard"
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def page_dashboard(client: APIClient) -> None:
    user = st.session_state.get("user", {})
    username = user.get("username", "User")
    today = datetime.now().strftime("%B %d, %Y")

    # Header
    hdr_l, hdr_r = st.columns([2, 1])
    with hdr_l:
        _page_header("Dashboard Overview", f"Welcome back, {username}!")
    with hdr_r:
        st.markdown(
            f'<div style="text-align:right;padding-top:12px">'
            f'<span style="color:{C["muted"]};font-size:14px">Good morning, {username.split()[0]}</span><br>'
            f'<span style="color:{C["dim"]};font-size:12px">{today}</span></div>',
            unsafe_allow_html=True,
        )

    # ── Fetch data ─────────────────────────────────────────
    docs, _ = client.get_documents()
    sessions_data, _ = client.get_sessions()
    docs = docs or []
    sessions_data = sessions_data or []

    doc_count = len(docs)
    session_count = len(sessions_data)
    total_queries = sum(s.get("message_count", 0) for s in sessions_data)
    total_chunks = sum(d.get("chunk_count", 0) for d in docs)

    # ── Stat cards ─────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.markdown(_stat_card("Total Docs", str(doc_count), "📄", f"+{doc_count} uploaded"), unsafe_allow_html=True)
    with c2:
        st.markdown(_stat_card("Total Queries", str(total_queries), "💬", "all sessions"), unsafe_allow_html=True)
    with c3:
        st.markdown(_stat_card("Active Sessions", str(session_count), "🔄"), unsafe_allow_html=True)
    with c4:
        st.markdown(_stat_card("Total Chunks", str(total_chunks), "🗄️"), unsafe_allow_html=True)

    # ── Recent Activity ─────────────────────────────────────
    st.markdown(_section_header("Recent Activity", "View All"), unsafe_allow_html=True)

    if sessions_data:
        import pandas as pd
        rows = []
        for s in sessions_data[:8]:
            last = s.get("last_message_at") or ""
            rows.append({
                "Session ID": (s.get("session_id", "")[:28] + "…") if len(s.get("session_id","")) > 28 else s.get("session_id",""),
                "Messages": s.get("message_count", 0),
                "Last Active": str(last)[:10] if last else "—",
                "Status": "Active",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        _empty_state("No activity yet. Upload a document and start chatting!", "💬")

    # ── Recent docs ─────────────────────────────────────────
    if docs:
        st.markdown(_section_header("Recent Documents"), unsafe_allow_html=True)
        for doc in docs[:3]:
            icon_emoji, _ = _file_icon(doc.get("filename", ""))
            status = doc.get("status", "unknown").lower()
            status_badge = _badge(status, status)
            st.markdown(
                f"""<div style="background:{C["card"]};border:1px solid{C["border"]};
border-radius:10px;padding:14px 18px;margin-bottom:8px;
display:flex;align-items:center;justify-content:space-between">
  <div style="display:flex;align-items:center;gap:12px">
    <span style="font-size:22px">{icon_emoji}</span>
    <div>
      <div style="font-weight:600;font-size:14px;color:{C["text"]}">{doc.get("filename","")}</div>
      <div style="font-size:12px;color:{C["muted"]}">{doc.get("chunk_count",0)} chunks
        &bull; {str(doc.get("created_at",""))[:10]}</div>
    </div>
  </div>
  {status_badge}
</div>""",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CHAT
# ══════════════════════════════════════════════════════════════════════════════

def page_chat(client: APIClient) -> None:
    # ── Initialise session state ────────────────────────────
    if "chat_session_id" not in st.session_state:
        st.session_state["chat_session_id"] = str(uuid.uuid4())
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    session_id: str = st.session_state["chat_session_id"]

    # ── Sidebar: session list ───────────────────────────────
    with st.sidebar:
        st.markdown(
            f"""<div style="padding:16px 8px 12px;border-bottom:1px solid{C["border"]}">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
    <div style="width:28px;height:28px;background:linear-gradient(135deg,#3B82F6,#6366F1);
         border-radius:6px;display:flex;align-items:center;justify-content:center;
         font-size:14px">📄</div>
    <span style="color:{C["text"]};font-weight:700;font-size:14px">DocuMind AI</span>
  </div>
</div>""",
            unsafe_allow_html=True,
        )

        if st.button("＋  New Chat", key="new_chat_btn", use_container_width=True):
            new_id = str(uuid.uuid4())
            st.session_state["chat_session_id"] = new_id
            st.session_state["chat_messages"] = []
            st.rerun()

        # Session list
        st.markdown(
            f'<div style="margin:16px 0 8px;padding:0 4px;font-size:11px;'
            f'font-weight:700;color:{C["dim"]};letter-spacing:.1em;'
            f'text-transform:uppercase">Recent Chats</div>',
            unsafe_allow_html=True,
        )

        sessions_list, _ = client.get_sessions()
        if sessions_list:
            for s in sessions_list[:10]:
                sid = s.get("session_id", "")
                label = sid[:22] + "…" if len(sid) > 22 else sid
                msgs = s.get("message_count", 0)
                is_active = sid == session_id
                if is_active:
                    st.markdown(
                        f'<div style="background:{C["accent"]};border-radius:8px;'
                        f'padding:10px 12px;margin:2px 4px;cursor:pointer;'
                        f'display:flex;align-items:center;gap:8px">'
                        f'<span style="font-size:13px">💬</span>'
                        f'<div><div style="color:#fff;font-size:13px;font-weight:600">'
                        f'{label}</div>'
                        f'<div style="color:rgba(255,255,255,.7);font-size:11px">'
                        f'{msgs} messages</div></div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    if st.button(f"💬 {label}", key=f"sess_{sid[:16]}", use_container_width=True):
                        st.session_state["chat_session_id"] = sid
                        # Load history
                        hist, _ = client.get_chat_history(sid)
                        if hist:
                            st.session_state["chat_messages"] = hist.get("messages", [])
                        st.rerun()
        else:
            st.markdown(
                f'<p style="color:{C["dim"]};font-size:13px;padding:8px">No sessions yet</p>',
                unsafe_allow_html=True,
            )

        # Back to nav
        st.markdown(f'<div style="height:24px;border-top:1px solid{C["border"]};margin-top:16px"></div>', unsafe_allow_html=True)
        if st.button("← Back to Nav", key="chat_back", use_container_width=True):
            st.session_state["current_page"] = "dashboard"
            st.rerun()

    # ── Main chat area ──────────────────────────────────────
    # Top bar
    top_l, top_r = st.columns([2, 1])
    with top_l:
        st.markdown(
            f'<div style="padding:4px 0 20px">'
            f'<span style="color:{C["muted"]};font-size:13px">Currently chatting in session: </span>'
            f'<span style="color:{C["text"]};font-size:13px;font-weight:600">'
            f'{session_id[:30]}…</span></div>',
            unsafe_allow_html=True,
        )
    with top_r:
        if st.button("🗑️  Clear History", key="clear_hist"):
            ok, err = client.clear_history(session_id)
            if ok:
                st.session_state["chat_messages"] = []
                st.toast("History cleared", icon="✅")
                st.rerun()
            else:
                st.toast(f"Error: {err}", icon="❌")

    # ── Message display ─────────────────────────────────────
    messages = st.session_state.get("chat_messages", [])
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        sources = msg.get("sources") or []
        with st.chat_message(role):
            st.markdown(content)
            if role == "assistant" and sources:
                with st.expander(f"📎 {len(sources)} Relevant Sources Found", expanded=False):
                    src_cols = st.columns(min(len(sources), 3))
                    for i, src in enumerate(sources):
                        with src_cols[i % 3]:
                            fname = src.get("filename", "Source")
                            page = src.get("page", 0)
                            icon_e, _ = _file_icon(fname)
                            st.markdown(
                                f"""<div style="background:{C["sidebar"]};border:1px solid{C["border"]};
border-radius:8px;padding:10px 12px">
  <span style="font-size:18px">{icon_e}</span>
  <div style="font-size:13px;font-weight:600;color:{C["text"]};margin-top:4px">{fname}</div>
  <div style="font-size:11px;color:{C["muted"]}">Page {page}</div>
</div>""",
                                unsafe_allow_html=True,
                            )

    # ── Input ────────────────────────────────────────────────
    st.markdown(
        f'<div style="padding-top:8px;padding-bottom:4px">'
        f'<div style="border-top:1px solid{C["border"]};margin-bottom:12px"></div></div>',
        unsafe_allow_html=True,
    )

    question = st.chat_input("Ask anything about your documents…")

    if question:
        # Add user message to state immediately
        st.session_state["chat_messages"].append({"role": "user", "content": question})

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                result, err = client.chat_query(session_id, question)

            if err:
                answer = f"Sorry, I encountered an error: {err}"
                sources: list = []
                st.error(answer)
            else:
                answer = result.get("answer", "")
                sources = result.get("sources", [])
                st.markdown(answer)

                if sources:
                    with st.expander(f"📎 {len(sources)} Relevant Sources Found", expanded=True):
                        src_cols = st.columns(min(len(sources), 3))
                        for i, src in enumerate(sources):
                            with src_cols[i % 3]:
                                fname = src.get("filename", "Source")
                                page = src.get("page", 0)
                                icon_e, _ = _file_icon(fname)
                                st.markdown(
                                    f"""<div style="background:{C["sidebar"]};border:1px solid{C["border"]};
border-radius:8px;padding:10px 12px">
  <span style="font-size:18px">{icon_e}</span>
  <div style="font-size:13px;font-weight:600;color:{C["text"]};margin-top:4px">{fname}</div>
  <div style="font-size:11px;color:{C["muted"]}">Page {page}</div>
</div>""",
                                    unsafe_allow_html=True,
                                )

        # Save assistant message
        st.session_state["chat_messages"].append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
        })

    # Footer
    st.markdown(
        f'<div style="text-align:center;color:{C["dim"]};font-size:11px;margin-top:8px">'
        f'🔒 &nbsp;Gemini 1.5 Flash &nbsp;•&nbsp; Encrypted Chat</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: UPLOAD DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════════

def page_upload(client: APIClient) -> None:
    _page_header(
        "Upload Documents",
        "Ingest your files or URLs to start training your custom AI intelligence.",
    )

    # ── Drop zone ──────────────────────────────────────────
    st.markdown(
        f"""<div style="background:{C["card"]};border:2px dashed{C["border"]};
border-radius:14px;padding:48px;text-align:center;margin-bottom:16px;
transition:border-color .2s">
  <div style="font-size:48px;margin-bottom:16px">📂</div>
  <h3 style="color:{C["text"]};font-size:18px;font-weight:600;margin:0 0 6px">
    Drag & drop files here</h3>
  <p style="color:{C["muted"]};font-size:14px;margin:0 0 20px">
    Support for heavy documents and large spreadsheets</p>
</div>""",
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Browse Files",
        type=["pdf", "docx", "doc", "txt", "csv", "xlsx", "xls", "md"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    # Format badges
    st.markdown(
        f"""<div style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 28px">
{"".join(f'<span style="background:{C["sidebar"]};border:1px solid{C["border"]};color:{C["muted"]};padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600">{ext}</span>'
for ext in ["PDF","DOCX","TXT","MD","CSV","XLSX"])}
</div>""",
        unsafe_allow_html=True,
    )

    # ── URL ingestion ──────────────────────────────────────
    st.markdown(
        f'<h3 style="font-size:16px;font-weight:600;color:{C["text"]};margin-bottom:12px">'
        f'🔗 &nbsp;Ingest from URL</h3>',
        unsafe_allow_html=True,
    )

    url_col, btn_col = st.columns([4, 1], gap="small")
    with url_col:
        url_input = st.text_input(
            "URL", placeholder="🌐  Paste a website URL to ingest…", label_visibility="collapsed", key="url_input"
        )
    with btn_col:
        st.markdown("<div style='padding-top:4px'>", unsafe_allow_html=True)
        url_btn = st.button("Add URL", key="add_url_btn", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if url_btn:
        if not url_input or not url_input.startswith("http"):
            st.error("Please enter a valid URL starting with http:// or https://")
        else:
            with st.spinner("Ingesting URL…"):
                data, err = client.upload_url(url_input)
            if err:
                st.error(f"URL ingestion failed: {err}")
            else:
                st.success(f"URL queued for processing — doc_id: `{data.get('doc_id','')}`")
                if "upload_queue" not in st.session_state:
                    st.session_state["upload_queue"] = []
                st.session_state["upload_queue"].append({
                    "name": url_input[:50],
                    "doc_id": data.get("doc_id", ""),
                    "status": data.get("status", "processing"),
                })

    # ── Upload queue ────────────────────────────────────────
    if uploaded_files:
        st.markdown(
            f'<h3 style="font-size:16px;font-weight:600;color:{C["text"]};'
            f'margin:28px 0 12px">Upload Queue '
            f'<span style="background:{C["accent"]};color:#fff;padding:2px 10px;'
            f'border-radius:12px;font-size:12px">{len(uploaded_files)} files</span></h3>',
            unsafe_allow_html=True,
        )

        prog = st.progress(0)
        for idx, f in enumerate(uploaded_files):
            icon_e, _ = _file_icon(f.name)
            prog.progress((idx + 1) / len(uploaded_files))

            col_icon, col_info, col_status = st.columns([0.4, 3, 1.5], gap="small")
            with col_icon:
                st.markdown(f'<div style="font-size:28px;padding-top:8px">{icon_e}</div>', unsafe_allow_html=True)
            with col_info:
                st.markdown(
                    f'<div style="padding:8px 0">'
                    f'<div style="font-weight:600;font-size:14px;color:{C["text"]}">{f.name}</div>'
                    f'<div style="font-size:12px;color:{C["muted"]}">{f.size/1024:.1f} KB</div></div>',
                    unsafe_allow_html=True,
                )
            with col_status:
                if st.button("Upload", key=f"upload_btn_{idx}_{f.name}", use_container_width=True):
                    with st.spinner(f"Uploading {f.name}…"):
                        data, err = client.upload_file(f.read(), f.name)
                    if err:
                        st.error(f"{f.name}: {err}")
                    else:
                        st.success(f"{f.name} → queued for processing")

            st.markdown(
                f'<div style="height:1px;background:{C["border"]};margin:4px 0"></div>',
                unsafe_allow_html=True,
            )

        prog.progress(1.0)

    # ── Saved queue history ─────────────────────────────────
    queue = st.session_state.get("upload_queue", [])
    if queue:
        st.markdown(_section_header("Recent Uploads"), unsafe_allow_html=True)
        for item in reversed(queue[-8:]):
            status = item.get("status", "processing")
            status_html = _badge(status, status)
            icon_e, _ = _file_icon(item.get("name", ""))
            st.markdown(
                f"""<div style="background:{C["card"]};border:1px solid{C["border"]};
border-radius:10px;padding:12px 16px;margin-bottom:6px;
display:flex;align-items:center;justify-content:space-between">
  <div style="display:flex;align-items:center;gap:10px">
    <span style="font-size:20px">{icon_e}</span>
    <span style="font-size:13px;font-weight:500;color:{C["text"]}">{item.get("name","")}</span>
  </div>
  {status_html}
</div>""",
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MY DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════════

def page_my_documents(client: APIClient) -> None:
    # Header with search + upload button
    top_l, top_r = st.columns([3, 1], gap="small")
    with top_l:
        docs_raw, err = client.get_documents()
        docs_raw = docs_raw or []
        count_badge = (
            f'<span style="background:{C["accent"]};color:#fff;padding:2px 10px;'
            f'border-radius:12px;font-size:13px;vertical-align:middle;'
            f'margin-left:8px">{len(docs_raw)}</span>'
        )
        st.markdown(
            f'<h1 style="font-size:26px;font-weight:700;color:{C["text"]};'
            f'margin-bottom:0">My Documents{count_badge}</h1>',
            unsafe_allow_html=True,
        )
    with top_r:
        if st.button("⬆️  Upload", key="nav_to_upload", use_container_width=True):
            st.session_state["current_page"] = "upload"
            st.rerun()

    # Search bar
    search_query = st.text_input(
        "Search", placeholder="🔍  Search your knowledge base…",
        label_visibility="collapsed", key="doc_search"
    )

    # ── Filter tabs ─────────────────────────────────────────
    filter_opts = ["All", "Ready", "Processing", "Failed"]
    selected_filter = st.radio(
        "filter", filter_opts, horizontal=True, label_visibility="collapsed", key="doc_filter"
    )

    # Apply filters
    docs = [
        d for d in docs_raw
        if (selected_filter == "All" or d.get("status", "").lower() == selected_filter.lower())
        and (not search_query or search_query.lower() in d.get("filename", "").lower())
    ]

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    if not docs:
        if err:
            st.error(f"Could not load documents: {err}")
        else:
            _empty_state("No documents found. Upload your first document!", "📄")
        return

    # ── Grid: 3 columns ─────────────────────────────────────
    cols_per_row = 3
    for row_start in range(0, len(docs), cols_per_row):
        row_docs = docs[row_start: row_start + cols_per_row]
        grid_cols = st.columns(cols_per_row, gap="small")
        for col_idx, doc in enumerate(row_docs):
            with grid_cols[col_idx]:
                _doc_card(client, doc)

    # Padding
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)


def _doc_card(client: APIClient, doc: dict) -> None:
    fname = doc.get("filename", "Unknown")
    status = doc.get("status", "unknown").lower()
    chunk_count = doc.get("chunk_count", 0)
    created = str(doc.get("created_at", ""))[:10]
    doc_id = doc.get("id", "")
    icon_e, icon_color = _file_icon(fname)

    status_colors = {
        "ready":      (C["success"],  "rgba(34,197,94,.15)"),
        "processing": (C["warning"],  "rgba(245,158,11,.15)"),
        "failed":     (C["danger"],   "rgba(239,68,68,.15)"),
    }
    s_fg, s_bg = status_colors.get(status, (C["muted"], C["sidebar"]))

    st.markdown(
        f"""<div style="background:{C["card"]};border:1px solid{C["border"]};
border-radius:12px;padding:18px;margin-bottom:12px;
transition:border-color .2s;min-height:160px">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;
       margin-bottom:12px">
    <span style="font-size:32px">{icon_e}</span>
    <span style="background:{s_bg};color:{s_fg};padding:3px 10px;border-radius:20px;
         font-size:10px;font-weight:700;letter-spacing:.05em;text-transform:uppercase">
      {status}</span>
  </div>
  <div style="font-weight:600;font-size:14px;color:{C["text"]};margin-bottom:4px;
       white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{fname}</div>
  <div style="font-size:12px;color:{C["muted"]}">{created} &bull; {chunk_count} chunks</div>
</div>""",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2, gap="small")
    with col_a:
        if st.button("📊 Status", key=f"status_{doc_id}", use_container_width=True):
            with st.spinner("Checking…"):
                s_data, s_err = client.get_doc_status(doc_id)
            if s_data:
                st.info(f"Status: **{s_data.get('status')}** | Chunks: **{s_data.get('chunk_count')}**")
            else:
                st.error(s_err)
    with col_b:
        if st.button("🗑️ Delete", key=f"del_{doc_id}", use_container_width=True):
            ok, d_err = client.delete_document(doc_id)
            if ok:
                st.toast(f"{fname} deleted", icon="✅")
                st.rerun()
            else:
                st.error(d_err)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ADMIN PANEL
# ══════════════════════════════════════════════════════════════════════════════

def page_admin(client: APIClient) -> None:
    user = st.session_state.get("user", {})
    if user.get("role") != "admin":
        st.error("Access denied. Admin privileges required.")
        return

    # Header
    hdr_l, hdr_r = st.columns([2, 1])
    with hdr_l:
        _page_header("Admin Control Panel", "Manage users and monitor system performance.")
    with hdr_r:
        st.markdown(
            f'<div style="text-align:right;padding-top:12px">'
            f'<span style="background:{C["accent"]};color:#fff;padding:8px 18px;'
            f'border-radius:8px;font-size:14px;font-weight:600;cursor:pointer">'
            f'+ Invite User</span></div>',
            unsafe_allow_html=True,
        )

    # ── Stat cards ─────────────────────────────────────────
    stats, s_err = client.admin_stats()
    stats = stats or {}
    total_users = stats.get("total_users", "—")
    total_docs  = stats.get("total_documents", "—")
    queries_today = stats.get("queries_today", "—")

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.markdown(_stat_card("Total Users", str(total_users), "👥", "+12% ↑"), unsafe_allow_html=True)
    with c2:
        st.markdown(_stat_card("Total Docs", str(total_docs), "📄", "+5% ↑"), unsafe_allow_html=True)
    with c3:
        st.markdown(_stat_card("Queries Today", str(queries_today), "🔍"), unsafe_allow_html=True)
    with c4:
        st.markdown(_stat_card("Active Users", "—", "⚡"), unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Filters bar ─────────────────────────────────────────
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1, 1, 1], gap="small")
    with f_col1:
        search_user = st.text_input(
            "s", placeholder="🔍  Search by name or email…",
            label_visibility="collapsed", key="admin_search"
        )
    with f_col2:
        role_filter = st.selectbox("Role", ["All Roles", "admin", "user"],
                                   label_visibility="collapsed", key="admin_role")
    with f_col3:
        status_filter = st.selectbox("Status", ["Status: All", "Active", "Inactive"],
                                     label_visibility="collapsed", key="admin_status")
    with f_col4:
        if st.button("⬇️ Export", key="admin_export", use_container_width=True):
            st.info("Export feature coming soon.")

    # ── User management table ───────────────────────────────
    st.markdown(_section_header("User Management"), unsafe_allow_html=True)

    users, u_err = client.admin_users()
    if u_err and not users:
        st.error(f"Could not load users: {u_err}")
        return

    users = users or []

    # Apply filters
    if role_filter != "All Roles":
        users = [u for u in users if u.get("role") == role_filter]
    if status_filter == "Active":
        users = [u for u in users if u.get("is_active")]
    elif status_filter == "Inactive":
        users = [u for u in users if not u.get("is_active")]
    if search_user:
        sq = search_user.lower()
        users = [u for u in users if sq in u.get("username","").lower() or sq in u.get("email","").lower()]

    if not users:
        _empty_state("No users match the current filters.", "👥")
        return

    # Table header
    st.markdown(
        f"""<div style="background:{C["sidebar"]};border:1px solid{C["border"]};
border-radius:12px 12px 0 0;padding:12px 16px;
display:grid;grid-template-columns:2fr 2fr 1fr 0.7fr 0.7fr 1fr 0.8fr 1.2fr;
gap:8px;margin-bottom:0">
{"".join(f'<span style="font-size:11px;font-weight:700;color:{C["muted"]};text-transform:uppercase;letter-spacing:.08em">{col}</span>' for col in ["USER","EMAIL","ROLE","DOCS","QUERIES","LAST LOGIN","STATUS","ACTION"])}
</div>""",
        unsafe_allow_html=True,
    )

    for i, u in enumerate(users):
        uid = u.get("id", "")
        uname = u.get("username", "")
        email = u.get("email", "")
        role  = u.get("role", "user")
        is_active = u.get("is_active", True)
        doc_count = u.get("doc_count", 0)
        initial = uname[0].upper() if uname else "U"

        role_badge_html   = _badge(role, role)
        status_badge_html = _badge("Active" if is_active else "Inactive", "active" if is_active else "inactive")
        action_color = C["danger"] if is_active else C["success"]
        action_label = "Deactivate" if is_active else "Activate"

        row_bg = C["card"] if i % 2 == 0 else C["sidebar"]
        border_r = "" if i < len(users) - 1 else "border-radius:0 0 12px 12px"

        st.markdown(
            f"""<div style="background:{row_bg};border:1px solid{C["border"]};
border-top:none;padding:14px 16px;
display:grid;grid-template-columns:2fr 2fr 1fr 0.7fr 0.7fr 1fr 0.8fr 1.2fr;
gap:8px;align-items:center;{border_r}">
  <div style="display:flex;align-items:center;gap:8px">
    <div style="width:28px;height:28px;background:linear-gradient(135deg,#3B82F6,#6366F1);
         border-radius:50%;display:flex;align-items:center;justify-content:center;
         color:#fff;font-size:11px;font-weight:700;flex-shrink:0">{initial}</div>
    <span style="font-size:13px;font-weight:600;color:{C["text"]}">{uname}</span>
  </div>
  <span style="font-size:13px;color:{C["muted"]}">{email}</span>
  {role_badge_html}
  <span style="font-size:13px;color:{C["text"]};text-align:center">{doc_count}</span>
  <span style="font-size:13px;color:{C["text"]};text-align:center">—</span>
  <span style="font-size:12px;color:{C["muted"]}">—</span>
  {status_badge_html}
  <div></div>
</div>""",
            unsafe_allow_html=True,
        )

        # Action button in separate row
        _, _, _, _, _, _, _, act_col = st.columns([2, 2, 1, 0.7, 0.7, 1, 0.8, 1.2], gap="small")
        with act_col:
            if is_active:
                if st.button(
                    f"Deactivate", key=f"deact_{uid}", use_container_width=True
                ):
                    ok, d_err = client.admin_deactivate(uid)
                    if ok:
                        st.toast(f"{uname} deactivated", icon="✅")
                        st.rerun()
                    else:
                        st.error(d_err)

    # Pagination hint
    st.markdown(
        f'<p style="color:{C["dim"]};font-size:12px;text-align:center;margin-top:12px">'
        f'Showing {len(users)} of {len(users)} users</p>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    st.set_page_config(
        page_title="DocuMind AI",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="auto",
        menu_items={
            "Get Help": None,
            "Report a bug": None,
            "About": "DocuMind AI — Powered by Gemini + ChromaDB",
        },
    )

    inject_css()

    # Initialise default session keys
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("current_page", "login")
    st.session_state.setdefault("chat_messages", [])

    client = get_client()
    is_auth: bool = st.session_state.get("authenticated", False)

    if not is_auth:
        page_login(client)
        return

    # ── Authenticated — render sidebar + route ──────────────
    if st.session_state.get("current_page") == "chat":
        # Chat has its own sidebar, so render page first
        page_chat(client)
    else:
        render_sidebar(client)
        page = st.session_state.get("current_page", "dashboard")
        routing = {
            "dashboard":    page_dashboard,
            "upload":       page_upload,
            "my_documents": page_my_documents,
            "admin":        page_admin,
        }
        routing.get(page, page_dashboard)(client)


if __name__ == "__main__":
    main()
