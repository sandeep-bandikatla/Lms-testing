import json
import datetime
import requests

from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

# ─── Load config ─────────────────────────────────────────────────────
with open('local_config.json', 'r') as f:
    config_data = json.load(f)

# ─── Mongo + Flask setup ────────────────────────────────────────────
client = MongoClient(config_data['MONGO_CONFIG']['url'])
db     = client["codegnan_product"]

app = Flask(__name__)
api = Api(app)

# ─── ChatRace credentials & hard-coded admin list ──────────────────
CHATRACE_API_KEY  = "1853853.I5E5YR7qRbx2iDJu6xO1sEx8lRN3mzsU7ryZ"
CHATRACE_BASE_URL = "https://api.chatrace.com"

# map each phone number to the admin's first name
ADMIN_ADMINS = {
    # "+919959555952": "Sairam Uppugundla",
    # "+918106429771": "Kallepu Saketh Reddy", 
    "+918977544090": "Datta",
    "+918884113330": "Akathma Devi",
    "+917036339459": "sandeep",
}

# ─── 1) /exam-report endpoint ───────────────────────────────────────
class ExamReport(Resource):
    def get(self):
        date_str = request.args.get("date")
        if date_str:
            try:
                report_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid date format. Expected YYYY-MM-DD."}), 400
        else:
            report_date = datetime.datetime.today() - datetime.timedelta(days=1)
        date_key = report_date.strftime("%Y-%m-%d")

        exams = list(db["Daily-Exam"].find({"startDate": date_key}))

        total_allocated     = len(exams)
        total_attempted     = sum(1 for e in exams if e.get("attempt-status"))
        total_not_attempted = total_allocated - total_attempted
        total_batches       = len({(e.get("batch"), e.get("location")) for e in exams})

        batch_map = {}
        for e in exams:
            key = (e.get("location"), e.get("batch"))
            rec = batch_map.setdefault(key, {
                "batch": e.get("batch"),
                "allocated": 0,
                "attempted": 0,
                "non_attempted": 0,
                "last_exam_end_time": "N/A"
            })
            rec["allocated"] += 1
            if e.get("attempt-status"):
                rec["attempted"] += 1
            else:
                rec["non_attempted"] += 1

            st  = e.get("startTime")
            dur = e.get("totalExamTime")
            if st and dur:
                try:
                    start_dt = datetime.datetime.strptime(f"{date_key} {st}", "%Y-%m-%d %H:%M")
                    end_dt   = start_dt + datetime.timedelta(minutes=int(dur))
                    tstr     = end_dt.strftime("%H:%M")
                    if rec["last_exam_end_time"] == "N/A" or tstr > rec["last_exam_end_time"]:
                        rec["last_exam_end_time"] = tstr
                except:
                    pass

        locations = {}
        for (loc, _), rec in batch_map.items():
            loc_entry = locations.setdefault(loc, {
                "total_batches":        0,
                "total_allocated":      0,
                "total_attempted":      0,
                "total_not_attempted":  0,
                "batches": []
            })
            loc_entry["total_batches"]       += 1
            loc_entry["total_allocated"]     += rec["allocated"]
            loc_entry["total_attempted"]     += rec["attempted"]
            loc_entry["total_not_attempted"] += rec["non_attempted"]
            loc_entry["batches"].append(rec)

        return jsonify({
            "report_date":                  date_key,
            "total_batches":                total_batches,
            "total_allocated_students":     total_allocated,
            "total_attempted_students":     total_attempted,
            "total_not_attempted_students": total_not_attempted,
            "locations":                    locations
        })

api.add_resource(ExamReport, '/exam-report')

# ─── 2) Scheduler logic ───────────────────────────────────────────────
tz                   = ZoneInfo("Asia/Kolkata")
last_report_done_for = None

