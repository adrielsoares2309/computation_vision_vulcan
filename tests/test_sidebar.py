from pathlib import Path

from streamlit.testing.v1 import AppTest

from frontend.components import sidebar


def test_sidebar_status_controls_render_without_exceptions(monkeypatch):
    monkeypatch.setattr(sidebar, "fetch_system_status", lambda: {"api_online": False})
    app = AppTest.from_string(
        "from frontend.components.sidebar import render_sidebar\nrender_sidebar()"
    ).run()

    assert not app.exception
    assert len(app.sidebar.toggle) == 1
    assert app.sidebar.toggle[0].value is False
    assert len(app.sidebar.markdown) >= 2


def test_application_initializes_with_native_navigation():
    entrypoint = Path(__file__).resolve().parents[1] / "frontend" / "app.py"
    app = AppTest.from_file(entrypoint, default_timeout=30).run()

    assert not app.exception
    assert "Dashboard Geral" in sidebar.MENU_OPTIONS
    assert len(sidebar.MENU_OPTIONS) == 9
    assert len(app.sidebar.toggle) == 1


def test_all_registered_pages_match_expected_navigation_items():
    source = (Path(__file__).resolve().parents[1] / "frontend" / "app.py").read_text(encoding="utf-8")
    assert "selected = render_sidebar()" in source
    assert "pages.get(selected, render_dashboard)" in source
    for title in sidebar.MENU_OPTIONS:
        assert f'"{title}"' in source


def test_sidebar_css_does_not_override_collapse_width_or_use_iframe():
    css = (Path(__file__).resolve().parents[1] / "frontend" / "styles.py").read_text(encoding="utf-8")
    sidebar_css = css.split("/* ── Barra Lateral (Sidebar) Padrão AeroMotion", 1)[1]
    sidebar_css = sidebar_css.split("/* Cabeçalho Operacional Compacto", 1)[0]

    assert "background-color: #FFFFFF !important;" in sidebar_css
    assert "color: #102A43 !important;" in sidebar_css
    assert "stSidebar] iframe" not in sidebar_css
    assert '[data-testid="stToolbar"], #MainMenu, footer' not in css
