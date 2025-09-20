import os
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
import re
from dotenv import load_dotenv

from core import (
    extract_text_from_pdf,
    extract_text_from_docx,
    get_hard_match_score,
    is_too_large,
    format_skills_list
)
from llm_manager import get_semantic_match_score, get_feedback_and_suggestions

# load .env
load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/analyze_resumes', methods=['POST'])
def analyze_resumes():
    data = request.get_json()
    job_description_data = data.get('job_description', '')
    resumes_data = data.get('resumes', [])

    if not job_description_data or not resumes_data:
        return jsonify({"error": "Missing job description or resume files"}), 400

    # Process job description
    job_description_text = ""
    if isinstance(job_description_data, str) and job_description_data.startswith("data:"):
        try:
            header, jd_base64 = job_description_data.split(',', 1)
            jd_bytes = base64.b64decode(jd_base64)
            header_lower = header.lower()
            if header_lower.startswith('data:application/pdf'):
                job_description_text = extract_text_from_pdf(jd_bytes)
            elif header_lower.startswith('data:application/vnd.openxmlformats-officedocument.wordprocessingml.document'):
                job_description_text = extract_text_from_docx(jd_bytes)
            else:
                job_description_text = ""
        except Exception as e:
            return jsonify({"error": f"Failed to parse job description file: {e}"}), 400
    else:
        # assume plain text
        job_description_text = job_description_data

    if not job_description_text.strip():
        return jsonify({"error": "Job description is empty or unreadable"}), 400

    results = []
    for res in resumes_data:
        file_name = res.get('fileName')
        content = res.get('content')
        if not file_name or not content:
            continue
        try:
            header, base64_content = content.split(',', 1)
            file_bytes = base64.b64decode(base64_content)
        except Exception as e:
            results.append({
                "resumeName": file_name,
                "candidateName": "N/A",
                "candidateEmail": "N/A",
                "score": 0,
                "verdict": "Low",
                "matchedSkills": [],
                "matchedSkillsFormatted": "None",
                "missingSkills": [],
                "missingSkillsFormatted": "None",
                "suggestions": "Could not decode resume file content."
            })
            continue

        # Check file size limit
        if is_too_large(file_bytes):
            results.append({
                "resumeName": file_name,
                "candidateName": "N/A",
                "candidateEmail": "N/A",
                "score": 0,
                "verdict": "Low",
                "matchedSkills": [],
                "matchedSkillsFormatted": "None",
                "missingSkills": [],
                "missingSkillsFormatted": "None",
                "suggestions": f"Resume file too large (>{MAX_RESUME_SIZE_MB} MB)."
            })
            continue

        resume_text = ""
        lname = file_name.lower()
        if lname.endswith('.pdf'):
            resume_text = extract_text_from_pdf(file_bytes)
        elif lname.endswith('.docx'):
            resume_text = extract_text_from_docx(file_bytes)
        else:
            resume_text = ""

        if not resume_text.strip():
            results.append({
                "resumeName": file_name,
                "candidateName": "N/A",
                "candidateEmail": "N/A",
                "score": 0,
                "verdict": "Low",
                "matchedSkills": [],
                "matchedSkillsFormatted": "None",
                "missingSkills": [],
                "missingSkillsFormatted": "None",
                "suggestions": "Resume file could not be read or unsupported format."
            })
            continue

        # Extract name heuristic
        candidate_name = "N/A"
        lines = resume_text.strip().splitlines()
        for line in lines[:5]:
            line_stripped = line.strip()
            if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$', line_stripped):
                candidate_name = line_stripped
                break

        # Extract email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', resume_text)
        candidate_email = email_match.group(0) if email_match else "N/A"

        # Scores and suggestions
        hard_score, matched_skills, missing_skills = get_hard_match_score(resume_text, job_description_text)
        semantic_score = get_semantic_match_score(resume_text, job_description_text)
        suggestions = get_feedback_and_suggestions(resume_text, job_description_text)

        total_score = round(hard_score + semantic_score)
        if total_score >= 80:
            verdict = "High"
        elif total_score >= 50:
            verdict = "Medium"
        else:
            verdict = "Low"

        results.append({
            "resumeName": file_name,
            "candidateName": candidate_name,
            "candidateEmail": candidate_email,
            "score": total_score,
            "verdict": verdict,
            "matchedSkills": matched_skills,
            "matchedSkillsFormatted": format_skills_list(matched_skills),
            "missingSkills": missing_skills,
            "missingSkillsFormatted": format_skills_list(missing_skills),
            "suggestions": suggestions
        })

    return jsonify(results), 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    if not os.getenv("GOOGLE_API_KEY"):
        print("[app.py] Warning: GOOGLE_API_KEY not set; semantic scoring and suggestions will be disabled.")
    app.run(host='0.0.0.0', port=port, debug=True)
