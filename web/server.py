from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restful import Resource
import requests 

app = Flask(__name__)
CORS(app) 

#JUDGE0_URL = "https://judge0.scubey.com"

class StdRunCode(Resource):
    def post(self):
        data = request.get_json()
        
        source_code = data.get("source_code")
        language_id = data.get("language_id")
        stdin = data.get("input", "")
        
        if not source_code or not language_id:
            return jsonify({"error": "Missing required fields: source_code and language_id"}), 400
        
        submission_data = {
            "source_code": source_code,
            "language_id": language_id,  
            "stdin": stdin
        }
        
        judge0_endpoint = "https://judge0.scubey.com/submissions/?base64_encoded=false&wait=true"
        
        response = requests.post(judge0_endpoint, json=submission_data, headers={"Content-Type": "application/json"})
       
        if response.status_code not in (200, 201):
            return jsonify({"error": response.text}), response.status_code
        
        result = response.json()

        return jsonify(result)

