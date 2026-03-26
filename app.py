import streamlit as st
import zipfile
import tempfile
import os
import re
import pandas as pd

st.set_page_config(page_title="Folder Scanner", layout="wide")

# ---------------- DARK MODE TOGGLE ----------------
dark_mode = st.toggle("🌙 Dark Mode")

if dark_mode:
    st.markdown("""
    <style>
    body, .stApp { background-color: #0e1117; color: white; }
    </style>
    """, unsafe_allow_html=True)

# ---------------- UI STYLE ----------------
st.markdown("""
<style>
.title {
    font-size:38px;
    font-weight:800;
    text-align:center;
    margin-bottom:10px;
}
.section {
    font-size:22px;
    font-weight:700;
    margin-top:20px;
}
.helper {
    font-size:15px;
    color:#888;
}
.card {
    padding:15px;
    border-radius:10px;
    text-align:center;
    font-weight:700;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">📂 Folder Scanner</div>', unsafe_allow_html=True)

# ---------------- USER MANUAL ----------------
with st.expander("📘 How to Use"):
    st.markdown("""
1️⃣ Enter source file names  
2️⃣ Upload ZIP or files  
3️⃣ Click Run Scan  
4️⃣ Use filters to analyze results  
5️⃣ Download report  
""")

# ---------------- INPUT ----------------
st.markdown('<div class="section">1️⃣ Enter Approved Source File Names (CISR, CCR, VSR, SRS)</div>', unsafe_allow_html=True)
source_input = st.text_area("", height=200)

st.markdown('<div class="section">2️⃣ Upload Folder / ZIP</div>', unsafe_allow_html=True)
uploaded_zip = st.file_uploader("Upload ZIP", type=["zip"])
uploaded_files = st.file_uploader("Or Upload Files", accept_multiple_files=True)

# ---------------- CLEAN ----------------
def clean_name(name):
    name = os.path.splitext(name)[0]
    name = re.sub(r'[\s_\-\.]*v\d+$', '', name, flags=re.IGNORECASE)
    return name.strip()

def extract_version(name):
    match = re.search(r'v\d+', name, re.IGNORECASE)
    return match.group().lower() if match else None

def split_parts(name):
    name = clean_name(name)
    name = re.sub(r'[^\w]+', ' ', name)
    return [p for p in name.split() if p]

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

# ---------------- DIFFERENCE ----------------
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

# ---------------- MATCH ----------------
def match_file(src, files):
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

        if src_version and tgt_version and src_version == tgt_version:
            match_count += 1

        if match_count > best_score:
            best_score = match_count
            best_match = f

    # ==========================================================
    # 🔒 LOCKED CLASSIFICATION BLOCK - DO NOT MODIFY
    # Any change here will affect matching behavior.
    # ==========================================================
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
    # ==========================================================

# ---------------- RUN ----------------
if st.button("🚀 Run Scan"):

    if not source_input:
        st.warning("Enter source file names")
        st.stop()

    files = load_files(uploaded_zip, uploaded_files)
    sources = [s.strip() for s in source_input.split("\n") if s.strip()]

    progress_text = st.empty()
    progress_bar = st.progress(0)

    results = []

    for i, src in enumerate(sources):
        progress_text.text(f"Processing {i+1}/{len(sources)}...")
        results.append([src] + match_file(src, files))
        progress_bar.progress((i + 1) / len(sources))

    df = pd.DataFrame(results, columns=[
        "Source File Name","YES/NO","Match Type",
        "Matched Files in Folder","Unmatched Files","Difference"
    ])

# ✅ STORE IN SESSION (FIXES FILTER BUG + EXTRA FILES)
    st.session_state["df"] = df
    st.session_state["all_files"] = files

    st.success("Scan Completed")

    # ---------------- DASHBOARD ----------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(df))
    c2.metric("Exact", len(df[df["Match Type"]=="Exact"]))
    c3.metric("Close", len(df[df["Match Type"]=="Close"]))
    c4.metric("Not Matched", len(df[df["YES/NO"]=="NO"]))

# ---------------- FILTER (WORKS WITHOUT RE-RUN) ----------------
if "df" in st.session_state:

    filter_option = st.selectbox(
        "Filter Results",
        ["All","Exact","Close","Partial","Not Matched"]
    )

    filtered_df = st.session_state["df"]

    if filter_option != "All":
        filtered_df = filtered_df[filtered_df["Match Type"] == filter_option]

    # ---------------- COLOR ----------------
    def highlight(row):
        if row["Match Type"] == "Exact":
            return ['background-color:#d4edda']*len(row)
        elif row["Match Type"] == "Close":
            return ['background-color:#fff3cd']*len(row)
        elif row["Match Type"] == "Partial":
            return ['background-color:#ffe5b4']*len(row)
        else:
            return ['background-color:#ffcccc']*len(row)

    st.dataframe(filtered_df.style.apply(highlight, axis=1), use_container_width=True)

    st.download_button(
        "📥 Download Report",
        filtered_df.to_csv(index=False),
        file_name="scan_report.csv"
    )
    # ---------------- EXTRA FILES FEATURE ----------------
    st.markdown("### 📌 Extra Files Detected")

    matched_files = set(filtered_df["Matched Files in Folder"])
    all_files = set(st.session_state.get("all_files", []))

    extra_files = [f for f in all_files if f not in matched_files and f != "-"]

    if extra_files:
        extra_df = pd.DataFrame(extra_files, columns=["Extra Files"])
        st.dataframe(extra_df, use_container_width=True)
    else:
        st.success("No extra files found ✅")
