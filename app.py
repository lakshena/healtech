"""Predictive Patient Flow Orchestrator - Flask + Bootstrap prototype."""
import csv, io, json, os, random
from pathlib import Path
from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for
import qrcode

BASE = Path(__file__).parent / "data"
app = Flask(__name__)

def load(name):
    return json.loads((BASE / name).read_text())

def save(name, data):
    (BASE / name).write_text(json.dumps(data, indent=2))

def read_csv(name):
    with open(BASE / name) as f:
        return list(csv.DictReader(f))

RESOURCE_FIELDS = [
    "hospital", "resource", "type", "available", "rent_per_day",
    "purchase_price",
]

def write_resources(resources):
    with (BASE / "resources.csv").open("w", newline="") as resource_file:
        writer = csv.DictWriter(resource_file, fieldnames=RESOURCE_FIELDS)
        writer.writeheader()
        writer.writerows(resources)

# Rule-based allocation: severity 4-5 prefer ICU, 3 ER, 1-2 General; fall back if full.
PREFS = {5: ["ICU", "ER", "General"], 4: ["ICU", "ER", "General"],
         3: ["ER", "General", "ICU"], 2: ["General", "ER"], 1: ["General", "ER"]}

def allocate(severity, beds):
    for ward in PREFS[int(severity)]:
        if beds[ward]["occupied"] < beds[ward]["total"]:
            return ward
    return None

def wait_minutes(severity, patients):
    ahead = sum(1 for p in patients if p["status"] == "waiting" and p["severity"] >= severity)
    return max(5, ahead * 12 - (severity - 1) * 3)

def set_status(pid, status):
    patients, beds = load("patients.json"), load("beds.json")
    p = next((x for x in patients if x["id"] == pid), None)
    if not p:
        return None, "Patient not found"
    if status == "admitted" and p["status"] != "admitted":
        ward = allocate(p["severity"], beds)
        if not ward:
            return None, "No beds available"
        beds[ward]["occupied"] += 1
        p["ward"] = ward
    if status == "discharged" and p["status"] == "admitted" and p["ward"]:
        beds[p["ward"]]["occupied"] -= 1
    p["status"] = status
    save("patients.json", patients); save("beds.json", beds)
    return p, None

# ---------- Pages ----------
@app.route("/")
def status_page():
    return render_template("status.html", beds=load("beds.json"),
                           patients=load("patients.json"),
                           arrivals=read_csv("patient_arrivals.csv"),
                           doctors=read_csv("doctor_schedules.csv"))

@app.route("/patient")
def patient_page():
    return render_template("patient.html")

@app.route("/staff")
def staff_page():
    return render_template("staff.html", patients=load("patients.json"))

@app.route("/ambulance")
def ambulance_page():
    return render_template("ambulance.html", beds=load("beds.json"))

@app.get("/marketplace")
def marketplace_page():
    return render_template(
        "marketplace.html",
        resources=read_csv("resources.csv"),
        exchanged=request.args.get("exchanged"),
        hospital=request.args.get("hospital"),
        transaction_type=request.args.get("transaction_type"),
        quantity=request.args.get("quantity"),
        rental_days=request.args.get("rental_days"),
        total=request.args.get("total"),
        listing_message=request.args.get("listing_message"),
    )

@app.post("/exchange")
def exchange_resource():
    hospital = request.form.get("hospital", "").strip()
    listing_id = request.form.get("listing_id", "")
    transaction_type = request.form.get("transaction_type", "")
    resources = read_csv("resources.csv")
    try:
        quantity = int(request.form.get("quantity", ""))
        rental_days = int(request.form.get("rental_days", "1"))
    except ValueError:
        quantity, rental_days = 0, 0

    error = None
    try:
        listing_index = int(listing_id)
    except ValueError:
        listing_index = -1

    if not hospital or listing_index < 0 or listing_index >= len(resources):
        error = "Enter your hospital name and choose an offer."
    elif transaction_type not in {"rent", "buy"}:
        error = "Choose whether to rent or buy this item."
    elif quantity < 1:
        error = "Quantity must be at least one."
    elif transaction_type == "rent" and not 1 <= rental_days <= 90:
        error = "Rental duration must be between 1 and 90 days."

    resource = resources[listing_index] if error is None else None
    if error is None and (
        quantity > int(resource["available"])
    ):
        error = "That offer does not have enough units available."

    if error:
        return render_template(
            "marketplace.html",
            resources=resources,
            error=error,
            hospital_name=hospital,
            selected_listing=listing_id,
            transaction_type=transaction_type,
            quantity=quantity if quantity > 0 else 1,
            rental_days=rental_days if rental_days > 0 else 1,
        ), 400

    unit_price = int(
        resource["rent_per_day"]
        if transaction_type == "rent"
        else resource["purchase_price"]
    )
    total = unit_price * quantity * (rental_days if transaction_type == "rent" else 1)
    resource["available"] = str(int(resource["available"]) - quantity)
    write_resources(resources)
    return redirect(url_for(
        "marketplace_page",
        exchanged=resource["resource"],
        hospital=hospital,
        supplier=resource["hospital"],
        transaction_type=transaction_type,
        quantity=quantity,
        rental_days=rental_days if transaction_type == "rent" else None,
        total=total,
    ))

