import streamlit as st
import asyncio
import time
import pathlib
import uuid
import threading
import http.server
import socketserver
import shutil
import sys

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from agents.graph import run_agent_async, RateLimitError
from agents.tools import set_project_root

# ─── Page Config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Vibe Code AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Clean CSS — minimal, no heavy animations ───────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    * { font-family: 'Inter', sans-serif !important; }

    .stApp { background: #0e0e1a; }

    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* ── Hero ─────────────────────────────────────── */
    .hero-container {
        text-align: center;
        padding: 3rem 1rem 1.5rem 1rem;
    }
    .hero-badge {
        display: inline-block;
        padding: 5px 14px;
        background: rgba(124, 58, 237, 0.12);
        border: 1px solid rgba(124, 58, 237, 0.25);
        border-radius: 50px;
        font-size: 0.72rem;
        font-weight: 600;
        color: #a78bfa;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }
    .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        color: #f1f5f9;
        line-height: 1.2;
        margin-bottom: 0.6rem;
    }
    .hero-subtitle {
        font-size: 1rem;
        color: #64748b;
        max-width: 520px;
        margin: 0 auto 1.5rem auto;
        line-height: 1.5;
    }

    /* ── Text area ────────────────────────────────── */
    .stTextArea textarea {
        background: #161625 !important;
        border: 1px solid #2a2a40 !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        font-size: 0.95rem !important;
        padding: 1rem !important;
    }
    .stTextArea textarea:focus {
        border-color: #7c3aed !important;
        box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.12) !important;
    }
    .stTextArea textarea::placeholder { color: #475569 !important; }

    /* ── Buttons ──────────────────────────────────── */
    .stButton > button {
        background: #7c3aed !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 2rem !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
    }
    .stButton > button:hover {
        background: #6d28d9 !important;
    }

    /* ── Progress ─────────────────────────────────── */
    .progress-card {
        background: #161625;
        border: 1px solid #2a2a40;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 1rem 0;
    }
    .step-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 0;
        border-bottom: 1px solid #1e1e30;
    }
    .step-row:last-child { border-bottom: none; }
    .step-icon {
        width: 34px; height: 34px;
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1rem; flex-shrink: 0;
    }
    .step-pending { background: #1e1e30; border: 1px solid #2a2a40; }
    .step-active  { background: rgba(124,58,237,0.15); border: 1px solid rgba(124,58,237,0.3); }
    .step-done    { background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.2); }
    .step-label   { font-size: 0.9rem; font-weight: 600; color: #e2e8f0; }
    .step-sub     { font-size: 0.75rem; color: #475569; margin-top: 2px; }

    /* ── Preview chrome ──────────────────────────── */
    .preview-bar {
        display: flex; align-items: center; gap: 8px;
        padding: 10px 16px;
        background: #161625;
        border: 1px solid #2a2a40;
        border-radius: 12px 12px 0 0;
        border-bottom: none;
    }
    .dot { width: 10px; height: 10px; border-radius: 50%; }
    .dot-r { background: #ef4444; }
    .dot-y { background: #eab308; }
    .dot-g { background: #22c55e; }
    .url-bar {
        flex: 1; margin: 0 10px;
        padding: 4px 12px;
        background: #0e0e1a;
        border: 1px solid #2a2a40;
        border-radius: 6px;
        color: #475569;
        font-size: 0.72rem;
        font-family: 'Consolas', monospace !important;
    }
    .preview-wrap {
        border: 1px solid #2a2a40;
        border-radius: 0 0 12px 12px;
        overflow: hidden;
        background: #fff;
    }

    /* ── Divider ──────────────────────────────────── */
    .divider {
        height: 1px;
        background: #1e1e30;
        margin: 1.5rem 0;
    }

    /* ── Tabs ─────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; background: #161625;
        border-radius: 10px; padding: 4px 6px;
        border: 1px solid #2a2a40;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px; color: #94a3b8; font-weight: 600;
        padding: 8px 18px !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(124,58,237,0.15) !important;
        color: #a78bfa !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Session State ───────────────────────────────────────────────────────────────
if "projects" not in st.session_state:
    st.session_state.projects = []
if "current_project" not in st.session_state:
    st.session_state.current_project = None
if "generating" not in st.session_state:
    st.session_state.generating = False
if "error" not in st.session_state:
    st.session_state.error = None
if "preview_port" not in st.session_state:
    st.session_state.preview_port = None


# ─── Helpers ─────────────────────────────────────────────────────────────────────
PROJECTS_BASE = pathlib.Path(__file__).parent / "generated_projects"


def get_project_dir(project_id: str) -> pathlib.Path:
    d = PROJECTS_BASE / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def delete_all_projects():
    """Remove every generated project from disk."""
    if PROJECTS_BASE.exists():
        shutil.rmtree(PROJECTS_BASE, ignore_errors=True)


def start_preview_server(directory: str, port: int = 8502):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=directory, **kw)
        def log_message(self, *_):
            pass

    try:
        httpd = socketserver.TCPServer(("", port), Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        return port
    except OSError:
        return start_preview_server(directory, port + 1)


def run_async_agent(prompt: str, project_dir: str, on_progress=None):
    """Bridge: run the async agent from sync Streamlit context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            run_agent_async(prompt, project_dir, on_progress)
        )
    finally:
        loop.close()


# ─── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;padding:1rem 0 0.5rem 0;">
        <span style="font-size:1.5rem;">⚡</span>
        <span style="font-size:1.1rem;font-weight:800;color:#f1f5f9;">Vibe Code AI</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown("""
    <p style="font-size:0.7rem;font-weight:700;color:#475569;
              text-transform:uppercase;letter-spacing:1.2px;margin-bottom:0.5rem;">
        📁 Recent Projects
    </p>
    """, unsafe_allow_html=True)

    if st.session_state.projects:
        for proj in reversed(st.session_state.projects):
            label = proj["name"][:30] + ("…" if len(proj["name"]) > 30 else "")
            if st.button(f"🔮 {label}", key=f"hist_{proj['id']}", use_container_width=True):
                st.session_state.current_project = proj
                st.session_state.error = None
                st.rerun()
    else:
        st.markdown("""
        <div style="text-align:center;padding:1.5rem 0;color:#475569;font-size:0.8rem;">
            No projects yet
        </div>
        """, unsafe_allow_html=True)


# ─── Main: Project View ─────────────────────────────────────────────────────────
if st.session_state.current_project and not st.session_state.generating:
    proj = st.session_state.current_project

    # Top bar — project name + New Project button
    top1, top2 = st.columns([4, 1])
    with top1:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding-top:0.5rem;">
            <span style="font-size:1.3rem;">🚀</span>
            <span style="font-size:1.15rem;font-weight:700;color:#e2e8f0;">{proj['name']}</span>
        </div>
        <p style="color:#475569;font-size:0.8rem;margin-top:4px;">
            {proj['prompt'][:100]}{'…' if len(proj['prompt'])>100 else ''}
        </p>
        """, unsafe_allow_html=True)
    with top2:
        if st.button("✨ New Project", use_container_width=True, key="new_proj_top"):
            # Delete existing projects from disk
            delete_all_projects()
            st.session_state.projects = []
            st.session_state.current_project = None
            st.session_state.preview_port = None
            st.session_state.error = None
            st.rerun()

    tab_preview, tab_code = st.tabs(["👁️ Preview", "📄 Source Code"])

    with tab_preview:
        port = proj.get("port", st.session_state.preview_port)
        url_text = f"http://localhost:{port}" if port else "localhost"

        st.markdown(f"""
        <div class="preview-bar">
            <div class="dot dot-r"></div>
            <div class="dot dot-y"></div>
            <div class="dot dot-g"></div>
            <div class="url-bar">🔒 {url_text}</div>
        </div>
        <div class="preview-wrap">
        """, unsafe_allow_html=True)

        # Render preview — use st.html (inline) for the generated content
        st.components.v1.html(proj["html"], height=600, scrolling=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with tab_code:
        st.code(proj["html"], language="html", line_numbers=True)

    # Download
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 3])
    with c1:
        st.download_button("⬇️ Download", data=proj["html"],
                           file_name="index.html", mime="text/html",
                           use_container_width=True)
    with c2:
        if port:
            st.markdown(f"""
            <a href="{url_text}" target="_blank"
               style="display:block;padding:0.55rem 0;text-align:center;
                      background:#161625;border:1px solid #2a2a40;border-radius:10px;
                      color:#a78bfa;text-decoration:none;font-weight:600;font-size:0.85rem;">
                🌐 Open in Browser
            </a>
            """, unsafe_allow_html=True)


# ─── Main: Landing / Input ───────────────────────────────────────────────────────
else:
    st.markdown("""
    <div class="hero-container">
        <div class="hero-badge">⚡ AI-Powered</div>
        <h1 class="hero-title">Build Apps with a Prompt</h1>
        <p class="hero-subtitle">
            Describe your idea and the AI will plan, architect, and code a working web app for you.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Prompt input — centered
    _, col_mid, _ = st.columns([1, 3, 1])
    with col_mid:
        user_prompt = st.text_area(
            label="prompt",
            label_visibility="collapsed",
            placeholder="Describe your app… e.g. 'Create a habit tracker with streaks'",
            height=110,
            key="prompt_input",
        )

        _, btn_col, _ = st.columns([1, 1, 1])
        with btn_col:
            generate_clicked = st.button(
                "⚡ Generate App",
                use_container_width=True,
                disabled=st.session_state.generating,
            )

    # ── Generation flow ──
    if generate_clicked and user_prompt and user_prompt.strip():
        st.session_state.generating = True
        st.session_state.error = None

        project_id = str(uuid.uuid4())[:8]
        project_dir = get_project_dir(project_id)

        _, prog_col, _ = st.columns([1, 3, 1])
        with prog_col:
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

            steps = [
                ("🧠", "Planning", "Analysing requirements…"),
                ("🏗️", "Architecting", "Designing structure…"),
                ("💻", "Coding", "Generating code…"),
            ]
            status_ph = st.empty()

            def render_progress(active_idx):
                parts = ['<div class="progress-card">']
                for i, (icon, label, sub) in enumerate(steps):
                    if i < active_idx:
                        cls, ic = "step-done", "✅"
                    elif i == active_idx:
                        cls, ic = "step-active", "⏳"
                    else:
                        cls, ic = "step-pending", icon
                    parts.append(f"""
                    <div class="step-row">
                        <div class="step-icon {cls}">{ic}</div>
                        <div>
                            <div class="step-label">{label}</div>
                            <div class="step-sub">{sub if i <= active_idx else 'Waiting…'}</div>
                        </div>
                    </div>""")
                parts.append("</div>")
                status_ph.markdown("".join(parts), unsafe_allow_html=True)

            render_progress(0)

            try:
                progress = {"idx": 0}

                def on_progress(stage, _data):
                    if stage == "planner":
                        progress["idx"] = 1
                        render_progress(1)
                    elif stage == "architect":
                        progress["idx"] = 2
                        render_progress(2)
                    elif stage == "coder":
                        progress["idx"] = 3
                        render_progress(3)

                result = run_async_agent(
                    prompt=user_prompt.strip(),
                    project_dir=str(project_dir),
                    on_progress=on_progress,
                )

                # Read generated HTML
                html_path = project_dir / "index.html"
                html = ""
                if html_path.exists():
                    html = html_path.read_text(encoding="utf-8")
                elif "generated_html" in result:
                    html = result["generated_html"]

                if not html:
                    raise ValueError("No HTML was generated")

                render_progress(3)

                plan_name = user_prompt.strip()[:50]
                if "plan" in result and hasattr(result["plan"], "name"):
                    plan_name = result["plan"].name

                port = start_preview_server(str(project_dir))
                st.session_state.preview_port = port

                project_data = {
                    "id": project_id,
                    "name": plan_name,
                    "prompt": user_prompt.strip(),
                    "html": html,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M"),
                    "dir": str(project_dir),
                    "port": port,
                }

                st.session_state.projects.append(project_data)
                st.session_state.current_project = project_data
                st.session_state.generating = False
                time.sleep(0.5)
                st.rerun()

            except RateLimitError as e:
                st.session_state.generating = False
                st.session_state.error = str(e)
                st.warning(f"🚦 {e}")

            except Exception as e:
                st.session_state.generating = False
                st.session_state.error = str(e)
                st.error(f"❌ Generation failed: {e}")

    elif generate_clicked and (not user_prompt or not user_prompt.strip()):
        st.warning(" Please describe the app you want to build.")

    if st.session_state.error and not st.session_state.generating:
        if "rate limit" in st.session_state.error.lower():
            st.warning(f"🚦 {st.session_state.error}")
        else:
            st.error(f"❌ {st.session_state.error}")
