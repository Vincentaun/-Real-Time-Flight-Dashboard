import requests
import pandas as pd
import matplotlib.pyplot as plt
import json
from datetime import datetime, timedelta
import smtplib
from apscheduler.schedulers.background import BackgroundScheduler
import folium
import streamlit as st
import time
import os

from config import (
    TDX_APP_ID,
    TDX_APP_KEY,
    AUTH_URL,
    API_URL,
    CACHE_FILE,
    REFRESH_INTERVAL,
    ENABLE_EMAIL_NOTIFICATIONS,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    SMTP_FROM,
    SMTP_TO,
)

# Credentials and endpoints are sourced via environment variables (see config.py)

# Global Variables
ACCESS_TOKEN = None
REFRESH_INTERVAL = 60  # Fetch data every 60 seconds
DATABASE = []  # Temporary list to simulate a database


# Authenticate and get an access token
def authenticate():
    global ACCESS_TOKEN
    response = requests.post(
        AUTH_URL,
        data={
            'grant_type': 'client_credentials',
            'client_id': TDX_APP_ID,
            'client_secret': TDX_APP_KEY
        }
    )
    if response.status_code == 200:
        ACCESS_TOKEN = response.json().get('access_token')
        print("Authenticated successfully.")
    else:
        raise Exception("Failed to authenticate with TDX API")


# Fetch live flight data
def fetch_flight_data():
    global ACCESS_TOKEN

    # Check if cached data exists
    if os.path.exists(CACHE_FILE):
        print("Loading data from cache...")
        return pd.read_csv(CACHE_FILE)

    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    response = requests.get(API_URL, headers=headers)

    if response.status_code == 401:  # Unauthorized
        print("Token expired. Re-authenticating...")
        authenticate()
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        response = requests.get(API_URL, headers=headers)

    if response.status_code == 429:  # Rate limit exceeded
        print("Rate limit reached. Waiting for 60 seconds...")
        time.sleep(60)  # Wait for 60 seconds before retrying
        response = requests.get(API_URL, headers=headers)

    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data)
        # Save data to cache
        df.to_csv(CACHE_FILE, index=False)
        return df
    else:
        raise Exception(f"Failed to fetch data: {response.text}")

# Save fetched data into a "database"
def save_to_database(df):
    global DATABASE
    DATABASE.extend(df.to_dict(orient='records'))


# Analyze flight delays
def analyze_delays(df):
    df['Scheduled'] = pd.to_datetime(df['ScheduleArrivalTime'])
    df['Actual'] = pd.to_datetime(df['ActualArrivalTime'], errors='coerce')
    df['DelayMinutes'] = (df['Actual'] - df['Scheduled']).dt.total_seconds() / 60

    # Plot delay distribution
    plt.hist(df['DelayMinutes'].dropna(), bins=20, edgecolor='k', alpha=0.7)
    plt.title('Delay Distribution')
    plt.xlabel('Delay (Minutes)')
    plt.ylabel('Frequency')
    plt.grid()
    plt.show()


# Display historical trends
def plot_trend():
    global DATABASE
    df = pd.DataFrame(DATABASE)
    if df.empty:
        print("No data available.")
        return

    df['FlightDate'] = pd.to_datetime(df['FlightDate'])
    trend = df.groupby('FlightDate').size()

    # Plot trend
    plt.figure(figsize=(10, 6))
    trend.plot(kind='line', title='Daily Flight Count Trend')
    plt.xlabel('Date')
    plt.ylabel('Number of Flights')
    plt.grid()
    plt.show()


# Live notification for delayed flights
def send_notification(flight):
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.starttls()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)

    subject = f"Flight {flight['FlightNumber']} Delayed!"
    body = f"Flight {flight['FlightNumber']} scheduled to arrive at {flight['ScheduleArrivalTime']} is delayed."
    msg = f"Subject: {subject}\n\n{body}"
    server.sendmail(SMTP_FROM, SMTP_TO, msg)
    server.quit()


# Schedule regular updates
def update_dashboard():
    global ACCESS_TOKEN

    # Refresh token if needed
    if not ACCESS_TOKEN:
        authenticate()

    df = fetch_flight_data()
    if not df.empty:
        save_to_database(df)
        print("Data fetched and saved.")

        # Notify for delayed flights
        delayed_flights = df[df['ArrivalRemark'] == 'Delayed']
        if ENABLE_EMAIL_NOTIFICATIONS:
            for _, flight in delayed_flights.iterrows():
                send_notification(flight)


# Create a Folium map for visualizing routes
def visualize_routes(df):
    m = folium.Map(location=[23.5, 121], zoom_start=7)

    for _, row in df.iterrows():
        # Add route markers
        folium.Marker(
            location=[row['DepartureLatitude'], row['DepartureLongitude']],
            popup=f"Departure: {row['DepartureAirportID']}",
            icon=folium.Icon(color="blue")
        ).add_to(m)

        folium.Marker(
            location=[row['ArrivalLatitude'], row['ArrivalLongitude']],
            popup=f"Arrival: {row['ArrivalAirportID']}",
            icon=folium.Icon(color="green")
        ).add_to(m)

    m.save('flight_routes.html')


# Streamlit Dashboard
def streamlit_dashboard():
    st.title("Flight Analytics Dashboard")
    st.sidebar.header("Options")
    selected_option = st.sidebar.selectbox("Choose Analysis", ["Real-Time Data", "Historical Trends", "Delay Analysis"])

    if selected_option == "Real-Time Data":
        st.write("Fetching live flight data...")
        df = fetch_flight_data()
        st.dataframe(df)

    elif selected_option == "Historical Trends":
        st.write("Displaying Historical Trends")
        plot_trend()

    elif selected_option == "Delay Analysis":
        st.write("Analyzing Flight Delays")
        df = pd.DataFrame(DATABASE)
        if not df.empty:
            analyze_delays(df)
        else:
            st.write("No data available.")


# Main Entry Point
if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_dashboard, 'interval', seconds=REFRESH_INTERVAL)
    scheduler.start()

    # Run Streamlit dashboard
    streamlit_dashboard()
