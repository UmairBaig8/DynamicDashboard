import streamlit as st
from pymongo import MongoClient
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from bson import Decimal128
import numpy as np

# Initialize session state
if 'derived_fields' not in st.session_state:
    st.session_state.derived_fields = {}

# MongoDB Connection
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets.mongo.uri)

client = init_connection()

# Data processing functions
def safe_flatten(doc):
    flat = {}
    for key, value in doc.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat[f"{key}_{sub_key}"] = sub_value
        else:
            flat[key] = value
    return flat

def convert_decimals(obj):
    if isinstance(obj, Decimal128):
        return float(obj.to_decimal())
    return obj

# Main App
def main():
    st.title("🏠 Dynamic Airbnb Analytics")
    
    # Data Loading
    db_name = st.sidebar.selectbox("Select Database", client.list_database_names())
    db = client[db_name]
    collection_name = st.sidebar.selectbox("Select Collection", db.list_collection_names())
    collection = db[collection_name]
    data = [convert_decimals(safe_flatten(doc)) for doc in collection.find().limit(1000)]
    df = pd.DataFrame(data)
    
    # Convert numeric fields
    numeric_fields = ['price', 'cleaning_fee', 'accommodates', 'bedrooms']
    for field in numeric_fields:
        if field in df.columns:
            df[field] = pd.to_numeric(df[field], errors='coerce')
    
    # Sidebar Controls
    st.sidebar.header("📊 Dashboard Configuration")
    
    # Derived Field Creation
    with st.sidebar.expander("➕ Create Derived Field"):
        new_field = st.text_input("Field name (e.g., total_cost)")
        formula = st.text_input("Formula (e.g., price + cleaning_fee)")
        if st.button("Create Field"):
            try:
                df[new_field] = df.eval(formula)
                st.session_state.derived_fields[new_field] = formula
                st.success(f"Created field: {new_field}")
            except Exception as e:
                st.error(f"Error creating field: {str(e)}")
    
    # Visualization Controls
    with st.sidebar.expander("📈 Chart Settings"):
        chart_type = st.selectbox("Chart Type", 
            ["Scatter", "Bar", "Line", "Histogram", "Box", "Pie"])
        
        available_fields = list(df.select_dtypes(include=np.number).columns) + \
                          list(df.select_dtypes(exclude=np.number).columns)
        
        x_axis = st.selectbox("X-Axis", available_fields)
        y_axis = st.selectbox("Y-Axis", available_fields, index=1) if chart_type not in ["Histogram", "Pie"] else None
        color_field = st.selectbox("Color By", [None] + available_fields)
        size_field = st.selectbox("Size By", [None] + available_fields) if chart_type == "Scatter" else None
    
    # Main Dashboard
    st.header("Custom Analytics")
    
    # Dynamic Metrics
    metric_fields = st.multiselect("Select Metrics", 
                                 df.select_dtypes(include=np.number).columns.tolist(),
                                 default=['price', 'cleaning_fee'])
    
    if metric_fields:
        cols = st.columns(len(metric_fields))
        for idx, field in enumerate(metric_fields):
            with cols[idx]:
                st.metric(f"Avg {field}", f"{df[field].mean():.2f}")
                st.caption(f"Min: {df[field].min():.2f} | Max: {df[field].max():.2f}")
    
    # Dynamic Visualization
    st.header("Custom Visualization")
    try:
        if chart_type == "Scatter":
            fig = px.scatter(df, x=x_axis, y=y_axis, color=color_field, size=size_field)
        elif chart_type == "Bar":
            fig = px.bar(df, x=x_axis, y=y_axis, color=color_field)
        elif chart_type == "Line":
            fig = px.line(df, x=x_axis, y=y_axis, color=color_field)
        elif chart_type == "Histogram":
            fig = px.histogram(df, x=x_axis, color=color_field)
        elif chart_type == "Box":
            fig = px.box(df, x=x_axis, y=y_axis, color=color_field)
        elif chart_type == "Pie":
            fig = px.pie(df, names=x_axis, values=y_axis)
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Couldn't render chart: {str(e)}")
    
    # Raw Data Explorer
    with st.expander("🔍 Data Explorer"):
        st.dataframe(df.head(100))

if __name__ == "__main__":
    main()