import json
from flask import request, jsonify
from flask_restful import Resource
from pymongo import MongoClient
from collections import defaultdict
from datetime import datetime

# ─── DB Config ────────────────────────────────────────────────────────────────
with open("local_config.json", "r") as f:
    cfg = json.load(f)

client      = MongoClient(cfg["MONGO_CONFIG"]["url"])
db          = client["codegnan_product"]
VERIF_COLL  = db["InternVerifiedQuestions"]
TESTERS     = db["Testers"]

class InternProgressSummary(Resource):
    def get(self):
        # 1. Fetch all creation+verification events
        events = list(VERIF_COLL.find())

        # 2. Build grouped summary by intern → subject → (tag__day) → stats
        summary = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(
                    lambda: {
                        "mcq_created":    0,
                        "mcq_verified":   0,
                        "code_created":   0,
                        "code_verified":  0,
                        "total_created":   0,
                        "total_verified":  0
                    }
                )
            )
        )

        for ev in events:
            intern_id  = ev.get("id", "unknown")
            qtype      = ev.get("questionType", "unknown")
            tag        = ev.get("tag", "unknown")
            subject    = ev.get("subject", "unknown").lower()

            # determine creation timestamp (new vs old docs)
            ca = ev.get("createdAt") if ev.get("createdAt") else ev.get("timestamp")
            if isinstance(ca, datetime):
                created_day = ca.strftime("%Y-%m-%d")
            else:
                created_day = "unknown"
            key_created = f"{tag}__{created_day}"
            stats_c     = summary[intern_id][subject][key_created]

            # increment created counters
            if qtype == "mcq_test":
                stats_c["mcq_created"]  += 1
            else:
                stats_c["code_created"] += 1
            stats_c["total_created"] += 1

            # if verified, determine verification timestamp
            if ev.get("verified", False):
                va = ev.get("verifiedAt") if ev.get("verifiedAt") else ca
                if isinstance(va, datetime):
                    verified_day = va.strftime("%Y-%m-%d")
                else:
                    verified_day = created_day
                key_verified = f"{tag}__{verified_day}"
                stats_v       = summary[intern_id][subject][key_verified]

                # increment verified counters
                if qtype == "mcq_test":
                    stats_v["mcq_verified"]  += 1
                else:
                    stats_v["code_verified"] += 1
                stats_v["total_verified"] += 1

        # 3. Fetch intern meta (name, designation, location)
        intern_meta = {
            t["id"]: {
                "name":        t.get("name", "Unknown"),
                "designation": t.get("Designation", []),
                "location":    t.get("location", "Unknown")
            }
            for t in TESTERS.find({}, {"id": 1, "name": 1, "Designation": 1, "location": 1})
        }

        # 4. Flatten into a list
        results = []
        for intern_id, subjects in summary.items():
            meta = intern_meta.get(intern_id, {})
            for subject, tagdict in subjects.items():
                for key, stats in tagdict.items():
                    tag, date = key.split("__")
                    results.append({
                        "internId":      intern_id,
                        "name":          meta.get("name", "Unknown"),
                        "designation":   meta.get("designation", []),
                        "location":      meta.get("location", "Unknown"),
                        "subject":       subject,
                        "tag":           tag,
                        "date":          date,
                        "mcq_created":   stats["mcq_created"],
                        "mcq_verified":  stats["mcq_verified"],
                        "code_created":  stats["code_created"],
                        "code_verified": stats["code_verified"],
                        "total_created":   stats["total_created"],
                        "total_verified": stats["total_verified"],
                    })

        # 5. Sort by internId, date, subject (descending)
        sorted_progress = sorted(
            results,
            key=lambda x: (x["internId"], x["date"], x["subject"]),
            reverse=True
        )

        return {"success": True, "progress": sorted_progress}, 200
