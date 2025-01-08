from prophet import Prophet
import pandas as pd
import os

# Define the path to the dataset file
DATASET_PATH = os.path.join("datasets", "demand_data.xlsx")

def calculate_monthly_average(data, month, year):
    """
    Calculate the average demand for a specific month and year.
    Exclude Sundays from the calculation.
    """
    monthly_data = data[(data['ds'].dt.month == month) & (data['ds'].dt.year == year)]
    monthly_data = monthly_data[monthly_data['ds'].dt.dayofweek != 6]  # Exclude Sundays
    return monthly_data['y'].mean() if not monthly_data.empty else 0

def predict_demand(periods, alert_for_monthly=False):
    """
    Predict demand for a specified number of future days.
    Includes flagged dates and optionally monthly alerts.
    """
    # Check if the dataset exists
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}. Ensure the file exists.")

    # Load dataset
    data = pd.read_excel(DATASET_PATH)

    # Validate dataset structure
    if 'Date' not in data.columns or 'Parcel Received' not in data.columns:
        raise ValueError("The dataset must contain 'Date' and 'Parcel Received' columns.")

    # Preprocess data
    data['ds'] = pd.to_datetime(data['Date'], errors='coerce')
    data['y'] = data['Parcel Received']

    if data['ds'].isnull().any():
        raise ValueError("The 'Date' column contains invalid dates.")

    # Fit the model
    model = Prophet(yearly_seasonality=True, weekly_seasonality=True)
    model.fit(data[['ds', 'y']])

    # Generate predictions
    future = model.make_future_dataframe(periods=periods, include_history=False)
    forecast = model.predict(future)

    # Prepare predictions
    forecast['Month'] = forecast['ds'].dt.month
    forecast['Year'] = forecast['ds'].dt.year
    forecast['Day'] = forecast['ds'].dt.day_name()

    # Filter out Sundays from the predictions
    forecast = forecast[forecast['ds'].dt.dayofweek != 6]

    predictions_df = forecast[['ds', 'yhat', 'Day']].rename(
        columns={'ds': 'Date', 'yhat': 'Parcel Received'}
    )

    # Calculate flagged dates
    flagged_dates = []
    alert = None
    last_year_avg = None
    predicted_avg = None

    if alert_for_monthly:
        predicted_month = predictions_df['Date'].iloc[0].month
        predicted_year = predictions_df['Date'].iloc[0].year

        # Calculate averages
        last_year_avg = calculate_monthly_average(data, predicted_month, predicted_year - 1)
        predicted_avg = predictions_df[predictions_df['Date'].dt.month == predicted_month]['Parcel Received'].mean()

        # Determine alert type
        if predicted_avg > last_year_avg:
            alert = True
        elif predicted_avg < last_year_avg:
            alert = False

        flagged_dates = predictions_df[predictions_df['Parcel Received'] > last_year_avg]['Date'].dt.strftime('%Y-%m-%d').tolist()

    # Return predictions and flagged dates
    return {
        "forecast": predictions_df.to_dict(orient='records'),
        "alert": alert,
        "last_year_avg": round(last_year_avg, 2) if last_year_avg else None,
        "predicted_avg": round(predicted_avg, 2) if predicted_avg else None,
        "flagged_dates": flagged_dates,
    }
