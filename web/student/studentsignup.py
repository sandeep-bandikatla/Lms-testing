from flask import request, render_template_string
from flask_restful import Resource
from pymongo import MongoClient
import uuid
from datetime import datetime
from gridfs import GridFS
import smtplib,bcrypt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PIL import Image
import os ,io

def compress_image(image_bytes, target_size_kb=10):
    """
    Compress the input image bytes so that its size is approximately at most target_size_kb (in KB).
    The function uses Pillow to open, convert, and (if needed) resize the image.
    Returns the compressed image bytes.
    """
    # Open the image from bytes
    image_io = io.BytesIO(image_bytes)
    try:
        image = Image.open(image_io)
    except Exception as e:
        raise ValueError("Invalid image file provided.")
   
    # Convert to RGB if necessary (JPEG requires RGB)
    if image.mode != "RGB":
        image = image.convert("RGB")
   
    quality = 85  # Starting quality setting
    compressed_io = io.BytesIO()
    image.save(compressed_io, format="JPEG", quality=quality)
    size_kb = len(compressed_io.getvalue()) / 1024

    # First, reduce quality until the size is under target_size_kb or quality reaches a threshold.
    while size_kb > target_size_kb and quality > 10:
        quality -= 5
        compressed_io = io.BytesIO()
        image.save(compressed_io, format="JPEG", quality=quality)
        size_kb = len(compressed_io.getvalue()) / 1024

    # If quality reduction alone is insufficient, resize the image.
    if size_kb > target_size_kb:
        width, height = image.size
        # Calculate a scaling factor based on current size versus target size.
        factor = (target_size_kb / size_kb) ** 0.5 
        new_width = max(1, int(width * factor))
        new_height = max(1, int(height * factor))
        image = image.resize((new_width, new_height), Image.LANCZOS) 
        quality = 85  # Reset quality after resizing
        compressed_io = io.BytesIO()
        image.save(compressed_io, format="JPEG", quality=quality)
        size_kb = len(compressed_io.getvalue()) / 1024
       
        # Further reduce quality if needed.
        while size_kb > target_size_kb and quality > 10:
            quality -= 5
            compressed_io = io.BytesIO()
            image.save(compressed_io, format="JPEG", quality=quality)
            size_kb = len(compressed_io.getvalue()) / 1024

    compressed_io.seek(0)
    return compressed_io.getvalue()


