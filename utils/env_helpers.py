"""Environment detection helpers for dual-mode operation (Streamlit + Desktop)."""
import os

# Streamlit sets this environment variable when running
IS_STREAMLIT = "STREAMLIT_SERVER_RUNNING" in os.environ
