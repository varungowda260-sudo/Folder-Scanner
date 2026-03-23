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
    name = os.path.splitext(name)[0]
    name = re.sub(r'\s*v\d+$', '', name, flags=re.IGNORECASE)
    return name.strip()

# -------- EXTRACT ALPHABETS (PRIMARY MATCH PRIORITY) --------
def get_alpha(s):
    return "".join(re.findall(r'[A-Za-z]+', s)).upper()

# -------- EXTRACT NUMBERS --------
def get_num(s):
    return "".join(re.findall(r'\d+', s))

# -------- PRECISE DIFFERENCE --------
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

    # remove duplicates while preserving order
    seen = set()
    clean_diff = []
    for x in diff:
        if x not in seen and x.strip() != "":
            seen.add(x)
            clean_diff.append(x)

    return ", ".join(clean_diff) if clean_diff else "-"

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
                "num": get_num(cleaned),
                "used": False
            })

    results = []

    for src in sources:
        src_clean = src
        src_alpha = get_alpha(src_clean)
        src_num = get_num(src_clean)

        best = None
        best_score = -1

        for f in files:
            if f["used"]:
                continue

            # PRIMARY FILTER: alphabet match must be strong
            alpha_score = fuzz.ratio(src_alpha, f["alpha"])

            if alpha_score < 60:
                continue  # reject weak alphabet matches

            # SECONDARY: full string similarity
            score = fuzz.ratio(src_clean, f["clean"])

            # PRIORITY: favor alphabet similarity
            final_score = (0.7 * alpha_score) + (0.3 * score)

            if final_score > best_score:
                best_score = final_score
                best = f

        # -------- CLASSIFICATION --------
        if best and best_score >= 95:
            match_type = "Exact"
            flag = "YES"
            best["used"] = True

        elif best and best_score >= 80:
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

        # -------- OUTPUT --------
        if best:
            matched = best["original"]
            unmatched = "-"
            diff = get_difference(src_clean, best["clean"])
        else:
            matched = "-"
            unmatched = src_clean
            diff = src_clean  # full difference

        results.append([
            src_clean,
            flag,
            match_type,
            matched,
            unmatched,
            diff
        ])

    return results

# -------- RUN --------
if st.button("🚀 Run Scan"):
    if not uploaded_zip or not source_input:
        st.warning("Upload ZIP and enter source names")
    else:
        sources = [s for s in source_input.split("\n") if s != ""]

        data = scan_files(uploaded_zip, sources)

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
