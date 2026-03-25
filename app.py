import streamlit as st
import zipfile
import tempfile
import os
import re
import pandas as pd

st.set_page_config(page_title="Folder Scanner", layout="wide")

# ---------------- UI STYLE ----------------
st.markdown("""
<style>
.title {
    font-size:38px;
    font-weight:800;
    text-align:center;
    margin-bottom:20px;
}
.section {
    font-size:22px;
    font-weight:700;
    margin-top:20px;
}
.dataframe th {
    font-size:18px !important;
    font-weight:800 !important;
    text-align:center !important;
}
.dataframe td {
    font-size:16px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">📂 Folder Scanner</div>', unsafe_allow_html=True)

# ---------------- INPUT ----------------
st.markdown('<div class="section">Source File Name (CCF, VSR, CSIR)</div>', unsafe_allow_html=True)
source_input = st.text_area("", height=200)

st.markdown('<div class="section">Upload Folder / ZIP</div>', unsafe_allow_html=True)
uploaded_zip = st.file_uploader("Upload ZIP", type=["zip"])
uploaded_files = st.file_uploader("Or Upload Files", accept_multiple_files=True)

# ---------------- CLEAN ----------------
def clean_name(name):
    name = os.path.splitext(name)[0]
    name = re.sub(r'[\s_\-\.]*v\d+$', '', name, flags=re.IGNORECASE)
    return name.strip()

# ---------------- NEW: VERSION EXTRACT ----------------
def extract_version(name):
    match = re.search(r'v\d+', name, re.IGNORECASE)
    return match.group().lower() if match else None

# ---------------- SPLIT (ENHANCED ONLY) ----------------
def split_parts(name):
    name = clean_name(name)

    # Normalize ALL special characters
    name = re.sub(r'[^\w]+', ' ', name)

    parts = name.split()

    return [p for p in parts if p]

# ---------------- LOAD FILES ----------------
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

    return files

# ---------------- DIFFERENCE (UNCHANGED) ----------------
def get_difference(src, tgt):
    src_clean = clean_name(src)
    tgt_full = tgt

    tgt_clean = clean_name(tgt_full)
    ext = os.path.splitext(tgt_full)[1]

    if src_clean == tgt_clean:
        return ext if ext else "-"

    src_norm = re.sub(r'[-_\s]+', '', src_clean)
    tgt_norm = re.sub(r'[-_\s]+', '', tgt_clean)

    if tgt_norm.startswith(src_norm):
        idx = len(src_clean)
        suffix = tgt_clean[idx:]
        return suffix + ext if (suffix + ext) else ext

    for i in range(len(src_clean)):
        if tgt_clean.startswith(src_clean[:len(src_clean)-i]):
            suffix = tgt_clean[len(src_clean)-i:]
            return suffix + ext

    return ext if ext else "-"

# ---------------- MATCH LOGIC ----------------
def match_file(src, files):
    src = src.strip()
    src_parts = split_parts(src)
    src_version = extract_version(src)

    best_match = None
    best_score = 0

    for f in files:
        tgt_parts = split_parts(f)
        tgt_version = extract_version(f)

        match_count = 0

        for i in range(min(len(src_parts), len(tgt_parts))):
            if src_parts[i] == tgt_parts[i]:
                match_count += 1
            else:
                break

        # VERSION-AWARE BOOST (SAFE ADDITION)
        if src_version and tgt_version and src_version == tgt_version:
            match_count += 1

        if match_count > best_score:
            best_score = match_count
            best_match = f

    # -------- CLASSIFICATION (MINIMAL EXTENSION) --------
   if best_score >= 4:
    return ["YES", "Exact", best_match, "-", "-"]

elif best_score == 3:
    diff = get_difference(src, best_match)
    return ["YES", "Close", best_match, "-", diff]

elif best_score == 2:
    diff = get_difference(src, best_match)
    return ["YES", "Partial", best_match, "-", diff]

elif best_score == 1:
    diff = get_difference(src, best_match)
    return ["YES", "Partial", best_match, "-", diff]

else:
    return ["NO", "Not Matched", "-", src, src]

# ---------------- RUN ----------------
if st.button("🚀 Run Scan"):

    if not source_input:
        st.warning("Enter source file names")
        st.stop()

    files = load_files(uploaded_zip, uploaded_files)

    if not files:
        st.warning("Upload ZIP or files")
        st.stop()

    sources = [s.strip() for s in source_input.split("\n") if s.strip()]

    progress = st.progress(0)
    total = len(sources)

    results = []

    for i, src in enumerate(sources):
        res = match_file(src, files)
        results.append([src] + res)
        progress.progress((i + 1) / total)

    df = pd.DataFrame(results, columns=[
        "Source File Name",
        "YES/NO",
        "Match Type",
        "Matched Files in Folder",
        "Unmatched Files",
        "Difference"
    ])

    st.success("Scan Completed")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", len(df))
    col2.metric("Exact", len(df[df["Match Type"] == "Exact"]))
    col3.metric("Close", len(df[df["Match Type"] == "Close"]))
    col4.metric("Not Matched", len(df[df["YES/NO"] == "NO"]))

    def highlight(row):
        if row["Match Type"] == "Exact":
            return ['background-color: #d4edda'] * len(row)
        elif row["Match Type"] == "Close":
            return ['background-color: #fff3cd'] * len(row)
        elif row["Match Type"] == "Partial":
            return ['background-color: #ffe5b4'] * len(row)
        else:
            return ['background-color: #ffcccc'] * len(row)

    st.dataframe(df.style.apply(highlight, axis=1), use_container_width=True)

    st.download_button(
        "📥 Download Report",
        df.to_csv(index=False),
        file_name="scan_report.csv"
    )
