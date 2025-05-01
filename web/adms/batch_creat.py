from flask import request,jsonify
from flask_restful import Resource
from pymongo import MongoClient
import uuid

class CreateBatch(Resource):
    def __init__(self, client, db, collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def post(self):
        id = str(uuid.uuid4())
        batchno = request.json.get('BatchId')
        course = request.json.get('TechStack')
        startdate = request.json.get('StartDate')
        enddate = request.json.get('EndDate')
        duration = request.json.get('Duration')
        status = request.json.get('Status')
        location = request.json.get('location')
    
        
        if self.db_name not in self.client.list_database_names():
            self.client[self.db_name]

        if self.collection_name not in self.db.list_collection_names():
            self.db.create_collection(self.collection_name)

        if not (batchno and course and startdate and enddate  and duration and status):
            return {"error": "Missing required fields"}, 400

        if self.collection.find_one({"$and":[{"Batch": batchno},{"location":location}]}):
            return {"error": "This Batch already exists"}, 409

        batchs_data = {
            "id": id,
            "Batch": batchno,
            "Course": course,
            "Duration": duration,
            "location" :location,
            "StartDate":startdate,
            "EndDate":enddate,
            "Status":status}

        result = self.collection.insert_one(batchs_data)
        batchs_data['_id'] = str(result.inserted_id)

        return {"message": "Batch successfully created", "batchs": batchs_data}, 201
    
    def get(self):
        location = request.args.get('location')

        if location == 'all':
            batches = list(self.collection.find({},{"password":0}))
            for batch in batches:
                batch["_id"] = str(batch["_id"])
            return {"message":"All batches data","data":batches},200

        else:
            batches = list(self.collection.find({"location":location},{"password":0}))
            for batch in batches:
                batch["_id"] = str(batch["_id"])

        return {"message":"All batches data","data":batches},200
    
    def put(self):
        data = request.json
        id = data.get("id")
        if not id:
            return {"error": "data is required to update a record"}, 400

        batch = self.collection.find_one({"id": id})
        if not batch:
            return {"error": "This batch not found"}, 404

        update_fields = {}
        if "StartDate" in data:
            update_fields["StartDate"] = data["StartDate"]
        if "EndDate" in data:
            update_fields["EndDate"] = data["EndDate"]
        if "Duration" in data:
            update_fields["Duration"] = data["Duration"]   
    
        if update_fields:
            self.collection.update_one({"id": id}, {"$set": update_fields})

        updated_mentor = self.collection.find_one({"id": id})
        updated_mentor["_id"] = str(updated_mentor["_id"])

        return {"message": "Mentor updated successfully", "Mentor": updated_mentor}, 200
