"""
Complete setup script:
1. Geocode all addresses in the CSV
2. Create Supabase table
3. Upload all data to Supabase
"""
import pandas as pd
import requests
import time
from supabase import create_client, Client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_API_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ROLE")  # Using service role for admin operations

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
        print(f"   Geocoding error: {str(e)}")
    
    return (None, None, None)

def geocode_csv():
    """Geocode all addresses in the CSV file"""
    csv_path = "Data for Glenwood Group.csv"
    print("=" * 70)
    print("STEP 1: GEOCODING ADDRESSES")
    print("=" * 70)
    
    print(f"\nLoading {csv_path}...")
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
    already_geocoded = len(df) - needs_geocoding
    
    print(f"\nAlready geocoded: {already_geocoded}")
    print(f"Needs geocoding: {needs_geocoding}")
    
    if needs_geocoding == 0:
        print("\n✅ All addresses are already geocoded!")
        return df
    
    # Estimate time
    estimated_minutes = needs_geocoding / 60
    print(f"\nEstimated time: ~{estimated_minutes:.1f} minutes")
    
    user_input = input(f"\nContinue with geocoding? (y/n): ")
    if user_input.lower() != 'y':
        print("Cancelled.")
        return None
    
    # Geocode addresses
    successful = 0
    failed = 0
    
    print("\nStarting geocoding...")
    for idx, row in df.iterrows():
        # Skip if already geocoded
        if pd.notna(row.get('Latitude')) and pd.notna(row.get('Longitude')):
            successful += 1
            continue
        
        if idx % 10 == 0:  # Progress update every 10 rows
            print(f"\nProgress: {idx + 1}/{len(df)}")
        
        # Get address components
        street = row.get('School Address', '')
        city = row.get('City', '')
        state = row.get('State', '')
        zip_code = row.get('Zip', '')
        
        print(f"  Row {idx + 1}: {city}, {state}")
        
        # Geocode
        lat, lon, formatted_addr = geocode_address(street, city, state, zip_code)
        
        if lat is not None and lon is not None:
            df.at[idx, 'Latitude'] = lat
            df.at[idx, 'Longitude'] = lon
            df.at[idx, 'Geocoded Address'] = formatted_addr
            successful += 1
            print(f"    ✓ {lat}, {lon}")
        else:
            failed += 1
            print(f"    ✗ Failed")
        
        # Save progress every 50 rows
        if (idx + 1) % 50 == 0:
            print(f"\n💾 Saving progress...")
            df.to_csv(csv_path, index=False)
    
    # Final save
    print(f"\n💾 Saving final results to {csv_path}...")
    df.to_csv(csv_path, index=False)
    
    print(f"\n✅ Geocoding complete!")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Total: {len(df)}")
    
    return df

