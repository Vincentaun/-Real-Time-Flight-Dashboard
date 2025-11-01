import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import requests
import folium
from folium.plugins import MarkerCluster
import plotly.express as px
from datetime import datetime
from folium.plugins import AntPath

# Load configuration securely from environment
from config import TDX_APP_ID, TDX_APP_KEY, AUTH_URL, DATA_URL

# TDX API Details are provided via environment variables loaded in config.py
# Mocked Airport Coordinates
AIRPORT_COORDINATES = {
    "TTT": (22.7583, 121.1016),  # Taitung Airport
    "GNI": (22.6739, 121.4667),  # Green Island Airport
    "TSA": (25.0694, 121.5525),  # Taipei Songshan Airport
    "TPE": (25.0777, 121.2321),  # Taiwan Taoyuan International Airport
    "KHH": (22.5771, 120.3500),  # Kaohsiung International Airport
    "TXG": (24.1863, 120.6515),  # Taichung Airport
    "HUN": (24.0239, 121.6170),  # Hualien Airport
    "MZG": (23.5697, 119.6300),  # Magong Airport (Penghu)
    "KNH": (24.4279, 118.3590),  # Kinmen Airport
    "LZN": (26.1598, 119.9582),  # Matsu Nangan Airport
    "RCN": (24.2659, 120.6217),  # Chiayi Airport
    "CYI": (23.4617, 120.3933),  # Chiayi Airport
    "PIF": (22.7002, 120.4578),  # Pingtung Airport
    "KYD": (22.0340, 120.7270),  # Lanyu (Orchid Island) Airport
    "WOT": (23.3733, 119.5022),  # Wang-an Airport (Penghu)
    "TTB": (22.7561, 121.0941),  # Taitung Fengnian Airport
    "HLG": (22.9994, 121.0000)   # Hualien Old Airport
}

# Authenticate and fetch flight data
def fetch_flight_data():
    auth_response = requests.post(AUTH_URL, data={
        'grant_type': 'client_credentials',
        'client_id': TDX_APP_ID,
        'client_secret': TDX_APP_KEY
    })
    access_token = auth_response.json().get('access_token')
    headers = {'authorization': f'Bearer {access_token}'}
    response = requests.get(DATA_URL, headers=headers)
    return pd.DataFrame(response.json())

