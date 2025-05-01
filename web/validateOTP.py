from flask import request
from pymongo import MongoClient
from flask_restful import Resource

class ValidateOTP(Resource):
    def __init__(self, client, db, otp_collection) -> None:
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = otp_collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def post(self):
        data = request.json
        email = data.get("email")
        otp = data.get("otp")
        print('*'*20,email,otp)

        if self.db_name not in self.client.list_database_names():
            self.client[self.db_name]

        # Check if the collection exists, if not, create it
        if self.collection_name not in self.db.list_collection_names():
            self.db.create_collection(self.collection_name)

        user = self.collection.find_one({"email": email})

        if user:
            # Email exists, check password
            if user["otp"] == otp:
                return {"message": "Email validation successful", "student_email":user["email"]}, 200
            else:
                return {"message": "OTP incorrect"}, 400
        else:
            return {"message": "User not found"}, 404
