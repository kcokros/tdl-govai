import streamlit as st
import pandas as pd
import plotly.express as px

# Load processed data
@st.cache_data
def load_data():
    data_path = '/content/drive/MyDrive/_PROJECT_/PJ-AI/processed_news_data.csv'
    return pd.read_csv(data_path)

# Summarize data by country
def prepare_choropleth_data(data):
    country_counts = data['Countries Mentioned'].value_counts().reset_index()
    country_counts.columns = ['Country', 'News_Count']
    return country_counts

# Streamlit App for Conflict Monitoring Dashboard
def main():
    st.title("Conflict Monitoring Dashboard")

    # Load data
    data = load_data()

    # Prepare choropleth data
    choropleth_data = prepare_choropleth_data(data)

    # Display choropleth map
    st.header("Global Conflict News Counts by Country")
    fig = px.choropleth(
        choropleth_data,
        locations="Country",
        locationmode="country names",
        color="News_Count",
        color_continuous_scale="Reds",
        title="Number of Conflict News Mentions by Country",
        labels={'News_Count': 'News Articles Count'},
    )
    fig.update_geos(showcoastlines=True, coastlinecolor="Gray")
    st.plotly_chart(fig)

if __name__ == "__main__":
    main()
