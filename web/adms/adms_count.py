from flask import request
from flask_restful import Resource
from pymongo import MongoClient


class AllAdminsCount(Resource):
    def __init__(self, client, db,bde_collection, mentor_collection,manager_collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.bde_collection = bde_collection
        self.mentor_collection = mentor_collection
        self.manager_collection = manager_collection
        self.db = self.client[self.db_name]
        self.bde_collection = self.db[self.bde_collection]
        self.mentor_collection = self.db[self.mentor_collection]
        self.manager_collection = self.db[self.manager_collection]


    def get(self):
        bdes = list(self.bde_collection.find({},{"password":0}))
        for bde in bdes:
            bde["_id"] = str(bde["_id"])

        mentors = list(self.mentor_collection.find({},{"password":0}))
        for mentor in mentors:
            mentor["_id"] = str(mentor["_id"])

        managers = list(self.manager_collection.find({},{"password":0}))
        for manager in managers:
            manager["_id"] = str(manager["_id"])
        
        return {"message":"BDE,Mentor,Manager Data","BDE":bdes,"Mentors":mentors,"Managers":managers},200
