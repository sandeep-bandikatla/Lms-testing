from flask import request, jsonify
from flask_restful import Resource
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

class ExaminerExamDayList(Resource):
    def get(self):
        try:
            # Extract query parameters from the GET request URL.
            batch = request.args.get("batch")
            location = request.args.get("location")
            
            if not all([batch, location]):
                return error_response("Missing required query parameters: batch or location", 400)
            
            # Query to return minimal fields (examName and batch) from Daily-Exam.
            exams = list(db["Daily-Exam"].find(
                {"batch": batch, "location": location},
                {"examName": 1, "batch": 1}
            ))
            
            if not exams:
                return error_response("No exam records found for the given batch and location", 404)
            
            # Remove duplicate exam names.
            unique_exam_names = set()
            exam_list = []
            for exam in exams:
                exam_name = exam.get("examName")
                exam_batch = exam.get("batch")
                if exam_name and exam_name not in unique_exam_names:
                    unique_exam_names.add(exam_name)
                    exam_list.append({"examName": exam_name, "batch": exam_batch})
            
            return jsonify({"success": True, "exams": exam_list})
        except Exception as e:
            return error_response(str(e), 500)