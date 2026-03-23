import streamlit as st
import zipfile
import tempfile
import os
import re
import pandas as pd
from rapidfuzz import fuzz

st.set_page_config(page_title="Enterprise File Matcher", layout="wide")

st.title("📂 Enterprise File Matcher")

# -------- INPUT --------
source_input = st.text_area("Enter Source File Names (one per line)")
uploaded_zip = st.file_uploader("Upload ZIP Folder", type=["zip"])

# -------- CLEAN FILE NAME --------
def clean_filename(filename):
    name = os.path.splitext(filename)[0]
    name = re.sub(r'\s*v\d+$', '', name, flags=re.IGNORECASE)
    return name.strip()

# -------- SCAN FUNCTION --------
def scan_files(zip_file, source_files):
    temp_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    folder_files = []

    for root, _, files in os.walk(temp_dir):
        for file in files:
            cleaned = clean_filename(file)
            folder_files.append((file, cleaned))

    results = []

    for src in source_files:
        matched_files = []
        unmatched_files = []
        best_score = 0

        for original, cleaned in folder_files:
            score = fuzz.ratio(src, cleaned)

            if score > best_score:
                best_score = score

            if score >= 80:
                matched_files.append(original)
            else:
                unmatched_files.append(original)

        # -------- CLASSIFICATION --------
        if best_score == 100:
            match_type = "Exact"
            match_flag = "YES"
        elif best_score >= 80:
            match_type = "Close"
            match_flag = "YES"
        elif best_score >= 50:
            match_type = "Partial"
            match_flag = "NO"
        else:
            match_type = "Not Matched"
            match_flag = "NO"

        results.append([
            src,
            match_flag,
            match_type,
            ", ".join(matched_files) if matched_files else "-",
            ", ".join(unmatched_files) if unmatched_files else "-"
        ])

    return results

# -------- RUN --------
if st.button("🚀 Run Scan"):
    if not uploaded_zip or not source_input:
        st.warning("Please upload ZIP and enter source file names")
    else:
        source_files = [s.strip() for s in source_input.split("\n") if s.strip()]

        st.info("Scanning...")

        data = scan_files(uploaded_zip, source_files)

        df = pd.DataFrame(data, columns=[
            "Source File Name",
            "YES/NO",
            "Match Type",
            "Matched Files in Folder",
            "Unmatched Files"
        ])

        st.success("Scan Completed ✅")
        st.dataframe(df, use_container_width=True)

        # DOWNLOAD
        st.download_button(
            "📥 Download Report",
            df.to_csv(index=False),
            file_name="Final_Report.csv",
            mime="text/csv"
        )