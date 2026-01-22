"""
web_app.py

A Streamlit web interface for the ZooMS Species Identification tool.
It uses the logic from compare_score.py to compare an uploaded PMF
against theoretical peptides.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Import the comparison logic from compare_score.py
# Ensure this script is in the same directory or PYTHONPATH includes src/casi/scripts
try:
    import compare_score
except ImportError:
    # Fallback if running from a different directory context
    sys.path.append(str(Path(__file__).parent))
    import compare_score

# Page Configuration
st.set_page_config(
    page_title="ZooMS Species Identifier",
    layout="wide",
    page_icon="🧬"
)

st.title("🧬 ZooMS Species Identification Tool")
st.markdown("""
This tool identifies species by comparing an experimental **Peptide Mass Fingerprint (PMF)** 
against a database of theoretical collagen peptides.
""")

# --- Sidebar Configuration ---
st.sidebar.header("⚙️ Configuration")

# 1. Theoretical Database Path
# Defaulting to a relative path common in the project structure, but editable
default_db_path = Path("theoretical_peptides_outputs/filtered_peptides")
db_path_input = st.sidebar.text_input(
    "Theoretical Peptides Folder", 
    value=str(default_db_path),
    help="Path to the folder containing the generated CSV files."
)
db_path = Path(db_path_input)

# 2. Mass Range
st.sidebar.subheader("Mass Range (m/z)")
col1, col2 = st.sidebar.columns(2)
with col1:
    min_mass = st.number_input("Min Mass", value=800.0, step=10.0)
with col2:
    max_mass = st.number_input("Max Mass", value=3500.0, step=10.0)
mass_range = (min_mass, max_mass)

# 3. Threshold
st.sidebar.subheader("Match Parameters")
threshold = st.sidebar.number_input(
    "Match Threshold (± Da)", 
    value=0.2, 
    step=0.05, 
    format="%.2f",
    help="Tolerance for matching experimental peaks to theoretical peaks."
)

# --- Helper Functions ---

@st.cache_data(show_spinner=False)
def load_theoretical_data(folder_path, m_range):
    """
    Loads and caches the theoretical peptide data to improve performance
    on subsequent runs.
    """
    if not folder_path.exists():
        return None
    return compare_score.load_theoretical_data(folder_path, m_range)

# --- Main Interface ---

st.header("1. Upload Experimental PMF")
uploaded_file = st.file_uploader(
    "Upload PMF text file (Tab separated: m/z, intensity)", 
    type=["txt", "csv", "tsv", "mzXML"] # Note: Logic currently supports tab-sep text
)

# Check if DB path exists
if not db_path.exists():
    st.warning(f"⚠️ Theoretical peptides folder not found at: `{db_path}`. Please check the path in the sidebar.")
else:
    # Load DB
    with st.spinner("Loading theoretical database..."):
        theor_peaks_list = load_theoretical_data(db_path, mass_range)
    
    if not theor_peaks_list:
        st.error("No CSV files found in the specified folder.")
    elif uploaded_file:
        st.header("2. Analysis Results")
        
        with st.spinner("Processing experimental PMF and comparing..."):
            try:
                # 1. Read Experimental PMF
                # Reset file pointer to start
                uploaded_file.seek(0)
                
                # compare_score.read_exp_pmf uses pd.read_table which accepts file-like objects
                act_peaks_df, total_peaks = compare_score.read_exp_pmf(uploaded_file, mass_range)
                
                st.info(f"**Detected Peaks in Range:** {total_peaks}")
                
                # 2. Run Comparison
                # We pass output=None because we don't want to write to a file on the server
                matches_dict, results_df = compare_score.process_all_species(
                    theor_peaks_list, 
                    act_peaks_df, 
                    threshold, 
                    total_peaks,
                )
                
                # 3. Display Results
                st.subheader("🏆 Top 20 Species Matches")
                
                # Get Top 20
                top_20 = results_df.head(20)
                
                # Display as interactive table
                st.dataframe(
                    top_20, 
                    use_container_width=True,
                    column_config={
                        "Match": st.column_config.ProgressColumn(
                            "Match Score",
                            format="%d",
                            min_value=0,
                            max_value=int(results_df["Match"].max())
                        )
                    }
                )
                
                # Download Button
                csv = results_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Full Results CSV",
                    data=csv,
                    file_name="species_matches.csv",
                    mime="text/csv",
                )
                
            except Exception as e:
                st.error(f"An error occurred during analysis: {e}")
                st.exception(e)
