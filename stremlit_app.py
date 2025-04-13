import time
import streamlit as st
import requests # Use requests to call the Flask API
from dotenv import load_dotenv
import os
import PyPDF2
import json
import pandas as pd
import openpyxl

# --- Configuration ---
load_dotenv() 

# URL of your Flask backend API
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:5000/analyze")

EXCEL_FILE_PATH = "cv_analysis_results_from_api.xlsx" # Changed filename slightly
REQUESTS_PER_MINUTE = 15 # Rate limit API calls from the frontend
SLEEP_TIME = 60 / REQUESTS_PER_MINUTE

# --- Helper Functions ---
def extract_text_from_pdf(pdf_file):
    """Extracts text content from an uploaded PDF file object."""
    try:
        # pdf_file is an UploadedFile object from Streamlit
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    except Exception as e:
        st.error(f"Error reading PDF '{pdf_file.name}': {e}")
        return None

def call_analysis_api(cv_text, job_description):
    """Calls the backend Flask API to analyze the CV."""
    payload = {
        "cv_text": cv_text,
        "job_description": job_description
    }
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(BACKEND_API_URL, headers=headers, json=payload, timeout=120) # Added timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        return response.json() # Parse JSON response from API

    except requests.exceptions.ConnectionError:
        st.error(f"Connection Error: Could not connect to the backend API at {BACKEND_API_URL}. Is the backend running?")
        return {"error": "Connection Error: Cannot reach backend API."}
    except requests.exceptions.Timeout:
         st.error(f"Request timed out waiting for backend API at {BACKEND_API_URL}.")
         return {"error": "Timeout: Backend API did not respond in time."}
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling backend API: {e}")
        # Try to get more details from the response if possible
        error_detail = ""
        try:
            error_detail = e.response.json()
        except:
             try: # if response is not json
                 error_detail = e.response.text
             except: # if no response attribute
                 error_detail = "No response details available."
        st.error(f"API Response Detail: {error_detail}")
        return {"error": f"API Request Failed: {e}"}
    except json.JSONDecodeError:
        st.error(f"Error decoding JSON response from backend API. Raw response: {response.text[:500]}...")
        return {"error": "Invalid JSON response from backend."}


def format_list_field(data_list, format_func):
    """Helper function to format list fields like education or work history."""
    if not isinstance(data_list, list):
        return "Invalid data format received"
    items = []
    for item in data_list:
        if isinstance(item, dict):
            items.append(format_func(item))
        elif isinstance(item, str):
             items.append(item)
    return "; ".join(items)