def build_metrics_for_date(date_key: str) -> dict:
    exams = list(db["Daily-Exam"].find({"startDate": date_key}))
    loc_map = {}
    for e in exams:
        loc = e.get("location", "Unknown")
        rec = loc_map.setdefault(loc, {"allocated": 0, "attempted": 0})
        rec["allocated"] += 1
        if e.get("attempt-status"):
            rec["attempted"] += 1

    alloc_parts       = [f"{loc} – {d['allocated']}" for loc, d in loc_map.items()]
    attempt_parts     = [f"{loc} – {d['attempted']}" for loc, d in loc_map.items()]
    non_attempt_parts = [f"{loc} – {d['allocated'] - d['attempted']}" for loc, d in loc_map.items()]

    total_alloc       = sum(d["allocated"] for d in loc_map.values())
    total_attempt     = sum(d["attempted"] for d in loc_map.values())
    total_non_attempt = total_alloc - total_attempt

    return {
        "alloc_parts":       ", ".join(alloc_parts),
        "attempt_parts":     ", ".join(attempt_parts),
        "non_attempt_parts": ", ".join(non_attempt_parts),
        "total_alloc":       total_alloc,
        "total_attempt":     total_attempt,
        "total_non_attempt": total_non_attempt
    }

def check_and_trigger_report():
    global last_report_done_for

    today_date = datetime.datetime.now(tz).date()
    today      = today_date.strftime("%Y-%m-%d")
    if last_report_done_for == today:
        return

    exams = list(db["Daily-Exam"].find({"startDate": today}))
    if not exams:
        return

    # wait until all exams finish
    latest_end = None
    for e in exams:
        st, dur = e.get("startTime"), e.get("totalExamTime")
        if st and dur is not None:
            start_dt = datetime.datetime.strptime(f"{today} {st}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            end_dt   = start_dt + datetime.timedelta(minutes=int(dur))
            if latest_end is None or end_dt > latest_end:
                latest_end = end_dt

    if not latest_end or datetime.datetime.now(tz) < latest_end:
        return

    hr       = datetime.datetime.now(tz).hour
    greeting = "Good Morning" if hr < 12 else "Good Evening"

    m = build_metrics_for_date(today)

    for phone, name in ADMIN_ADMINS.items():
        # build & print the human-readable text
        message_text = (
            f"{greeting} {name}, on {today}\n\n"
            f"Exam was allocated to {m['total_alloc']} students: {m['alloc_parts']}\n"
            f"Exam attempted students: {m['attempt_parts']}, not attempted: {m['non_attempt_parts']}\n"
            f"Total – {m['total_attempt']} students took the exam, {m['total_non_attempt']} did not."
        )
        print(f"\n[DAILY REPORT]\n{message_text}\n")

        # structured actions payload
        payload = {
            "phone":      phone,
            "first_name": name,
            "actions": [
                { "action": "add_tag",                       "tag_name": "SP_adminreports" },
                { "action": "set_field_value",               "field_name": "SP_Report_Date",            "value": today },
                { "action": "set_field_value",               "field_name": "SP_Greetings",              "value": greeting },
                { "action": "set_field_value",               "field_name": "SP_locations_allocated",     "value": m["alloc_parts"] },
                { "action": "set_field_value",               "field_name": "SP_total_allocated",         "value": str(m["total_alloc"]) },
                { "action": "set_field_value",               "field_name": "SP_locations_attempted",     "value": m["attempt_parts"] },
                { "action": "set_field_value",               "field_name": "SP_locations_not_attempted", "value": m["non_attempt_parts"] },
                { "action": "set_field_value",               "field_name": "SP_total_attempted",         "value": str(m["total_attempt"]) },
                { "action": "set_field_value",               "field_name": "SP_total_not_attempted",     "value": str(m["total_non_attempt"]) }
            ]
        }
        headers = {
            "Content-Type":   "application/json",
            "Accept":         "application/json",
            "X-ACCESS-TOKEN": CHATRACE_API_KEY
        }
        try:
            resp = requests.post(f"{CHATRACE_BASE_URL}/users", json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            print(f"[INFO] Actions sent to {name} ({phone})")
        except Exception as e:
            print(f"[ERROR] Failed to send to {name} ({phone}): {e}")

    last_report_done_for = today

# start scheduler
scheduler = BackgroundScheduler(timezone=tz)
scheduler.add_job(check_and_trigger_report, 'interval', minutes=1, id="daily_report_job")
scheduler.start()