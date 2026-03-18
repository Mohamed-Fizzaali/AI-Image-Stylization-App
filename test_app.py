import sys
from unittest.mock import MagicMock

# Mock streamlit to prevent NoSessionContext on global execution
import streamlit as st
st.switch_page = MagicMock()
st.rerun = MagicMock()
st.error = MagicMock()

def test_app_import():
    try:
        import frontend.app
        assert True
    except Exception as e:
        import traceback
        traceback.print_exc()
        assert False, f"Failed to import app: {e}"
