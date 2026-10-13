# Healtech

Healtech is a prototype for hospital operations and resource sharing. It
contains two independently launched applications:

- A **Flask patient-flow app** for check-in, QR-based staff workflows, ambulance
  intake, and a hospital equipment marketplace.
- A **Streamlit hospital dashboard** for bed and emergency-room trends, doctor
  availability, hospital notices, and a visual sample equipment marketplace.

Both applications use illustrative prototype data. They are not clinical
decision-support or payment systems.

## Marketplace pitch

**Put underused medical equipment to work—and help another hospital get what
it needs, when it needs it.**

The marketplace makes inter-hospital resource sharing easier to evaluate:
browse offers by hospital, compare a clear per-item daily rental rate with a
one-time purchase price, check listed availability, and estimate the cost for
the quantity and rental duration you need. Hospitals can also add, update, or
remove listings in the Flask prototype.

This can help hospitals discover nearby capacity before buying equipment they
may only need temporarily, while giving suppliers a simple way to advertise
available stock. Actual availability, delivery, rental terms, and payment must
be confirmed directly between hospitals. The current marketplace is a demo; it
does not process payments or arrange fulfillment.

## Flask patient-flow app

### Run it

From the repository root:

```powershell
python -m pip install -r requirements.txt
python app.py
```

When the server reports that it is running, open the dashboard at
<http://172.16.15.245:5000>. This is the hospital status overview. To open a
specific section directly, visit `/patient`, `/staff`, `/ambulance`, or
`/marketplace` on the same address.

The Flask app listens on all network interfaces by default. To open it from
another computer or phone on the **same trusted private Wi-Fi/LAN**:

1. On the computer running Flask, find its private IPv4 address with
   `ipconfig` on Windows or `ip addr` on Linux.
2. From the other device on that same network, open
   `http://<server-LAN-IP>:5000/marketplace`, replacing `<server-LAN-IP>` with
   that address. For example: `http://192.168.1.25:5000/marketplace`.

Do not use `127.0.0.1` from another device; it refers to that other device
itself. This private-network address does **not** make the app available from
unrelated servers or over the public internet. If the app runs on another
server, use that server's hostname or reachable IP and configure its network
and firewall to allow the app's port. On the same private network, the local
firewall may also need to allow inbound connections to the selected port.

### Access from outside the local network

A LAN address such as `http://192.168.x.x:5000` is only reachable on that
network. To let users elsewhere access the site, deploy it to a public hosting
provider and share the provider's public HTTPS address. The marketplace is a
page within the deployed site, at `<public-https-address>/marketplace`; it is
not a separately hosted app. The example Render hostname
`healtech-marketplace.onrender.com` is not guaranteed to exist until a Render
service has been created and deployed from this repository's `render.yaml`.
Confirm that both the site's root and `/marketplace` load before sharing it.

Browser camera access for QR scanning requires a secure context: HTTPS on a
deployed site, or localhost for local development. A plain HTTP LAN address
cannot be made camera-capable by changing the URL path. On the staff page,
enter a patient ID manually if the browser cannot use the camera.

Hosting providers may require a specific port; set `PORT` before launch, for
example:

```powershell
$env:PORT = "8080"
python app.py
```

The app also honors `HOST`; set it only if the hosting environment requires a
specific bind address. For a public or production deployment, use a production
WSGI server and add authentication, HTTPS, and hospital-level access controls.
Binding to `0.0.0.0` alone does not publish the app through a hosting provider's
firewall or router.

### Publish the Flask website on Render

The repository includes a Render Blueprint (`render.yaml`) for deploying the
**whole Flask app**. This publishes the overview and all Flask pages; the
marketplace is at `/marketplace` on the same site, not a separate service.

