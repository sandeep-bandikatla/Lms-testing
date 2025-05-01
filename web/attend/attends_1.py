from flask import request
from flask_restful import Resource
from pymongo import MongoClient


class Attendace(Resource):
    def __init__(self, client, db, collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def post(self):
        course = request.json.get('subject')
        batchNo = request.json.get('batches')
        location = request.json.get('location')
    
        if not (course and batchNo and location):
            return {"error": "Missing required fields"}, 400
        
        # if course == 'Python':
        alldata = list(self.collection.find({"$and":[{"BatchNo":batchNo},{"location":location}]},{"studentId": 1, "name":1,"BatchNo": 1, "email": 1}))
        for data in alldata:
            data["_id"] = str(data["_id"])  
            #print("batch-wise students data----",len(data["BatchNo"]))
        return {"message": "selected batch data","students_data": alldata}, 200
        
        # elif course == 'CoreJava' or 'AdvancedJava':
        #     alldata = list(self.collection.find({"$and":[{"BatchNo":batchNo},{"location":location}]},{"password":0}))
        #     for data in alldata:
        #         data["_id"] = str(data["_id"] )
        #         #print("corejava batch data----",data["BatchNo"])
        #     return {"message": "CoreJava batch data","students_data": alldata}, 200
        
        # elif course == 'MySQL' or 'Flask' or 'Frontend' or 'SoftSkills' or 'Aptitude':
        #     alldata = list(self.collection.find({"$and":[{"BatchNo":batchNo},{"location":location}]},{"password":0}))
        #     return {"message": "Getting All Students data","students_data": alldata}, 200