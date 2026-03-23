import streamlit as st
import pdfplumber
import requests
import google.generativeai as genai
import json
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# -------------------- CONFIG --------------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

# -------------------- PDF TEXT EXTRACTION --------------------
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text


# -------------------- CLEAN JSON --------------------
def clean_json(response_text):
    try:
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    return {}


# -------------------- GEMINI: EXTRACT SKILLS --------------------
def extract_info(text):
    prompt = f"""
    You are an expert ATS system.

    Analyze the resume and extract:
    1. Skills
    2. Experience level
    3. Suitable roles

    Return ONLY JSON:
    {{
        "skills": [],
        "experience": "",
        "roles": []
    }}

    Resume:
    {text}
    """

    response = model.generate_content(prompt)
    return clean_json(response.text)


# -------------------- FETCH JOBS --------------------
def fetch_jobs():
    url = "https://remoteok.com/api"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    return response.json()


# -------------------- AI MATCH SCORING --------------------
def ai_match_score(resume_text, job):
    job_desc = f"""
    Job Title: {job.get("position")}
    Company: {job.get("company")}
    Description: {job.get("description")}
    """

    prompt = f"""
    You are an expert recruiter.

    Compare the resume with the job description.

    Give:
    1. Match score (0-100)
    2. Short reason
    3. Missing important skills

    Return ONLY JSON:
    {{
        "score": number,
        "reason": "",
        "missing_skills": []
    }}

    Resume:
    {resume_text}

    Job:
    {job_desc}
    """

    response = model.generate_content(prompt)
    return clean_json(response.text)


# -------------------- AI MATCH JOBS --------------------
def ai_match_jobs(resume_text, jobs):
    results = []

    for job in jobs[:10]:  # limit to reduce API cost
        if not isinstance(job, dict):
            continue

        data = ai_match_score(resume_text, job)

        results.append({
            "title": job.get("position"),
            "company": job.get("company"),
            "score": data.get("score", 0),
            "reason": data.get("reason", ""),
            "missing": data.get("missing_skills", []),
            "link": job.get("url")
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)


# -------------------- STREAMLIT UI --------------------
st.set_page_config(page_title="AI Job Agent", page_icon="🚀")

st.title("🚀 AI Job Matching Agent (Gemini + AI Scoring)")

uploaded_file = st.file_uploader("Upload your resume (PDF)")

if uploaded_file:
    st.info("📄 Reading resume...")
    resume_text = extract_text_from_pdf(uploaded_file)

    st.info("🧠 Extracting info with AI...")
    info = extract_info(resume_text)

    st.subheader("🧠 Extracted Profile")
    st.write("**Skills:**", info.get("skills", []))
    st.write("**Experience:**", info.get("experience", ""))
    st.write("**Roles:**", info.get("roles", []))

    st.info("🌍 Fetching jobs...")
    jobs = fetch_jobs()

    st.info("🤖 AI is matching jobs (this may take ~10–20 sec)...")
    matches = ai_match_jobs(resume_text, jobs)

    st.subheader("🔥 Top AI-Matched Jobs")

    if matches:
        for job in matches:
            st.write(f"### {job['title']} at {job['company']}")
            st.write(f"✅ Match Score: {job['score']}/100")
            st.write(f"💡 Reason: {job['reason']}")
            st.write(f"⚠️ Missing Skills: {job['missing']}")
            st.write(job['link'])
            st.write("---")
    else:
        st.warning("No matches found. Try a different resume.")