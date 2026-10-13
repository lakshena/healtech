from flask import Flask, render_template, request
import pandas as pd
import qrcode

app = Flask(__name__)

# --- Dashboard Route ---
@app.route("/")
def dashboard():
    beds = pd.read_csv("data/beds.csv")
    patients = pd.read_csv("data/patients.csv")
    doctors = pd.read_csv("data/doctors.csv")
    return render_template("dashboard.html",
                           beds=beds.to_dict(orient="records"),
                           patients=patients.to_dict(orient="records"),
                           doctors=doctors.to_dict(orient="records"))

# --- Patient Registration + QR ---
@app.route("/register", methods=["POST"])
def register_patient():
    name = request.form["name"]
    severity = request.form["severity"]
    df = pd.read_csv("data/patients.csv")
    new_id = len(df) + 1
    df.loc[len(df)] = [new_id, name, "waiting", severity]
    df.to_csv("data/patients.csv", index=False)

    img = qrcode.make(f"PatientID:{new_id}")
    img.save(f"static/qr_{new_id}.png")

    return f"✅ Patient {name} registered with ID {new_id}. QR generated!"

# --- Marketplace View ---
@app.route("/marketplace")
def marketplace():
    df = pd.read_csv("data/resources.csv")
    return render_template("marketplace.html", resources=df.to_dict(orient="records"))

# --- Marketplace Exchange ---
@app.route("/exchange", methods=["POST"])
def exchange():
    hospital = request.form["hospital"]
    resource = request.form["resource"]
    df = pd.read_csv("data/resources.csv")
    df.loc[df["hospital"]==hospital, "available"] = df.loc[df["hospital"]==hospital, "available"] - 1
    df.to_csv("data/resources.csv", index=False)
    return f"✅ {hospital} has shared {resource}. Transaction recorded!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
