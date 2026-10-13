from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


st.set_page_config(
    page_title="Hospital Overview",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { color-scheme: light; }
    .stApp { background: #eaf4e8; color: #111111; }
    [data-testid="stSidebar"] {
        background: #dcebd9;
        border-right: 1px solid #b8cdb5;
    }
    [data-testid="stHeader"] { background: rgba(234, 244, 232, 0.9); }
    h1, h2, h3, p, label, [data-testid="stCaptionContainer"] {
        color: #111111;
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #cbd8c8;
        border-radius: 12px;
        padding: 16px;
    }
    [data-testid="stSelectbox"] [role="combobox"],
    [data-testid="stTextInput"] input {
        background: #ffffff;
        color: #111111;
        border-color: #777777;
    }
    .stButton > button {
        background: #111111;
        color: #ffffff;
        border: 1px solid #111111;
        border-radius: 8px;
    }
    .stButton > button:hover {
        background: #333333;
        color: #ffffff;
        border-color: #333333;
    }
    [data-testid="stPlotlyChart"],
    [data-testid="stDataFrame"] {
        background: #ffffff;
        border: 1px solid #cbd8c8;
        border-radius: 12px;
        padding: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

UNITS = ["Emergency", "ICU", "Medical", "Surgery", "Pediatrics"]
API_PATHS = {
    "beds": "/api/dashboard/bed-occupancy",
    "er": "/api/dashboard/er-queue",
    "doctors": "/api/dashboard/doctor-availability",
    "alerts": "/api/dashboard/bottlenecks",
}

DEMO_DOCTOR_NAMES = {
    "Emergency": [
        "Dr. Aisha Menon", "Dr. Aarav Kulkarni", "Dr. Farah Siddiqui",
        "Dr. Karan Bedi", "Dr. Nisha Thomas", "Dr. Dev Malhotra",
        "Dr. Meera Nair", "Dr. Kabir Sethi", "Dr. Rhea Kapoor",
        "Dr. Arjun Rao", "Dr. Sana Fernandes", "Dr. Vikram Shah",
    ],
    "ICU": [
        "Dr. Nandini Rao", "Dr. Ishaan Patel", "Dr. Tania Ghosh",
        "Dr. Rohan Das", "Dr. Priya Iyer", "Dr. Armaan Khan",
        "Dr. Leena Joseph", "Dr. Sameer Bose",
    ],
    "Medical": [
        "Dr. Mira Menon", "Dr. Aditya Roy", "Dr. Ananya Kapoor",
        "Dr. Neil D'Souza", "Dr. Kavya Reddy", "Dr. Vivaan Shah",
        "Dr. Isha Banerjee", "Dr. Omar Qureshi", "Dr. Tara Mukherjee",
        "Dr. Dhruv Nair", "Dr. Zoya Ali", "Dr. Kunal Mehta",
        "Dr. Ritu Sharma", "Dr. Reyansh Das", "Dr. Pooja Pillai",
        "Dr. Manav Arora",
    ],
    "Surgery": [
        "Dr. Kabir Anand", "Dr. Siya Gupta", "Dr. Rishabh Sen",
        "Dr. Alia George", "Dr. Siddharth Jain", "Dr. Noor Ahmed",
        "Dr. Yash Bhatia", "Dr. Sara Dutta", "Dr. Harish Nambiar",
        "Dr. Diya Rao", "Dr. Arnav Bose",
    ],
    "Pediatrics": [
        "Dr. Avni Shah", "Dr. Shaan Thomas", "Dr. Aditi Verma",
        "Dr. Reya Dutta", "Dr. Anil Koshy", "Dr. Myra Kapoor",
        "Dr. Eshan Roy",
    ],
}

DEMO_DOCTOR_COUNTS = {
    "Emergency": {"available": 7, "on_call": 3},
    "ICU": {"available": 5, "on_call": 2},
    "Medical": {"available": 9, "on_call": 4},
    "Surgery": {"available": 6, "on_call": 3},
    "Pediatrics": {"available": 4, "on_call": 2},
}

DEPARTMENT_SPECIALTIES = {
    "Emergency": "Emergency medicine",
    "ICU": "Critical care",
    "Medical": "Internal medicine",
    "Surgery": "General surgery",
    "Pediatrics": "Pediatrics",
}

MARKETPLACE_ITEMS = [
    {
        "name": "Oxygen concentrator",
        "category": "Respiratory care",
        "daily_rate": 850,
        "description": "Portable unit for home oxygen support.",
        "availability": "2 available",
        "image": "oxygen-concentrator.svg",
    },
    {
        "name": "Manual wheelchair",
        "category": "Mobility",
        "daily_rate": 450,
        "description": "Foldable wheelchair with comfortable armrests.",
        "availability": "4 available",
        "image": "wheelchair.svg",
    },
    {
        "name": "Adjustable hospital bed",
        "category": "Patient care",
        "daily_rate": 1200,
        "description": "Height-adjustable bed with side rails.",
        "availability": "3 available",
        "image": "hospital-bed.svg",
    },
    {
        "name": "Patient monitor",
        "category": "Monitoring",
        "daily_rate": 700,
        "description": "Bedside monitor for vital-sign observation.",
        "availability": "2 available",
        "image": "patient-monitor.svg",
    },
]


def make_demo_doctor_roster() -> list[dict]:
    """Create a sample individual roster from the department totals."""
    roster = []
    for department, names in DEMO_DOCTOR_NAMES.items():
        counts = DEMO_DOCTOR_COUNTS[department]
        available_count = counts["available"]
        on_call_count = counts["on_call"]
        for index, name in enumerate(names):
            if index < available_count:
                shift_status = "On duty"
                availability = "Available"
            elif index < available_count + on_call_count:
                shift_status = "On call"
                availability = "Not available"
            else:
                shift_status = "Off duty"
                availability = "Not available"
            roster.append(
                {
                    "name": name,
                    "department": department,
                    "specialty": DEPARTMENT_SPECIALTIES[department],
                    "shift": ["Day", "Evening", "Night"][index % 3],
                    "shift_status": shift_status,
                    "availability": availability,
                }
            )
    return roster


def make_demo_data(days: int, selected_unit: str) -> dict:
    """Generate illustrative operational data for the selected view."""
    today = date.today()
    bed_rows = []
    bed_units = []
    unit_capacity = {
        "Emergency": 24,
        "ICU": 32,
        "Medical": 74,
        "Surgery": 38,
        "Pediatrics": 26,
    }
    base_occupancy = {
        "Emergency": 0.78,
        "ICU": 0.91,
        "Medical": 0.84,
        "Surgery": 0.73,
        "Pediatrics": 0.69,
    }

    for index, unit in enumerate(UNITS):
        capacity = unit_capacity[unit]
        occupied = round(capacity * base_occupancy[unit])
        bed_units.append({"unit": unit, "occupied": occupied, "total": capacity})
        for offset in range(days - 1, -1, -1):
            day = today - timedelta(days=offset)
            wave = ((days - offset + index * 2) % 5) - 2
            bed_rows.append(
                {
                    "date": day.isoformat(),
                    "unit": unit,
                    "occupied": max(0, min(capacity, occupied + wave)),
                    "total": capacity,
                }
            )

    er_hours = [
        "06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
        "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
    ]
    er_counts = [7, 9, 11, 14, 17, 19, 16, 21, 24, 22, 20, 18]
    er_hourly = [
        {"time": hour, "queue_length": count}
        for hour, count in zip(er_hours, er_counts)
    ]

    doctors = make_demo_doctor_roster()
    alerts = [
        {
            "reason_code": "ER-TRIAGE-02",
            "severity": "High",
            "title": "Triage queue above target",
            "detail": "Seven people have waited more than 20 minutes for triage.",
            "location": "Emergency",
            "count": 7,
            "updated": "4 min ago",
        },
        {
            "reason_code": "BED-TURNOVER-04",
            "severity": "High",
            "title": "ICU beds nearing capacity",
            "detail": "Only 3 staffed beds remain available in intensive care.",
            "location": "ICU",
            "count": 3,
            "updated": "9 min ago",
        },
        {
            "reason_code": "STAFF-COVER-03",
            "severity": "Medium",
            "title": "Evening shift coverage gap",
            "detail": "Medical ward coverage is below plan for the 19:00 shift.",
            "location": "Medical",
            "count": 2,
            "updated": "16 min ago",
        },
        {
            "reason_code": "LAB-RESULT-01",
            "severity": "Low",
            "title": "Lab results pending",
            "detail": "Four emergency panels are awaiting verification.",
            "location": "Emergency",
            "count": 4,
            "updated": "22 min ago",
        },
    ]

    if selected_unit != "All units":
        bed_rows = [row for row in bed_rows if row["unit"] == selected_unit]
        bed_units = [row for row in bed_units if row["unit"] == selected_unit]
        doctors = [row for row in doctors if row["department"] == selected_unit]
        alerts = [row for row in alerts if row["location"] == selected_unit]

    return {
        "bed_trend": bed_rows,
        "bed_units": bed_units,
        "er_hourly": er_hourly,
        "er_wait_minutes": 38,
        "er_critical": 3,
        "doctors": doctors,
        "alerts": alerts,
    }


def request_json(base_url: str, path: str, params: dict | None = None):
    response = requests.get(
        f"{base_url.rstrip('/')}{path}",
        params=params,
        timeout=8,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def load_api_data(base_url: str, days: int, selected_unit: str) -> dict:
    """Load data from the dashboard's four documented endpoints."""
    params = {"days": days, "unit": selected_unit}
    bed_payload = request_json(base_url, API_PATHS["beds"], params)
    er_payload = request_json(base_url, API_PATHS["er"])
    doctor_payload = request_json(base_url, API_PATHS["doctors"], params)
    alert_payload = request_json(base_url, API_PATHS["alerts"], params)

    data = {
        "bed_trend": bed_payload["trend"],
        "bed_units": bed_payload["units"],
        "er_hourly": er_payload["hourly"],
        "er_wait_minutes": er_payload["wait_minutes"],
        "er_critical": er_payload["critical"],
        "doctors": doctor_payload["doctors"],
        "alerts": (
            alert_payload
            if isinstance(alert_payload, list)
            else alert_payload["alerts"]
        ),
    }
    for key in ("bed_trend", "bed_units", "er_hourly", "doctors", "alerts"):
        if not isinstance(data[key], list):
            raise ValueError(f"Hospital data returned an invalid '{key}' value.")
    return data


def render_bed_chart(data: dict):
    frame = pd.DataFrame(data["bed_trend"])
    if frame.empty:
        st.info("No bed information is available for this area.")
        return
    frame["date"] = pd.to_datetime(frame["date"])
    frame["occupancy"] = (frame["occupied"] / frame["total"] * 100).round(1)
    figure = px.line(
        frame,
        x="date",
        y="occupancy",
        color="unit",
        markers=True,
        labels={"date": "", "occupancy": "Beds in use (%)", "unit": "Area"},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    figure.update_layout(
        height=315,
        margin=dict(l=8, r=8, t=12, b=8),
        legend_title_text="",
        hovermode="x unified",
    )
    figure.update_yaxes(range=[0, 105], ticksuffix="%", gridcolor="#e8edf2")
    figure.update_xaxes(showgrid=False)
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})


def render_er_chart(data: dict):
    frame = pd.DataFrame(data["er_hourly"])
    if frame.empty:
        st.info("No emergency room waiting information is available.")
        return
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=frame["time"],
            y=frame["queue_length"],
            mode="lines+markers",
            line=dict(color="#e77742", width=3, shape="spline"),
            marker=dict(size=7),
            fill="tozeroy",
            fillcolor="rgba(231, 119, 66, 0.12)",
            hovertemplate="%{x}<br><b>%{y} people waiting</b><extra></extra>",
        )
    )
    figure.add_hline(
        y=15,
        line_dash="dot",
        line_color="#cf9a35",
        annotation_text="Target 15",
        annotation_position="top left",
    )
    figure.update_layout(
        height=270,
        margin=dict(l=8, r=8, t=16, b=8),
        showlegend=False,
        yaxis_title="People waiting",
        xaxis_title="",
    )
    figure.update_yaxes(rangemode="tozero", gridcolor="#e8edf2")
    figure.update_xaxes(showgrid=False)
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})


