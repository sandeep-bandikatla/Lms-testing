from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from pymongo import MongoClient
import json
from bson import ObjectId  # For converting ObjectId to string

# Load Config
with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)

MONGO_CONFIG = config_data['MONGO_CONFIG']['url']
client = MongoClient(MONGO_CONFIG)
db = client["codegnan_product"]

def error_response(message, status_code=400):
    """Helper function to generate error responses."""
    response = jsonify({"success": False, "message": message})
    response.status_code = status_code
    return response

def json_serializable(data):
    """Convert MongoDB documents to JSON serializable format."""
    if isinstance(data, list):
        return [json_serializable(item) for item in data]
    elif isinstance(data, dict):
        return {key: json_serializable(value) for key, value in data.items()}
    elif isinstance(data, ObjectId):
        return str(data)  # Convert ObjectId to string
    return data

class GetAvailableExams(Resource):
    """API to fetch available exams based on studentId from multiple collections."""

    def get(self):
        try:
            student_id = request.args.get("studentId")
            if not student_id:
                return error_response("'studentId' parameter is required.", 400)
            
            # Collections to query; currently only "Daily-Exam" is enabled.
            collections = ["Daily-Exam"]
            exams_data = {}

            # Retrieve the following fields plus "paper" (to compute subjects) and "attempt-status".
            projection = {
                "examId": 1,
                "examName": 1,
                "startDate": 1,
                "startTime": 1,
                "totalExamTime": 1,
                "attempt-status": 1,
                "subjects": 1,
                "paper": 1
            }

            for collection in collections:
                exams = list(
                    db[collection]
                    .find({"studentId": student_id}, projection)
                    .sort("startDate", -1)
                    .limit(4)
                )
                
                result_list = []
                for exam in exams:
                    # Compute subjects: check "paper" field first; if not available, use the top-level "subjects" field.
                    if exam.get("paper") and isinstance(exam.get("paper"), list) and exam.get("paper"):
                        subject_list = [
                            item.get("subject")
                            for item in exam.get("paper")
                            if item.get("subject")
                        ]
                    elif exam.get("subjects") and isinstance(exam.get("subjects"), list) and exam.get("subjects"):
                        subject_list = [
                            item.get("subject")
                            for item in exam.get("subjects")
                            if item.get("subject")
                        ]
                    else:
                        subject_list = []
                    
                    exam_info = {
                        "_id": str(exam.get("_id")),
                        "examId": exam.get("examId"),
                        "examName": exam.get("examName"),
                        "totalExamTime": exam.get("totalExamTime"),
                        "startDate": exam.get("startDate"),
                        "startTime": exam.get("startTime"),
                        "attempt-status": exam.get("attempt-status"),
                        "subjects": subject_list
                    }
                    result_list.append(exam_info)
                
                exams_data[collection] = result_list
            
            return {"success": True, "message": "Exams Fetched Successfully", "exams": exams_data}, 200

        except Exception as e:
            return error_response(f"Error fetching available exams: {str(e)}", 500)
