from flask import request
from flask_restful import Resource
from pymongo import MongoClient
from datetime import datetime

class GetAttendance(Resource):
    def __init__(self, client, db, collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def get(self):
        course = request.args.get('subject')
        batch = request.args.get('batch')
        location = request.args.get('location')
        
        if not  batch:
            return {"error": "Missing required fields"}, 400 

        attendance = list(self.collection.find({"$and":[{"course":course},{"batchNo": batch},{"location":location}]},{"password":0}))
        #print('view attendance:------------',attendance)
        for attend in attendance:
            attend["_id"] = str(attend["_id"])
        return {"message":"Getting All Batchswise ","data": attendance}, 200