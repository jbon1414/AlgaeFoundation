"""
Upload geocoded data to Supabase (skip geocoding step)
"""
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_API_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ROLE")

def upload_to_supabase():
    """Upload data to Supabase"""
    print("=" * 70)
    print("UPLOADING DATA TO SUPABASE")
    print("=" * 70)
    
    # Load CSV
    csv_path = "Data for Glenwood Group.csv"
    print(f"\nLoading {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Total rows: {len(df)}")
    
    # Check for geocoded data
    if 'Latitude' in df.columns:
        geocoded_count = df['Latitude'].notna().sum()
        print(f"Geocoded rows: {geocoded_count}/{len(df)} ({geocoded_count/len(df)*100:.1f}%)")
    
    # Connect to Supabase
    if SUPABASE_URL is None or SUPABASE_KEY is None:
        print("❌ Error: Supabase credentials not found in .env file")
        return False
    
    print(f"\nConnecting to Supabase: {SUPABASE_URL}")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Table name
    table_name = "teacher_data"
    
    print(f"\n📋 Creating table: {table_name}")
    
    # Create table SQL
    create_table_sql = """
DROP TABLE IF EXISTS teacher_data;

CREATE TABLE teacher_data (
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

CREATE INDEX idx_state ON teacher_data(state);
CREATE INDEX idx_year ON teacher_data(year);
CREATE INDEX idx_semester ON teacher_data(semester);
    """
    
    try:
        # Execute SQL to create table
        supabase.postgrest.session.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            json={"query": create_table_sql}
        )
        print("✓ Table created successfully!")
    except Exception as e:
        print(f"Note: Could not auto-create table: {str(e)}")
        print("\nPlease run this SQL in Supabase SQL Editor:")
        print("-" * 70)
        print(create_table_sql)
        print("-" * 70)
        input("\nPress Enter after running the SQL...")
    
    # Helper functions
    def to_bool(val):
        if pd.isna(val):
            return None
        if isinstance(val, bool):
            return val
        val_str = str(val).strip().lower()
        return val_str in ['yes', 'y', 'true', '1', 'true']
    
    def to_int(val):
        if pd.isna(val):
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            val_str = str(val).strip()
            if val_str.lower() in ['yes', 'y', 'true']:
                return 100
            if val_str.lower() in ['no', 'n', 'false']:
                return 0
            return None
    
    # Prepare data
    print("\nPreparing data for upload...")
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
    
    print(f"Prepared {len(records)} records")
    
    # Upload in batches
    batch_size = 100
    total_batches = (len(records) + batch_size - 1) // batch_size
    
    print(f"\nUploading in {total_batches} batches of {batch_size}...")
    
    uploaded = 0
    failed = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        try:
            result = supabase.table(table_name).insert(batch).execute()
            uploaded += len(batch)
            print(f"  ✓ Batch {batch_num}/{total_batches} uploaded ({len(batch)} records)")
        except Exception as e:
            failed += len(batch)
            print(f"  ✗ Batch {batch_num}/{total_batches} failed: {str(e)}")
    
    print(f"\n{'='*70}")
    print(f"🎉 UPLOAD COMPLETE!")
    print(f"{'='*70}")
    print(f"   Uploaded: {uploaded} records")
    print(f"   Failed: {failed} records")
    print(f"   Table: {table_name}")
    print(f"   Supabase URL: {SUPABASE_URL}")
    
    return failed == 0

if __name__ == "__main__":
    upload_to_supabase()
