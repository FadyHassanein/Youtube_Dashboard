import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from datetime import datetime

# Define a function to simplify country representation
def audience_simple(country):
    """Simplify country codes into broader categories."""
    if country == 'US':
        return 'USA'
    elif country == 'IN':
        return 'India'
    else:
        return 'Other'

# Load data with caching to improve performance
@st.cache_data

def load_data():
    """Load and preprocess all necessary datasets."""
    # Load aggregate metrics by video
    df_agg = pd.read_csv('Aggregated_Metrics_By_Video.csv').iloc[1:, :]
    df_agg.columns = ['Video', 'Video title', 'Video publish time', 'Comments added', 'Shares', 'Dislikes', 'Likes',
                      'Subscribers lost', 'Subscribers gained', 'RPM(USD)', 'CPM(USD)', 'Average % viewed', 'Average view duration',
                      'Views', 'Watch time (hours)', 'Subscribers', 'Your estimated revenue (USD)', 'Impressions', 'Impressions ctr(%)']
    
    # Convert date columns to datetime
    df_agg['Video publish time'] = pd.to_datetime(df_agg['Video publish time'], format='mixed')
    df_agg['Average view duration'] = df_agg['Average view duration'].apply(lambda x: datetime.strptime(x, '%H:%M:%S'))
    df_agg['Avg_duration_sec'] = df_agg['Average view duration'].apply(lambda x: x.second + x.minute * 60 + x.hour * 3600)

    # Calculate additional metrics
    df_agg['Engagement_ratio'] = (df_agg['Comments added'] + df_agg['Shares'] + df_agg['Dislikes'] + df_agg['Likes']) / df_agg['Views']
    df_agg['Views / sub gained'] = df_agg['Views'] / df_agg['Subscribers gained']
    df_agg.sort_values('Video publish time', ascending=False, inplace=True)

    # Load other datasets
    df_agg_sub = pd.read_csv('Aggregated_Metrics_By_Country_And_Subscriber_Status.csv')
    df_comments = pd.read_csv('Aggregated_Metrics_By_Video.csv')
    df_time = pd.read_csv('Video_Performance_Over_Time.csv')

    # Fix date formatting issues
    df_time['Date'] = df_time['Date'].str.replace("Sept", "Sep", regex=False)
    df_time['Date'] = pd.to_datetime(df_time['Date'], format='%d %b %Y', errors='coerce')

    return df_agg, df_agg_sub, df_comments, df_time

# Load the datasets
df_agg, df_agg_sub, df_comments, df_time = load_data()

# Prepare aggregate metrics dataset
# Create a copy for calculations
df_agg_diff = df_agg.copy()

# Define date filters for the last 12 months
metric_date_12mo = df_agg_diff["Video publish time"].max() - pd.DateOffset(months=12)

# Filter numeric columns for median calculations
numeric_df = df_agg_diff[df_agg_diff["Video publish time"] > metric_date_12mo].select_dtypes(include='number')
median_agg = numeric_df.median()

# Merge daily data with video publish data
df_time_diff = pd.merge(df_time, df_agg.loc[:, ['Video', 'Video publish time']], left_on='External Video ID', right_on='Video')

# Calculate days published
df_time_diff['days_published'] = (df_time_diff['Date'] - df_time_diff['Video publish time']).dt.days

# Filter for videos published in the last year
date_12mo = df_agg['Video publish time'].max() - pd.DateOffset(months=12)
df_time_diff_yr = df_time_diff[df_time_diff['Video publish time'] >= date_12mo]

# Calculate daily view data (mean, median, and percentiles)
views_days = pd.pivot_table(df_time_diff_yr, index='days_published', values='Views', aggfunc=[
    np.mean, np.median, lambda x: np.percentile(x, 80), lambda x: np.percentile(x, 20)]).reset_index()
views_days.columns = ['days_published', 'mean_views', 'median_views', '80pct_views', '20pct_views']
views_days = views_days[views_days['days_published'].between(0, 30)]

# Calculate cumulative views
views_cumulative = views_days.loc[:, ['days_published', 'median_views', '80pct_views', '20pct_views']]
views_cumulative.loc[:, ['median_views', '80pct_views', '20pct_views']] = views_cumulative.loc[:, ['median_views', '80pct_views', '20pct_views']].cumsum()

# Sidebar for user selection
add_sidebar = st.sidebar.selectbox('Aggregate or Individual Video', ('Aggregate Metrics', 'Individual Video Analysis'))

