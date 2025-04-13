# CV Analyzer using Gemini AI, Flask, and Streamlit

This project analyzes uploaded CVs (in PDF format) against a provided job description using Google's Gemini AI . It provides a match score (1-10), detailed reasoning for the score, and extracts key information like contact details, skills, education, and work history.

The system is built with a decoupled architecture:

*   **Backend:** A Flask API that handles communication with the Google Gemini API for the core analysis.
*   **Frontend:** A Streamlit web application that provides the user interface for uploading CVs, entering job descriptions, displaying results, and saving reports.

## Features

*   Upload multiple CVs simultaneously (PDF format).
*   Input a detailed job description.
*   Extracts text content from uploaded PDF files.
*   Sends CV text and job description to a Flask backend API.
*   Backend API utilizes Google Gemini AI  for analysis.
*   AI provides structured JSON output containing:
    *   Personal Info (Name, Email, Phone)
    *   Skills (List relevant to the job description)
    *   Education History
    *   Work History
    *   Match Score (1-10 rating of CV fit for the job)
    *   Match Reasons (Key factors influencing the score)
    *   Consideration (Detailed HR-style motivation for the score)
*   Frontend displays analysis results for each CV.
*   Aggregates results from all analyzed CVs.
*   Saves the aggregated analysis results to an Excel file (`.xlsx`).


