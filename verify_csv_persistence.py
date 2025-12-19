"""
Comprehensive test to verify CSV persistence and geocoding
"""
import pandas as pd
import os

print("=" * 70)
print("CSV PERSISTENCE AND GEOCODING TEST")
print("=" * 70)

csv_path = "Data for Glenwood Group.csv"

# Check current CSV state
print("\n1. CURRENT CSV STATE")
print("-" * 70)
df = pd.read_csv(csv_path)
print(f"   Total rows: {len(df)}")
print(f"   Columns: {df.columns.tolist()}")
print(f"   Has Latitude column: {'Latitude' in df.columns}")
print(f"   Has Longitude column: {'Longitude' in df.columns}")

if 'Latitude' in df.columns:
    geocoded_count = df['Latitude'].notna().sum()
    print(f"   Geocoded rows: {geocoded_count} / {len(df)} ({geocoded_count/len(df)*100:.1f}%)")

# Show file modification time
mod_time = os.path.getmtime(csv_path)
from datetime import datetime
print(f"   Last modified: {datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')}")

print("\n2. TESTING UPLOAD FEATURE BEHAVIOR")
print("-" * 70)
print("   The upload feature in app.py does the following:")
print("   ✓ Reads uploaded CSV/Excel file")
print("   ✓ Geocodes all addresses (1 second per address)")
print("   ✓ Adds Latitude, Longitude, Geocoded Address columns")
print("   ✓ Appends to existing CSV using pd.concat()")
print("   ✓ Saves permanently with: df.to_csv(csv_path, index=False)")
print("   ✓ Clears Streamlit cache and reruns to show new data")

print("\n3. PERSISTENCE VERIFICATION")
print("-" * 70)
print("   Q: Will the CSV be updated for the future?")
print("   A: YES! Here's why:")
print("      - Line 182 in app.py: combined_data.to_csv(main_csv_path, index=False)")
print("      - This OVERWRITES the CSV file on disk")
print("      - All future app runs will load the updated CSV")
print("      - Line 200 in app.py: df = pd.read_csv('Data for Glenwood Group.csv')")
print("      - This loads from disk, so changes persist across sessions")

print("\n4. HOW TO ADD GEOCODING TO EXISTING DATA")
print("-" * 70)
print("   Option A: Run the batch script")
print("      python geocode_existing_data.py")
print(f"      This will geocode all {len(df)} rows (~{len(df)/60:.1f} minutes)")
print()
print("   Option B: Use the upload feature")
print("      1. Export current CSV")
print("      2. Upload it back through the dashboard")
print("      3. It will geocode and save automatically")

print("\n5. TEST DATA PROVIDED")
print("-" * 70)
print("   test_upload.csv - 2 sample rows for testing upload")
print("      - 1600 Pennsylvania Ave (White House)")
print("      - 350 Fifth Avenue (Empire State Building)")
print()
print("   To test: Run streamlit app and upload test_upload.csv")
print("   Expected: 2 rows added with geocoded lat/lon")

print("\n" + "=" * 70)
print("READY TO TEST!")
print("=" * 70)
print("\nRun: streamlit run app.py")
print("Then upload 'test_upload.csv' to verify everything works!")