@app.post("/marketplace/listings/save")
def save_marketplace_listing():
    resources = read_csv("resources.csv")
    listing_id = request.form.get("listing_id", "").strip()
    hospital = request.form.get("hospital", "").strip()
    resource = request.form.get("resource", "").strip()
    resource_type = request.form.get("type", "").strip()

    try:
        available = int(request.form.get("available", ""))
        rent_per_day = int(request.form.get("rent_per_day", ""))
        purchase_price = int(request.form.get("purchase_price", ""))
        listing_index = int(listing_id) if listing_id else None
    except ValueError:
        return render_template(
            "marketplace.html",
            resources=resources,
            listing_error="Enter whole-number availability and prices.",
        ), 400

    if not hospital or not resource or not resource_type:
        return render_template(
            "marketplace.html",
            resources=resources,
            listing_error="Hospital, equipment name, and category are required.",
        ), 400
    if min(available, rent_per_day, purchase_price) < 0:
        return render_template(
            "marketplace.html",
            resources=resources,
            listing_error="Availability and prices cannot be negative.",
        ), 400
    if listing_index is not None and not 0 <= listing_index < len(resources):
        return render_template(
            "marketplace.html",
            resources=resources,
            listing_error="That listing no longer exists. Refresh and try again.",
        ), 404

    listing = {
        "hospital": hospital,
        "resource": resource,
        "type": resource_type,
        "available": str(available),
        "rent_per_day": str(rent_per_day),
        "purchase_price": str(purchase_price),
    }
    if listing_index is None:
        resources.append(listing)
        message = "Listing added."
    else:
        resources[listing_index] = listing
        message = "Listing updated."
    write_resources(resources)
    return redirect(url_for("marketplace_page", listing_message=message))

@app.post("/marketplace/listings/<int:listing_index>/delete")
def delete_marketplace_listing(listing_index):
    resources = read_csv("resources.csv")
    if not 0 <= listing_index < len(resources):
        return render_template(
            "marketplace.html",
            resources=resources,
            listing_error="That listing no longer exists. Refresh and try again.",
        ), 404
    del resources[listing_index]
    write_resources(resources)
    return redirect(url_for("marketplace_page", listing_message="Listing removed."))

# ---------- APIs ----------
@app.get("/api/status")
def api_status():
    patients = load("patients.json")
    return jsonify(beds=load("beds.json"),
                   waiting=sum(p["status"] == "waiting" for p in patients),
                   avg_wait=wait_minutes(2, patients))

@app.post("/api/checkin")
def api_checkin():
    d = request.get_json()
    patients = load("patients.json")
    p = {"id": f"P-{random.randint(2000, 9999)}", "name": d["name"],
         "severity": int(d["severity"]), "status": "waiting", "ward": None}
    patients.append(p); save("patients.json", patients)
    return jsonify(patient=p, wait=wait_minutes(p["severity"], patients))

@app.get("/api/qr/<pid>")
def api_qr(pid):
    buf = io.BytesIO()
    qrcode.make(pid).save(buf, format="PNG"); buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.post("/api/patients/<pid>/status")
def api_set_status(pid):
    p, err = set_status(pid, request.get_json()["status"])
    return (jsonify(error=err), 400) if err else jsonify(patient=p)

@app.post("/api/ambulance/recommend")
def api_recommend():
    sev = int(request.get_json()["severity"])
    return jsonify(ward=allocate(sev, load("beds.json")))

@app.post("/api/ambulance/approve")
def api_approve():
    d = request.get_json()
    beds = load("beds.json")
    ward = d["ward"]
    if beds[ward]["occupied"] >= beds[ward]["total"]:
        return jsonify(error="Ward full"), 400
    beds[ward]["occupied"] += 1; save("beds.json", beds)
    patients = load("patients.json")
    p = {"id": f"A-{random.randint(2000, 9999)}", "name": d.get("name") or "Ambulance patient",
         "severity": int(d["severity"]), "status": "admitted", "ward": ward}
    patients.append(p); save("patients.json", patients)
    return jsonify(patient=p)

if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG") == "1",
    )
