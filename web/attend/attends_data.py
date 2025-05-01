from flask import request
from flask_restful import Resource
from pymongo import MongoClient
from datetime import datetime
import uuid

class AttendData(Resource):
    def __init__(self, client, db, collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def post(self):
        #print('--------------',request.json)
        course = request.json.get('subject')
        batchNo = request.json.get('batch')
        datetime = request.json.get('datetime')
        students = request.json.get('students')
        location = request.json.get('location')
        id = str(uuid.uuid4())

        if not (course and batchNo and students):
            return {"error": "Missing required fields"}, 400
        
        if self.collection.find_one({"batchNo": batchNo, "location": location,'datetime':datetime,'course':course}):
            return {"message": "Students Attendance with this batch and location already exists", "status": "duplicate"}, 409

        Attend_data = {
            "id":id,
            "course":course,
            "batchNo":batchNo,
            "students":students,
            "datetime":datetime,
            "location":location
        }
        result = self.collection.insert_one(Attend_data)
        Attend_data['_id'] = str(result.inserted_id)

        return {"message": "Students Attendance Recived",'Attendance':Attend_data,'status':"existed"}, 200
    
    """def get(self):
        attendance = list(self.collection.find({}))
        for attend in attendance:
            attend["_id"] = str(attend["_id"])
        return {"All Attendance": attendance}, 200"""