class StudentSignup(Resource):
    def __init__(self, client, db, collection):
        super().__init__()
        self.client = client
        self.db_name = db
        self.collection_name = collection
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
        self.fs = GridFS(self.db)  # Initialize GridFS for storing files 

    '''def send_email(self, name, email):
        # Email content in HTML format
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to Codegnan Placements!</title>
            <style>
                /* Global styles */
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #ffffff;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    border-radius: 10px;
                }
                .content {
                    text-align: center;
                }
                h1, p {
                    margin-bottom: 20px;
                }
                .button {
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #FFA500;
                    color: #ffffff;
                    text-decoration: none;
                    border-radius: 5px;
                    transition: background-color 0.3s ease;
                }
                .button:hover {
                    background-color: #FFD700;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="content">
                    <h1>Welcome to Codegnan Placements!</h1>
                    <p>Hello, {{ name }},</p>
                    <p>Congratulations on taking the first step towards a successful career!</p>
                    <p>At Codegnan Placements, we are committed to helping you achieve your goals and aspirations. Our team of experts is here to support you every step of the way.</p>
                    <p>Explore our website to discover a world of opportunities and resources tailored just for you.</p>
                    <a href="https://placements.codegnan.com" class="button">Explore Now</a>
                </div>
            </div>
        </body>
        </html>
        """

        # Render email template with student's name
        rendered_html = render_template_string(html_content, name=name)

        # Email configuration
        sender_email = "Placements@codegnan.com"
        recipient_email = email
        subject = "Welcome to Codegnan Placements!"

        # Create message container
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Attach HTML content to the email
        msg.attach(MIMEText(rendered_html, 'html'))

        # Send email using SMTP (for Gmail)
        smtp_server = smtplib.SMTP('smtp.gmail.com', 587)  # Update SMTP server details for Gmail
        smtp_server.starttls()
        smtp_server.login(sender_email, 'tlmc pumi pxhy gwko')  # Update sender's email and password
        smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
        smtp_server.quit()'''

    def post(self):
        # Extract data from the request
        data = request.form
        timestamp = datetime.now().isoformat()

        email = data.get('email')
        name = data.get('name')
        Dob = data.get('dob')
        age = int(data.get('age'))
        gender = data.get('gender')
        password = data.get('password')
        h_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        state = data.get('state')
        qualification = data.get("qualification")
        city = data.get("cityName")
        department = data.get("department")
        yearOfPassing = data.get("yearOfPassing")
        collegeName = data.get("collegeName")
        highestGraduationpercentage = float(data.get("highestGraduationPercentage"))
        studentSkills = data.getlist("studentSkills[]")
        tenthStandard = float(data.get("tenthStandard"))
        twelfthStandard = float(data.get("twelfthStandard"))
        resume = request.files.get('resume')
        resume_file = resume.read()
        profile = request.files.get('profilePic')
        profile_bytes = profile.read()
        try:
            pro_file = compress_image(profile_bytes, target_size_kb=10)
        except Exception as e:
            print(e)
            return {"error": "Failed to compress profile image: " + str(e)}, 400
        #pro_file = profile.read()
        collegeUSNNumber = data.get("collegeUSNNumber")
        githubLink=data.get("githubLink")
        arrears=data.get("arrears")
        arr_cnt = data.get("arrearsCount")
        tenthyear = data.get('tenthPassoutYear')
        twelfthyear = data.get('twelfthPassoutYear')
        status = data.get('profileStatus')

        # Check if the database exists, if not, create it
        if self.db_name not in self.client.list_database_names():
            self.client[self.db_name]

        '''# Check if the collection exists, if not, create it
        if self.collection_name not in self.db.list_collection_names():
            self.db.create_collection(self.collection_name)

        # Check if all required fields are present
        if not (name and email and password and resume_file):
            return {"error": "Missing required fields"}, 400

        # Check if the email already exists in the collection
        if self.collection.find_one({"email": email}):
            return {"error": "Email already exists"}, 409'''
       
        # Insert student signup data into MongoDB
        student_data = {
            "timestamp": timestamp,
            "name": name,
            "DOB":Dob,
            "password": h_pwd,
            "age": age,
            "gender":gender,
            "state": state,
            "qualification": qualification,
            "yearOfPassing": yearOfPassing,
            "city": city,
            "department": department,
            "collegeName": collegeName,
            "highestGraduationpercentage": highestGraduationpercentage,
            "studentSkills": studentSkills,
            "tenthStandard": tenthStandard,
            "twelfthStandard":twelfthStandard,
            "collegeUSNNumber":collegeUSNNumber,
            "githubLink":githubLink,
            "TenthPassoutYear":tenthyear,
            "TwelfthPassoutYear":twelfthyear,
            "arrears":arrears,
            "ArrearsCount":arr_cnt,
            "ProfileStatus":status
        }
        result = self.collection.find_one({"email":email})
        ids = result["id"]
        std_id = result['studentId']
        self.collection.update_many({"email":email}, {"$set": student_data})
        #student_data['_id'] = str(result.inserted_id)

        # Save the resume file to GridFS with student ID as filename
        resume_id = self.fs.put(resume_file, filename=ids)
        student_data['resume_id'] = str(resume_id)

        file_pic = self.db.fs.files.find_one({"filename": std_id})
        print(file_pic)
        if file_pic:
            file_id = file_pic["_id"]
            self.fs.delete(file_id)
            profile_id = self.fs.put(pro_file, filename=std_id)
            student_data['profile'] = str(profile_id)
        else:
            profile_id = self.fs.put(pro_file, filename=std_id)
            student_data['profile'] = str(profile_id)
            
        print("For post student signup-----",student_data)
        
        #self.send_email(name, email)

        return {"message": "Student signup successful", "student": student_data }, 201
    
    def put(self):
        data = request.form
        timestamp = datetime.now().isoformat()

        age = int(data.get('age'))
        arrears=data.get("arrears")
        arr_cnt = data.get("arrearsCount")
        city = data.get("cityName")
        collegeName = data.get("collegeName")
        collegeUSNNumber = data.get("collegeUSNNumber")
        department = data.get("department")
        Dob = data.get('dob')
        email = data.get('email')
        gender = data.get('gender')
        githubLink=data.get("githubLink")
        highestGraduationpercentage = float(data.get("highestGraduationPercentage"))
        name = data.get('name')
        status = data.get('profileStatus')
        qualification = data.get("qualification")
        state = data.get('state')
        studentSkills = data.getlist("studentSkills[]")
        tenthyear = data.get('tenthPassoutYear')
        tenthStandard = float(data.get("tenthStandard"))
        twelfthStandard = float(data.get("twelfthStandard"))
        twelfthyear = data.get('twelfthPassoutYear')        
        yearOfPassing = data.get("yearOfPassing")
        
        std_data = {
            "timestamp": timestamp,
            "name": name,
            "DOB":Dob,
            "age": age,
            "gender":gender,
            "state": state,
            "qualification": qualification,
            "yearOfPassing": yearOfPassing,
            "city": city,
            "department": department,
            "collegeName": collegeName,
            "highestGraduationpercentage": highestGraduationpercentage,
            "studentSkills": studentSkills,
            "tenthStandard": tenthStandard,
            "twelfthStandard":twelfthStandard,
            "collegeUSNNumber":collegeUSNNumber,
            "githubLink":githubLink,
            "TenthPassoutYear":tenthyear,
            "TwelfthPassoutYear":twelfthyear,
            "arrears":arrears,
            "ArrearsCount":arr_cnt,
            "ProfileStatus":status
        }
        result = self.collection.find_one({"email":email})

        self.collection.update_many({"email":email}, {"$set": std_data})
        print("For put student signup-----",std_data)
        return {"message": "Student  successful", "student": std_data }, 200