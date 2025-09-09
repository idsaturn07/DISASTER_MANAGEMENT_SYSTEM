# Disaster Management System

A comprehensive disaster management system with weather data integration for real-time emergency alerts and announcements.

## Features

### Core Features
- **User Management**: Sign up, sign in, and role-based access (User, Admin, Government)
- **Incident Reporting**: Users can report disasters and emergencies
- **Shelter Management**: Find nearby shelters during emergencies
- **Medical Assistance**: Request medical help and emergency healthcare
- **Donation System**: Contribute to relief efforts
- **Government Coordination**: Admin can forward incidents to government for response

### Weather Integration Features
- **Real-time Weather Data**: Fetch current weather conditions for Indian cities
- **Extreme Weather Detection**: Automatically detect extreme weather conditions across India
- **Weather-based Announcements**: Create announcements linked to weather data
- **Weather Alerts**: Display weather-related alerts prominently on user dashboards
- **Weather History**: Track weather data over time
- **Automatic Alert Management**: Weather alerts automatically disappear when conditions return to normal

## Weather Data Integration

### How it Works
1. **Automatic Extreme Weather Scanning**: System scans major Indian cities for extreme weather conditions
2. **Extreme Weather Detection**: The system automatically detects:
   - Extreme temperatures (>40°C or <-10°C)
   - High wind speeds (>20 m/s)
   - Severe weather conditions (Thunderstorms, Tornadoes, Hurricanes)
3. **Automatic Alert Creation**: When extreme weather is detected, the system automatically creates weather alert announcements
4. **Automatic Alert Management**: Weather alerts automatically disappear when conditions return to normal
5. **Weather-based Announcements**: Admins can also manually create announcements linked to weather data
6. **User Dashboard**: Weather alerts are prominently displayed on user dashboards

### Weather Data Fields
- Location
- Temperature (°C)
- Humidity (%)
- Wind Speed (m/s)
- Weather Condition
- Extreme Weather Flag
- Weather Alert Message

## Setup Instructions

### Prerequisites
- Python 3.8+
- Supabase account (optional - for database features)
- OpenWeatherMap API key (optional - for enhanced weather features)

### Quick Setup
1. **Run the setup script** (recommended):
   ```bash
   python setup.py
   ```
   This will:
   - Create a `.env` file from template
   - Check your configuration
   - Test weather API functionality
   - Provide setup instructions

### Manual Installation
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create environment file:
   ```bash
   python setup.py
   ```
   Or manually create `.env` file from `ENV_TEMPLATE.txt`

4. **Configure Environment Variables** (optional):
   - `SUPABASE_URL`: Your Supabase project URL (for database features)
   - `SUPABASE_KEY`: Your Supabase anon key (for database features)
   - `WEATHER_API_KEY`: Your OpenWeatherMap API key (optional - app works with free APIs)

### Database Setup (Optional)
If using Supabase:
1. Run the SQL schema in your Supabase project:
   ```sql
   -- Copy and run the contents of supabase_schema.sql
   ```

### Running the Application
```bash
python app.py
```

### Testing
- Test weather API: `python test_free_weather.py`
- Test Indian cities weather: `python test_indian_weather.py`
- Test speed comparison: `python test_speed_comparison.py`
- Test OpenWeatherMap API: `python test_weather_api.py`
- Check configuration: `python setup.py`

## API Integration

### OpenWeatherMap API
The system integrates with OpenWeatherMap API to fetch real-time weather data:
- Current weather conditions
- Temperature, humidity, wind speed
- Weather alerts and warnings
- Geographic coordinates

### Weather Alert Criteria
- **Extreme Temperature**: >40°C or <-10°C
- **High Temperature**: >35°C or <-5°C
- **High Wind Speed**: >20 m/s
- **Severe Weather**: Thunderstorms, Tornadoes, Hurricanes

## Admin Features

### Weather Data Management
1. **Fast Weather Scanning**: Scan major Indian cities for extreme weather conditions in under 1 minute
2. **Check & Remove Resolved Alerts**: Manually check and remove weather alerts where conditions have returned to normal
3. **View Weather History**: See recent weather data entries with extreme conditions highlighted
4. **Automatic Alert Creation**: System automatically creates weather alerts when extreme conditions are detected
5. **Manual Weather Checks**: Check specific locations for weather conditions
6. **Monitor Extreme Conditions**: Track extreme weather events across multiple locations
7. **Parallel Processing**: Uses optimized parallel processing for faster weather data retrieval

### Content Management
1. **Delete Announcements**: Remove announcements that are no longer relevant
2. **Delete Incidents**: Remove reported incidents that have been resolved or are invalid
3. **Manage Weather Alerts**: Control weather-related announcements and their lifecycle

### Announcement Creation
- Create general announcements
- Create weather-related announcements
- Link announcements to specific weather data
- Set severity levels (Low, Medium, High, Critical)

## User Features

### Dashboard
- View recent announcements
- See weather alerts prominently displayed
- Access emergency services
- Find nearby shelters

### Weather Alerts
- Real-time weather alerts
- Extreme weather warnings
- Location-specific weather information
- Historical weather data

## Security Features
- Role-based access control
- Rate limiting on signup
- Secure API key management
- Input validation and sanitization

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License
This project is licensed under the MIT License.
