from flask import Flask, request, render_template, send_file
import pandas as pd
import requests
import json

app = Flask(__name__)

# Load CSV with BLS codes
csv_file_path = csv_file_path = r"C:\Users\ConnorWills\OneDrive - Mangum Economic Consulting, LLC\Connor\Work\BLS Automation\la_area_with_correct_series_ids.csv"
df_csv = pd.read_csv(csv_file_path)

# Extract state and county codes
state_series = df_csv[df_csv["display_level"] == 0].set_index("area_text")
county_series = df_csv[df_csv["area_type_code"] == "F"].copy()

# State name to abbreviation mapping
state_name_to_abbr = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", 
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", 
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
}

def fetch_bls_data(county_name, state_name):
    """Fetch employment and unemployment data from BLS API"""
    state_abbr = state_name_to_abbr.get(state_name)
    if not state_abbr:
        return None, f"Invalid state name: {state_name}"

    county_data = county_series[
        (county_series["area_text"].str.contains(county_name)) & 
        (county_series["area_text"].str.endswith(state_abbr))
    ]

    if county_data.empty:
        return None, f"County {county_name}, {state_name} not found."

    state_data = state_series.loc[state_name]

    series_ids = [
        county_data["employment_code"].values[0],
        state_data["employment_code"],
        county_data["unemployment_code"].values[0],
        state_data["unemployment_code"],
    ]

    data_payload = {
        "seriesid": series_ids,
        "startyear": "2017",
        "endyear": "2024",
    }

    response = requests.post(
        'https://api.bls.gov/publicAPI/v1/timeseries/data/',
        data=json.dumps(data_payload),
        headers={'Content-type': 'application/json'}
    )

    if response.status_code != 200:
        return None, "BLS API request failed."

    json_data = response.json()
    series_data = {}

    for series in json_data['Results']['series']:
        series_id = series['seriesID']
        rows = [{"Year": int(dp['year']), "Month": int(dp['period'][1:]), "Value": float(dp['value'])} for dp in series['data']]
        series_data[series_id] = pd.DataFrame(rows)

    df = pd.DataFrame({"Year": [], "Month": []})
    for idx, (series_id, series_df) in enumerate(series_data.items()):
        series_df = series_df.rename(columns={"Value": f"Series_{idx}"})
        df = df.merge(series_df, on=["Year", "Month"], how="outer") if not df.empty else series_df

    df = df.rename(columns={
        "Series_0": "Employment (County)",
        "Series_1": "Employment (State)",
        "Series_2": "Unemployment (County)",
        "Series_3": "Unemployment (State)",
    }).sort_values(by=["Year", "Month"]).reset_index(drop=True)

    filename = f"{county_name}_{state_abbr}_BLS_Data.xlsx"
    df.to_excel(filename, index=False)

    return filename, None

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        county_name = request.form["county"]
        state_name = request.form["state"]
        filename, error = fetch_bls_data(county_name, state_name)
        
        if error:
            return render_template("index.html", error=error)
        
        return send_file(filename, as_attachment=True)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
