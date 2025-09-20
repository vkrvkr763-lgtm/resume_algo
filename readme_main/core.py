import fitz  # PyMuPDF for PDF reading
from io import BytesIO
from docx import Document
import re

STOP_WORDS = {
    'and', 'the', 'of', 'in', 'to', 'a', 'with', 'for', 'on',
    'is', 'are', 'that', 'by', 'as', 'this', 'an', 'or', 'at',
    'from', 'it', 'be', 'which', 'you', 'we'
}

MAX_RESUME_SIZE_MB = 200

KNOWN_SKILLS = {
    'python', 'java', 'sql', 'excel', 'machine learning', 'deep learning',
    'communication', 'teamwork', 'project management', 'docker', 'aws',
    'javascript', 'react', 'nodejs', 'git', 'linux'
}

def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"[core] Error reading PDF: {e}")
        return ""

def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        doc = Document(BytesIO(file_bytes))
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        print(f"[core] Error reading DOCX: {e}")
        return ""

def get_hard_match_score(resume_text: str, jd_text: str):
    jd_words_all = set(re.findall(r'\b\w+\b', jd_text.lower()))
    resume_words_all = set(re.findall(r'\b\w+\b', resume_text.lower()))
    
    jd_skills = {w for w in jd_words_all if w not in STOP_WORDS and w in KNOWN_SKILLS}
    resume_skills = {w for w in resume_words_all if w not in STOP_WORDS and w in KNOWN_SKILLS}

    if not jd_skills:
        return 0.0, [], []

    matched = resume_skills.intersection(jd_skills)
    missing = jd_skills.difference(resume_skills)

    score = (len(matched) / len(jd_skills)) * 50

    return score, sorted(list(matched)), sorted(list(missing))

def is_too_large(file_bytes: bytes) -> bool:
    size_mb = len(file_bytes) / (1024 * 1024)
    return size_mb > MAX_RESUME_SIZE_MB

def format_skills_list(skills_list):
    if not skills_list:
        return "None"
    return ", ".join(skills_list)

def generate_feedback(score, matched, missing):
    feedback = []
    feedback.append(f"Match Score: {score:.1f}/50")
    if matched:
        feedback.append(f"Skills matched: {', '.join(matched)}")
    else:
        feedback.append("No skills matched from the JD.")
    if missing:
        feedback.append(f"Skills missing: {', '.join(missing)}")
    else:
        feedback.append("No skills missing. Good fit!")

    # Limit feedback to max 3 lines
    return "\n".join(feedback[:3])

# === Example usage ===
if __name__ == "__main__":
    resume_text = "Experienced Python developer with knowledge of AWS, Docker, and Machine Learning."
    jd_text = "Looking for a Python developer skilled in Docker, AWS, and communication."

    score, matched, missing = get_hard_match_score(resume_text, jd_text)
    feedback = generate_feedback(score, matched, missing)

    print(feedback)
