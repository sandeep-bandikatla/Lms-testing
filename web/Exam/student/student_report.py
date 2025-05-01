from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from pymongo import MongoClient
import json

# Load configuration and create MongoDB client
with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)
MONGO_CONFIG = config_data['MONGO_CONFIG']['url']
client = MongoClient(MONGO_CONFIG)
db = client["codegnan_product"]

def error_response(message, status_code=400):
    response = jsonify({"success": False, "message": message})
    response.status_code = status_code
    return response

class StudentExamReports(Resource):
    def get(self):
        stdid = request.args.get("stdId")
        if not stdid:
            return error_response("Missing required query parameter: stdId", 400)
        
        # List of collections to query
        exam_collections = ["Daily-Exam", "Weekly-Exam", "Monthly-Exam"]
        results = {}
        
        for coll_name in exam_collections:
            collection = db[coll_name]
            # Fetch documents matching the given studentId
            documents = list(collection.find({"studentId": stdid}))
            # Convert ObjectId to string for JSON serialization
            for doc in documents:
                doc["_id"] = str(doc["_id"])
            # Store the results, even if the list is empty
            results[coll_name] = documents
        
        return jsonify({"success": True, "results": results})