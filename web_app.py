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
from typing import Tuple, List, Optional, Any

# Import the comparison logic from compare_score.py
# Ensure this script is in the same directory or PYTHONPATH includes src/casi/scripts

import casi.scripts.compare_score as compare_score

def configure_page() -> None:
    """
    Configures the Streamlit page settings, title, and description.
    """
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

def get_sidebar_config() -> Tuple[Path, Tuple[float, float], float]:
    """
    Renders the sidebar configuration and returns the selected parameters.

    Returns:
        Tuple containing:
            - Path: The path to the theoretical peptides database.
            - Tuple[float, float]: The mass range (min_mass, max_mass).
            - float: The match threshold.
    """
    st.sidebar.header("⚙️ Configuration")

    # 1. Theoretical Database Path
    # Defaulting to a relative path for filtered peptides, but allowing user input for flexibility
    default_db_path = Path("filtered_peptides")
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
    return db_path, mass_range, threshold

@st.cache_data(show_spinner=False)
def load_theoretical_data(
    folder_path: Path, 
    m_range: Tuple[float, float]
) -> Optional[List[Any]]:
    """
    Loads and caches the theoretical peptide data to improve performance
    on subsequent runs.

    Args:
        folder_path: Path to the folder containing CSV files.
        m_range: Tuple of (min_mass, max_mass).

    Returns:
        A list of theoretical peaks data structures, or None if folder doesn't exist.
    """
    if not folder_path.exists():
        return None
    return compare_score.load_theoretical_data(folder_path, m_range)

def read_experimental_pmf(
    uploaded_file: Any, 
    mass_range: Tuple[float, float]
) -> Tuple[pd.DataFrame, int]:
    """
    Reads the uploaded PMF file and extracts peaks within the mass range.

    Args:
        uploaded_file: The uploaded file object (Streamlit UploadedFile).
        mass_range: Tuple of (min_mass, max_mass).

    Returns:
        Tuple containing:
            - pd.DataFrame: Dataframe of experimental peaks.
            - int: The number of peaks detected.
    """
    # Reset file pointer to start
    uploaded_file.seek(0)
    
    # compare_score.read_exp_pmf uses pd.read_table which accepts file-like objects
    act_peaks_df = compare_score.read_exp_pmf(uploaded_file, mass_range)
    total_peaks = len(act_peaks_df)
    return act_peaks_df, total_peaks

def run_species_comparison(
    theor_peaks_list: List[Any],
    act_peaks_df: pd.DataFrame,
    threshold: float,
    total_peaks: int
) -> pd.DataFrame:
    """
    Compares experimental peaks against the theoretical database.

    Args:
        theor_peaks_list: List of theoretical peaks data.
        act_peaks_df: Dataframe of experimental peaks.
        threshold: Matching threshold in Daltons.
        total_peaks: Total number of peaks detected.

    Returns:
        pd.DataFrame: The results dataframe sorted by score.
    """
    
    results_df, _ = compare_score.process_all_species(
        theor_peaks_list, 
        act_peaks_df, 
        threshold, 
        total_peaks,
    )
    return results_df

def display_results(results_df: pd.DataFrame) -> None:
    """
    Displays the analysis results in the Streamlit interface.

    Args:
        results_df: Dataframe containing the comparison results.
    """
    st.subheader("🏆 Top 20 Species Matches")
    
    # Get Top 20
    top_20 = results_df.head(20)
    
    # Display as interactive table
    st.dataframe(
        top_20, 
        use_container_width=True
    )
    
    # Download Button
    csv = results_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Full Results CSV",
        data=csv,
        file_name="species_matches.csv",
        mime="text/csv",
    )

def main() -> None:
    """Main execution function for the Streamlit app."""
    configure_page()
    
    db_path, mass_range, threshold = get_sidebar_config()

    st.header("1. Upload Experimental PMF")
    uploaded_file = st.file_uploader(
        "Upload PMF text file (Tab separated: m/z, intensity)", 
        type=["txt", "csv", "tsv", "mzXML"] # Note: Logic currently supports tab-sep text
    )

    # Check if DB path exists
    if not db_path.exists():
        st.warning(f"⚠️ Theoretical peptides folder not found at: `{db_path}`. Please check the path in the sidebar.")
        return

    # Load DB
    with st.spinner("Loading theoretical database..."):
        theor_peaks_list = load_theoretical_data(db_path, mass_range)
    
    if not theor_peaks_list:
        st.error("No CSV files found in the specified folder.")
        return

    if uploaded_file:
        st.header("2. Analysis Results")
        
        with st.spinner("Processing experimental PMF and comparing..."):
            try:
                # 1. Read Experimental PMF
                act_peaks_df, total_peaks = read_experimental_pmf(uploaded_file, mass_range)

                st.info(f"**Detected Peaks in Range:** {total_peaks}")
                
                # 2. Run Comparison
                results_df = run_species_comparison(
                    theor_peaks_list, 
                    act_peaks_df, 
                    threshold, 
                    total_peaks
                )
                
                # 3. Display Results
                display_results(results_df)
                
            except Exception as e:
                st.error(f"An error occurred during analysis: {e}")
                st.exception(e)

if __name__ == "__main__":
    main()
