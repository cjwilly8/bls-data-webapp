import tkinter as tk
from tkinter import messagebox
import requests
import json
import pandas as pd

# ----------------- Load State & County Codes from CSV ----------------- #
csv_file_path = "la_area_with_correct_series_ids.csv"  # Updated CSV with series IDs
df_csv = pd.read_csv(csv_file_path)

# Extract state and county codes with their series IDs
state_series = df_csv[df_csv["display_level"] == 0].set_index("area_text")
county_series = df_csv[df_csv["area_type_code"] == "F"].copy()

# State Name to Abbreviation Mapping
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
def align_lists(*lists):
    """Align lists to the same length by padding with None."""
    max_length = max(len(lst) for lst in lists)
    return [lst + [None] * (max_length - len(lst)) for lst in lists]

def fetch_data():
    county_name = county_entry.get().strip()
    state_name = state_entry.get().strip()

    # Convert full state name to abbreviation
    state_abbr = state_name_to_abbr.get(state_name, None)
    if not state_abbr:
        messagebox.showerror("Error", "Invalid state name. Please enter a valid state (e.g., 'California').")
        return

    # Get the county and state data
    county_data = county_series[
        (county_series["area_text"].str.contains(county_name)) & 
        (county_series["area_text"].str.endswith(state_abbr))
    ]

    if county_data.empty:
        messagebox.showerror("Error", f"Could not find data for {county_name}, {state_name}.")
        return

    state_data = state_series.loc[state_name]

    # Extract series IDs
    series_ids = [
        county_data["employment_code"].values[0],  # Employment (County)
        state_data["employment_code"],           # Employment (State)
        county_data["unemployment_code"].values[0],  # Unemployment (County)
        state_data["unemployment_code"],         # Unemployment (State)
    ]

    # BLS API call (replace 'your_api_key_here' with a valid API key)
    api_key = "your_api_key_here"
    data_payload = {
        "seriesid": series_ids,
        "startyear": "2000",
        "endyear": "2024",
    }

    try:
        response = requests.post(
            'https://api.bls.gov/publicAPI/v1/timeseries/data/',
            data=json.dumps(data_payload),
            headers={'Content-type': 'application/json'}
        )
        response.raise_for_status()  # Check for HTTP errors
        json_data = response.json()

        # Prepare a dictionary to hold individual series data
        series_data = {}

        for series in json_data['Results']['series']:
            series_id = series['seriesID']
            rows = []
            for data_point in series['data']:
                year = int(data_point['year'])
                month = int(data_point['period'].replace("M", ""))  # Convert "M01" to 1
                value = float(data_point['value'])
                rows.append({"Year": year, "Month": month, "Value": value})
            series_data[series_id] = pd.DataFrame(rows)

        # Merge series data into a single DataFrame
        df = pd.DataFrame({"Year": [], "Month": []})
        for idx, (series_id, series_df) in enumerate(series_data.items()):
            series_df = series_df.rename(columns={"Value": f"Series_{idx}"})
            if df.empty:
                df = series_df
            else:
                df = pd.merge(df, series_df, on=["Year", "Month"], how="outer")

        # Rename columns to meaningful names
        df = df.rename(columns={
            "Series_0": "Employment (County)",
            "Series_1": "Employment (State)",
            "Series_2": "Unemployment (County)",
            "Series_3": "Unemployment (State)",
        })

        # Sort by Year and Month
        df = df.sort_values(by=["Year", "Month"]).reset_index(drop=True)

        # Save to Excel
        output_filename = f"{county_name}_{state_abbr}_BLS_Data.xlsx"
        df.to_excel(output_filename, index=False)
        messagebox.showinfo("Success", f"Data saved as {output_filename}")

    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"API request failed: {e}")
    except KeyError:
        messagebox.showerror("Error", "Unexpected API response structure. Please check your API key and series IDs.")

# ----------------- Tkinter UI Setup ----------------- #
root = tk.Tk()
root.title("BLS Data Fetcher")

# Create UI Elements
tk.Label(root, text="Enter County Name:").grid(row=0, column=0, padx=10, pady=10)
county_entry = tk.Entry(root, width=30)
county_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(root, text="Enter State Name:").grid(row=1, column=0, padx=10, pady=10)
state_entry = tk.Entry(root, width=30)
state_entry.grid(row=1, column=1, padx=10, pady=10)

fetch_button = tk.Button(root, text="Fetch Data", command=fetch_data)
fetch_button.grid(row=2, column=0, columnspan=2, pady=10)

# Run Tkinter Loop
root.mainloop()