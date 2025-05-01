from flask import request
from flask_restful import Resource
from pymongo import MongoClient
from datetime import datetime

class EditJob(Resource):
    def __init__(self,client,db,job_collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.update_jobs = job_collection
        self.db = self.client[self.db_name]
        self.update_job = self.db[self.update_jobs]

    def post(self):
        data = request.get_json()
        print('*'*30,data)
        job_id = data.get("job_id")
        update_data = {
            "companyName":data.get('companyName'),
            "jobRole": data.get('jobRole'),
            "salary": data.get('salary'),
            "graduates": data.get('graduates',[]),
            "educationQualification": data.get('educationQualification'),
            "department": data.get('department',[]),
            "percentage": data.get('percentage'),
            "jobSkills": data.get("jobSkills", []),
            "jobLocation": data.get('jobLocation'),
            "specialNote": data.get("specialNote"),
            "bond": data.get('bond')}

        if not job_id:
            return {"error": "Missing required parameter: job_id"}, 400
        else:
            jobs = self.update_job.find_one({"id":job_id})

            if jobs:
                update_data = {k: v for k, v in update_data.items() if v is not None}
                self.update_job.update_one({"id": job_id},{"$set": update_data})
                return {"message": "Job list Updated successful", "userType":"BDE-User","job_id":job_id}, 200
            else:
                # Log or handle if a file is not found
                return {"message": "job list Not found with job_id","job_id":job_id}, 404
            