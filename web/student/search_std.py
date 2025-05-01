from flask import Flask, send_file, request, abort, make_response
from flask_restful import Resource
from pymongo import MongoClient
from gridfs import GridFS
import json
import base64

with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)
MONGO_CONFIG = config_data['MONGO_CONFIG']['url']
client = MongoClient(MONGO_CONFIG)
db = client["codegnan_product"]

class Search_student(Resource):
    def __init__(self, client, db, std_collection, job_collection, attendance):
        super().__init__()
        self.client = client
        self.db_name = db
        self.std_collection = std_collection
        self.job_collection = job_collection
        self.attendance = attendance
        self.db = self.client[self.db_name]
        self.job_collection = self.db[self.job_collection]
        self.std_collection = self.db[self.std_collection]
        self.attend_collection = self.db[self.attendance]
        self.fs = GridFS(self.db)

    def get(self):
        std_id = request.args.get('studentId')
        location = request.args.get('location')

        if not std_id:
            return {"error": "Student ID is required"}, 400

        # Fetch student data once
        student_data = self.std_collection.find_one({"studentId": std_id, "location": location})
        if not student_data:
            return {"error": "Student not found"}, 404
        student_data["_id"] = str(student_data["_id"])

        # Profile Picture
        profile = None
        try:
            pic = self.fs.find_one({'filename': std_id})
            if pic:
                profile = base64.b64encode(pic.read()).decode('utf-8')
        except Exception as e:
            print(f"Fetching image from DB failed: {e}")

        # Attendance Records
        Attends_data = []
        attendance_cursor = self.attend_collection.find({
            "students.studentId": std_id,
            "location": location
        })
        for attend in attendance_cursor:
            student_attendance = next((s for s in attend.get("students", []) if s["studentId"] == std_id), None)
            if student_attendance:
                Attends_data.append({
                    "studentId": student_attendance['studentId'],
                    "course": attend.get('course'),
                    "batchNo": attend.get('batchNo'),
                    "name": student_attendance.get('name'),
                    "status": student_attendance.get('status'),
                    "remarks": student_attendance.get('remarks'),
                    "datetime": attend.get('datetime'),
                    "location": attend.get('location')
                })

        # --- Aggregated Exam Results ---
        exam_collections = ["Daily-Exam", "Weekly-Exam", "Monthly-Exam"]
        aggregated_data = {}

        for coll_name in exam_collections:
            collection = self.db[coll_name]

            pipeline = [
                {"$match": {"studentId": student_data["id"]}},
                {"$lookup": {
                    "from": "student_login_details",
                    "localField": "studentId",
                    "foreignField": "id",
                    "as": "student"
                }},
                {"$unwind": "$student"},
                {"$project": {
                    "examName": 1,
                    "totalExamTime": 1,
                    "startDate": 1,
                    "startTime": 1,
                    "attempt-status": 1,
                    "paper": 1,
                    "analysis": 1,
                    "batch": 1,
                    "location": 1,
                    "student.name": 1,
                    "student.studentId": 1,
                    "student.id": 1,
                    "student.studentPhNumber": 1
                }}
            ]

            exams = list(collection.aggregate(pipeline))
            for exam in exams:
                student_info = exam.get("student", {})
                student_id = student_info.get("id")
                exam_name = exam.get("examName")
                if not student_id or not exam_name:
                    continue

                composite_key = f"{student_id}_{exam_name}"
                if composite_key not in aggregated_data:
                    aggregated_data[composite_key] = {
                        "student": {
                            "id": student_info.get("id"),
                            "name": student_info.get("name"),
                            "studentId": student_info.get("studentId"),
                            "phNumber": student_info.get("studentPhNumber")
                        },
                        "subjects": {},
                        "examDetails": {
                            "examName": exam_name,
                            "startDate": exam.get("startDate"),
                            "startTime": exam.get("startTime"),
                            "totalExamTime": exam.get("totalExamTime"),
                            "batch": exam.get("batch"),
                            "location": exam.get("location")
                        }
                    }

                paper_subjects = exam.get("paper", [])
                analysis_info = exam.get("analysis", {})
                analysis_details = analysis_info.get("details", [])

                subject_map = {}
                subjects_summary = aggregated_data[composite_key]["subjects"]

                def init_subject(subject_name):
                    if subject_name not in subjects_summary:
                        subjects_summary[subject_name] = {
                            "max_mcq_marks": 0,
                            "obtained_mcq_marks": 0,
                            "max_code_marks": 0,
                            "obtained_code_marks": 0
                        }

                for subject_data in paper_subjects:
                    subj_name = subject_data.get("subject", "UnknownSubject")
                    init_subject(subj_name)

                    for mcq in subject_data.get("MCQs", []):
                        q_id = mcq.get("questionId")
                        score_value = mcq.get("Score", 1)
                        subjects_summary[subj_name]["max_mcq_marks"] += score_value
                        subject_map[q_id] = {"subject": subj_name, "type": "mcq", "score": score_value}

                    for code_q in subject_data.get("Coding", []):
                        q_id = code_q.get("questionId")
                        score_value = code_q.get("Score", 1)
                        subjects_summary[subj_name]["max_code_marks"] += int(score_value)
                        subject_map[q_id] = {"subject": subj_name, "type": "code", "score": score_value}

                for detail in analysis_details:
                    q_id = detail.get("questionId")
                    score_awarded = detail.get("scoreAwarded", 0)
                    if q_id in subject_map:
                        subj_name = subject_map[q_id]["subject"]
                        q_type = subject_map[q_id]["type"]
                        if q_type == "mcq":
                            subjects_summary[subj_name]["obtained_mcq_marks"] += score_awarded
                        else:
                            subjects_summary[subj_name]["obtained_code_marks"] += score_awarded

        reports = list(aggregated_data.values())
        exam_results = {
            "success": True,
            "studentId": student_data["id"],
            "reports": reports
        }

        # Job Eligibility
        student_skills = student_data.get("studentSkills", [])
        applied_jobs = student_data.get("applied_jobs", [])
        all_jobs = list(self.job_collection.find())
        for job in all_jobs:
            job["_id"] = str(job["_id"])
        eligible_jobs = [job for job in all_jobs if set(job.get("jobSkills", [])).issubset(set(student_skills))]

        if not applied_jobs:
            return {
                "message": "Student found but hasn't applied to any jobs.",
                "student_data": student_data,
                "Attendance": Attends_data,
                "eligible_jobs_details": eligible_jobs,
                "Exam_Results": exam_results,
                "profile": profile
            }, 200

        applied_jobs_data = list(self.job_collection.find({"id": {"$in": applied_jobs}}, {"password": 0}))
        for job in applied_jobs_data:
            job["_id"] = str(job["_id"])
            job["applicants_ids"] = [str(app_id) for app_id in job.get("applicants_ids", [])]

        return {
            "message": "Student found and job details retrieved",
            "student_data": student_data,
            "applied_jobs_list": len(applied_jobs),
            "eligible_jobs_list": len(eligible_jobs),
            "applied_jobs_details": applied_jobs_data,
            "eligible_jobs_details": eligible_jobs,
            "Attendance": Attends_data,
            "Exam_Results": exam_results,
            "profile": profile
        }, 200
