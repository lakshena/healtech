"""Predictive Patient Flow Orchestrator - Flask + Bootstrap prototype."""
import csv, io, json, random
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_file
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
    app.run(debug=True)
