import os
import json
import google.generativeai as genai
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- Configuration & Setup ---
load_dotenv() 

# Configure Gemini AI
api_key = os.getenv("GEMINI_API_KEY")
gemini_configured = False
model = None
if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        gemini_configured = True
        print("Gemini AI Configured Successfully.")
    except Exception as e:
        print(f"Error configuring Gemini AI: {e}")
else:
    print("Error: GEMINI_API_KEY not found in environment variables.")

# Load Prompt Template
PROMPT_FILE_PATH = "prompt.txt"
HR_PROMPT_TEMPLATE = ""
try:
    with open(PROMPT_FILE_PATH, 'r', encoding='utf-8') as f:
        HR_PROMPT_TEMPLATE = f.read()
    print(f"HR Prompt Template Loaded Successfully from {PROMPT_FILE_PATH}.")
except FileNotFoundError:
    print(f"Error: Prompt file '{PROMPT_FILE_PATH}' not found in the current directory.")
except Exception as e:
    print(f"Error reading prompt file '{PROMPT_FILE_PATH}': {e}")

# Create Flask App
app = Flask(__name__)

# --- Helper Function (Internal Analysis Logic) ---
def analyze_cv_internal(cv_text, job_description):
    """Internal function to perform CV analysis using Gemini."""
    if not gemini_configured:
        print("Error: Gemini AI not configured.")
        return {"error": "Gemini AI is not configured on the server."}
    if not HR_PROMPT_TEMPLATE:
        print("Error: HR Prompt template missing.")
        return {"error": "HR Prompt template is missing or empty on the server."}
    if not model:
        print("Error: Gemini model not initialized.")
        return {"error": "Gemini model not initialized."}

    # Construct the full prompt
    prompt = f"""
{HR_PROMPT_TEMPLATE}

---
CV:
{cv_text}
---
Job Description:
{job_description}
---

Please provide ONLY a JSON response with the following structure (do NOT include any surrounding text, markdown formatting like ```json, or explanations):
{{
    "personal_info": {{
        "name": "string (extract from CV)",
        "email": "string (extract from CV)",
        "phone": "string (extract from CV)"
    }},
    "skills": ["list of strings (relevant skills from CV based on job description)"],
    "education": [
        {{ "degree": "string", "university": "string", "graduation_year": "string (optional)" }}
    ],
    "work_history": [
        {{ "title": "string", "company": "string", "duration": "string (e.g., YYYY-YYYY or X years)" }}
    ],
    "match_score": number (1-10 integer rating based on job fit),
    "match_reasons": ["list of strings (key reasons for the match score, comparing CV to Job Desc)"],
    "consideration": "string (detailed motivation for the match_score based on CV vs Job Description analysis)"
}}
"""
    try:
        print("Sending request to Gemini API...")
        response = model.generate_content(prompt)
        print("Received response from Gemini API.")

        try:
            json_string = response.text.strip()
            if json_string.startswith("```json"):
                json_string = json_string[len("```json"):].strip()
            if json_string.endswith("```"):
                json_string = json_string[:-len("```")].strip()

            analysis_result = json.loads(json_string)
            print("Successfully parsed JSON response.")
            return analysis_result

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {e}")
            print(f"Raw response received that caused decoding error:\n---\n{response.text}\n---")
            return {
                "error": "Failed to decode JSON response from AI. The AI might not have followed the JSON format instruction.",
                "raw_response_snippet": response.text[:500]
            }
        except AttributeError:
             print("Received invalid response object structure from Gemini (no 'text' attribute).")
             print(f"Raw Response Object: {response}")
             return {"error": "Received invalid response object structure from AI."}

    except Exception as e:
        print(f"Error calling Gemini API: {str(e)}")
        return {"error": f"An error occurred during AI analysis: {str(e)}"}


# --- API Endpoint ---

@app.route('/analyze', methods=['POST'])
def analyze_cv_endpoint():
    """API endpoint to analyze a CV against a job description."""
    if not request.is_json:
        print("Received non-JSON request.")
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    cv_text = data.get('cv_text')
    job_description = data.get('job_description')

    if not cv_text or not job_description:
        print("Missing required fields in request.")
        return jsonify({"error": "Missing 'cv_text' or 'job_description' in request body"}), 400

    print(f"Received analysis request. CV length: {len(cv_text)}, Job Desc length: {len(job_description)}")
    analysis_result = analyze_cv_internal(cv_text, job_description)

    if isinstance(analysis_result, dict) and 'error' in analysis_result:
         print(f"Analysis failed: {analysis_result['error']}")
         return jsonify(analysis_result), 500

    print("Analysis complete. Sending successful response.")
    return jsonify(analysis_result), 200




@app.route('/', methods=['GET'])
def root():
    """Basic endpoint to confirm the API is running."""
    print("Root path '/' accessed.")
    return jsonify({
        "message": "CV Analysis API is running.",
        "status": "OK",
        "endpoints": {
            "/analyze": "POST request with {'cv_text': '...', 'job_description': '...'}"
        }
    }), 200



# --- Run the App ---
if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=True) 






