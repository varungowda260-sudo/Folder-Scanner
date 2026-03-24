import streamlit as st
import os
import re
import pandas as pd
from collections import defaultdict

st.set_page_config(page_title="Enterprise File Scanner Pro", layout="wide")

# ---------------- UI ----------------
st.markdown("""
<style>
.title {font-size:42px;font-weight:800;text-align:center;margin-bottom:20px;}
.section {font-size:22px;font-weight:700;margin-top:20px;}
.dataframe th {font-size:20px !important;font-weight:800 !important;}
.dataframe td {font-size:16px !important;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">📂 Enterprise File Scanner PRO</div>', unsafe_allow_html=True)

# ---------------- INPUT ----------------
st.markdown('<div class="section">Source File Name(CCF,VSR,CSIR)</div>', unsafe_allow_html=True)
source_input = st.text_area("", height=180)

st.markdown('<div class="section">Folder Path (Required for Rename)</div>', unsafe_allow_html=True)
folder_path = st.text_input("Enter full folder path")

# ---------------- NORMALIZATION ----------------
def normalize(text):
    return text.strip().upper()

def clean_name(name):
    name = os.path.splitext(name)[0]
    name = re.sub(r'[\s_\-\.]*v\d+$', '', name, flags=re.IGNORECASE)
    return normalize(name)

def split_parts(name):
    return clean_name(name).split("-")

# ---------------- LOAD FILES ----------------
def load_files(path):
    files = []
    for root, _, f in os.walk(path):
        for file in f:
            files.append(file)
    return list(set(files))

# ---------------- INDEX ----------------
def build_index(files):
    index = defaultdict(list)
    for f in files:
        parts = split_parts(f)
        if len(parts) >= 3:
            key = tuple(parts[:3])
            index[key].append(f)
    return index

# ---------------- SUGGEST FIX ----------------
def suggest_fix(src, candidates):
    src_parts = split_parts(src)

    if not candidates:
        return None

    best = candidates[0]
    tgt_parts = split_parts(best)

    # Construct corrected name
    corrected = "-".join(src_parts[:3])

    if len(tgt_parts) > 3:
        corrected += "-" + tgt_parts[3]

    return corrected

# ---------------- MATCH ----------------
def match(src, index):
    src_parts = split_parts(src)

    if len(src_parts) < 3:
        return ["NO", "Not Matched", "-", src, None, "Invalid format"]

    key = tuple(src_parts[:3])

    if key not in index:
        return ["NO", "Not Matched", "-", src, None, "No prefix match"]

    candidates = index[key]

    for f in candidates:
        if split_parts(f) == src_parts:
            return ["YES", "Exact", f, "-", None, "Perfect match"]

    # Close match
    fix = suggest_fix(src, candidates)

    return [
        "YES",
        "Close",
        ", ".join(candidates[:3]),
        "-",
        fix,
        "Prefix matched, suggested correction available"
    ]

# ---------------- RUN ----------------
if st.button("🚀 Run Scan"):

    if not source_input or not folder_path:
        st.warning("Provide source names and folder path")
        st.stop()

    files = load_files(folder_path)
    index = build_index(files)

    sources = [s.strip() for s in source_input.split("\n") if s.strip()]

    results = []

    for src in sources:
        res = match(src, index)
        results.append([src] + res)

    df = pd.DataFrame(results, columns=[
        "Source File Name",
        "YES/NO",
        "Match Type",
        "Matched Files",
        "Unmatched Files",
        "Suggested Fix",
        "Debug"
    ])

    st.dataframe(df, use_container_width=True)

    # ---------------- BULK RENAME ----------------
    st.markdown("### ✏️ Bulk Rename Tool")

    rename_candidates = df[df["Suggested Fix"].notna()]

    if not rename_candidates.empty:
        st.warning(f"{len(rename_candidates)} files can be corrected")

        if st.button("⚡ Apply Safe Rename"):

            log = []

            for _, row in rename_candidates.iterrows():
                old_name = row["Matched Files"].split(",")[0]
                new_name = row["Suggested Fix"] + ".pdf"

                old_path = os.path.join(folder_path, old_name)
                new_path = os.path.join(folder_path, new_name)

                if os.path.exists(old_path) and not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    log.append(f"{old_name} → {new_name}")

            st.success("Rename completed safely")

            st.text("\n".join(log))

    else:
        st.success("No files need correction")

    # Export
    file = "Enterprise_Report.xlsx"
    df.to_excel(file, index=False)

    with open(file, "rb") as f:
        st.download_button("📥 Download Report", f, file_name=file)
