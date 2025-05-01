from flask import request
from flask_restful import Resource
from pymongo import MongoClient
import uuid
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random,bcrypt

class Add_zoho_Student(Resource):
    def __init__(self, client, db, bde_collection, manager_collection, mentor_collection,collection,batch):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = collection
        self.manager_collection = manager_collection
        self.mentor_collection = mentor_collection
        self.bde_collection = bde_collection
        self.batch = batch
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
        self.bde_collection = self.db[self.bde_collection]
        self.manager_collection = self.db[self.manager_collection]
        self.mentor_collection = self.db[self.mentor_collection]
        self.batch = self.db[self.batch]

    def send_email(self,email,batchNo,password):

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
                    text-align: left;
                }}
                h1 {{
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
                    <h1>Welcome to Codegnan Placements!</h1>
                    <p>Hello,</p>
                    <p>We are excited to welcome you to the Codegnan Placements Portal, your gateway to exploring placement opportunities and career growth.</p>
                    <p>You are assigned to batch: {batchNo}.</p>
                    <p>Below are your login credentials to access the portal:</p>
                        <p>Username: {email}</p>
                        <p>Password: {password}</p>
                        <p>Portal Link: https://placements.codegnan.com/login</p>
                    <p>Please log in to the portal at your earliest convenience and update your password for security purposes. The platform provides access to job opportunities, placement schedules, and resources to support your career journey.</p>
                    <p>If you face any issues while logging in or have questions, feel free to reach out to us.</p>
                    <p>We wish you all the best as you take the next step toward a bright future!</p>
                    <a href="https://placements.codegnan.com" class="button">Explore Now</a>
                    <p><b>Best Regards,</b></p>
                    <p>CodegnanDestination Placements Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        sender_email = "placements@codegnan.com"
        recipient_email = email
        subject = "Welcome to Codegnan Placements!"

        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        msg.attach(MIMEText(html_content, 'html'))

        smtp_server = smtplib.SMTP('smtp.gmail.com', 587)  
        smtp_server.starttls()
        smtp_server.login(sender_email, 'tlmc pumi pxhy gwko')  
        smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
        print("New Student mail Sent...!")
        smtp_server.quit()
        
    def post(self):
        data = request.json
        print("Zoho----post----",data)
        if not data:
            return {"error": "No data provided"}, 400
        
        u_c = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        l_c = [chr(i) for i in range(ord('a'), ord('z') + 1)]

        if self.collection_name not in self.db.list_collection_names():
            self.db.create_collection(self.collection_name)

        time = datetime.now().isoformat()
        studentId = data.get("studentId")
        batchNo = data.get("batchNo")
        name = data.get("name")
        email = data.get("email").lower()
        Studentphno = data.get("studentPhNumber")
        parentNo = data.get("parentNumber")
        location = data.get("location").lower()
        mos = data.get('modeOfStudy')
        status = data.get('profileStatus')

        if not all([studentId, batchNo]):
            return {"error": "Missing required fields for student"}, 400
        
        if not self.batch.find_one({"Batch":batchNo}):
                return {"error": "This BatchNo does not found in DB"}, 404
        
        if self.collection.find_one({"studentId": studentId}):
            return {"error": "studentId already exists"}, 404

        if self.collection.find_one({"email": email}):
            return {"error": "Email already exists"}, 404
        
        if self.manager_collection.find_one({"email": email}):
            return {"error": "Email already existed in Manager"}, 404
    
        if self.bde_collection.find_one({"email":email}):
            return {"message": " This mail Already existed in BDE ", "status": "error"},404
        
        if self.mentor_collection.find_one({"email":email}):
            return {"message": " This mail Already existed Mentor", "status": "error"},404

        password = ''.join(random.choice(u_c) + str(random.randint(0, 9)) + random.choice(l_c) for _ in range(2))
        h_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        id = str(uuid.uuid4())

        student_data = {
                "id": id,
                "name":name,
                "studentId": studentId,
                "BatchNo": batchNo,
                "email": email,
                "password": h_pwd,
                "studentPhNumber":Studentphno,
                "parentNumber": parentNo,
                "ModeofStudey":mos,
                "location" :location,
                "ProfileStatus":status,
                "created_time":time
            }

        result = self.collection.insert_one(student_data)
        student_data['_id'] = str(result.inserted_id)

        self.send_email(email, batchNo, password)

        return {"message": "Student added successfully", "student": student_data}, 200


    def put(self):
        data = request.json
        print("zoho---put---",data)
        stdid = data.get("studentId")

        if not stdid:
            return {"message":"Missing required fields"},404
        
        student = self.collection.find_one({"studentId": stdid})
        if not student:
            return {"message": "Student not found"}, 404

        updated_data = {
            "name": data.get("name"),
            "BatchNo":data.get("batchNo"),
            "email":data.get("email").lower(),
            "studentPhNumber": data.get("studentPhNumber"),
            "parentNumber": data.get("parentNumber"),
            "location": data.get("location").lower(),
            "ModeofStudey": data.get("modeOfStudy")}
            
        self.collection.update_one({"studentId": stdid},{"$set": updated_data})

        return {"message": "Student updated successfully", "studentId": stdid}, 200