from flask import request
from flask_restful import Resource
from pymongo import MongoClient
from datetime import datetime

class AttendCheck(Resource):
    def __init__(self, client, db, collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def post(self):
        course = request.json.get('subject')
        batch = request.json.get('batch')
        date = request.json.get('date')  
        location = request.json.get('location')
        #print(request.json)
        if not (course and batch and date):
            return {"error": "Missing required fields"}, 400

        query = {'course': course, 'batchNo': batch,'datetime': date,'location':location}
        existing_attendance = self.collection.find_one(query)
        #print('*'*30,existing_attendance)
        if existing_attendance:
            existing_attendance['_id'] = str(existing_attendance['_id'])
            return {'Message': "existed", 'data': existing_attendance}, 200
        else:
            return {'Message': "notexisted"}, 202
