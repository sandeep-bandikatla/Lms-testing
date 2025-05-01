from flask import request
from flask_restful import Resource
from pymongo import MongoClient
import PyPDF2
import docx
import google.generativeai as genai 

API_KEY = 'AIzaSyBWz9JYmqiKMliiILiS-10A30W9YoEhkQs'
#'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'
genai.configure(api_key=API_KEY)

def extract_text_from_file(file):
    text = ''
    if file.filename.endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    elif file.filename.endswith('.docx'):
        doc = docx.Document(file)
        text = '\n'.join([p.text for p in doc.paragraphs])
    else:
        raise ValueError("Unsupported file format. Please upload a .pdf or .docx file.")

    # Count the number of words
    word_count = len(text.split())
    return text, word_count

def analyze_resume_with_gemini(resume_text):
    """Use Google Gemini API to analyze resume text for ATS scoring and feedback."""
    model = genai.GenerativeModel('gemini-1.5-pro') 

    prompt = f"""
    You are an ATS scoring assistant. Critically evaluate the following resume for a professional role. Provide the following:
    1. Extracted Skills: List all skills found in the resume as a comma-separated list.
    2. Missing Skills: List all relevant skills missing from the resume as a comma-separated list.
    3. ATS Score: Provide a numeric score (0-100) reflecting the resume's quality and relevance.
    4. Feedback: Provide actionable suggestions for improvement under these categories:
       - Skills
       - Sections
       - Formatting

    Use this format:
    - Extracted Skills: skill1, skill2, skill3, etc.
    - Missing Skills: skill1, skill2, skill3, etc.
    - ATS Score: XX.XX
    - Feedback:
       - Skills: <feedback>
       - Sections: <feedback>
       - Formatting: <feedback>
    Resume content:
    {resume_text}
    """

    try:
        response = model.generate_content(prompt)
        content = response.text  # Gemini returns text directly

        ats_score = None
        extracted_skills = []
        missing_skills = []
        feedback_sections = {"Skills": "", "Sections": "", "Formatting": ""}

        for line in content.splitlines():
            if "ATS Score:" in line:
                ats_score = round(float(line.split(":")[1].strip()), 2)
            elif "Extracted Skills:" in line:
                extracted_skills = [skill.strip() for skill in line.split(":")[1].split(",")]
            elif "Missing Skills:" in line:
                missing_skills = [skill.strip() for skill in line.split(":")[1].split(",")]
            elif "- Skills:" in line:
                feedback_sections["Skills"] = line.split(":", 1)[1].strip()
            elif "- Sections:" in line:
                feedback_sections["Sections"] = line.split(":", 1)[1].strip()
            elif "- Formatting:" in line:
                feedback_sections["Formatting"] = line.split(":", 1)[1].strip()

        return ats_score, extracted_skills, missing_skills, feedback_sections
    except Exception as e:
        return None, [], [], {"Error": str(e)}


class ATSCheck(Resource):
    def __init__(self, client, db, collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def post(self):
        file = request.files.get('resume')
        std_id = request.form.get('student_id')
        
        if file.filename == '':
            return {"error": "No file selected."}, 400
        # print('file-uploaded')
        try:
            resume_text, word_count = extract_text_from_file(file)
            ats_score, extracted_skills, suggesting_skills, feedback_sections = analyze_resume_with_gemini(resume_text)

            if self.collection.find_one({"std_Id":std_id}):
                self.collection.delete_one({"std_Id":std_id})

            self.collection.insert_one({"std_Id":std_id,
                "resume_text": resume_text,
                "ats_score": ats_score,
                "extracted_skills": extracted_skills,
                "suggesting_skills": suggesting_skills,
                "feedback_sections": feedback_sections,"word_count": word_count })

            return {
                "ats_score": ats_score,
                "extracted_skills": extracted_skills,
                "suggesting_skills": suggesting_skills,
                "feedback_sections": feedback_sections,
                "word_count": word_count  }, 200
        except Exception as e:
            return {"error": str(e)}, 500
    

    def get(self):
        id = request.args.get('student_id')

        if not id:
            return {"error":"missing required data"},404
        
        resume = self.collection.find_one({"std_Id":id})
        resume["_id"] = str(resume["_id"])
        
        return {"massage":"data found","Resume_data":resume},200
