# web/Exam/examiner/whatsapp_trigger.py

import requests
from datetime import datetime
from zoneinfo import ZoneInfo

CHATRACE_API_KEY = "1853853.I5E5YR7qRbx2iDJu6xO1sEx8lRN3mzsU7ryZ"
CHATRACE_BASE_URL = "https://api.chatrace.com"

def trigger_whatsapp(
    student_name,
    student_id,
    whatsapp_number,
    exam_name,
    start_date,
    start_time,
    total_time,
    subjects,
    batch,
    flow_id=None  # Optional: If you want to automatically send a ChatRace flow
):
    """
    Send exam details to ChatRace by creating/updating a contact and attaching
    any relevant custom fields, tags, or actions — including the studentId.
    Prints all timestamp fields to the console before returning.
    """
    # Build the payload
    payload = {
        "phone": whatsapp_number,
        "first_name": student_name,
        "last_name": "",       # optional
        "gender": "male",      # optional – adjust as needed
        "actions": []
    }

    # Optionally kick off a predefined flow
    if flow_id:
        payload["actions"].append({
            "action": "send_flow",
            "flow_id": flow_id
        })

    # Always tag this contact as an exam order
    payload["actions"].append({
        "action": "add_tag",
        "tag_name": "SP_ExamOrder"
    })

    # Include internal studentId as a custom field
    payload["actions"].append({
        "action": "set_field_value",
        "field_name": "SP_StudentId",
        "value": student_id
    })

    # Exam metadata fields
    payload["actions"].append({
        "action": "set_field_value",
        "field_name": "SP_ExamBatch",
        "value": batch
    })
    payload["actions"].append({
        "action": "set_field_value",
        "field_name": "SP_ExamSub",
        "value": subjects
    })
    payload["actions"].append({
        "action": "set_field_value",
        "field_name": "SP_ExamDayOrder",
        "value": exam_name
    })
    payload["actions"].append({
        "action": "set_field_value",
        "field_name": "SP_ExamDt",
        "value": start_date
    })
    payload["actions"].append({
        "action": "set_field_value",
        "field_name": "SP_ExamT",
        "value": start_time
    })
    payload["actions"].append({
        "action": "set_field_value",
        "field_name": "SP_ExamDuration",
        "value": str(total_time)
    })

    # Headers for ChatRace API
    headers = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "X-ACCESS-TOKEN": CHATRACE_API_KEY
    }

    # 1) Create or update the ChatRace contact
    try:
        resp1 = requests.post(
            f"{CHATRACE_BASE_URL}/users",
            headers=headers,
            json=payload,
            timeout=10
        )
        resp1.raise_for_status()
    except Exception as e:
        print(f"[ERROR] POST /users failed for {student_name}: {e}")
        return None

    # 2) Retrieve the updated contact record
    clean_phone = whatsapp_number.lstrip("+")
    try:
        resp2 = requests.get(
            f"{CHATRACE_BASE_URL}/users/{clean_phone}",
            headers=headers,
            timeout=10
        )
        resp2.raise_for_status()
    except Exception as e:
        print(f"[ERROR] GET /users/{clean_phone} failed: {e}")
        return None

    info = resp2.json()

    def to_ist(ms_str: str) -> str | None:
        """
        Convert millisecond timestamp string to 'YYYY-MM-DD HH:MM:SS' in Asia/Kolkata.
        """
        try:
            ms = int(ms_str or "0")
            if ms <= 0:
                return None
            return datetime.fromtimestamp(ms / 1000, tz=ZoneInfo("Asia/Kolkata")) \
                           .strftime("%Y-%m-%d %H:%M:%S")
        except:
            return None

    # Build the metrics dict
    metrics = {
        "id":               info.get("id"),
        "studentId":        student_id,
        "first_name":       info.get("first_name"),
        "batch":            batch,
        "last_sent":        to_ist(info.get("last_sent")),
        "last_delivered":   to_ist(info.get("last_delivered")) or "undelivered",
        "last_seen":        to_ist(info.get("last_seen")),
        "last_interaction": to_ist(info.get("last_interaction")),
        "recorded_at":      datetime.now(tz=ZoneInfo("Asia/Kolkata"))
    }

    # 3) Print all timestamps to console
    print(
        f"[WhatsApp] studentId={metrics['studentId']} | "
        f"last_sent={metrics['last_sent']} | "
        f"delivered={metrics['last_delivered']} | "
        f"seen={metrics['last_seen']} | "
        f"interaction={metrics['last_interaction']} | "
        f"recorded_at={metrics['recorded_at'].strftime('%Y-%m-%d %H:%M:%S')}"
    )

    return metrics
