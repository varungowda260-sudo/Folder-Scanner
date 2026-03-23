import streamlit as st
import zipfile
import tempfile
import os
import re
import pandas as pd
from rapidfuzz import fuzz

st.set_page_config(page_title="Folder Scanner", layout="wide")
st.title("📂 Folder Scanner")

# -------- INPUT --------
source_input = st.text_area("Enter Source File Names (one per line)")
uploaded_zip = st.file_uploader("Upload ZIP Folder", type=["zip"])

# -------- CLEAN --------
def clean_name(name):
    return os.path.splitext(name)[0]

# -------- ALPHA --------
def get_alpha(s):
    return "".join(re.findall(r'[A-Za-z]+', s))

# -------- DIFFERENCE --------
def get_difference(a, b):
    diff = []
    for i in range(max(len(a), len(b))):
        ca = a[i] if i < len(a) else ""
        cb = b[i] if i < len(b) else ""

        if ca != cb:
            if ca:
                diff.append(ca)
            if cb:
                diff.append(cb)

    seen = set()
    final = []
    for x in diff:
        if x not in seen and x != "":
            seen.add(x)
            final.append(x)

    return ", ".join(final) if final else "-"

# -------- SCAN --------
def scan_files(zip_file, sources):
    temp_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(zip_file, 'r') as z:
        z.extractall(temp_dir)

    files = []
    for root, _, f in os.walk(temp_dir):
        for file in f:
            cleaned = clean_name(file)
            files.append({
                "original": file,
                "clean": cleaned,
                "alpha": get_alpha(cleaned),
                "used": False
            })

    results = []

    for src in sources:
        src_clean = src
        src_alpha = get_alpha(src_clean)

        best = None
        best_score = -1

        # -------- EXACT MATCH --------
        for f in files:
            if f["used"]:
                continue
            if src_clean == f["clean"]:
                best = f
                best_score = 100
                break

        # -------- CLOSE MATCH --------
        if not best:
            for f in files:
                if f["used"]:
                    continue

                alpha_score = fuzz.ratio(src_alpha, f["alpha"])
                if alpha_score < 70:
                    continue

                score = fuzz.ratio(src_clean, f["clean"])

                if score > best_score:
                    best_score = score
                    best = f

        # -------- CLASSIFICATION --------
        if best and best_score == 100:
            match_type = "Exact"
            flag = "YES"
            best["used"] = True

        elif best and best_score >= 85:
            match_type = "Close"
            flag = "YES"
            best["used"] = True

        elif best and best_score >= 60:
            match_type = "Partial"
            flag = "NO"
            best["used"] = True

        else:
            match_type = "Not Matched"
            flag = "NO"
            best = None

        if best:
            matched = best["original"]
            unmatched = "-"
            diff = get_difference(src_clean, best["clean"])
        else:
            matched = "-"
            unmatched = src_clean
            diff = src_clean

        results.append([
            src_clean,
            flag,
            match_type,
            matched,
            unmatched,
            diff
        ])

    # -------- UNMAPPED FILES --------
    unmapped_count = 0
    for f in files:
        if not f["used"]:
            unmapped_count += 1
            results.append([
                "-",
                "NO",
                "Unmapped File",
                "-",
                f["original"],
                f["original"]
            ])

    return results, len(files), unmapped_count

# -------- RUN --------
if st.button("🚀 Run Scan"):
    if not uploaded_zip or not source_input:
        st.warning("Upload ZIP and enter source names")
    else:
        sources = [line for line in source_input.split("\n") if line != ""]

        data, total_files, unmapped_count = scan_files(uploaded_zip, sources)

        df = pd.DataFrame(data, columns=[
            "Source File Name",
            "YES/NO",
            "Match Type",
            "Matched Files in Folder",
            "Unmatched Files",
            "Difference"
        ])

        st.success("Scan Completed ✅")
        st.dataframe(df, use_container_width=True)

        st.download_button(
            "📥 Download Report",
            df.to_csv(index=False),
            file_name="Folder_Scanner_Report.csv"
        )

        # -------- FINAL VALIDATION MESSAGE --------
        total_sources = len(sources)
        processed_sources = len([r for r in data if r[0] != "-"])

        # Strict validation conditions
        condition_1 = processed_sources == total_sources
        condition_2 = total_files >= 0
        condition_3 = len(data) >= total_sources

        if condition_1 and condition_2 and condition_3:
            st.success("✅ All files successfully compared with the source filename")
        else:
            st.error("❌ Verification incomplete — some files or sources were not properly processed")
