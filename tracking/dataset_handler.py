import pandas as pd
import os

DATASET_PATH = "datasets/demand_data.xlsx"

def save_uploaded_data(file):
    """Append new data from an uploaded Excel file."""
    new_data = pd.read_excel(file)

    # Validate data format
    if not all(col in new_data.columns for col in ['Date', 'Parcel Received']):
        raise ValueError("Invalid file format. Must contain 'Date' and 'Parcel Received' columns.")

    new_data['Date'] = pd.to_datetime(new_data['Date'])

    # Merge with existing dataset
    if os.path.exists(DATASET_PATH):
        existing_data = pd.read_excel(DATASET_PATH)
        combined_data = pd.concat([existing_data, new_data]).drop_duplicates()
    else:
        combined_data = new_data

    # Save combined dataset
    os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
    combined_data.to_excel(DATASET_PATH, index=False)
    return combined_data
