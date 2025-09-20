import os
import re
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI

# Initialize LLM
llm = None
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest",
            google_api_key=GOOGLE_API_KEY
        )
    except Exception as e:
        print(f"[llm_manager] Failed to initialize LLM: {e}")
else:
    print("[llm_manager] GOOGLE_API_KEY not configured.")

def get_semantic_match_score(resume_text: str, jd_text: str) -> float:
    """Return a float score from 0 to 50."""
    if llm is None:
        return 0.0
    try:
        prompt_template = PromptTemplate.from_template(
            """You are an assistant to evaluate how well a candidate's resume matches a job description.
Provide a relevance score (integer) from 0 to 100, where 100 means perfect match. 
**Respond ONLY with one integer.**

Resume:
{resume}

Job Description:
{jd}
"""
        )
        chain = LLMChain(llm=llm, prompt=prompt_template)
        response = chain.invoke({"resume": resume_text, "jd": jd_text})
        text = response.get("text", "").strip()
        m = re.search(r'\d+', text)
        if m:
            val = int(m.group())
            # clamp
            if val < 0:
                val = 0
            elif val > 100:
                val = 100
            # normalize to 0–50
            return val * 0.5
        else:
            # fallback
            return 25.0
    except Exception as e:
        print(f"[llm_manager] Error in get_semantic_match_score: {e}")
        return 0.0

def get_feedback_and_suggestions(resume_text: str, jd_text: str) -> str:
    if llm is None:
        return "LLM not available. Please set the GOOGLE_API_KEY."
    try:
        prompt_template = PromptTemplate.from_template(
            """You are a resume improvement advisor. Compare the candidate’s resume to the job description.
Provide **bullet point suggestions** to help the candidate improve the resume, focusing on:
- missing technical AND soft skills
- relevant project or experience highlighting
- using terminology from the JD
- formatting and clarity if needed

Respond with bullet points only.
Job Description:
{jd}

Resume:
{resume}

Suggestions:
"""
        )
        chain = LLMChain(llm=llm, prompt=prompt_template)
        response = chain.invoke({"resume": resume_text, "jd": jd_text})
        text = response.get("text", "").strip()

        # Limit to max 3 lines for feedback display
        lines = text.splitlines()
        limited_text = "\n".join(lines[:3]) if len(lines) > 3 else text

        return limited_text
    except Exception as e:
        print(f"[llm_manager] Error in get_feedback_and_suggestions: {e}")
        return "Could not generate suggestions due to an error."
