from flask import request, jsonify
from flask_restful import Resource, abort
import datetime
import pytz

class GetJobDetails(Resource):
    def __init__(self, client, db, job_collection):
        super().__init__()
        self.client = client
        self.db = self.client[db]
        self.job_collection = self.db[job_collection]

    def get(self):
        job_id = request.args.get('job_id')
        print('----GetJobDetails----',job_id)
        if not job_id:
            return {"error": "Missing 'job_id' parameter"}, 400

        job_document = self.job_collection.find_one({"id": job_id}, {"_id": 0}) 
        ist = pytz.timezone('Asia/Kolkata')
        current_timestamp = datetime.datetime.now(ist).strftime("%Y-%m-%d %H:%M")
        deadline = job_document.get("deadLine")
        if current_timestamp > deadline:
            isActive = False
        else:
            isActive = True
        
        job_document["isActive"] = isActive
        if not job_document:
            return {"error": "Job not found"}, 404

        return job_document, 200