def setup_supabase_table(df):
    """Create table in Supabase and upload data"""
    print("\n" + "=" * 70)
    print("STEP 2: SETTING UP SUPABASE")
    print("=" * 70)
    
    if SUPABASE_URL is None or SUPABASE_KEY is None:
        print("❌ Error: Supabase credentials not found in .env file")
        return False
    
    print(f"\nConnecting to Supabase: {SUPABASE_URL}")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Table name
    table_name = "teacher_data"
    
    print(f"\nPreparing to create table: {table_name}")
    print("\nNote: Creating the table structure via SQL...")
    
    # Create SQL for table creation
    create_table_sql = f"""
    -- Drop table if exists (for fresh start)
    DROP TABLE IF EXISTS {table_name};
    
    -- Create table
    CREATE TABLE {table_name} (
        id BIGSERIAL PRIMARY KEY,
        year TEXT,
        first_name TEXT,
        last_name TEXT,
        school_name TEXT,
        school_district TEXT,
        school_address TEXT,
        city TEXT,
        state TEXT,
        zip TEXT,
        county TEXT,
        email TEXT,
        title_1 BOOLEAN,
        public_private TEXT,
        students_receiving_free_reduced_lunch INTEGER,
        ell_students_in_class BOOLEAN,
        returning_teacher BOOLEAN,
        total_students INTEGER,
        semester TEXT,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        geocoded_address TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Create index on state for faster filtering
    CREATE INDEX idx_state ON {table_name}(state);
    CREATE INDEX idx_year ON {table_name}(year);
    CREATE INDEX idx_semester ON {table_name}(semester);
    """
    
    print("\nSQL Command to execute in Supabase SQL Editor:")
    print("-" * 70)
    print(create_table_sql)
    print("-" * 70)
    
    input("\nPlease execute the above SQL in your Supabase SQL Editor, then press Enter to continue...")
    
    # Prepare data for upload
    print("\nPreparing data for upload...")
    
    # Helper function to convert to boolean
    def to_bool(val):
        if pd.isna(val):
            return None
        if isinstance(val, bool):
            return val
        val_str = str(val).strip().lower()
        return val_str in ['yes', 'y', 'true', '1', 'true']
    
    # Helper function to convert to int
    def to_int(val):
        if pd.isna(val):
            return None
        try:
            # Handle numeric strings
            return int(float(val))
        except (ValueError, TypeError):
            # If it's not a number, try to extract number
            val_str = str(val).strip()
            if val_str.lower() in ['yes', 'y', 'true']:
                return 100  # Assume "Yes" means 100%
            if val_str.lower() in ['no', 'n', 'false']:
                return 0
            return None
    
    # Convert DataFrame to records
    records = []
    for idx, row in df.iterrows():
        record = {
            'year': str(row['Year']) if pd.notna(row['Year']) else None,
            'first_name': str(row['First Name']) if pd.notna(row['First Name']) else None,
            'last_name': str(row['Last Name']) if pd.notna(row['Last Name']) else None,
            'school_name': str(row['School Name']) if pd.notna(row['School Name']) else None,
            'school_district': str(row['School District']) if pd.notna(row['School District']) else None,
            'school_address': str(row['School Address']) if pd.notna(row['School Address']) else None,
            'city': str(row['City']) if pd.notna(row['City']) else None,
            'state': str(row['State']) if pd.notna(row['State']) else None,
            'zip': str(row['Zip']) if pd.notna(row['Zip']) else None,
            'county': str(row['County']) if pd.notna(row['County']) else None,
            'email': str(row['Email']) if pd.notna(row['Email']) else None,
            'title_1': to_bool(row['Title 1']),
            'public_private': str(row['PublicPrivate']) if pd.notna(row['PublicPrivate']) else None,
            'students_receiving_free_reduced_lunch': to_int(row['Students Receiving Free_Reduced Lunch']),
            'ell_students_in_class': to_bool(row['ELL Students in Class']),
            'returning_teacher': to_bool(row['Returning Teacher']),
            'total_students': to_int(row['Total Students']),
            'semester': str(row['Semester']) if pd.notna(row['Semester']) else None,
            'latitude': float(row['Latitude']) if pd.notna(row.get('Latitude')) else None,
            'longitude': float(row['Longitude']) if pd.notna(row.get('Longitude')) else None,
            'geocoded_address': str(row['Geocoded Address']) if pd.notna(row.get('Geocoded Address')) else None,
        }
        records.append(record)
    
    print(f"Prepared {len(records)} records for upload")
    
    # Upload in batches
    batch_size = 100
    total_batches = (len(records) + batch_size - 1) // batch_size
    
    print(f"\nUploading data in {total_batches} batches of {batch_size}...")
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        try:
            result = supabase.table(table_name).insert(batch).execute()
            print(f"  ✓ Batch {batch_num}/{total_batches} uploaded ({len(batch)} records)")
        except Exception as e:
            print(f"  ✗ Batch {batch_num}/{total_batches} failed: {str(e)}")
            return False
    
    print(f"\n✅ All data uploaded successfully!")
    print(f"   Total records: {len(records)}")
    print(f"   Table name: {table_name}")
    
    return True

def main():
    """Main execution function"""
    print("\n" + "=" * 70)
    print("ALGAE FOUNDATION - SUPABASE SETUP")
    print("=" * 70)
    
    # Step 1: Geocode
    df = geocode_csv()
    if df is None:
        print("\nSetup cancelled.")
        return
    
    # Step 2: Setup Supabase
    success = setup_supabase_table(df)
    
    if success:
        print("\n" + "=" * 70)
        print("🎉 SETUP COMPLETE!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Update app.py to use Supabase instead of CSV")
        print("2. Test the dashboard with Supabase data")
        print("3. Deploy to Streamlit Cloud")
    else:
        print("\n❌ Setup failed. Please check the errors above.")

if __name__ == "__main__":
    main()
