## 2026-03-18 - Missing Image Fallback & Dependency Fix
**Learning:** Missing watermark images can crash OpenCV `cv2.imread` if not explicitly verified with `Path.exists()`, or lead to unexpected behavior later down the pipeline. Streamlit global imports often trigger `NoSessionContext` when called programmatically outside a server.
**Action:** When validating image loading via OpenCV, explicitly verify file presence. And always mock `st.switch_page` and similar context-dependent streamlite methods when running tests or validations outside the web server wrapper.
