import pymongo
from flask_restful import Resource, reqparse
import datetime
import pytz



class ListOpenings(Resource):
    def __init__(self, client, db, collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def get(self):

        if self.db_name not in self.client.list_database_names():
            self.client[self.db_name]

        # Check if the collection exists, if not, create it
        if self.collection_name not in self.db.list_collection_names():
            self.db.create_collection(self.collection_name)
            
        job_documents = self.collection.find()

        # Prepare the list of job dictionaries
        job_list = []
        

        ist = pytz.timezone('Asia/Kolkata')
        current_timestamp = datetime.datetime.now(ist).strftime("%Y-%m-%d %H:%M")
        for job_document in job_documents:

            deadline = job_document.get("deadLine")
    
            # Compare current timestamp with deadline
            if current_timestamp > deadline:
                isActive = False
            else:
                isActive = True
            job_dict = {
                "job_id": job_document.get('id'),
                "companyName": job_document.get('companyName'),
                "jobRole": job_document.get('jobRole'),
                "graduates": job_document.get('graduates'),
                "salary": job_document.get('salary'),
                "educationQualification": job_document.get('educationQualification'),
                "department": job_document.get('department'),
                "percentage": job_document.get('percentage'),
                "technologies": job_document.get('jobSkills'),
                "bond": job_document.get('bond'),
                "jobLocation": job_document.get('jobLocation'),
                "specialNote": job_document.get('specialNote'),
                "deadLine": job_document.get("deadLine"),
                "isActive": isActive
            }
            job_list.append(job_dict)
        job_list.reverse()
        return {"jobs": job_list}, 200
