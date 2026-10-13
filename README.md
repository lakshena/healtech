# Healtech dashboard

Run the Streamlit dashboard from the repository root:

```powershell
python -m pip install streamlit pandas plotly requests
python -m streamlit run "Dashboard main.py"
```

The dashboard includes a sample hospital overview and a medical equipment
marketplace with illustrative daily rental prices and local SVG illustrations.
Select **Hospital overview** or **Marketplace** in the left panel. Live
hospital data is optional and can be connected by entering the API base URL
provided by the administrator.

Marketplace listings and prices are demo data, not confirmed offers.