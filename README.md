# Algae Foundation Analytics Dashboard

A Streamlit-based analytics dashboard for teacher data with geocoding capabilities and Supabase integration.

## Features

- 📊 Interactive analytics dashboard with visualizations
- 🗺️ Geographic distribution maps (choropleth and geocoded locations)
- 📤 Upload and geocode new teacher data
- 🔍 Advanced filtering by year, state, semester, school type, and more
- 📥 Download filtered or complete datasets
- 🔐 Password-protected access

## Setup

### Prerequisites

- Python 3.8+
- Supabase account and project
- Environment variables configured (see `.env` file)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Supabase credentials:
```
SUPABASE_API_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
```

3. Run the application:
```bash
streamlit run app.py
```

## Utility Scripts

The following utility scripts are available for one-time setup and data migration:

### `setup_supabase_database.py`
Complete setup script that:
- Geocodes all addresses in the CSV file
- Creates the Supabase table structure
- Uploads all data to Supabase

**Usage:** Run this once during initial setup to migrate data from CSV to Supabase.

### `geocode_existing_data.py`
Geocodes existing addresses in the CSV file and adds Latitude/Longitude columns.

**Usage:** Run this if you need to geocode addresses in your CSV file before uploading.

### `upload_to_supabase.py`
Uploads geocoded CSV data directly to Supabase (skips geocoding step).

**Usage:** Run this if your CSV already has geocoded data and you just need to upload to Supabase.

## Project Structure

```
.
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── setup_supabase_database.py     # Complete setup script
├── geocode_existing_data.py        # Geocoding utility
├── upload_to_supabase.py           # Upload utility
└── Data for Glenwood Group.csv     # Source data file
```

## Notes

- The dashboard uses Supabase as the primary data source
- Geocoding is done via Nominatim API (OpenStreetMap) with rate limiting (1 request/second)
- Password protection is enabled by default

