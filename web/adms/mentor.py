from flask import request
from flask_restful import Resource
from pymongo import MongoClient
import uuid
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import bcrypt

class Mentors(Resource):
    def __init__(self, client, db, bde_collection, manager_collection, collection, student_collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.bde_collection = bde_collection
        self.manager_collection = manager_collection
        self.collection = collection
        self.student_collection = student_collection
        self.db = self.client[self.db_name]
        self.bde_collection = self.db[self.bde_collection]
        self.manager_collection = self.db[self.manager_collection]
        self.collection = self.db[self.collection]
        self.student_collection = self.db[self.student_collection]
    def send_email(self, name, email,password):
        # Email content in HTML format
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Codegnan Placements!</title>
            <style>
                /* Global styles */
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #ffffff;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    border-radius: 10px;
                }}
                .content {{
                    text-align: center;
                }}
                h1, p {{
                    margin-bottom: 20px;
                }}
                .button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #FFA500;
                    color: #ffffff;
                    text-decoration: none;
                    border-radius: 5px;
                    transition: background-color 0.3s ease;
                }}
                .button:hover {{
                    background-color: #FFD700;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="content">
                    <h1>Welcome to Codegnan...!</h1>
                    <p>Hello, {name},</p>
                    <p>Congratulations on joining our team as a Mentor/Trainer!</p>
                    <p>We are excited to have you on board and look forward to working together to achieve great success.</p>
                    <p>Below are your login credentials to access the portal:</p>
                        <p>Username: {email}</p>
                        <p>Password: {password}</p>
                        <p>Portal Link: https://placements.codegnan.com/login</p>
                    <p>Explore our website to learn more about our services and offerings.</p>
                    <a href="https://www.codegnan.com" class="button">Explore Now</a>
                </div>
            </div>
        </body>
        </html>
        """

        sender_email = "placements@codegnan.com"
        recipient_email = email
        subject = "Welcome to Codegnan Placements!"

        # Create message container
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        msg.attach(MIMEText(html_content, 'html'))


        smtp_server = smtplib.SMTP('smtp.gmail.com', 587)  
        smtp_server.starttls()
        smtp_server.login(sender_email, 'tlmc pumi pxhy gwko')  
        smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
        smtp_server.quit()

    def post(self):
        id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        name = request.json.get('name')
        email = request.json.get("email").lower()
        phNo = request.json.get("PhNumber")
        location =  request.json.get("location")
        usertype = request.json.get("userType")
        password = 'CG@Mentor'
        h_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        designation = request.json.get('Designation')
        print('*'*50,request.json)
        
        if self.db_name not in self.client.list_database_names():
            self.client[self.db_name]

        if not (name and email and password):
            return {"error": "Missing required fields"}, 400
            
        if self.manager_collection.find_one({"email":email}):
            return {"message": " This mail Already exsited in Manager", "status": "error"},404
        
        if self.bde_collection.find_one({"email":email}):
            return {"message": " This mail Already exsited in BDE", "status": "error"},404
        
        if self.collection.find_one({"email":email}):
            return {"message": " This mail Already exsited in Mentor", "status": "error"},404
        
        if self.student_collection.find_one({"email":email}):
            return {"message": " This mail Already exsited as a Student", "status": "error"},404

        mentor = {
            "id": id,
            "timestamp": timestamp,
            "name": name,
            "email": email,
            "password": h_pwd,
            "PhNumber": phNo,
            "Designation":designation,
            "location" :location,
            "usertype":usertype
        }
        result = self.collection.insert_one(mentor)
        mentor['_id'] = str(result.inserted_id)

        self.send_email(name, email,password)
        print("mentor ki mail Sent...!")
        return {"message": "Mentor signup successful", "mentor": mentor}, 201

    def put(self):
        data = request.json
        print('Mentor-PUT-----',data)
        id = data.get("id")
        email = data.get('email')

        # if self.collection.find_one({"email":email}):
        #     return {"message": " This mail Already existed ", "status": "error"},404
        
        if self.manager_collection.find_one({"email":email}):
            return {"message": " This mail Already existed ", "status": "error"},404
        
        if self.bde_collection.find_one({"email":email}):
            return {"message": " This mail Already existed ", "status": "error"},404
        
        if self.student_collection.find_one({"email":email}):
            return {"message": " This mail Already existed as a Student", "status": "error"},404

        
        if not id:
            return {"error": "data is required to update a record"}, 400

        mentor = self.collection.find_one({"id": id})
        if not mentor:
            return {"error": "Mentor with the specified email not found"}, 404

        update_fields = {}
        if "name" in data:
            update_fields["name"] = data["name"]
        if "email" in data:
            update_fields["email"] = data["email"]
        if "PhNumber" in data:
            update_fields["PhNumber"] = data["PhNumber"]
        if "Designation" in data:
            update_fields["Designation"] = data["Designation"]
        if "location" in data:
            update_fields["location"] = data["location"]
    
        if update_fields:
            self.collection.update_one({"id": id}, {"$set": update_fields})

        updated_mentor = self.collection.find_one({"id": id})
        updated_mentor["_id"] = str(updated_mentor["_id"])

        return {"message": "Mentor updated successfully", "Mentor": updated_mentor}, 200


    def delete(self):
        id = request.args.get('id')

        if not id:
            return {"error": "data is required to delete a record"}, 400

        result = self.collection.delete_one({"id": id})
        if result.deleted_count == 0:
            return {"error": "Mentor with the specified Id not found"}, 404

        return {"message": "Mentor deleted successfully"}, 200

    def get(self):
        mentors = list(self.collection.find({},{"password":0}))
        for mentor in mentors:
            mentor["_id"] = str(mentor["_id"])
        return {"mentors": mentors}, 200