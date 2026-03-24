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
st.markdown('<div class="section">Source File Name(CCF,VSR,CSIR)</div>', unsafe_allow_html=True)
source_input = st.text_area("", height=200)

st.markdown('<div class="section">Upload Folder / ZIP</div>', unsafe_allow_html=True)
uploaded_zip = st.file_uploader("Upload ZIP", type=["zip"])
uploaded_files = st.file_uploader("Or Upload Files", accept_multiple_files=True)

# ---------------- CLEAN ----------------
def clean_name(name):
    name = os.path.splitext(name)[0]
    name = re.sub(r'[\s_\-\.]*v\d+$', '', name, flags=re.IGNORECASE)
    return name.strip()

# ---------------- SPLIT ----------------
def split_parts(name):
    return clean_name(name).split("-")

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

# ---------------- MATCH (YOUR ORIGINAL LOGIC) ----------------
def match_file(src, files):
    src = src.strip()
    src_parts = split_parts(src)

    if len(src_parts) < 3:
        return ["NO", "Not Matched", "-", src, src]

    exact_match = None
    close_matches = []

    for f in files:
        tgt_parts = split_parts(f)

        if len(tgt_parts) < 3:
            continue

        if (
            src_parts[0] == tgt_parts[0] and
            src_parts[1] == tgt_parts[1] and
            src_parts[2] == tgt_parts[2]
        ):
            if len(src_parts) > 3 and len(tgt_parts) > 3:
                if src_parts[3] == tgt_parts[3]:
                    exact_match = f
                    break
                else:
                    close_matches.append(f)
            else:
                close_matches.append(f)

    if exact_match:
        return ["YES", "Exact", exact_match, "-", "-"]

    if close_matches:
        return ["YES", "Close", ", ".join(close_matches[:3]), "-", "-"]

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

    # -------- PROGRESS --------
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
        "Matched Files",
        "Unmatched Files",
        "Difference"
    ])

    st.success("Scan Completed")

    # -------- SUMMARY --------
    col1, col2, col3 = st.columns(3)
    col1.metric("Total", len(df))
    col2.metric("Matched", len(df[df["YES/NO"] == "YES"]))
    col3.metric("Unmatched", len(df[df["YES/NO"] == "NO"]))

    # ---------------- SEARCH ----------------
    search = st.text_input("🔍 Search in results")

    filtered_df = df.copy()

    if search:
        filtered_df = filtered_df[
            filtered_df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        ]

    # ---------------- HIGHLIGHT ----------------
    def highlight(row):
        if row["YES/NO"] == "NO":
            return ['background-color: #ffcccc'] * len(row)
        elif row["Match Type"] == "Close":
            return ['background-color: #fff3cd'] * len(row)
        elif row["Match Type"] == "Exact":
            return ['background-color: #d4edda'] * len(row)
        return [''] * len(row)

    # ---------------- TABS ----------------
    tab1, tab2, tab3 = st.tabs(["📊 All Results", "✅ Matched", "❌ Unmatched"])

    with tab1:
        st.dataframe(filtered_df.style.apply(highlight, axis=1), use_container_width=True)

    with tab2:
        st.dataframe(
            filtered_df[filtered_df["YES/NO"] == "YES"].style.apply(highlight, axis=1),
            use_container_width=True
        )

    with tab3:
        st.dataframe(
            filtered_df[filtered_df["YES/NO"] == "NO"].style.apply(highlight, axis=1),
            use_container_width=True
        )

    # ---------------- DOWNLOAD ----------------
    st.markdown("### 📥 Download")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "Download Filtered Results",
            filtered_df.to_csv(index=False),
            file_name="filtered_results.csv"
        )

    with col2:
        st.download_button(
            "Download Full Report",
            df.to_csv(index=False),
            file_name="full_report.csv"
        )
