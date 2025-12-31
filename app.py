import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import time
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Glenwood Group Teacher Analytics",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Password protection
def check_password():
    """Returns `True` if the user has entered the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state.get("password", "") == "MarissaNalley":
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password
    st.text_input(
        "Please enter the password to access the dashboard:", 
        type="password", 
        on_change=password_entered, 
        key="password"
    )
    
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Password incorrect")
    
    return False

if not check_password():
    st.stop()  # Do not continue if check_password is not True

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    """Initialize Supabase client"""
    supabase_url = os.getenv("SUPABASE_API_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        st.error("⚠️ Supabase credentials not found. Please check your .env file.")
        st.stop()
    
    return create_client(supabase_url, supabase_key)

supabase = init_supabase()

# Helper functions for data conversion
def to_bool(val):
    """Convert value to boolean, handling various input formats."""
    if pd.isna(val):
        return None
    if isinstance(val, bool):
        return val
    val_str = str(val).strip().lower()
    return val_str in ['yes', 'y', 'true', '1']

def to_int(val):
    """Convert value to integer, handling various input formats."""
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

# Geocoding function
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
        st.warning(f"Geocoding error for {street}, {city}: {str(e)}")
    
    return (None, None, None)

# Upload and process data function
def process_uploaded_file(uploaded_file):
    """
    Process uploaded file, geocode addresses, and append to Supabase
    """
    try:
        # Read uploaded file
        if uploaded_file.name.endswith('.csv'):
            new_data = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            new_data = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file format. Please upload CSV or Excel file.")
            return False
        
        st.info(f"Loaded {len(new_data)} rows from uploaded file")
        
        # Initialize geocoding columns if they don't exist
        if 'Latitude' not in new_data.columns:
            new_data['Latitude'] = None
        if 'Longitude' not in new_data.columns:
            new_data['Longitude'] = None
        if 'Geocoded Address' not in new_data.columns:
            new_data['Geocoded Address'] = None
        
        # Geocode addresses
        st.info("Starting geocoding process...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_rows = len(new_data)
        successful_geocodes = 0
        
        for idx, row in new_data.iterrows():
            # Update progress
            progress = (idx + 1) / total_rows
            progress_bar.progress(progress)
            status_text.text(f"Geocoding row {idx + 1} of {total_rows}...")
            
            # Get address components
            street = row.get('School Address', '')
            city = row.get('City', '')
            state = row.get('State', '')
            zip_code = row.get('Zip', '')
            
            # Skip if already geocoded
            if pd.notna(row.get('Latitude')) and pd.notna(row.get('Longitude')):
                successful_geocodes += 1
                continue
            
            # Geocode
            lat, lon, formatted_addr = geocode_address(street, city, state, zip_code)
            
            if lat is not None and lon is not None:
                new_data.at[idx, 'Latitude'] = lat
                new_data.at[idx, 'Longitude'] = lon
                new_data.at[idx, 'Geocoded Address'] = formatted_addr
                successful_geocodes += 1
        
        progress_bar.progress(1.0)
        status_text.text(f"Geocoding complete! Successfully geocoded {successful_geocodes} of {total_rows} addresses")
        
        # Prepare records for Supabase
        st.info("Uploading to database...")
        records = []
        for idx, row in new_data.iterrows():
            record = {
                'year': str(row['Year']) if pd.notna(row.get('Year')) else None,
                'first_name': str(row['First Name']) if pd.notna(row.get('First Name')) else None,
                'last_name': str(row['Last Name']) if pd.notna(row.get('Last Name')) else None,
                'school_name': str(row['School Name']) if pd.notna(row.get('School Name')) else None,
                'school_district': str(row['School District']) if pd.notna(row.get('School District')) else None,
                'school_address': str(row['School Address']) if pd.notna(row.get('School Address')) else None,
                'city': str(row['City']) if pd.notna(row.get('City')) else None,
                'state': str(row['State']) if pd.notna(row.get('State')) else None,
                'zip': str(row['Zip']) if pd.notna(row.get('Zip')) else None,
                'county': str(row['County']) if pd.notna(row.get('County')) else None,
                'email': str(row['Email']) if pd.notna(row.get('Email')) else None,
                'title_1': to_bool(row.get('Title 1')),
                'public_private': str(row['PublicPrivate']) if pd.notna(row.get('PublicPrivate')) else None,
                'students_receiving_free_reduced_lunch': to_int(row.get('Students Receiving Free_Reduced Lunch')),
                'ell_students_in_class': to_bool(row.get('ELL Students in Class')),
                'returning_teacher': to_bool(row.get('Returning Teacher')),
                'total_students': to_int(row.get('Total Students')),
                'semester': str(row['Semester']) if pd.notna(row.get('Semester')) else None,
                'latitude': float(row['Latitude']) if pd.notna(row.get('Latitude')) else None,
                'longitude': float(row['Longitude']) if pd.notna(row.get('Longitude')) else None,
                'geocoded_address': str(row['Geocoded Address']) if pd.notna(row.get('Geocoded Address')) else None,
            }
            records.append(record)
        
        # Upload to Supabase in batches
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            supabase.table('teacher_data').insert(batch).execute()
        
        st.success(f"✅ Successfully added {len(new_data)} rows to the database!")
        
        return True
        
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False

# Load and clean data
@st.cache_data(ttl=60)  # Cache for 60 seconds to allow updates
def load_data():
    """Load data from Supabase"""
    try:
        # Fetch all data from Supabase
        response = supabase.table('teacher_data').select('*').execute()
        
        # Convert to DataFrame
        df = pd.DataFrame(response.data)
        
        if df.empty:
            st.warning("No data found in database")
            return pd.DataFrame()
        
        # Rename columns to match original CSV format
        column_mapping = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'school_name': 'School Name',
            'school_district': 'School District',
            'school_address': 'School Address',
            'city': 'City',
            'state': 'State',
            'zip': 'Zip',
            'county': 'County',
            'email': 'Email',
            'title_1': 'Title 1',
            'public_private': 'PublicPrivate',
            'students_receiving_free_reduced_lunch': 'Students Receiving Free_Reduced Lunch',
            'ell_students_in_class': 'ELL Students in Class',
            'returning_teacher': 'Returning Teacher',
            'total_students': 'Total Students',
            'semester': 'Semester',
            'year': 'Year',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'geocoded_address': 'Geocoded Address'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Fill null text values with 'Unknown'
        text_columns = ['First Name', 'Last Name', 'School Name', 'School District', 
                       'School Address', 'City', 'State', 'Zip', 'County', 'Email', 'Semester']
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].fillna('Unknown')
        
        # Ensure PublicPrivate has proper values
        if 'PublicPrivate' in df.columns:
            df['PublicPrivate'] = df['PublicPrivate'].fillna('Unknown')
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data from Supabase: {str(e)}")
        return pd.DataFrame()

df = load_data()

# Sidebar filters
st.sidebar.header("Filters")

# Year filter
years = sorted(df['Year'].dropna().unique())
selected_years = st.sidebar.multiselect(
    "Select Year(s)",
    options=years,
    default=years
)

# State filter
states = sorted(df['State'].dropna().unique())
selected_states = st.sidebar.multiselect(
    "Select State(s)",
    options=states,
    default=states if len(states) <= 10 else []
)

# Semester filter
semesters = sorted(df['Semester'].dropna().unique())
selected_semesters = st.sidebar.multiselect(
    "Select Semester(s)",
    options=semesters,
    default=semesters
)

# Returning teacher filter
returning_options = ["All", "Returning Only", "New Only"]
returning_filter = st.sidebar.radio(
    "Teacher Status",
    options=returning_options,
    index=0
)

# School type filter
school_types = sorted(df['PublicPrivate'].dropna().unique())
selected_school_types = st.sidebar.multiselect(
    "Select School Type(s)",
    options=school_types,
    default=school_types
)


# Student count slider
student_min = int(df['Total Students'].min())
student_max = int(df['Total Students'].max())
student_range = st.sidebar.slider(
    "Total Students",
    min_value=student_min,
    max_value=student_max,
    value=(student_min, student_max)
)

# Apply filters
filtered_df = df.copy()

# Year filter
if selected_years:
    filtered_df = filtered_df[filtered_df['Year'].isin(selected_years)]

# State filter
if selected_states:
    filtered_df = filtered_df[filtered_df['State'].isin(selected_states)]

# Semester filter
if selected_semesters:
    filtered_df = filtered_df[filtered_df['Semester'].isin(selected_semesters)]

# School type filter
if selected_school_types:
    filtered_df = filtered_df[filtered_df['PublicPrivate'].isin(selected_school_types)]

# Numeric filters
filtered_df = filtered_df[
    (filtered_df['Total Students'].between(student_range[0], student_range[1]))
]

# Returning teacher filter
if returning_filter == "Returning Only":
    filtered_df = filtered_df[filtered_df['Returning Teacher'] == True]
elif returning_filter == "New Only":
    filtered_df = filtered_df[filtered_df['Returning Teacher'] == False]

# Main page
st.title("🧪 Algae Foundation Analytics Dashboard")
st.markdown("---")

# Upload Section
with st.expander("📤 Upload New Data", expanded=False):
    st.markdown("### Upload and Geocode New Teacher Data")
    st.markdown("Upload a CSV or Excel file with new teacher data. Addresses will be automatically geocoded.")
    
    # Initialize processing state
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    
    # Show success message if just completed
    if st.session_state.processing_complete:
        st.success("✅ Upload completed successfully! Data has been added to the database.")
        if st.button("Upload Another File"):
            st.session_state.processing_complete = False
            st.rerun()
    else:
        uploaded_file = st.file_uploader(
            "Choose a file (CSV or Excel)",
            type=['csv', 'xlsx', 'xls'],
            help="Upload a file with teacher data. Must include columns: School Address, City, State, Zip",
            key="file_uploader"
        )
        
        if uploaded_file is not None:
            st.write(f"**Selected file:** {uploaded_file.name}")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🚀 Process and Add Data", type="primary", key="process_button"):
                    with st.spinner("Processing file..."):
                        success = process_uploaded_file(uploaded_file)
                        if success:
                            # Mark processing as complete
                            st.session_state.processing_complete = True
                            # Clear cache to reload data
                            st.cache_data.clear()
                            st.rerun()
            with col2:
                st.info("⚠️ Note: Geocoding may take 1-2 seconds per address due to API rate limits")

st.markdown("---")

# Calculate key metrics (for use throughout the dashboard)
total_teachers = len(filtered_df)
returning_teachers = int(filtered_df['Returning Teacher'].sum())
new_teachers = total_teachers - returning_teachers
total_students = int(filtered_df['Total Students'].sum())

# KPIs at top
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Teachers", f"{total_teachers:,}")

with col2:
    st.metric("Returning Teachers", f"{returning_teachers:,}")

with col3:
    st.metric("New Teachers", f"{new_teachers:,}")

with col4:
    st.metric("Total Students", f"{total_students:,}")

st.markdown("---")

# Geographic Distribution
st.subheader("Geographic Distribution")

# State-level choropleth
state_counts = filtered_df.groupby('State').agg({
    'First Name': 'count',
    'Total Students': 'sum'
}).reset_index()
state_counts.columns = ['State', 'Teacher Count', 'Total Students']

# Create hover text
state_counts['text'] = (
    state_counts['State'] + '<br>' +
    'Teachers: ' + state_counts['Teacher Count'].astype(str) + '<br>' +
    'Students: ' + state_counts['Total Students'].astype(str)
)

fig_map = go.Figure(data=go.Choropleth(
    locations=state_counts['State'].tolist(),
    z=state_counts['Teacher Count'].tolist(),
    locationmode='USA-states',
    colorscale='YlOrRd',
    text=state_counts['text'].tolist(),
    colorbar=dict(
        title=dict(text="Teachers")
    )
))

fig_map.update_layout(
    title_text='Teacher Distribution Across USA',
    geo=dict(
        scope='usa',
        projection=go.layout.geo.Projection(type='albers usa'),
        showlakes=True,
        lakecolor='rgb(255, 255, 255)',
        bgcolor='rgba(0,0,0,0)'
    ),
    height=500,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig_map, use_container_width=True)

# Geocoded locations map
st.subheader("Geocoded School Locations")

# Filter for rows with valid coordinates
geocoded_df = filtered_df[filtered_df['Latitude'].notna() & filtered_df['Longitude'].notna()].copy()

if len(geocoded_df) > 0:
    st.info(f"Showing {len(geocoded_df)} geocoded locations out of {len(filtered_df)} total schools")
    
    # Create hover text
    geocoded_df['hover_text'] = (
        '<b>' + geocoded_df['School Name'] + '</b><br>' +
        geocoded_df['City'] + ', ' + geocoded_df['State'] + '<br>' +
        'Teachers: 1<br>' +
        'Students: ' + geocoded_df['Total Students'].astype(str)
    )
    
    # Create density heatmap
    fig_heatmap = go.Figure(go.Densitymapbox(
        lat=geocoded_df['Latitude'].tolist(),
        lon=geocoded_df['Longitude'].tolist(),
        z=geocoded_df['Total Students'].tolist(),
        radius=15,
        colorscale='YlOrRd',
        showscale=True,
        hoverinfo='skip',
        colorbar=dict(title="Students")
    ))
    
    # Add scatter points on top
    fig_heatmap.add_trace(go.Scattermapbox(
        lat=geocoded_df['Latitude'].tolist(),
        lon=geocoded_df['Longitude'].tolist(),
        mode='markers',
        marker=dict(
            size=6,
            color='rgb(0, 0, 139)',
            opacity=0.6
        ),
        text=geocoded_df['hover_text'].tolist(),
        hoverinfo='text',
        name='Schools'
    ))
    
    # Update layout
    fig_heatmap.update_layout(
        mapbox=dict(
            style='open-street-map',
            center=dict(lat=39.8283, lon=-98.5795),  # Center of USA
            zoom=3
        ),
        height=600,
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0)
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)
else:
    st.warning("No geocoded locations available to display on map")

st.markdown("---")

# Analytics section
st.subheader("Analytics")

# Row 1: Returning vs New, School Type Distribution
col1, col2 = st.columns(2)

with col1:
    # Returning vs New pie chart
    fig_returning = go.Figure(data=[go.Pie(
        labels=['New Teachers', 'Returning Teachers'],
        values=[new_teachers, returning_teachers],
        hole=0.4,
        marker=dict(colors=['#FF6B6B', '#4ECDC4'])
    )])
    fig_returning.update_traces(textposition='inside', textinfo='percent+label')
    fig_returning.update_layout(title_text="Teacher Status Distribution")
    st.plotly_chart(fig_returning, use_container_width=True)

with col2:
    # School type distribution
    school_type_counts = filtered_df['PublicPrivate'].value_counts().reset_index()
    school_type_counts.columns = ['School Type', 'Count']
    
    fig_school_type = go.Figure(data=[go.Pie(
        labels=school_type_counts['School Type'].tolist(),
        values=school_type_counts['Count'].tolist(),
        hole=0.4,
        marker=dict(colors=px.colors.sequential.RdBu)
    )])
    fig_school_type.update_traces(textposition='inside', textinfo='percent+label')
    fig_school_type.update_layout(title_text="School Type Distribution")
    st.plotly_chart(fig_school_type, use_container_width=True)

# Row 2: Title 1, ELL Students
col1, col2 = st.columns(2)

with col1:
    # Title 1 distribution
    title1_true = int((filtered_df['Title 1'] == True).sum())
    title1_false = int((filtered_df['Title 1'] == False).sum())
    
    fig_title1 = go.Figure(data=[go.Bar(
        x=['Non-Title 1', 'Title 1'],
        y=[title1_false, title1_true],
        text=[title1_false, title1_true],
        textposition='outside',
        marker=dict(color=['#95E1D3', '#F38181'])
    )])
    fig_title1.update_layout(
        title='Title 1 School Distribution',
        showlegend=False,
        xaxis_title='Title 1 Status',
        yaxis_title='Count'
    )
    st.plotly_chart(fig_title1, use_container_width=True)

with col2:
    # ELL Students
    ell_true = int((filtered_df['ELL Students in Class'] == True).sum())
    ell_false = int((filtered_df['ELL Students in Class'] == False).sum())
    
    fig_ell = go.Figure(data=[go.Bar(
        x=['No ELL Students', 'Has ELL Students'],
        y=[ell_false, ell_true],
        text=[ell_false, ell_true],
        textposition='outside',
        marker=dict(color=['#FCBAD3', '#AA96DA'])
    )])
    fig_ell.update_layout(
        title='ELL Students in Classrooms',
        showlegend=False,
        xaxis_title='ELL Status',
        yaxis_title='Count'
    )
    st.plotly_chart(fig_ell, use_container_width=True)

# Row 3: Free/Reduced Lunch Distribution, Students by Semester
col1, col2 = st.columns(2)

with col1:
    # Free/Reduced Lunch histogram
    frl_data = filtered_df['Students Receiving Free_Reduced Lunch'].dropna().tolist()
    
    fig_frl = go.Figure(data=[go.Histogram(
        x=frl_data,
        nbinsx=20,
        marker=dict(color='#A8E6CF')
    )])
    fig_frl.update_layout(
        title='Distribution of % Free/Reduced Lunch',
        xaxis_title='% Free/Reduced Lunch',
        yaxis_title='Count',
        showlegend=False
    )
    st.plotly_chart(fig_frl, use_container_width=True)

with col2:
    # Teachers by semester
    semester_counts = filtered_df['Semester'].value_counts().reset_index()
    semester_counts.columns = ['Semester', 'Count']
    
    fig_semester = go.Figure(data=[go.Bar(
        x=semester_counts['Semester'].tolist(),
        y=semester_counts['Count'].tolist(),
        text=semester_counts['Count'].tolist(),
        textposition='outside',
        marker=dict(color=px.colors.sequential.Sunset)
    )])
    fig_semester.update_layout(
        title='Teachers by Semester',
        showlegend=False,
        xaxis_title='Semester',
        yaxis_title='Count'
    )
    st.plotly_chart(fig_semester, use_container_width=True)

st.markdown("---")

# Top locations
st.subheader("Top Locations")

col1, col2, col3 = st.columns(3)

with col1:
    top_states = filtered_df['State'].value_counts().head(10).reset_index()
    top_states.columns = ['State', 'Teachers']
    
    fig_top_states = go.Figure(data=[go.Bar(
        x=top_states['State'].tolist(),
        y=top_states['Teachers'].tolist(),
        text=top_states['Teachers'].tolist(),
        textposition='outside',
        marker=dict(color=top_states['Teachers'].tolist(), colorscale='Blues', showscale=False)
    )])
    fig_top_states.update_layout(
        title='Top 10 States',
        showlegend=False,
        xaxis_title='State',
        yaxis_title='Teachers'
    )
    st.plotly_chart(fig_top_states, use_container_width=True)

with col2:
    top_counties = filtered_df['County'].value_counts().head(10).reset_index()
    top_counties.columns = ['County', 'Teachers']
    
    fig_top_counties = go.Figure(data=[go.Bar(
        y=top_counties['County'].tolist(),
        x=top_counties['Teachers'].tolist(),
        text=top_counties['Teachers'].tolist(),
        textposition='outside',
        orientation='h',
        marker=dict(color=top_counties['Teachers'].tolist(), colorscale='Oranges', showscale=False)
    )])
    fig_top_counties.update_layout(
        title='Top 10 Counties',
        showlegend=False,
        xaxis_title='Teachers',
        yaxis_title='County',
        yaxis={'categoryorder':'total ascending'}
    )
    st.plotly_chart(fig_top_counties, use_container_width=True)

with col3:
    top_districts = filtered_df['School District'].value_counts().head(10).reset_index()
    top_districts.columns = ['District', 'Teachers']
    
    fig_top_districts = go.Figure(data=[go.Bar(
        y=top_districts['District'].tolist(),
        x=top_districts['Teachers'].tolist(),
        text=top_districts['Teachers'].tolist(),
        textposition='outside',
        orientation='h',
        marker=dict(color=top_districts['Teachers'].tolist(), colorscale='Greens', showscale=False)
    )])
    fig_top_districts.update_layout(
        title='Top 10 School Districts',
        showlegend=False,
        xaxis_title='Teachers',
        yaxis_title='District',
        yaxis={'categoryorder':'total ascending'}
    )
    st.plotly_chart(fig_top_districts, use_container_width=True)

st.markdown("---")

# Raw data table
st.subheader("Raw Data")

st.dataframe(
    filtered_df,
    use_container_width=True,
    height=400
)

st.markdown("---")

# Download section
st.subheader("Download Data")

col1, col2 = st.columns(2)

with col1:
    # Download filtered data
    csv_filtered = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Data",
        data=csv_filtered,
        file_name=f"glenwood_filtered_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col2:
    # Download all data
    csv_all = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download All Data",
        data=csv_all,
        file_name=f"glenwood_all_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# Footer
st.markdown("---")
st.caption(f"Dashboard generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')} | Showing {len(filtered_df):,} of {len(df):,} total records")