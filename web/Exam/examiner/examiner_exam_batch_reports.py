from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from pymongo import MongoClient
import json

# Load configuration and connect to MongoDB.
with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)

MONGO_CONFIG = config_data['MONGO_CONFIG']['url']
client = MongoClient(MONGO_CONFIG)
db = client["codegnan_product"]

def error_response(message, status_code=400):
    response = jsonify({"success": False, "message": message})
    response.status_code = status_code
    return response

class ExaminerBatchReports(Resource):
    def get(self):
        try:
            # Extract required parameter: batch.
            batch = request.args.get("batch")
            if not batch:
                return error_response("Missing required query parameter: batch", 400)
            
            # Optional parameter: examName.
            examName = request.args.get("examName")
            
            # Build the match filter. If examName is provided, filter by it; otherwise, retrieve all exams for the batch.
            match_filter = {"batch": batch}
            if examName:
                match_filter["examName"] = examName
            
            # Aggregation pipeline to join student details.
            pipeline = [
                {"$match": match_filter},
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
            
            exams = list(db["Daily-Exam"].aggregate(pipeline))
            if not exams:
                msg = f"No exam records found for batch {batch}"
                if examName:
                    msg += f" and examName {examName}"
                return error_response(msg, 404)
            
            # Instead of merging by student alone, use a composite key: student id + examName.
            aggregated_data = {}
            for exam in exams:
                student_info = exam.get("student", {})
                student_id = student_info.get("id")
                exam_name = exam.get("examName")
                if not student_id or not exam_name:
                    continue

                # Use a composite key so that each exam session is treated separately.
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
                            "totalExamTime": exam.get("totalExamTime")
                        }
                    }
                
                # Process exam paper and analysis details for this exam record.
                paper_subjects = exam.get("paper", [])
                analysis_info = exam.get("analysis", {})
                analysis_details = analysis_info.get("details", [])
                
                # Local helper structures.
                subject_map = {}      # Maps questionId -> {subject, type, score}
                subjects_summary = {} # Summary for this exam session.
                
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
                    
                    # Process MCQs.
                    for mcq in subject_data.get("MCQs", []):
                        q_id = mcq.get("questionId")
                        score_value = mcq.get("Score", 1)
                        subjects_summary[subj_name]["max_mcq_marks"] += score_value
                        subject_map[q_id] = {"subject": subj_name, "type": "mcq", "score": score_value}
                    
                    # Process Coding questions.
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
                
                # Assign the subjects summary for this composite key.
                aggregated_data[composite_key]["subjects"] = subjects_summary
            
            reports = list(aggregated_data.values())
            result = {"success": True, "batch": batch, "reports": reports}
            if examName:
                result["examName"] = examName
            return jsonify(result)
        except Exception as e:
            return error_response(str(e), 500)