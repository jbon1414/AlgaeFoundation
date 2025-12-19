"""
Quick test script to geocode just the first 5 rows
"""
import pandas as pd
import requests
import time

def geocode_address(street, city, state, zip_code, country="USA"):
    """
    Geocode an address using Nominatim API
    Returns tuple: (latitude, longitude, formatted_address)
    """
    base_url = "https://nominatim.openstreetmap.org/search"
    
    params = {
        'street': str(street) if pd.notna(street) else '',
        'city': str(city) if pd.notna(city) else '',
        'state': str(state) if pd.notna(state) else '',
        'postalcode': str(zip_code) if pd.notna(zip_code) else '',
        'country': country,
        'format': 'json',
        'addressdetails': 1,
        'limit': 1
    }
    
    # Remove empty parameters
    params = {k: v for k, v in params.items() if v}
    
    headers = {
        'User-Agent': 'AlgaeFoundation-Dashboard/1.0'
    }
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        
        # Respect Nominatim usage policy: max 1 request per second
        time.sleep(1)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                result = data[0]
                return (
                    float(result.get('lat', None)),
                    float(result.get('lon', None)),
                    result.get('display_name', '')
                )
    except Exception as e:
        print(f"Geocoding error for {street}, {city}: {str(e)}")
    
    return (None, None, None)

# Load the CSV
csv_path = "Data for Glenwood Group.csv"
print(f"Loading {csv_path}...")
df = pd.read_csv(csv_path)

# Take only first 5 rows for testing
df_test = df.head(5).copy()

print(f"Testing with {len(df_test)} rows\n")

# Add geocoding columns
df_test['Latitude'] = None
df_test['Longitude'] = None
df_test['Geocoded Address'] = None

# Geocode addresses
for idx, row in df_test.iterrows():
    print(f"Row {idx + 1}/{len(df_test)}:")
    
    # Get address components
    street = row.get('School Address', '')
    city = row.get('City', '')
    state = row.get('State', '')
    zip_code = row.get('Zip', '')
    
    print(f"  Address: {street}, {city}, {state} {zip_code}")
    
    # Geocode
    lat, lon, formatted_addr = geocode_address(street, city, state, zip_code)
    
    if lat is not None and lon is not None:
        df_test.at[idx, 'Latitude'] = lat
        df_test.at[idx, 'Longitude'] = lon
        df_test.at[idx, 'Geocoded Address'] = formatted_addr
        print(f"  ✓ Success: {lat}, {lon}")
    else:
        print(f"  ✗ Failed to geocode")
    print()

# Save test results
df_test.to_csv("test_geocoded_5_rows.csv", index=False)
print(f"✅ Saved results to test_geocoded_5_rows.csv")
print(f"\nResults preview:")
print(df_test[['School Name', 'City', 'State', 'Latitude', 'Longitude']].to_string())
