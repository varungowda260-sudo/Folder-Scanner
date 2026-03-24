import streamlit as st
import zipfile
import tempfile
import os
import re
import pandas as pd

st.set_page_config(page_title="Enterprise File Scanner", layout="wide")

# ---------------- CUSTOM UI ----------------
st.markdown("""
<style>
.big-title {
    font-size: 36px;
    font-weight: 700;
    text-align: center;
    margin-bottom: 10px;
}

.section-title {
    font-size: 22px;
    font-weight: 600;
    margin-top: 20px;
}

.dataframe th {
    font-size: 18px !important;
    font-weight: bold !important;
}

.dataframe td {
    font-size: 16px !important;
}

button {
    font-size: 18px !important;
    padding: 10px 20px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">📂 Enterprise Folder Scanner</div>', unsafe_allow_html=True)

# ---------------- INPUT SECTION ----------------
st.markdown('<div class="section-title">Source File Name(CCF,VSR,CSIR)</div>', unsafe_allow_html=True)
source_input = st.text_area("", height=180)

st.markdown('<div class="section-title">Upload ZIP / Folder Files</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    uploaded_zip = st.file_uploader("Upload ZIP", type=["zip"])

with col2:
    uploaded_files = st.file_uploader("Upload Folder Files", accept_multiple_files=True)

# ---------------- CLEAN ----------------
def clean_name(name):
    name = os.path.splitext(name)[0]
    name = re.sub(r'[_\-]?v\d+$', '', name, flags=re.IGNORECASE)
    return name.strip()

# ---------------- MATCH ----------------
def classify_match(src, tgt):
    src_parts = clean_name(src).split("-")
    tgt_parts = clean_name(tgt).split("-")

    if len(src_parts) < 4 or len(tgt_parts) < 4:
        return "Not Matched", "NO"

    for i in range(4):
        if src_parts[i] != tgt_parts[i]:
            return "Not Matched", "NO"

    if src_parts == tgt_parts:
        return "Exact", "YES"
    return "Close", "YES"

# ---------------- LOAD ----------------
def load_files(zip_file, uploaded_files):
    files = []
    temp_dir = tempfile.mkdtemp()

    if zip_file:
        with zipfile.ZipFile(zip_file, 'r') as z:
            z.extractall(temp_dir)
        for root, _, f in os.walk(temp_dir):
            for file in f:
                files.append(file)

    if uploaded_files:
        for f in uploaded_files:
            files.append(f.name)

    return list(set(files))

# ---------------- SCAN ----------------
def scan(sources, files):
    results = []

    for src in sources:
        match = None
        match_type = "Not Matched"
        flag = "NO"

        for f in files:
            t, fl = classify_match(src, f)

            if t == "Exact":
                match = f
                match_type = t
                flag = fl
                break
            elif t == "Close" and match_type != "Exact":
                match = f
                match_type = t
                flag = fl

        if match:
            results.append([src, flag, match_type, match, "-", "-"])
        else:
            results.append([src, "NO", "Not Matched", "-", src, src])

    return results

# ---------------- RUN ----------------
if st.button("🚀 Run Scan"):
    if not source_input:
        st.warning("Enter source names")
    else:
        sources = [s.strip() for s in source_input.split("\n") if s.strip()]
        files = load_files(uploaded_zip, uploaded_files)

        if not files:
            st.warning("Upload files or ZIP")
        else:
            data = scan(sources, files)

            df = pd.DataFrame(data, columns=[
                "Source File Name",
                "YES/NO",
                "Match Type",
                "Matched Files",
                "Unmatched Files",
                "Difference"
            ])

            st.success("✅ Scan Completed")
            st.dataframe(df, use_container_width=True)

            st.download_button(
                "📥 Export Excel",
                df.to_csv(index=False),
                file_name="report.csv"
            )
