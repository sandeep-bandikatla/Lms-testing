from flask import request
from flask_restful import Resource
from pymongo import MongoClient

class GetBatchwiseAttendance(Resource):
    def __init__(self, client, db, collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def get(self):
        batch = request.args.get('batch')
        location = request.args.get('location')
        
        if not  batch:
            return {"error": "Missing required fields"}, 400 

        attendance = list(self.collection.find({"$and":[{"batchNo": batch},{"location":location}]}))
        #print('view attendance:---',len(attendance),'------------',attendance)
        for attend in attendance:
            attend["_id"] = str(attend["_id"])
        return {"message":"Getting All Batchswise Attendance","data": attendance}, 200