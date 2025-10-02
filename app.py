from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from models import SurveySubmission, StoredSurveyRecord
from storage import append_json_line
import hashlib

app = Flask(__name__)
CORS(app, resources={r"/v1/*": {"origins": "*"}})

def hash_value(value: str) -> str:
    """Return SHA-256 hash of a string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "ok",
        "message": "API is alive",
        "utc_time": datetime.now(timezone.utc).isoformat()
    })

@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    # Convert to dict so we can modify before saving
    record_data = submission.dict()

    # --- Exercise 11 additions ---
    # 1) Hash PII fields
    record_data["email"] = hash_value(record_data["email"])
    record_data["age"] = hash_value(str(record_data["age"]))

    # 2) Add server-enriched fields
    record_data.update({
        "received_at": datetime.now(timezone.utc),
        "ip": request.headers.get("X-Forwarded-For", request.remote_addr or ""),
        "user_agent": request.headers.get("User-Agent"),
    })

    # 3) Add submission_id if missing
    if not record_data.get("submission_id"):
        base = submission.email + datetime.now().strftime("%Y%m%d%H")
        record_data["submission_id"] = hash_value(base)

    # Build a StoredSurveyRecord instance
    record = StoredSurveyRecord(**record_data)

    # Append to file
    append_json_line(record.dict())

    return jsonify({"status": "ok"}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

