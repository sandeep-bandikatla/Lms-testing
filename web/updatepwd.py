from flask import request
from flask_restful import Resource
from pymongo import MongoClient
import bcrypt,json

with open('local_config.json', 'r') as f:
    config = json.load(f)
client = MongoClient(config['MONGO_CONFIG']['url'])
db     = client["codegnan_product"]
collection = db["Testers"]

class Updatepassword(Resource):
    def __init__(self, client, db,bde_collection, manager_collection, mentor_collection, std_collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.std_collection = std_collection
        self.db = self.client[self.db_name]
        self.std_collection = self.db[self.std_collection]
        self.bde_collection = self.db[bde_collection]
        self.manager_collection = self.db[manager_collection]
        self.mentor_collection = self.db[mentor_collection]
        self.tester_collection = collection

    def post(self):
        email = request.json.get('email')
        password = request.json.get('password')
        h_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        print("User data ----", email, password)

        if not email or not password:
            return {"error": "Email or password missing. Try again."}, 400

        collections = {
            "Student": self.std_collection,
            "Mentor": self.mentor_collection,
            "Manager": self.manager_collection,
            "BDE": self.bde_collection,
            "Tester":self.tester_collection
        }

        # Find and update user in the appropriate collection
        for role, collection in collections.items():
            user_data = collection.find_one({"email": email})
            if user_data:
                collection.update_one({"email": email}, {"$set": {"password": h_pwd}})
                return {"message": "Password Updated Successfully..!", "user": role}, 200

        return {"message": "No data found for this email"}, 400

    
    """def post(self):
        email = request.json.get('email')
        password = request.json.get('password')
        print("user data----",email,password)
        if not email:
            return {"error": "Email not found Try again after sometime"}, 400
        else:
            data = self.student_collection.find_one({"email": email})
            if data:
                self.student_collection.update_one({"email":email},{"$set": {"password":password}})
                return {"message":"Password Updated Successfully..!","user":"Student"}, 200
            else:
                return {"message":"No data found for this email"},400"""