if add_sidebar == "Aggregate Metrics":
    st.title('Aggregate Metrics')
    st.write('This dashboard shows the aggregate metrics for the videos in the dataset.')
    # Select relevant columns for aggregate metrics
    df_agg_metrics = df_agg[['Video publish time', 'Views', 'Likes', 'Subscribers', 'Shares', 'Comments added', 'RPM(USD)', 'Average % viewed',
                             'Avg_duration_sec', 'Engagement_ratio', 'Views / sub gained']]

    # Define date ranges for 6-month and 12-month comparisons
    metric_date_6mo = df_agg_metrics['Video publish time'].max() - pd.DateOffset(months=6)
    metric_date_12mo = df_agg_metrics['Video publish time'].max() - pd.DateOffset(months=12)

    # Calculate medians for the metrics
    metric_medians6mo = df_agg_metrics[df_agg_metrics['Video publish time'] >= metric_date_6mo].median()
    metric_medians12mo = df_agg_metrics[df_agg_metrics['Video publish time'] >= metric_date_12mo].median()

    # Display metrics in columns
    col1, col2, col3, col4, col5 = st.columns(5)
    columns = [col1, col2, col3, col4, col5]

    count = 0
    for i in metric_medians6mo.index:
        with columns[count]:
            if isinstance(metric_medians6mo[i], (pd.Timestamp, pd.Timedelta)) or isinstance(metric_medians12mo[i], (pd.Timestamp, pd.Timedelta)):
                value6mo = metric_medians6mo[i].total_seconds() if isinstance(metric_medians6mo[i], pd.Timedelta) else metric_medians6mo[i].timestamp()
                value12mo = metric_medians12mo[i].total_seconds() if isinstance(metric_medians12mo[i], pd.Timedelta) else metric_medians12mo[i].timestamp()
            else:
                value6mo = metric_medians6mo[i]
                value12mo = metric_medians12mo[i]

            if value12mo != 0:
                delta = (value6mo - value12mo) / value12mo
            else:
                delta = 0

            st.metric(label=i, value=round(value6mo, 1), delta="{:.1%}".format(delta))
            count += 1
            if count >= 5:
                count = 0



    df_agg_diff['Publish_date'] = df_agg_diff['Video publish time'].apply(lambda x: x.date())
    df_agg_diff_final = df_agg_diff.loc[:, ['Video title', 'Publish_date', 'Views', 'Likes', 'Subscribers', 'Shares', 'Comments added', 'RPM(USD)', 'Average % viewed',
                                            'Avg_duration_sec', 'Engagement_ratio', 'Views / sub gained']]
     
    st.dataframe(df_agg_diff_final)

if add_sidebar == "Individual Video Analysis":
    st.title('Individual Video Analysis')
    st.write('This dashboard shows the individual video analysis for the videos in the dataset.')
     # Dropdown for video selection
    videos = tuple(df_agg['Video title'])
    video_select = st.selectbox('Pick a Video:', videos)

    # Filter datasets for selected video
    agg_filtered = df_agg[df_agg['Video title'] == video_select]
    agg_sub_filtered = df_agg_sub[df_agg_sub['Video Title'] == video_select]
    agg_sub_filtered['Country'] = agg_sub_filtered['Country Code'].apply(audience_simple)
    agg_sub_filtered.sort_values('Is Subscribed', inplace=True)

    # Create a bar chart for country-wise subscription data
    fig = px.bar(agg_sub_filtered, x='Views', y='Is Subscribed', color='Country', orientation='h')
    st.plotly_chart(fig)

    # Filter time data for the selected video
    agg_time_filtered = df_time_diff[df_time_diff['Video Title'] == video_select]
    first_30 = agg_time_filtered[agg_time_filtered['days_published'].between(0, 30)]
    first_30 = first_30.sort_values('days_published')

    # Create a comparison chart for view performance in the first 30 days
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['20pct_views'],
                              mode='lines',
                              name='20th percentile', line=dict(color='purple', dash='dash')))
    fig2.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['median_views'],
                              mode='lines',
                              name='50th percentile', line=dict(color='black', dash='dash')))
    fig2.add_trace(go.Scatter(x=views_cumulative['days_published'], y=views_cumulative['80pct_views'],
                              mode='lines',
                              name='80th percentile', line=dict(color='royalblue', dash='dash')))
    fig2.add_trace(go.Scatter(x=first_30['days_published'], y=first_30['Views'].cumsum(),
                              mode='lines',
                              name='Current Video', line=dict(color='firebrick', width=8)))

    # Update layout for the chart
    fig2.update_layout(title='View comparison first 30 days',
                       xaxis_title='Days Since Published',
                       yaxis_title='Cumulative views')

    st.plotly_chart(fig2)
