from flask import request
from flask_restful import Resource
from pymongo import MongoClient

class ManagerLeaveupdated(Resource):
    def __init__(self,client,db,leave_collection,manager_collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.leave_collection = leave_collection
        self.manager_collection = manager_collection
        self.db = self.client[self.db_name]
        self.leave_collection = self.db[self.leave_collection]
        self.manager_collection = self.db[self.manager_collection]

    def get(self):
        location = request.args.get('location')
        
        if location == "all":
            leaves = list(self.leave_collection.find({},{"password":0}))
            for res in leaves:
                res["_id"] = str(res["_id"])
            return {"message":"All leaves locations","leaves":leaves},200
        
        else:       
            leaves = list(self.leave_collection.find({"location":location},{"password":0}))
            for res in leaves:
                res["_id"] = str(res["_id"])
        
        return {"message":"All leaves locations","leaves":leaves},200
    
    def put(self):
        data = request.json
        print('PUT-----',data)
        id = data.get("studentId")
        managerId = data.get("managerId")

        if not id:
            return {"error": "data is required to update a record"}, 400

        manager = self.manager_collection.find_one({"id":managerId})
        if not manager:
            return {"error": "Manager with the specified Id not found"}, 404
        print('-----------managers-----',manager['name'])
        update_fields = {}
        if "status" in data:
            update_fields["status"] = data["status"]
            update_fields["AcceptedBy"]=manager['name']
        
        if update_fields:
            self.leave_collection.update_one({"id": id}, {"$set": update_fields})

        updated = self.leave_collection.find_one({"id": id})
        updated["_id"] = str(updated["_id"])

        

        return {"message": "Manager updated successfully", "manager": updated}, 200
