from flask import request
from flask_restful import Resource
from pymongo import MongoClient
import smtplib
import random,json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText      

with open('local_config.json', 'r') as f:
    config = json.load(f)
client = MongoClient(config['MONGO_CONFIG']['url'])
db     = client["codegnan_product"]
collection = db["Testers"]

class ForgotPwd(Resource):
    def __init__(self, client, db, otp_collection,bde_collection, manager_collection, mentor_collection, std_collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.std_collection = std_collection
        self.otp_collection = otp_collection
        self.db = self.client[self.db_name]
        self.otp_collection = self.db[self.otp_collection]
        self.std_collection = self.db[self.std_collection]
        self.bde_collection = self.db[bde_collection]
        self.manager_collection = self.db[manager_collection]
        self.mentor_collection = self.db[mentor_collection]
        self.tester_collection = collection
    def send_email(self, email, otp,name):
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Welcome to Codegnan Placements!</title>
            </head>
            <body>
                <p>Dear { name },</p>
                    <p>We have sent you a One-Time-Password(OTP) to verify your request. Please use below code</p>
                    <p>Your OTP is:- <b style="font-size:25px">{ otp }</b> </p> 
                    <p><b>Note:</b></p>
                    <p>This OTP will expire in 10 minutes from the time of request.</p>
                    <p>At CodegnanDestination,we are committed in helping you to achieve your goals and aspirations.</p>
                    <p>Our team is here to support you in every step.</p>
                    <p>Feel free to revert back for any more queries</p><br><br>
                <p><b>Best Regards,</b></p>
                <p>CodegnanDestination Placements Team</p>
                
            </body>
            </html>
            """
            #Emial detials
            sender_email = "Placements@codegnan.com"
            recipient_email = email
            subject = "OTP for your Forgot Password!"
                    
            msg = MIMEMultipart('alternative')
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(html_content, 'html'))
            
            smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
            smtp_server.starttls()
            smtp_server.login(sender_email, 'tlmc pumi pxhy gwko')  # Update with your sender's email and password
            smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
            smtp_server.quit()

    
    def post(self):
        u_c = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        l_c = [chr(i) for i in range(ord('a'), ord('z') + 1)]

        email = request.json.get('email')
        print("Student forgotpassword-------",email)

        user_data = None
        collections = {
            "student": self.std_collection,
            "mentor": self.mentor_collection,
            "manager": self.manager_collection,
            "bde": self.bde_collection,
            "tester":self.tester_collection
        }

        for role, collection in collections.items():
            user_data = collection.find_one({"email": email})
            if user_data:
                user_role = role
                break

        if not user_data:
            return {"error": "Please enter a registered email!"}, 400

        self.otp_collection.delete_many({"email": email})

        print('*' * 30, user_data.get('studentId', user_data.get('mentorId', user_data.get('managerId', user_data.get('bdeId', 'Unknown')))))

        otp = ''.join(random.choice(u_c) + str(random.randint(0, 9)) + random.choice(l_c) for _ in range(2))
        otp_data = {"email": email, "otp": otp, "role": user_role}
        self.otp_collection.insert_one(otp_data)

        self.send_email(email, otp, user_data.get('name', user_data.get('name', user_data.get('name', user_data.get('name', 'Unknown')))))

        return {"message": "OTP sent successfully!"}, 200


    """def post(self):
        u_c = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        l_c = [chr(i) for i in range(ord('a'), ord('z') + 1)]

        email = request.json.get('email')
        print("Student forgotpassword-------",email)
        data = self.std_collection.find_one({"email": email})
        if not data:
            return {"error": "Plz Enter Registered Email...!"}, 400
        if self.collection.find_one({"email": email}):
            self.collection.drop()

        print('*'*30,data['studentId'])
        otp = ''.join(random.choice(u_c) + str(random.randint(0, 9)) + random.choice(l_c) for _ in range(2))
        otp_data = {"email": email,"otp": otp}
        self.collection.insert_one(otp_data)

        self.send_email(email, otp,data['studentId'])

        return {"message": "OTP sent successfully","user":"student"}, 200"""