1. Sign in to Render and start a Blueprint deployment for this repository:
   [Deploy Healtech to Render](https://render.com/deploy?repo=https://github.com/lakshena/healtech).
   You can also choose **New → Blueprint** in Render and connect
   `lakshena/healtech` manually.
2. Select the branch containing `render.yaml` (use `main` after the deployment
   setup has been merged), then review the Blueprint.
3. Review and apply the Blueprint. It installs `requirements-render.txt` and
   starts the Flask WSGI app with Render's assigned port.
4. When the service is live, copy its public `https://<service-name>.onrender.com`
   address. Share the marketplace at
   `https://<service-name>.onrender.com/marketplace`; replace the example host
   with the exact URL Render assigns.

The local/LAN demo address and a Render-style hostname do not become public
just by putting them in a browser. A public URL is available only after the
Blueprint is applied and Render shows the service as **Live**. Then test both
the service root and `/marketplace`; a Render 404 means the service or route
isn't live at that address yet.

The Render Blueprint uses the free web-service plan, which may spin down while
idle. Its local demo JSON and CSV files are not backed by persistent storage;
edits or sample-data changes may be lost when the service restarts or is
redeployed.

**Public demo warning:** this app has no login or hospital-level authorization.
Anyone with the public link may view and change demo patient data and may add,
edit, remove, or order marketplace listings. Use only fictional data for a
public demo. Do not enter real patient information or use this deployment for
real clinical workflows or transactions. Add authentication and persistent
storage before broader operational use.

### Pages

| URL | Function |
| --- | --- |
| `/` | Hospital status overview with bed occupancy, patient queue, arrival trends, and doctor schedules. |
| `/patient` | Patient check-in form; submits a name and severity, then displays the patient ID, estimated wait, and QR code. |
| `/staff` | Staff patient queue with QR scanning or manual ID entry; supports admitting and discharging patients. |
| `/ambulance` | Enter an incoming patient's severity, get a ward recommendation, then approve the admission. |
| `/marketplace` | Browse equipment offers and submit an estimated rent or purchase request. Includes listing management controls. |

### Marketplace workflow

1. Browse and search offers, including supplier hospital, resource category,
   stock, rental price per item per day, and purchase price per item.
2. Choose an offer, enter the requesting hospital, and select rent or buy.
   Rental requests include a duration of 1–90 days; the page calculates an
   estimated total as you edit quantity and duration.
3. Submit a demo request. The prototype checks the requested stock, reduces
   the listing's available quantity, and displays an estimated total. It does
   not create a payment, delivery, or fulfillment record.
4. Use **Manage listings** to add, edit, or remove offers. Listing edits update
   the local CSV inventory.

**Important:** There is no login, identity verification, or listing ownership
enforcement. Anyone with access to the prototype can modify or remove any
listing. Do not use it for real transactions or sensitive information.

### Flask API

All API request and response bodies use JSON.

| Method and URL | Function |
| --- | --- |
| `GET /api/status` | Returns bed totals, number of waiting patients, and an estimated wait. |
| `POST /api/checkin` | Adds a waiting patient. Send `{"name":"Example","severity":3}`; severity is from 1 (mild) to 5 (critical). Returns the patient record and estimated wait. |
| `GET /api/qr/<patient_id>` | Returns a PNG QR code for the patient ID. |
| `POST /api/patients/<patient_id>/status` | Changes a patient's status. Send `{"status":"admitted"}` or `{"status":"discharged"}`. Admission allocates a suitable free bed; errors such as a full hospital return HTTP 400. |
| `POST /api/ambulance/recommend` | Recommends a ward for the supplied severity, for example `{"severity":4}`. |
| `POST /api/ambulance/approve` | Approves an ambulance admission. Send `{"name":"Example","severity":4,"ward":"ICU"}`; name is optional. |
| `POST /exchange` | Marketplace form handler. Validates the selected offer and rent/buy terms, calculates an estimate, and reduces the local demo stock. It does not store an order history. |
| `POST /marketplace/listings/save` | Adds a listing when `listing_id` is blank, or updates the indexed listing when provided. |
| `POST /marketplace/listings/<listing_index>/delete` | Removes the indexed marketplace listing. |

The marketplace is part of the Flask app; it uses server-rendered HTML forms,
not JSON, for its listing and order actions.

### Flask data files

The app reads and writes its local demo data under `data/`:

- `beds.json` — ward capacity and occupied beds.
- `patients.json` — patient IDs, severity, status, and ward.
- `patient_arrivals.csv` and `doctor_schedules.csv` — dashboard charts and
  schedule information.
- `resources.csv` — marketplace offers. Columns are `hospital`, `resource`,
  `type`, `available`, `rent_per_day`, and `purchase_price`; prices are integer
  rupee amounts.

Patient status changes and marketplace actions update local JSON or CSV files.
Use a copy of the data files if you want to experiment without changing the
checked-in sample data.

## Streamlit hospital dashboard

The Streamlit dashboard is a separate app from the Flask server. It offers a
hospital overview and a visual sample equipment marketplace; it does not use
the Flask `/marketplace` listing editor.

Install its additional packages and run it:

```powershell
python -m pip install streamlit pandas plotly requests
python -m streamlit run "Dashboard main.py" --server.address 0.0.0.0 --server.port 8501
```

Streamlit prints a **Local URL** in the terminal when the dashboard is ready
(typically <http://localhost:8501>). Open that URL in a browser, then choose
**Hospital overview** or **Marketplace** in the left sidebar. For another
device on the same private network, open
`http://<server-LAN-IP>:8501` instead. This Streamlit marketplace is a separate
visual sample from the Flask `/marketplace` page and its listing editor.

### Hospital overview features

- **Sample or live source:** the default is illustrative sample data. Live
  information can be loaded from a compatible hospital data API.
- **Bed trends:** choose a 7-, 14-, or 30-day history and filter by hospital
  area.
- **Emergency room activity:** view the queue trend, current wait estimate, and
  urgent-case count.
- **Doctor availability:** search the roster and filter by availability.
- **Notices:** review hospital alerts with severity, location, count, and
  reference details.
- **Refresh:** clear cached dashboard data and reload the selected source.

The dashboard's optional live source expects these GET endpoints on the
administrator-provided API base URL:

| Endpoint | Expected data |
| --- | --- |
| `/api/dashboard/bed-occupancy?days=<n>&unit=<name>` | `trend` and `units` arrays. |
| `/api/dashboard/er-queue` | `hourly`, `wait_minutes`, and `critical`. |
| `/api/dashboard/doctor-availability?days=<n>&unit=<name>` | `doctors` array. |
| `/api/dashboard/bottlenecks?days=<n>&unit=<name>` | An alerts array, directly or under an `alerts` key. |

If live data cannot be loaded, the dashboard reports the issue and falls back
to sample information.

### Streamlit marketplace

This visual-only sample marketplace includes category filtering, text search,
equipment cards, illustrative availability, and per-day rental prices. The
listings and prices are defined in `Dashboard main.py` and images are in
`assets/marketplace/`. They are not connected to the Flask CSV inventory.

## Project map

```text
app.py                    Flask routes, patient and bed logic, JSON APIs
Dashboard main.py         Streamlit dashboard and visual marketplace
templates/                Flask pages and shared layout
data/                     Local prototype JSON and CSV data
assets/marketplace/       Streamlit marketplace illustrations
static/                   Flask static assets
requirements.txt          Flask application dependencies
```

## Prototype and deployment notes

- Sample patient, bed, staff, and marketplace information is illustrative.
- The Flask development server and local files are intended for a demo, not a
  production deployment.
- Before real use, add authentication and hospital-level access controls,
  persistent transactional storage, audit logging, verified listings, and
  secure payment and fulfillment workflows.
