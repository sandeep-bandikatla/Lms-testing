# app.py

import uuid
import json
import threading
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import bcrypt
from flask import Flask, request
from flask_restful import Resource, Api
from pymongo import MongoClient

# ─── Load config & connect to MongoDB ─────────────────────────────────────────
with open('local_config.json', 'r') as f:
    cfg = json.load(f)

client = MongoClient(cfg['MONGO_CONFIG']['url'])
db     = client["codegnan_product"]

# ─── Collections ─────────────────────────────────────────────────────────────
testers_col       = db["Testers"]
curriculum_source = db["Curriculum"]

# ─── Flask setup ──────────────────────────────────────────────────────────────
app = Flask(__name__)
api = Api(app)


class Testers(Resource):
    def send_email(self, name, email, password, designation):
        subject_role = designation[0] if isinstance(designation, list) else designation

        html = f"""
        <!DOCTYPE html>
        <html lang="en"><head><meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1.0">
        <title>Welcome to Codegnan!</title>
        <style>
          body{{font-family:Arial;margin:0;background:#f5f5f5}}
          .container{{max-width:600px;margin:20px auto;padding:20px;
                     background:#fff;border-radius:8px;
                     box-shadow:0 2px 6px rgba(0,0,0,0.1)}}
          .button{{display:inline-block;padding:10px 20px;
                   background:#FFA500;color:#fff;text-decoration:none;
                   border-radius:4px}}
          .button:hover{{background:#FFD700}}
        </style>
        </head><body>
          <div class="container">
            <p>Hi {name},</p>
            <p>Welcome to the Codegnan team as our newest <strong>{subject_role}</strong> intern!  
               We’re delighted to have you on board and look forward to working together toward great success.</p>
            <p>Below are your portal login credentials:</p>
            <ul>
              <li><strong>Portal:</strong> <a href="https://placements.codegnan.com/login">https://placements.codegnan.com/login</a></li>
              <li><strong>Username:</strong> {email}</li>
              <li><strong>Password:</strong> {password}</li>
            </ul>
            <p>Once you’ve logged in, feel free to explore the portal and visit our website to learn more about our services and offerings.  
               If you have any questions or need assistance, just let me know!</p>
          </div>
        </body></html>
        """

        sender = "placements@codegnan.com"
        msg = MIMEMultipart('alternative')
        msg['From']    = sender
        msg['To']      = email
        msg['Subject'] = "Welcome to Codegnan Placements!"
        msg.attach(MIMEText(html, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, 'tlmc pumi pxhy gwko')
        server.sendmail(sender, email, msg.as_string())
        server.quit()

    def post(self):
        data        = request.get_json(force=True)
        tester_id   = str(uuid.uuid4())
        now_iso     = datetime.now().isoformat()
        name        = data.get('name')
        email       = data.get('email', '').lower()
        phNo        = data.get('PhNumber')
        location    = data.get('location')
        usertype    = data.get('userType')
        designation = data.get('Designation')  # str or list
        raw_pw      = 'CG@Tester'

        # Validate input
        if not (name and email and designation):
            return {"error": "Missing required fields: name, email, Designation"}, 400
        if testers_col.find_one({"email": email}):
            return {"message": "Email already exists"}, 409

        # Bulk-fetch curriculum for all designations
        subjects = designation if isinstance(designation, list) else [designation]
        docs = list(curriculum_source.find(
            {"subject": {"$in": subjects}},
            {"_id":1, "subject":1, "Topics":1, "SubTopics":1, "DayOrder":1}
        ))

        # Group them by subject (lowercased)
        grouped = {subj.lower(): {} for subj in subjects}
        for d in docs:
            subj_key = d['subject'].lower()           # lowercase key
            sid      = str(d['_id'])
            day      = d.get('DayOrder', 'Day-Unknown')
            subs     = [
                {"title": st, "status": False, "tag": f"{day}:{i+1}"}
                for i, st in enumerate(d.get("SubTopics", []))
            ]
            grouped[subj_key][sid] = {
                "Topics":    d.get("Topics", []),
                "SubTopics": subs
            }

        # Hash password & insert tester with embedded curriculumTable
        hashed_pw = bcrypt.hashpw(raw_pw.encode(), bcrypt.gensalt()).decode()
        tester = {
            "id":              tester_id,
            "timestamp":       now_iso,
            "name":            name,
            "email":           email,
            "password":        hashed_pw,
            "PhNumber":        phNo,
            "Designation":     designation,
            "location":        location,
            "usertype":        usertype,
            "curriculumTable": grouped
        }
        testers_col.insert_one(tester)

        # prepare response object
        response_obj = {
            "id":          tester_id,
            "name":        name,
            "email":       email,
            "PhNumber":    phNo,
            "Designation": designation,
            "location":    location
        }

        # Send welcome email in background
        threading.Thread(
            target=self.send_email,
            args=(name, email, raw_pw, designation),
            daemon=True
        ).start()

        return {"message": "Tester signup successful", "tester": response_obj}, 201

    def get(self):
        projection = {
            "_id": 0,
            "id": 1,
            "name": 1,
            "email": 1,
            "PhNumber": 1,
            "Designation": 1,
            "location": 1
        }
        testers = list(testers_col.find({}, projection))
        return {"testers": testers}, 200

    def put(self):
        data      = request.get_json(force=True)
        tester_id = data.get("id")
        if not tester_id:
            return {"error": "ID required"}, 400
        if not testers_col.find_one({"id": tester_id}):
            return {"error": "Tester not found"}, 404

        updates = {f: data[f] for f in
                   ("name", "email", "PhNumber", "Designation", "location", "usertype")
                   if f in data}
        if updates:
            # keep email lowercase if it’s being updated
            if "email" in updates:
                updates["email"] = updates["email"].lower()
            testers_col.update_one({"id": tester_id}, {"$set": updates})

        updated = testers_col.find_one({"id": tester_id}, {"_id":0, "password":0})
        return {"message": "Tester updated successfully", "tester": updated}, 200

    def delete(self):
        tester_id = request.args.get("id")
        if not tester_id:
            return {"error": "ID required"}, 400
        result = testers_col.delete_one({"id": tester_id})
        if result.deleted_count == 0:
            return {"error": "Tester not found"}, 404
        return {"message": "Tester deleted successfully"}, 200