def render_doctor_roster(doctors: list[dict], selected_unit: str):
    frame = pd.DataFrame(doctors)
    if frame.empty:
        st.info("No doctors are listed for this area.")
        return

    available_count = int((frame["availability"] == "Available").sum())
    unavailable_count = len(frame) - available_count
    availability_column, shift_column = st.columns(2)
    availability_column.success(f"{available_count} available")
    shift_column.info(f"{unavailable_count} not available")

    search_column, status_column = st.columns([2, 1])
    search_term = search_column.text_input(
        "Search doctors",
        placeholder="Search by name, specialty, or area",
    ).strip().lower()
    status_filter = status_column.selectbox(
        "Show",
        ["Everyone", "Available now", "Not available now"],
    )
    if search_term:
        searchable = frame[
            ["name", "department", "specialty", "shift", "shift_status"]
        ].astype(str).agg(" ".join, axis=1).str.lower()
        frame = frame[searchable.str.contains(search_term, regex=False)]
    availability_filter = {
        "Everyone": None,
        "Available now": "Available",
        "Not available now": "Not available",
    }[status_filter]
    if availability_filter:
        frame = frame[frame["availability"] == availability_filter]

    roster_scope = "Hospital-wide" if selected_unit == "All units" else selected_unit
    st.caption(f"{len(frame)} doctors · {roster_scope}")
    if frame.empty:
        st.info("No doctors match your search and availability filter.")
        return

    display_frame = frame[
        ["name", "department", "specialty", "shift", "shift_status", "availability"]
    ].rename(
        columns={
            "name": "Doctor",
            "department": "Area",
            "specialty": "Specialty",
            "shift": "Shift",
            "shift_status": "Shift status",
            "availability": "Availability",
        }
    )
    display_frame["Availability"] = display_frame["Availability"].map(
        lambda value: f"● {value}"
    )

    def style_availability(value: str) -> str:
        if value == "● Available":
            return "color: #166534; background-color: #dcfce7; font-weight: 700;"
        return "color: #991b1b; background-color: #fee2e2; font-weight: 700;"

    st.dataframe(
        display_frame.style.map(style_availability, subset=["Availability"]),
        hide_index=True,
        width="stretch",
        height=min(680, 42 + len(display_frame) * 38),
    )


