"""Testes de interface Streamlit (AppTest) para validação integral da Sidebar e das 9 páginas industriais."""

from __future__ import annotations

from pathlib import Path
from streamlit.testing.v1 import AppTest

from frontend.components.sidebar import MENU_OPTIONS

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = str(ROOT / "frontend" / "app.py")


def test_sidebar_renders_all_controls_and_navigates_all_nine_pages():
    """Garante que a sidebar renderiza todos os controles e navega pelas 9 páginas sem erros."""
    at = AppTest.from_file(APP_PATH, default_timeout=25)
    at.run()

    assert len(at.exception) == 0, f"Exceções na carga inicial: {at.exception}"
    assert len(at.error) == 0, f"Erros na carga inicial: {at.error}"
    assert len(at.sidebar.radio) == 1
    assert list(at.sidebar.radio[0].options) == MENU_OPTIONS
    assert len(at.sidebar.selectbox) == 2
    assert len(at.sidebar.button) == 6
    assert len(at.sidebar.toggle) == 1

    # Testa navegação sequencial por todas as 9 páginas industriais
    for page_name in MENU_OPTIONS:
        at.sidebar.radio[0].set_value(page_name).run()
        assert len(at.exception) == 0, f"Exceção na página {page_name}: {at.exception}"
        assert len(at.error) == 0, f"Erro na página {page_name}: {at.error}"
        assert at.session_state["vt_nav_menu"] == page_name
        assert at.sidebar.radio[0].value == page_name


def test_sidebar_filters_and_regime_buttons_persist_state():
    """Garante que os filtros de célula/liga e botões de regime na sidebar funcionam e persistem."""
    at = AppTest.from_file(APP_PATH, default_timeout=25)
    at.run()

    # Seleciona célula CEL-203 e liga Liga_Titanio_Ti6Al4V
    at.sidebar.selectbox[0].set_value("CEL-203").run()
    assert at.session_state["selected_cell"] == "CEL-203"

    at.sidebar.selectbox[1].set_value("Liga_Titanio_Ti6Al4V").run()
    assert at.session_state["selected_alloy"] == "Liga_Titanio_Ti6Al4V"

    # Aciona botão de regime Usinagem Pesada
    at.sidebar.button[1].click().run()
    assert at.session_state["regime_selecionado"] == "Usinagem_Pesada"
    assert len(at.exception) == 0


def test_standalone_page_files_render_complete_sidebar_and_content():
    """Garante que acessar diretamente qualquer arquivo em frontend/pages/ não gera tela em branco."""
    for page_file in [
        "frontend/pages/dashboard.py",
        "frontend/pages/oee.py",
        "frontend/pages/vision.py",
    ]:
        at = AppTest.from_file(str(ROOT / page_file), default_timeout=20)
        at.run()
        assert len(at.exception) == 0, f"Exceção em {page_file}: {at.exception}"
        assert len(at.sidebar.radio) == 1, f"Sidebar ausente em {page_file}"
        assert len(at.main) > 0, f"Conteúdo principal vazio em {page_file}"
