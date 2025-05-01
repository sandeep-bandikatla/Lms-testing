from flask import Request,request,jsonify
from flask_restful import Resource,abort
from pymongo import MongoClient

class SuperAdmin(Resource):
    def __init__(self, client, db, admin_collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = admin_collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

    def post(self):
        email = request.json.get("username")
        password = request.json.get("password")
        #print('Admins:---','*'*50,email,password)
       
        if self.db_name not in self.client.list_database_names():
            self.client[self.db_name]

        if self.collection_name not in self.db.list_collection_names():
            self.db.create_collection(self.collection_name)

        # data = {"email": email,"password": password}
        # self.collection.insert_one(data)

        user = self.collection.find_one({"email": email})

        if user['usertype'] == "superAdmin":
            if user["password"] == password:
                return {"message": "Login successful","userType":"superAdmin"}, 200
            else:
                return {"message": "Username & Password incorrect"}, 400

        elif user['usertype'] == "super":
            if user["password"] == password:
                return {"message": "SuperAdmin Login successful","userType":"super"}, 200
            else:
                return {"message": "Username & Password incorrect"}, 400
            
        elif user['usertype'] == "Python":
            if user["password"] == password:
                return {"message": "Login successful","userType":"Python"}, 200
            else:
                return {"message": "Username & Password incorrect"}, 400
            
        elif user['usertype'] == "Java":
            if user["password"] == password:
                return {"message": "Login successful","userType":"Java"}, 200
            else:
                return {"message": "Username & Password incorrect"}, 400
        else:
            return {"message": "User not found"}, 404



"""hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        data = {"email": email, "password": hashed_password}
        self.collection.insert_one(data)
        return {"message": "User registered successfully"}, 201

    def login_user(self, email, password):
        user = self.collection.find_one({"email": email})
        if user:
            # Email exists, check hashed password
            if bcrypt.checkpw(password.encode('utf-8'), user["password"]):
                return {"message": "Login successful", "userType": "superAdmin"}, 200
"""