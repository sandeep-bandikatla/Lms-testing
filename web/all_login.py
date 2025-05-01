from flask import request,jsonify
from pymongo import MongoClient
#from flask_jwt_extended import create_access_token
from flask_restful import Resource
import bcrypt,json

with open('local_config.json', 'r') as config_file:
    config_data = json.load(config_file)

MONGO_CONFIG = config_data['MONGO_CONFIG']['url']
client = MongoClient(MONGO_CONFIG)
db = client["codegnan_product"]
tester_collection = db["Testers"]

class Logins(Resource):
    def __init__(self, client, db_name,bde_collection, manager_collection, mentor_collection, student_collection) -> None:
        super().__init__()
        self.client = client
        self.db_name = db_name
        self.bde_collection = bde_collection
        self.manager_collection = manager_collection
        self.mentor_collection = mentor_collection
        self.student_collection = student_collection
        self.db = self.client[self.db_name]
        self.bde_collection = self.db[self.bde_collection]
        self.manager_collection = self.db[self.manager_collection]
        self.mentor_collection = self.db[self.mentor_collection]
        self.student_collection = self.db[self.student_collection]
        
    def post(self):
        try:
            email = request.json.get("email")
            password = request.json.get("password")
            #print('data----',email,password)
            # h_password = bcrypt.checkpw(password.encode('utf-8'), password)
            if not email or not password:
                return {"message": "Email and password are required", "status": "error"},404
            
            for collection in [self.bde_collection, self.manager_collection, self.mentor_collection, self.student_collection,tester_collection]:
                user = collection.find_one({"email": email})
                
                if user and bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
                    usertype = collection.name
                    if usertype == 'student_login_details':
                        #access_key = create_access_token(identity=email)#str({"email": user["email"], "usertype": usertype}))
                        #print('---------------------------',access_key)
                        return {"message": "Login successful","id":user["id"],"Location":user["location"],
                            "user": {"email": user["email"],"Profile":user["ProfileStatus"],"usertype": usertype}},200 #"jwtaccess":access_key},200
                    else:
                        return {"message": "Login successful","id":user["id"],"Location":user["location"],
                        "user": {"email": user["email"],"usertype": usertype}},200
                    
            return {"message": "Invalid email or password", "status": "error"},400

        except Exception as e:
            return {"message": f"An error occurred: {str(e)}", "status": "error"},401
