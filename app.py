@app.post("/v1/survey")
def submit_survey():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "invalid_json", "detail": "Body must be application/json"}), 400

    try:
        submission = SurveySubmission(**payload)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "detail": ve.errors()}), 422

    # Build record with enriched fields (still using raw validated values)
    record = StoredSurveyRecord(
        **submission.dict(),
        received_at=datetime.now(timezone.utc),
        ip=request.headers.get("X-Forwarded-For", request.remote_addr or ""),
        user_agent=request.headers.get("User-Agent"),
        submission_id=payload.get("submission_id")  # optional
    )

    # Convert to dict so we can hash sensitive fields before writing
    record_dict = record.dict()

    # Hash PII
    record_dict["email"] = hash_value(submission.email)   # keep original validated value
    record_dict["age"] = hash_value(str(submission.age))

    # If no submission_id provided, compute one
    if not record_dict.get("submission_id"):
        base = submission.email + datetime.now().strftime("%Y%m%d%H")
        record_dict["submission_id"] = hash_value(base)

    # Write to NDJSON file
    append_json_line(record_dict)

    return jsonify({"status": "ok"}), 201