# --- Main Streamlit App Logic ---
def main():
    st.set_page_config(page_title="CV Scanner ", layout="wide")
    st.title("CV Sorting & Job Match Analyzer")
    # st.caption(f"Backend API Target: `{BACKEND_API_URL}`")

    # Job Description Input
    st.subheader("1. Enter Job Description")
    job_description = st.text_area(
        "Paste the job description here",
        height=200,
        placeholder="Enter the full job description..."
    )

    # Multiple CV Upload
    st.subheader("2. Upload CVs (PDF)")
    uploaded_files = st.file_uploader(
        "Choose one or more PDF files",
        type="pdf",
        accept_multiple_files=True
    )

    # Add a button to trigger analysis
    st.subheader("3. Analyze")
    analyze_button = st.button(
        "Analyze Uploaded CVs",
        disabled=(not uploaded_files or not job_description) # Enable only when both inputs are ready
    )

    if analyze_button: # Only run analysis when the button is clicked
        st.markdown("---")
        st.header("Analysis Results")
        all_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_files = len(uploaded_files)

        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processing: {uploaded_file.name} ({i+1}/{total_files})...")
            with st.spinner(f"Analyzing {uploaded_file.name}..."):
                analysis_data = None # Reset for each file
                try:
                    # 1. Extract text from PDF
                    extract_start_time = time.time()
                    cv_text = extract_text_from_pdf(uploaded_file)
                    extract_duration = time.time() - extract_start_time
                    if cv_text is None:
                        st.error(f"Skipping {uploaded_file.name} due to PDF read error.")
                        # Add error row
                        all_data.append({
                            "CV Filename": uploaded_file.name, "Name": "PDF Error", "Email": "N/A", "Phone": "N/A",
                            "Match Score": 0, "Consideration": "Could not read PDF", "Match Reasons": "N/A",
                            "Skills": "N/A", "Education": "N/A", "Work History": "N/A",
                            "Job Description Snippet": job_description[:100] + "..." if len(job_description) > 100 else job_description
                        })
                        continue # Skip to next file

                    if not cv_text.strip():
                         st.warning(f"Extracted text from {uploaded_file.name} is empty. Skipping analysis.")
                         # Add warning row
                         all_data.append({
                            "CV Filename": uploaded_file.name, "Name": "Empty PDF", "Email": "N/A", "Phone": "N/A",
                            "Match Score": 0, "Consideration": "PDF contained no extractable text", "Match Reasons": "N/A",
                            "Skills": "N/A", "Education": "N/A", "Work History": "N/A",
                            "Job Description Snippet": job_description[:100] + "..." if len(job_description) > 100 else job_description
                        })
                         continue

                    st.write(f"Extracted text from {uploaded_file.name} ({len(cv_text)} chars) in {extract_duration:.2f}s.")

                    # 2. Call Backend API for Analysis
                    api_start_time = time.time()
                    analysis_data = call_analysis_api(cv_text, job_description)
                    api_duration = time.time() - api_start_time
                    st.write(f"API call for {uploaded_file.name} took {api_duration:.2f} seconds.")

                    # 3. Process API Response
                    if analysis_data and 'error' not in analysis_data:
                        # Extract relevant data safely using .get() with defaults
                        personal_info = analysis_data.get("personal_info", {})
                        name = personal_info.get("name", "N/A")
                        email = personal_info.get("email", "N/A")
                        phone = personal_info.get("phone", "N/A")

                        skills_list = analysis_data.get("skills", [])
                        skills = ", ".join(skills_list) if isinstance(skills_list, list) else "Invalid data"

                        education = format_list_field(
                            analysis_data.get("education", []),
                            lambda edu: f"{edu.get('degree', 'N/A')} at {edu.get('university', 'N/A')}"
                                        f"{' (' + edu.get('graduation_year', '') + ')' if edu.get('graduation_year') else ''}"
                        )
                        work_history = format_list_field(
                            analysis_data.get("work_history", []),
                            lambda work: f"{work.get('title', 'N/A')} at {work.get('company', 'N/A')}"
                                        f"{' (' + work.get('duration', '') + ')' if work.get('duration') else ''}"
                        )

                        match_score = analysis_data.get("match_score", 0)
                        match_reasons_list = analysis_data.get("match_reasons", [])
                        match_reasons = "; ".join(match_reasons_list) if isinstance(match_reasons_list, list) else "Invalid data"

                        consideration = analysis_data.get("consideration", "N/A")

                        # Create a row for the data
                        row = {
                            "CV Filename": uploaded_file.name,
                            "Name": name,
                            "Email": email,
                            "Phone": phone,
                            "Match Score": match_score,
                            "Consideration": consideration,
                            "Match Reasons": match_reasons,
                            "Skills": skills,
                            "Education": education,
                            "Work History": work_history,
                            "Job Description Snippet": job_description[:100] + "..." if len(job_description) > 100 else job_description
                        }
                        all_data.append(row)

                        # Display immediate feedback
                        st.write(f"**Result for {name} ({uploaded_file.name}):**")
                        st.metric(label="Match Score", value=f"{match_score}/10")
                        st.write(f"**Consideration:** {consideration}")
                        with st.expander("See Extracted Details"):
                            st.json({k: v for k, v in row.items() if k not in ["Match Score", "Consideration", "Job Description Snippet", "CV Filename"]})

                    else:
                        # Handle error from API call
                        error_msg = analysis_data.get("error", "Unknown error from API") if analysis_data else "No response from API"
                        st.error(f"Failed to analyze {uploaded_file.name}: {error_msg}")
                        # Add error row
                        all_data.append({
                            "CV Filename": uploaded_file.name, "Name": "API Error", "Email": "N/A", "Phone": "N/A",
                            "Match Score": 0, "Consideration": error_msg, "Match Reasons": "N/A",
                            "Skills": "N/A", "Education": "N/A", "Work History": "N/A",
                            "Job Description Snippet": job_description[:100] + "..." if len(job_description) > 100 else job_description
                        })

                    # Rate Limiting (applied *after* processing each file)
                    time.sleep(SLEEP_TIME)

                except Exception as e:
                    st.error(f"An unexpected error occurred in the frontend while processing {uploaded_file.name}: {str(e)}")
                    # Add error row for unexpected frontend errors
                    all_data.append({
                        "CV Filename": uploaded_file.name, "Name": "Frontend Error", "Email": "N/A", "Phone": "N/A",
                        "Match Score": 0, "Consideration": f"Frontend Error: {e}", "Match Reasons": "N/A",
                        "Skills": "N/A", "Education": "N/A", "Work History": "N/A",
                        "Job Description Snippet": job_description[:100] + "..." if len(job_description) > 100 else job_description
                    })

            # Update progress bar
            progress_bar.progress((i + 1) / total_files)
            st.markdown("---") # Separator between file results

        status_text.text("Analysis Complete!")
        st.balloons()

        # 4. Write ALL data to Excel file
        if all_data:
            st.header("Summary Report")
            try:
                df = pd.DataFrame(all_data)
                column_order = [ # Define desired column order
                    "CV Filename", "Name", "Email", "Phone", "Match Score",
                    "Consideration", "Match Reasons", "Skills", "Education",
                    "Work History", "Job Description Snippet"
                ]
                df = df.reindex(columns=column_order) # Ensure columns exist and are ordered

                # Display results in Streamlit table
                st.dataframe(df)

                # Save to Excel
                excel_output_path = os.path.join(".", EXCEL_FILE_PATH) # Save in current dir relative to app.py
                df.to_excel(excel_output_path, sheet_name='CV Analysis Results', index=False)
                st.success(f"Analysis report saved to Excel file: {excel_output_path}")

                # Provide download button
                with open(excel_output_path, "rb") as fp:
                    st.download_button(
                        label="Download Excel Report",
                        data=fp,
                        file_name=EXCEL_FILE_PATH,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                st.error(f"Error preparing or writing data to Excel: {e}")
                st.subheader("Raw Data (Error Fallback)")
                st.json(all_data) # Display raw data if DataFrame/Excel writing failed

    elif not uploaded_files and analyze_button:
        st.warning("Please upload one or more CV files before analyzing.")
    elif not job_description and analyze_button:
        st.warning("Please enter a job description before analyzing.")

if __name__ == "__main__":
    main()







