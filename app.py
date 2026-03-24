import streamlit as st
import zipfile
import tempfile
import os
import re
import pandas as pd

st.set_page_config(page_title="Folder Scanner", layout="wide")

# ---------------- UI ----------------
st.title("📂 Folder Scanner")

st.subheader("Source File Name (CCF, VSR, CSIR)")
source_input = st.text_area("", height=200)

st.subheader("Upload Folder / ZIP")
uploaded_zip = st.file_uploader("Upload ZIP", type=["zip"])
uploaded_files = st.file_uploader("Or Upload Files", accept_multiple_files=True)

# ---------------- CLEAN ----------------
def clean_name(name):
    name = os.path.splitext(name)[0]
    name = re.sub(r'[\s_\-\.]*v\d+$', '', name, flags=re.IGNORECASE)
    return name.strip()

# ---------------- SPLIT ----------------
def split_parts(name):
    name = clean_name(name)
    return [p for p in re.split(r'[-_\s]+', name) if p]

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

    return files

# ---------------- DIFFERENCE (FINAL FIX) ----------------
def get_difference(src, tgt):
    src_clean = clean_name(src)
    tgt_full = tgt
    tgt_clean = clean_name(tgt_full)
    ext = os.path.splitext(tgt_full)[1]

    # Case 1: exact base match → only extension
    if src_clean == tgt_clean:
        return ext if ext else "-"

    # Case 2: target starts with source → extract suffix
    if tgt_clean.startswith(src_clean):
        suffix = tgt_clean[len(src_clean):]
        return suffix + ext if (suffix + ext) else ext

    # Case 3: fallback (safe)
    return tgt_full

# ---------------- MATCH ----------------
def match_file(src, files):
    src = src.strip()
    src_parts = split_parts(src)
    src_clean = clean_name(src)

    best_match = None
    best_score = 0

    for f in files:
        tgt_parts = split_parts(f)

        match_count = 0

        for i in range(min(len(src_parts), len(tgt_parts))):
            if src_parts[i] == tgt_parts[i]:
                match_count += 1
            else:
                break

        if match_count > best_score:
            best_score = match_count
            best_match = f

    if not best_match:
        return ["NO", "Not Matched", "-", src, src]

    tgt_clean = clean_name(best_match)

    # -------- STRICT EXACT --------
    if src_clean == tgt_clean:
        return ["YES", "Exact", best_match, "-", "-"]

    elif best_score == 3:
        diff = get_difference(src, best_match)
        return ["YES", "Close", best_match, "-", diff]

    elif best_score == 2:
        diff = get_difference(src, best_match)
        return ["YES", "Partial", best_match, "-", diff]

    else:
        return ["NO", "Not Matched", "-", src, src]

# ---------------- RUN ----------------
if st.button("🚀 Run Scan"):

    if not source_input:
        st.warning("Enter source names")
        st.stop()

    files = load_files(uploaded_zip, uploaded_files)

    if not files:
        st.warning("Upload files")
        st.stop()

    sources = [s.strip() for s in source_input.split("\n") if s.strip()]

    results = []
    progress = st.progress(0)

    for i, src in enumerate(sources):
        results.append([src] + match_file(src, files))
        progress.progress((i + 1) / len(sources))

    df = pd.DataFrame(results, columns=[
        "Source File Name",
        "YES/NO",
        "Match Type",
        "Matched Files in Folder",
        "Unmatched Files",
        "Difference"
    ])

    st.success("Scan Completed")

    st.dataframe(df, use_container_width=True)

    st.download_button(
        "📥 Download Report",
        df.to_csv(index=False),
        file_name="scan_report.csv"
    )
