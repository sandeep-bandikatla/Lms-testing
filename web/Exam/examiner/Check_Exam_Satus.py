from flask import request
from flask_restful import Resource
from pymongo import MongoClient
import json

# Load configuration from local file
with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)

MONGO_CONFIG = config_data['MONGO_CONFIG']['url']
client = MongoClient(MONGO_CONFIG)

# Access the database
db = client['codegnan_product']

class CheckExamStatus(Resource):
    def get(self):
        # Retrieve query parameters
        exam_type = request.args.get('examType')  # examType should match collection name, e.g. "Daily-Exam"
        exam_date = request.args.get('date')        # Expected format: "YYYY-MM-DD"
        batch = request.args.get('batch')           
        location = request.args.get('location')
        
        # Validate that required parameters are provided.
        if not exam_type or not exam_date:
            return {"error": "Missing required query parameters: examType and date"}, 400
        
        # Access the collection using the exam_type
        exam_collection = db[exam_type]
        
        # Search for any document with the given startDate
        exam_doc = exam_collection.find_one({"startDate": exam_date, "batch": batch, "location": location})
        
        # If found, respond with status true and a message; otherwise, status false.
        if exam_doc:
            return {
                "status": True,
                "message": f"Exam has already been scheduled for {batch} on {exam_date}"
            }, 409
        else:
            return {
                "status": False,
                "message": ""
            }, 200