def render_alerts(alerts: list[dict]):
    if not alerts:
        st.success("There are no current notices for this area.")
        return
    for alert in alerts:
        with st.container(border=True):
            left, right = st.columns([5, 1])
            with left:
                st.markdown(f"**{alert.get('title', 'Hospital notice')}**")
                st.caption(alert.get("detail", "No additional information."))
            with right:
                st.markdown(f"**{alert.get('severity', 'Medium')}**")
                st.caption(alert.get("updated", ""))
            with st.expander("More details"):
                location, count = st.columns(2)
                location.caption(f"Area: {alert.get('location', 'Hospital-wide')}")
                count.caption(f"Count: {alert.get('count', 0)}")
                st.caption(
                    f"Reference: `{alert.get('reason_code', 'UNSPECIFIED')}`"
                )


def render_marketplace():
    st.title("Medical equipment marketplace")
    st.caption(
        "Browse sample medical equipment available to rent. "
        "Prices are shown per day."
    )

    categories = ["All equipment"] + sorted(
        {item["category"] for item in MARKETPLACE_ITEMS}
    )
    filter_column, search_column = st.columns([1, 2])
    selected_category = filter_column.selectbox("Equipment type", categories)
    search_term = search_column.text_input(
        "Search equipment",
        placeholder="Try oxygen, wheelchair, bed...",
    ).strip().lower()
    filtered_items = [
        item
        for item in MARKETPLACE_ITEMS
        if (
            selected_category == "All equipment"
            or item["category"] == selected_category
        )
        and (
            not search_term
            or search_term in item["name"].lower()
            or search_term in item["description"].lower()
            or search_term in item["category"].lower()
        )
    ]
    st.caption(f"{len(filtered_items)} sample item(s) listed")
    if not filtered_items:
        st.info("No equipment matches your search. Try a different term.")
        return

    for start in range(0, len(filtered_items), 3):
        cards = st.columns(3)
        for card, item in zip(cards, filtered_items[start : start + 3]):
            with card:
                with st.container(border=True):
                    image_path = os.path.join(
                        os.path.dirname(__file__),
                        "assets",
                        "marketplace",
                        item["image"],
                    )
                    st.image(image_path, width="stretch")
                    st.caption(item["category"])
                    st.subheader(item["name"])
                    st.markdown(f"**₹{item['daily_rate']:,} / day**")
                    st.write(item["description"])
                    st.caption(item["availability"])

    st.info(
        "These are demo listings and illustrative prices, not confirmed offers. "
        "Please check actual availability, delivery, and rental terms with "
        "the equipment provider."
    )


