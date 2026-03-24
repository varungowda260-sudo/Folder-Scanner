import streamlit as st
import zipfile
import tempfile
import os
import re
import pandas as pd

st.set_page_config(page_title="Enterprise File Scanner", layout="wide")
st.title("📂 Enterprise File Scanner (High Precision)")

# ---------------- CONFIG ----------------
MAX_FILE_SIZE_MB = 204800  # 200 GB logical handling

# ---------------- CLEAN NAME ----------------
def clean_name(name):
    name = os.path.splitext(name)[0]

    # remove version suffixes like v01, _v2, -v3
    name = re.sub(r'[_\-]?v\d+$', '', name, flags=re.IGNORECASE)

    return name.strip()

# ---------------- SPLIT ----------------
def split_parts(name):
    return name.split("-")

# ---------------- STRICT MATCH ----------------
def classify_match(src, target):
    src_clean = clean_name(src)
    tgt_clean = clean_name(target)

    src_parts = split_parts(src_clean)
    tgt_parts = split_parts(tgt_clean)

    # Must have at least 4 parts
    if len(src_parts) < 4 or len(tgt_parts) < 4:
        return "Not Matched", "NO"

    # STRICT first 4 phrase match
    for i in range(4):
        if src_parts[i] != tgt_parts[i]:
            return "Not Matched", "NO"

    # Classification after strict validation
    if src_parts == tgt_parts:
        return "Exact", "YES"
    else:
        return "Close", "YES"

# ---------------- DIFFERENCE ----------------
def get_difference(src, tgt):
    src_clean = clean_name(src)
    tgt_clean = clean_name(tgt)

    diff = []
    for a, b in zip(src_clean, tgt_clean):
        if a != b:
            diff.append(f"{a}->{b}")

    return ", ".join(diff) if diff else "-"

# ---------------- LOAD FILES ----------------
def load_files(uploaded_zip=None, uploaded_files=None):
    temp_dir = tempfile.mkdtemp()
    all_files = []

    # ZIP handling
    if uploaded_zip:
        with zipfile.ZipFile(uploaded_zip, 'r') as z:
            z.extractall(temp_dir)

        for root, _, files in os.walk(temp_dir):
            for f in files:
                all_files.append(f)

    # Multiple file upload (folder simulation)
    if uploaded_files:
        for f in uploaded_files:
            all_files.append(f.name)

    return list(set(all_files))  # remove duplicates

# ---------------- SCAN ENGINE ----------------
def scan(sources, folder_files):
    results = []

    for src in sources:
        best_match = None
        best_type = "Not Matched"
        best_flag = "NO"

        for f in folder_files:
            match_type, flag = classify_match(src, f)

            if match_type == "Exact":
                best_match = f
                best_type = match_type
                best_flag = flag
                break

            elif match_type == "Close" and best_type != "Exact":
                best_match = f
                best_type = match_type
                best_flag = flag

        if best_match:
            matched = best_match
            unmatched = "-"
            diff = get_difference(src, best_match)
        else:
            matched = "-"
            unmatched = src
            diff = src

        results.append([
            src,
            best_flag,
            best_type,
            matched,
            unmatched,
            diff
        ])

    return results

# ---------------- UI ----------------

col1, col2 = st.columns(2)

with col1:
    source_input = st.text_area("📥 Enter Source File Names (one per line)", height=200)

with col2:
    uploaded_zip = st.file_uploader("Upload ZIP Folder", type=["zip"])
    uploaded_files = st.file_uploader(
        "Or Upload Folder Files (Select Multiple)",
        accept_multiple_files=True
    )

# ---------------- RUN ----------------
if st.button("🚀 Run High Precision Scan"):
    if not source_input:
        st.warning("Enter source file names")
    else:
        sources = [s.strip() for s in source_input.split("\n") if s.strip()]

        folder_files = load_files(uploaded_zip, uploaded_files)

        if not folder_files:
            st.warning("Upload ZIP or files")
        else:
            with st.spinner("Scanning with strict precision..."):
                data = scan(sources, folder_files)

            df = pd.DataFrame(data, columns=[
                "Source File Name",
                "YES/NO",
                "Match Type",
                "Matched Files in Folder",
                "Unmatched Files",
                "Difference"
            ])

            st.success("✅ Scan Completed (Error-Free Logic Applied)")
            st.dataframe(df, use_container_width=True)

            st.download_button(
                "📥 Download Report",
                df.to_csv(index=False),
                file_name="Enterprise_Scan_Report.csv"
            )