# Create Folium map for flight routes
# Updated function to track airplane paths
# Updated function to animate flight paths
def create_flight_map(df):
    # Initialize map
    m = folium.Map(location=[23.5, 121], zoom_start=7)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():
        dep_code = row['DepartureAirportID']
        arr_code = row['ArrivalAirportID']

        if dep_code in AIRPORT_COORDINATES and arr_code in AIRPORT_COORDINATES:
            dep_coords = AIRPORT_COORDINATES[dep_code]
            arr_coords = AIRPORT_COORDINATES[arr_code]

            # Add markers for departure and arrival airports
            folium.Marker(dep_coords, tooltip=f"Departure: {dep_code}").add_to(marker_cluster)
            folium.Marker(arr_coords, tooltip=f"Arrival: {arr_code}").add_to(marker_cluster)

            # Simulate path by creating intermediate waypoints
            latitudes = [
                dep_coords[0] + i * (arr_coords[0] - dep_coords[0]) / 10 for i in range(11)
            ]
            longitudes = [
                dep_coords[1] + i * (arr_coords[1] - dep_coords[1]) / 10 for i in range(11)
            ]
            path = list(zip(latitudes, longitudes))

            # Animate flight path using AntPath
            AntPath(
                locations=path,
                color="blue",
                weight=2.5,
                opacity=0.8,
                dash_array=[10, 20],
                delay=1000  # Animation speed (ms)
            ).add_to(m)

            # Add a marker for the current position (simulate live tracking)
            current_position = path[len(path) // 2]  # Example: mid-point as current position
            folium.Marker(
                current_position,
                icon=folium.Icon(color='red', icon='plane', prefix='fa'),
                tooltip=f"Flight: {row['FlightNumber']}",
            ).add_to(m)

    return m


# Initialize Dash app
app = dash.Dash(__name__)

# Layout
app.layout = html.Div([
    html.H1("Real-Time Flight Dashboard"),
    dcc.Interval(id="update-interval", interval=60000, n_intervals=0),  # Update every 60 seconds

    # Filters
    html.Div([
        html.Label("Filter by Airline:"),
        dcc.Dropdown(id="filter-airline", multi=False, placeholder="Select an Airline"),
        
        html.Label("Filter by Departure Airport:"),
        dcc.Dropdown(id="filter-departure", multi=False, placeholder="Select a Departure Airport"),
        
        html.Label("Filter by Arrival Airport:"),
        dcc.Dropdown(id="filter-arrival", multi=False, placeholder="Select an Arrival Airport"),
    ], style={"margin-bottom": "20px"}),

    # Flight Delays
    html.Div(id="flight-alerts", style={"margin-top": "20px", "font-weight": "bold", "color": "red"}),

    # Flight Visualization (Bar Chart)
    dcc.Graph(id="arrival-status", style={"margin-top": "20px"}),

    # Map
    html.Iframe(id="flight-map", width="100%", height="600", style={"border": "none", "margin-top": "20px"}),

    # Last Update Time
    html.Div(id="last-update", style={"margin-top": "10px", "font-weight": "bold"})
])

# Callback to update filters and dashboard
@app.callback(
    [Output("filter-airline", "options"),
     Output("filter-departure", "options"),
     Output("filter-arrival", "options"),
     Output("arrival-status", "figure"),
     Output("flight-alerts", "children"),
     Output("flight-map", "srcDoc"),
     Output("last-update", "children")],
    [Input("update-interval", "n_intervals"),
     Input("filter-airline", "value"),
     Input("filter-departure", "value"),
     Input("filter-arrival", "value")]
)
def update_dashboard(n_intervals, airline, departure, arrival):
    # Fetch and process data
    df = fetch_flight_data()
    df['ScheduleArrivalTime'] = pd.to_datetime(df['ScheduleArrivalTime'])

    # Populate filter options
    airline_options = [{'label': i, 'value': i} for i in df['AirlineID'].unique()]
    departure_options = [{'label': i, 'value': i} for i in df['DepartureAirportID'].unique()]
    arrival_options = [{'label': i, 'value': i} for i in df['ArrivalAirportID'].unique()]

    # Filter data based on user selection
    if airline:
        df = df[df['AirlineID'] == airline]
    if departure:
        df = df[df['DepartureAirportID'] == departure]
    if arrival:
        df = df[df['ArrivalAirportID'] == arrival]

    # Delayed Flights
    delayed_flights = df[df['ArrivalRemark'] == "Delayed"]
    delay_alerts = delayed_flights[['FlightNumber', 'ArrivalRemark']].to_dict('records')
    alerts = [f"Flight {f['FlightNumber']}: {f['ArrivalRemark']}" for f in delay_alerts]
    alert_message = "No delays" if not alerts else " | ".join(alerts)
    
    # Plot arrival statuses using a scatter plot
    # Create a bar chart with a brick-like pattern
    fig = px.bar(
        df,
        x='FlightNumber',
        y='ScheduleArrivalTime',
        color='ArrivalRemark',
        title="Flight Schedule: Flight Number vs. Scheduled Arrival Time",
        labels={
            'ScheduleArrivalTime': 'Scheduled Arrival Time',
            'FlightNumber': 'Flight Number',
            'ArrivalRemark': 'Status'
        },
        hover_data=['AirlineID', 'DepartureAirportID', 'ArrivalAirportID']
    )

    # Add customizations for a brick-like appearance
    fig.update_traces(
        marker=dict(
            pattern=dict(
                shape="x",  # Brick-like cross pattern
                size=10,    # Adjust pattern size
                solidity=0.3  # Transparency within the pattern
            )
        )
    )

    # Update layout for better aesthetics
    fig.update_layout(
        title=dict(
            text="Flight Schedule: Flight Number vs. Scheduled Arrival Time",
            font=dict(size=20, family='Arial', color='DarkBlue'),
            x=0.5  # Center the title
        ),
        xaxis=dict(
            title="Flight Number",
            tickmode='linear',  # Use linear ticks
            tick0=0,  # Start from 0
            dtick=5,  # Set gaps between ticks
            showgrid=True,
            gridcolor='LightGrey',
            zeroline=False
        ),
        yaxis=dict(
            title="Scheduled Arrival Time",
            showgrid=True,
            gridcolor='LightGrey'
        ),
        legend=dict(
            title="Status",
            font=dict(size=12),
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='LightGrey',
            borderwidth=1
        ),
        plot_bgcolor='rgba(240,240,240,1)',  # Light background
        paper_bgcolor='rgba(250,250,250,1)',  # Light surrounding area
        hovermode="x"
    )

    # Highlight delayed flights with annotations
    for _, row in df[df['ArrivalRemark'] == 'Delayed'].iterrows():
        fig.add_annotation(
            x=row['FlightNumber'],
            y=row['ScheduleArrivalTime'],
            text="Delayed",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowcolor='Red',
            font=dict(size=10, color='Red'),
            ax=20,  # Position of the annotation relative to the point
            ay=-20
        )

        
    # Create Folium map
    flight_map = create_flight_map(df)
    map_html = flight_map._repr_html_()

    # Last update time
    last_update = f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    return airline_options, departure_options, arrival_options, fig, alert_message, map_html, last_update

if __name__ == "__main__":
    app.run_server(debug=True)
