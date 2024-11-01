import streamlit as st
import pandas as pd
import plotly.express as px
import openai
from streamlit_plotly_events import plotly_events
import os

# Set Streamlit layout to wide
st.set_page_config(layout="wide")

# Request OpenAI API Key input from the user
api_key = st.text_input("Enter your OpenAI API Key", type="password")

# Set OpenAI API Key if provided
if api_key:
    openai.api_key = api_key
else:
    st.warning("Please enter your OpenAI API key to continue.")

# Load processed data
@st.cache_data
def load_data():
    data_path = 'D:/PROJECT/GOV_AI-WAR/data/processed_news_data.csv'
    data = pd.read_csv(data_path)
    data['Pub_Date'] = pd.to_datetime(data['Pub_Date'], errors='coerce')  # Keep full datetime for deduplication

    # Filter only rows where Conflict Escalation is TRUE
    data = data[data['Conflict Escalation'] == True]

    # Remove duplicates based on 'News_Title' while keeping the latest news by date
    data = data.sort_values('Pub_Date').drop_duplicates(subset='News_Title', keep='last')
    
    # Convert 'Pub_Date' to date only for other processing
    data['Pub_Date'] = data['Pub_Date'].dt.date
    
    return data

# Summarize data by country within date range
def prepare_choropleth_data(data, date_range):
    filtered_data = data[(data['Pub_Date'] >= date_range[0]) & (data['Pub_Date'] <= date_range[1])]
    if 'Countries Mentioned' in filtered_data.columns:
        country_counts = filtered_data['Countries Mentioned'].fillna('Unknown').value_counts().reset_index()
        country_counts.columns = ['Country', 'News_Count']
        return country_counts
    else:
        raise ValueError("'Countries Mentioned' column not found in the dataset")

# Sidebar menu buttons
if "menu_selection" not in st.session_state:
    st.session_state.menu_selection = "Dashboard"  # Default to "Dashboard"

with st.sidebar:
    if st.button("Paper", use_container_width=True):  # Full-width button
        st.session_state.menu_selection = "Paper"
    if st.button("Dashboard", use_container_width=True):  # Full-width button
        st.session_state.menu_selection = "Dashboard"

# Display content based on the selected menu
if st.session_state.menu_selection == "Paper":
    st.title("Paper and Documentation")
    # Placeholder for paper/documentation content
    st.write("Content for paper and documentation goes here.")

elif st.session_state.menu_selection == "Dashboard":
    st.title("Conflict Monitoring Dashboard")

    try:
        # Load data
        data = load_data()
        
        # Date range slider with only date format (no time)
        min_date = data['Pub_Date'].min()
        max_date = data['Pub_Date'].max()
        date_range = st.slider(
            "Select Date Range",
            min_value=min_date,
            max_value=max_date,
            value=(max_date, max_date),  # Set default to the last day only
            format="YYYY-MM-DD"
        )

        # Prepare data for the map
        choropleth_data = prepare_choropleth_data(data, date_range)
        
        # Dynamically set the color scale maximum based on the date range's highest news count
        max_news_count = choropleth_data["News_Count"].max()

        # Display choropleth map
        st.header("Global Conflict News Counts by Country")
        fig = px.choropleth(
            choropleth_data,
            locations="Country",
            locationmode="country names",
            color="News_Count",
            color_continuous_scale="Reds",
            title="Number of Conflict News Mentions by Country",
            labels={'News_Count': 'News Articles Count'}
        )

        # Set the color bar range
        fig.update_layout(coloraxis_colorbar=dict(ticksuffix=""), coloraxis_cmax=max_news_count)
        fig.update_geos(showcoastlines=True, coastlinecolor="Gray")

        # Display the map and handle clicks
        selected_points = plotly_events(fig, click_event=True, hover_event=False)

        # Display the top 3 countries with the most conflict news below the map and above the news table
        top_countries = choropleth_data.nlargest(3, 'News_Count')
        top_countries_display = ", ".join([f"{row['Country']}({row['News_Count']})" for _, row in top_countries.iterrows()])
        st.write(f"Countries with most news about conflict: {top_countries_display}")

        # Handle map click to select a country
        if selected_points and "pointIndex" in selected_points[0]:
            # Retrieve the clicked country based on point index
            point_index = selected_points[0]["pointIndex"]
            clicked_country = choropleth_data.iloc[point_index]["Country"]
            st.session_state["selected_country"] = clicked_country

        if "selected_country" in st.session_state:
            clicked_country = st.session_state["selected_country"]
            
            st.subheader(f"News Articles for {clicked_country} between {date_range[0]} and {date_range[1]}")

            # Filter news for the clicked country and date range
            mask = (
                data['Countries Mentioned'].str.contains(clicked_country, case=False, na=False) &
                (data['Pub_Date'] >= date_range[0]) & 
                (data['Pub_Date'] <= date_range[1])
            )
            country_news = data[mask]

            # Pagination setup
            items_per_page = 10
            total_pages = (len(country_news) + items_per_page - 1) // items_per_page
            
            # Display pagination control above the table
            page = st.number_input("Page", min_value=1, max_value=total_pages, step=1, value=1)
            start = (page - 1) * items_per_page
            end = start + items_per_page
            paginated_news = country_news.iloc[start:end]
            
            # Display paginated news table with clickable URL
            if len(paginated_news) > 0:
                # Display news articles in a table format
                st.write(
                    paginated_news[['Pub_Date', 'News_Title', 'URL']].to_html(
                        index=False, 
                        escape=False, 
                        formatters={'URL': lambda x: f'<a href="{x}" target="_blank">Link</a>'}
                    ), 
                    unsafe_allow_html=True
                )
            else:
                st.write("No news articles found for the selected criteria.")
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.write("Please check your data format and try again.")

# Function to call OpenAI API for analysis with the new API structure

# Define the OpenAI conflict escalation analysis function
def get_conflict_analysis(country):
    # Create a structured prompt for OpenAI
    prompt = (
        f"As part of an analysis for the Ministry of Foreign Affairs, provide an assessment on the probability of conflict escalation in {country}. "
        f"Refer to any typical indicators or patterns related to economic or political tensions in similar situations, as well as any regional dependencies. "
        f"Provide a structured report as follows: "
        f"- **Situation Overview**: Describe any relevant political or economic background for {country}. "
        f"- **Risk of Fiscal Impact**: Assess the potential economic impact of escalation on government fiscal stability. "
        f"- **Evacuation Considerations**: Estimate the number of Indonesian nationals who might need evacuation and any specific logistical challenges. "
        f"- **Conflict Prevention Recommendations**: Provide recommendations to reduce the risk of escalation or mitigate impacts."
    )

    # Call OpenAI API to generate response using the ChatCompletion endpoint
    response = openai.ChatCompletion.create(
        model="gpt-4",  # Use gpt-4 or gpt-3.5-turbo based on your access
        messages=[
            {"role": "system", "content": "You are an expert analyst for conflict assessment."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.7
    )

    return response['choices'][0]['message']['content'].strip()

# Dropdown and analysis display below the news table
st.subheader("Choose a country for further conflict escalation analysis")
chosen_country = st.selectbox("Select a country for analysis", choropleth_data["Country"].unique())

if chosen_country:
    st.subheader(f"Conflict Escalation Analysis for {chosen_country}")
    analysis = get_conflict_analysis(chosen_country)
    if analysis:
        st.write(analysis)
