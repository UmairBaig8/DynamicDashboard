import streamlit as st
from pymongo import MongoClient
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from bson import Decimal128
from decimal import Decimal
import sys

# Configuration
DEFAULT_NUMERIC = 0.0
MAX_SAMPLE_SIZE = 1000

@st.cache_resource
def init_connection():
    try:
        if "uri" in st.secrets.mongo:
            return MongoClient(st.secrets.mongo.uri)
        return MongoClient(
            host=st.secrets.mongo.get("host", "localhost"),
            port=st.secrets.mongo.get("port", 27017),
            username=st.secrets.mongo.get("username", ""),
            password=st.secrets.mongo.get("password", "")
        )
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {str(e)}")
        sys.exit(1)

client = init_connection()

def safe_convert(value):
    if isinstance(value, Decimal128):
        try: return float(value.to_decimal())
        except: return DEFAULT_NUMERIC
    return value

def safe_flatten(doc):
    flat = {}
    for key, value in doc.items():
        try:
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat[f"{key}_{sub_key}"] = safe_convert(sub_value)
            else:
                flat[key] = safe_convert(value)
        except: pass
    return flat

def safe_dataframe(data):
    try:
        df = pd.DataFrame(data)
        
        numeric_config = [
            ('price_$numberDecimal', 'price', float),
            ('cleaning_fee_$numberDecimal', 'cleaning_fee', float),
            ('review_scores_review_scores_rating_$numberInt', 'review_rating', int),
            ('accommodates_$numberInt', 'accommodates', int),
            ('bedrooms_$numberInt', 'bedrooms', int),
            ('bathrooms_$numberDecimal', 'bathrooms', float),
            ('host_host_is_superhost', 'host_is_superhost', bool)
        ]
        
        for src, dest, dtype in numeric_config:
            if src in df.columns:
                df[dest] = pd.to_numeric(df[src], errors='coerce').fillna(DEFAULT_NUMERIC).astype(dtype)
            else:
                df[dest] = dtype(DEFAULT_NUMERIC)
                
        if 'address_location_coordinates' in df.columns:
            df['coordinates'] = df['address_location_coordinates'].apply(
                lambda x: (x[1], x[0]) if isinstance(x, list) and len(x)==2 else (None, None))
            df[['lat', 'lon']] = pd.DataFrame(df['coordinates'].tolist(), index=df.index)
            
        return df
    except Exception as e:
        st.error(f"Data processing error: {str(e)}")
        return pd.DataFrame()

def render_metrics(df):
    try:
        st.header("📊 Key Metrics")
        cols = st.columns(5)
        metrics = {
            "Avg Price": f"${df['price'].mean():.2f}",
            "Avg Rating": f"{df['review_rating'].mean():.0f}/100",
            "Superhost %": f"{df['host_is_superhost'].mean()*100:.1f}%",
            "Avg Bedrooms": f"{df['bedrooms'].mean():.1f}",
            "Avg Bathrooms": f"{df['bathrooms'].mean():.1f}"
        }
        for (k, v), col in zip(metrics.items(), cols):
            col.metric(k, v)
    except: st.warning("Metrics unavailable")

def render_price_analysis(df):
    try:
        st.header("💰 Pricing Insights")
        fig = px.scatter(df, x='accommodates', y='price', 
                        color='room_type', size='bedrooms',
                        hover_name='property_type',
                        title="Price vs Capacity")
        st.plotly_chart(fig)
    except: st.warning("Price analysis unavailable")

def render_review_analysis(df):
    try:
        review_cols = [c for c in df.columns if c.startswith('review_scores_')]
        if review_cols:
            st.header("⭐ Review Breakdown")
            scores = df[review_cols].mean().reset_index()
            scores.columns = ['Category', 'Score']
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=scores['Score'], theta=scores['Category'], fill='toself'
            ))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,10])))
            st.plotly_chart(fig)
    except: st.warning("Review analysis unavailable")

def render_amenities(df):
    try:
        if 'amenities' in df.columns:
            st.header("🏆 Top Amenities")
            amenities = df['amenities'].explode().value_counts().head(10)
            fig = px.bar(amenities, orientation='h', 
                         labels={'index':'Amenity', 'value':'Count'})
            st.plotly_chart(fig)
    except: st.warning("Amenities analysis unavailable")

def render_geo(df):
    try:
        if 'lat' in df.columns and 'lon' in df.columns:
            st.header("📍 Geographic Distribution")
            fig = px.scatter_mapbox(df.dropna(subset=['lat', 'lon']),
                                  lat='lat', lon='lon', color='price',
                                  size='accommodates', zoom=10,
                                  mapbox_style="open-street-map")
            st.plotly_chart(fig)
    except: st.warning("Map unavailable")

def main():
    try:
        st.title("🏠 Airbnb Analytics Dashboard")
        # Database/Collection selection
        db_name = st.sidebar.selectbox("Select Database", client.list_database_names())
        db = client[db_name]
        collection_name = st.sidebar.selectbox("Select Collection", db.list_collection_names())
        collection = db[collection_name]
        
        try:
            data = list(collection.find().limit(MAX_SAMPLE_SIZE))
            df = safe_dataframe([safe_flatten(d) for d in data])
        except Exception as e:
            st.error(f"Data load failed: {str(e)}")
            return
        
        render_metrics(df)
        render_price_analysis(df)
        render_review_analysis(df)
        render_amenities(df)
        render_geo(df)
        
    except Exception as e:
        st.error(f"Critical error: {str(e)}")

if __name__ == "__main__":
    main()