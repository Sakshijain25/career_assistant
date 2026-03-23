import streamlit as st
import pdfplumber
import requests
import google.generativeai as genai
import json
import re
import os
from dotenv import load_dotenv

# -------------------- CONFIG --------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print("GEMINI_API_KEY:", GEMINI_API_KEY)  # Debugging line

genai.configure(api_key=GEMINI_API_KEY)

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
def extract_skills(text):
    prompt = f"""
    You are an expert ATS (Applicant Tracking System).

    Analyze this resume and extract:
    1. Top skills (technical + soft skills)
    2. Experience level (Beginner / Intermediate / Expert)
    3. Suitable job roles

    Return ONLY valid JSON:
    {{
        "skills": [],
        "experience": "",
        "roles": []
    }}

    Resume:
    {text}
    """

    response = model.generate_content(prompt)
    return response.text


# -------------------- FETCH JOBS --------------------
def fetch_jobs():
    url = "https://remoteok.com/api"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    return response.json()


# -------------------- MATCH JOBS --------------------
def match_jobs(skills, jobs):
    matched = []

    for job in jobs:
        if not isinstance(job, dict):
            continue

        description = str(job.get("description", "")).lower()
        score = 0

        for skill in skills:
            if skill.lower() in description:
                score += 1

        if score > 0:
            matched.append({
                "title": job.get("position"),
                "company": job.get("company"),
                "score": score,
                "link": job.get("url")
            })

    return sorted(matched, key=lambda x: x["score"], reverse=True)[:10]


# -------------------- STREAMLIT UI --------------------
st.set_page_config(page_title="AI Job Agent", page_icon="🚀")

st.title("🚀 AI Job Matching Agent (Gemini Powered)")

uploaded_file = st.file_uploader("Upload your resume (PDF)")

if uploaded_file:
    st.info("Reading your resume...")
    text = extract_text_from_pdf(uploaded_file)

    st.info("Analyzing with AI...")
    result = extract_skills(text)

    data = clean_json(result)

    skills = data.get("skills", [])
    experience = data.get("experience", "")
    roles = data.get("roles", [])

    st.subheader("🧠 Extracted Info")
    st.write("**Skills:**", skills)
    st.write("**Experience Level:**", experience)
    st.write("**Suggested Roles:**", roles)

    st.info("Fetching jobs...")
    jobs = fetch_jobs()

    st.info("Matching jobs for you...")
    matches = match_jobs(skills, jobs)

    st.subheader("🔥 Top Job Matches")

    if matches:
        for job in matches:
            st.write(f"### {job['title']} at {job['company']}")
            st.write(f"Match Score: {job['score']}")
            st.write(job['link'])
            st.write("---")
    else:
        st.warning("No strong matches found. Try improving your resume.")