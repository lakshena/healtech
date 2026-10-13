# Predictive Patient Flow Orchestrator (Flask + Bootstrap)
pip install -r requirements.txt
python app.py      # open http://127.0.0.1:5000
Pages: / (status + Chart.js), /patient (check-in + QR), /staff (JS QR scanner, admit/discharge), /ambulance (severity-based bed allocation, human approval).
Data: data/*.json and data/*.csv (mock).