with st.sidebar:
    st.header("Choose your view")
    selected_page = st.selectbox(
        "Open",
        ["Hospital overview", "Marketplace"],
    )
    if selected_page == "Hospital overview":
        data_source = st.selectbox(
            "Information source",
            ["Sample data", "Live hospital data"],
        )
        api_base_url = os.getenv("MEMBER1_API_BASE_URL", "")
        if data_source == "Live hospital data":
            api_base_url = st.text_input(
                "Hospital data address",
                value=api_base_url,
                placeholder="Enter the address provided by your administrator",
                help="Ask your administrator for the live hospital data address.",
            )
        selected_range = st.selectbox(
            "Bed history",
            ["7 days", "14 days", "30 days"],
        )
        selected_unit = st.selectbox("Hospital area", ["All areas", *UNITS])
        refresh = st.button(
            "Update information",
            type="primary",
            width="stretch",
        )
        st.divider()
        st.caption("This overview does not show individual patient information.")

if selected_page == "Marketplace":
    render_marketplace()
    st.stop()


st.title("Hospital overview")
st.caption("A simple view of beds, emergency room activity, staff, and notices.")

days = int(selected_range.split()[0])
unit_filter = "All units" if selected_unit == "All areas" else selected_unit
if refresh:
    st.cache_data.clear()

