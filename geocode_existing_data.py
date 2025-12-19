"""
Script to geocode existing data in the CSV and add Latitude/Longitude columns
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

def main():
    # Load the CSV
    csv_path = "Data for Glenwood Group.csv"
    print(f"Loading {csv_path}...")
    df = pd.read_csv(csv_path)
    
    print(f"Total rows: {len(df)}")
    
    # Add geocoding columns if they don't exist
    if 'Latitude' not in df.columns:
        df['Latitude'] = None
    if 'Longitude' not in df.columns:
        df['Longitude'] = None
    if 'Geocoded Address' not in df.columns:
        df['Geocoded Address'] = None
    
    # Count how many need geocoding
    needs_geocoding = df[df['Latitude'].isna()].shape[0]
    print(f"\nRows needing geocoding: {needs_geocoding}")
    
    if needs_geocoding == 0:
        print("All addresses are already geocoded!")
        return
    
    # Ask for confirmation
    user_input = input(f"\nThis will make ~{needs_geocoding} API calls at 1 per second (~{needs_geocoding/60:.1f} minutes). Continue? (y/n): ")
    if user_input.lower() != 'y':
        print("Cancelled.")
        return
    
    # Geocode addresses
    successful = 0
    failed = 0
    
    for idx, row in df.iterrows():
        # Skip if already geocoded
        if pd.notna(row.get('Latitude')) and pd.notna(row.get('Longitude')):
            successful += 1
            continue
        
        print(f"\nProcessing row {idx + 1}/{len(df)}...")
        
        # Get address components
        street = row.get('School Address', '')
        city = row.get('City', '')
        state = row.get('State', '')
        zip_code = row.get('Zip', '')
        
        print(f"  Address: {street}, {city}, {state} {zip_code}")
        
        # Geocode
        lat, lon, formatted_addr = geocode_address(street, city, state, zip_code)
        
        if lat is not None and lon is not None:
            df.at[idx, 'Latitude'] = lat
            df.at[idx, 'Longitude'] = lon
            df.at[idx, 'Geocoded Address'] = formatted_addr
            successful += 1
            print(f"  ✓ Success: {lat}, {lon}")
        else:
            failed += 1
            print(f"  ✗ Failed to geocode")
        
        # Save progress every 50 rows
        if (idx + 1) % 50 == 0:
            print(f"\n💾 Saving progress...")
            df.to_csv(csv_path, index=False)
    
    # Final save
    print(f"\n💾 Saving final results...")
    df.to_csv(csv_path, index=False)
    
    print(f"\n✅ Complete!")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Total: {len(df)}")

if __name__ == "__main__":
    main()
