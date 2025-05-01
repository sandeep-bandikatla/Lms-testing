from flask import request
from flask_restful import Resource
from pymongo import MongoClient
from datetime import datetime
import json

with open('local_config.json', 'r') as f:
    config = json.load(f)
client = MongoClient(config['MONGO_CONFIG']['url'])
db     = client["codegnan_product"]
collection = db["student_login_details"]

class zoho_Invoice(Resource):
    def __init__(self):
        super().__init__()
        self.collection = collection

    def put(self):
        data = request.json
        print("zoho-invoice----put---",data)
        stdid = data.get("studentId")

        if not stdid:
            return {"message":"Missing required fields"},404
        
        student = self.collection.find_one({"studentId": stdid})
        if not student:
            return {"message": "Student not found"}, 404

        updated_data = {
            "created_time":data.get("Invmodif_T"),
            "invoiceURL": data.get("invoiceURL"),
            "total":data.get("totalFee"),
            "paidamount":data.get("paidAmount"),
            "balance":data.get("balance"),
            "duedate":data.get("dueDate")
        }
        self.collection.update_one({"studentId": stdid},{"$set": updated_data})

        return {"message": "Student updated successfully", "studentId": stdid}, 200