api_error = None
api_error_detail = None
if data_source == "Live hospital data":
    if not api_base_url.strip():
        api_error = "Enter the hospital data address to load live information."
        data = make_demo_data(days, unit_filter)
    else:
        try:
            data = load_api_data(api_base_url.strip(), days, unit_filter)
        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
        ) as error:
            api_error = "Live information is temporarily unavailable."
            api_error_detail = str(error)
            data = make_demo_data(days, unit_filter)
else:
    data = make_demo_data(days, unit_filter)

if data_source == "Sample data":
    st.info(
        "You are viewing sample information. Choose **Live hospital data** "
        "in the left panel to connect to current information."
    )
elif api_error:
    st.warning(f"{api_error} Sample information is shown instead.")
    if api_error_detail:
        with st.expander("More information"):
            st.caption(api_error_detail)
else:
    st.success("Live hospital information is connected.")

occupied_beds = sum(int(unit["occupied"]) for unit in data["bed_units"])
total_beds = sum(int(unit["total"]) for unit in data["bed_units"])
occupancy = (occupied_beds / total_beds * 100) if total_beds else 0
queue_now = int(data["er_hourly"][-1]["queue_length"]) if data["er_hourly"] else 0
available_doctors = sum(
    1 for row in data["doctors"] if row["availability"] == "Available"
)
total_doctors = len(data["doctors"])
active_alerts = len(data["alerts"])

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric(
    "Beds in use",
    f"{occupancy:.0f}%",
    f"{occupied_beds} of {total_beds} beds",
    delta_color="off",
)
kpi2.metric(
    "Emergency room",
    f"{queue_now} waiting",
    "People waiting now",
    delta_color="off",
)
kpi3.metric(
    "Doctors on duty",
    f"{available_doctors} / {total_doctors}",
    "Available now",
    delta_color="off",
)
kpi4.metric(
    "Notices",
    str(active_alerts),
    "Please review" if active_alerts else "Nothing needs attention",
    delta_color="inverse" if active_alerts else "normal",
)

st.divider()
left, right = st.columns([1.35, 1])
with left:
    st.subheader("Beds in use")
    st.caption(f"Daily use over the last {selected_range.lower()}")
    render_bed_chart(data)
with right:
    st.subheader("Emergency room waiting")
    st.caption(
        f"Typical wait: {data['er_wait_minutes']} minutes · "
        f"Urgent cases: {data['er_critical']}"
    )
    render_er_chart(data)

st.divider()
st.subheader("Find a doctor")
st.caption("Search doctors by name or area, or narrow the list by availability.")
render_doctor_roster(data["doctors"], unit_filter)

st.divider()
alerts_left, alerts_right = st.columns([3, 1])
with alerts_left:
    st.subheader("Notices to review")
with alerts_right:
    st.caption(f"{active_alerts} current")
render_alerts(data["alerts"])

st.caption(
    "Sample information is illustrative and not for clinical decision-making."
)
