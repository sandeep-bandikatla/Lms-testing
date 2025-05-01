from flask import request
from pymongo import MongoClient
from flask_restful import Resource

class BdeLogin(Resource):
    def __init__(self, client, db_name, collection) -> None:
        super().__init__()
        self.client = client
        self.db_name = db_name
        self.collection_name = collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def post(self):
        # Get request data
        data = request.json
        username = data.get("username")
        password = data.get("password")
        print(username, password)
        # Check if the database exists, if not, create it
        if self.db_name not in self.client.list_database_names():
            self.client[self.db_name]

        # Check if the collection exists, if not, create it
        if self.collection_name not in self.db.list_collection_names():
            self.db.create_collection(self.collection_name)

        

        # Check if the email exists in the collection
        user = self.collection.find_one({"email": username})

        if user:
            # Email exists, check password
            if user["password"] == password:
                return {"message": "Login successful","userType":"bde"}, 200
            else:
                return {"message": "Password incorrect"}, 400
        else:
            return {"message": "User not found"}, 404
