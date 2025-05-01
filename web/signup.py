from flask_restful import Resource
from flask import request, jsonify
from werkzeug.security import generate_password_hash
from bson import ObjectId

class Signup(Resource):
    def __init__(self, collection):
        super().__init__()
        self.collection = collection

    def post(self):
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not (username and email and password):
            return {"error": "Missing required fields"}, 400

        hashed_password = generate_password_hash(password)

        user_data = {
            "username": username,
            "email": email,
            "password": hashed_password
        }
        try:
            result = self.collection.insert_one(user_data)
            user_data['_id'] = str(result.inserted_id)
            return {"message": "Signup successful", "user": user_data}, 201
        except Exception as e:
            return {"error": str(e)}, 500