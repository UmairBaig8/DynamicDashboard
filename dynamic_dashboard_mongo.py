import streamlit as st
from pymongo import MongoClient
import plotly.express as px
from bson import Decimal128
from collections import defaultdict

# MongoDB Connection
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets.mongo.uri)

#client = init_connection()
with st.sidebar.expander("➕ Database Selection:"):
    mongo_uri = st.text_input("Mongo URI")
    if mongo_uri:
        client = MongoClient(mongo_uri)
    else:
        client = MongoClient(st.secrets.mongo.uri)
    # Database/Collection selection
    db_name = st.selectbox("Select Database", client.list_database_names())
    db = client[db_name]
    collection_name = st.selectbox("Select Collection", db.list_collection_names())
    collection = db[collection_name]
    # Reset selections when database/collection changes
    if st.session_state.get("prev_db") != db_name or st.session_state.get("prev_collection") != collection_name:
        st.session_state.selected_metrics = []
        st.session_state.prev_db = db_name
        st.session_state.prev_collection = collection_name

def get_available_fields():
    """Fetch available fields from MongoDB collection"""
    try:
        # Get sample documents to discover fields
        sample_docs = list(collection.aggregate([
            {"$sample": {"size": 10}},
            {"$limit": 10}
        ]))
        
        # Flatten nested documents
        fields = set()
        for doc in sample_docs:
            flattened = safe_flatten(doc)
            fields.update(flattened.keys())
            
        # Add custom fields from session state
        fields.update(st.session_state.get("custom_fields", {}).keys())
        return sorted(fields)
    
    except Exception as e:
        st.error(f"Field discovery error: {str(e)}")
        return []

def safe_flatten(doc, parent_key='', sep='_'):
    """Flatten nested dictionaries"""
    items = {}
    for k, v in doc.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(safe_flatten(v, new_key, sep=sep))
        else:
            items[new_key] = v
    return items

# Helper to convert MongoDB types
def convert_value(value):
    if isinstance(value, Decimal128):
        return float(value.to_decimal())
    return value

# Metric Configuration
METRIC_OPERATIONS = {
    "Count": {"operator": "$sum", "value": 1, "requires_field": False},
    "Sum": {"operator": "$sum", "value": "$value", "requires_field": True},
    "Average": {"operator": "$avg", "value": "$value", "requires_field": True},
    "Max": {"operator": "$max", "value": "$value", "requires_field": True},
    "Min": {"operator": "$min", "value": "$value", "requires_field": True},
    "Unique Count": {"operator": "$addToSet", "value": "$value", "requires_field": True}
}

def validate_fields(data, required_fields):
    missing = [field for field in required_fields if field not in data[0]]
    if missing:
        st.error(f"Missing fields: {', '.join(missing)}")
        return False
    return True

def build_metric_group(field, metrics):
    group_stage = {"_id": None}
    for metric in metrics:
        config = METRIC_OPERATIONS[metric]
        if metric == "Count":
            group_stage[metric.lower()] = {config["operator"]: config["value"]}
        else:
            if config["requires_field"]:
                value = config["value"].replace("$value", f"${field}")
                group_stage[metric.lower()] = {config["operator"]: value}
    return group_stage

# Main Application
def main():
    st.title("🏠 Airbnb Analytics Dashboard")
    
    # Initialize session state variables
    if 'selected_metrics' not in st.session_state:
        st.session_state.selected_metrics = []
    if 'selected_metric_type' not in st.session_state:
        st.session_state.selected_metric_type = []
    if 'selected_chart_type' not in st.session_state:
        st.session_state.selected_chart_type = "scatter"
    if 'selected_x_field' not in st.session_state:
        st.session_state.selected_x_field = "price"
    if 'selected_y_field' not in st.session_state:
        st.session_state.selected_y_field = "cleaning_fee"
    if 'selected_color_field' not in st.session_state:
        st.session_state.selected_color_field = ""
    if 'selected_size_field' not in st.session_state:
        st.session_state.selected_size_field = ""

    # Get available fields from MongoDB
    available_fields = get_available_fields()
    st.write(available_fields)

    # Sidebar Configuration
    st.sidebar.header("Configuration")
    
    # Field Management
    with st.sidebar.expander("➕ Custom Fields"):
        new_field = st.text_input("New field name")
        mongo_expr = st.text_input("MongoDB expression")
        if st.button("Add Field"):
            if new_field and mongo_expr:
                st.session_state.custom_fields[new_field] = mongo_expr
                st.rerun()
                
    # Metric Selection
    metric_fields = st.sidebar.multiselect(
        "Metric Fields", 
        available_fields,
        default=st.session_state.get("selected_metrics", []),
        key="metric_fields"
    )
    # Metric Selection
    metric_types = st.sidebar.multiselect(
        "Metric Types", 
        list(METRIC_OPERATIONS.keys()), 
        default=st.session_state.get("selected_metric_type", ["Average", "Max"]),
        key="metric_types"
    )    

    with st.sidebar.expander("➕ Chart Options:"):
        # Visualization Settings
        # Chart Type
        chart_type = st.sidebar.selectbox(
            "Chart Type", 
            ["scatter", "bar", "line", "histogram", "box", "pie"],
            index=0,
            key="chart_type"
        )
        
        # Dynamic field selection
        # X-Axis Field
        x_field = st.sidebar.selectbox(
            "X-Axis Field", 
            available_fields,
            index=available_fields.index(st.session_state.selected_x_field) if st.session_state.selected_x_field in available_fields else 0,
            key="x_field"
        )
        y_field = st.sidebar.selectbox(
            "Y-Axis Field", 
            available_fields,
            index=available_fields.index(st.session_state.selected_y_field) if st.session_state.selected_y_field in available_fields else 0,
            key="y_field"
        )
        color_field = st.sidebar.selectbox(
            "Color Field", 
            available_fields,
            index=available_fields.index(st.session_state.selected_color_field) if st.session_state.selected_color_field in available_fields else 0,
            key="color_field"
        )
        size_field = st.sidebar.selectbox(
            "Size Field", 
            available_fields,
            index=available_fields.index(st.session_state.selected_size_field) if st.session_state.selected_size_field in available_fields else 0,
            key="size_field"
        )

        # x_field = st.selectbox("X-Axis Field", available_fields, index=available_fields.index("price") if "price" in available_fields else 0)
        # y_field = st.selectbox("Y-Axis Field", available_fields, index=available_fields.index("cleaning_fee") if "cleaning_fee" in available_fields else 0) if chart_type != "pie" else None
        # color_field = st.selectbox("Color Field", [None] + available_fields) if chart_type not in ["histogram", "pie"] else None
        # size_field = st.selectbox("Size Field", [None] + available_fields) if chart_type == "scatter" else None

    # Initialize custom fields
    if "custom_fields" not in st.session_state:
        st.session_state.custom_fields = {}

    # Build base pipeline
    pipeline = []
    for field, expr in st.session_state.custom_fields.items():
        try:
            pipeline.append({"$addFields": {field: eval(expr)}})
        except Exception as e:
            st.error(f"Error in field '{field}': {str(e)}")

    # Metrics Calculation
    if metric_fields and metric_types:
        st.header("📊 Metrics Dashboard")
        cols = st.columns(len(metric_fields))
        
        for idx, field in enumerate(metric_fields):
            with cols[idx]:
                st.subheader(field.replace("_", " ").title())
                
                try:
                    metric_pipeline = pipeline.copy()
                    metric_pipeline.append({"$group": build_metric_group(field, metric_types)})
                    result = list(collection.aggregate(metric_pipeline))[0]
                    
                    for metric in metric_types:
                        if metric == "Count":
                            value = result.get(metric.lower(), 0)
                        elif metric == "Unique Count":
                            value = len(result.get(metric.lower(), []))
                        else:
                            value = result.get(metric.lower(), 0)
                        st.metric(metric, f"{round(value, 2) if isinstance(value, float) else value}")
                        
                except Exception as e:
                    st.error(f"Metrics error: {str(e)}")

    # Visualization
    if x_field:
        try:
            st.session_state.selected_x_field = x_field
            vis_pipeline = pipeline.copy()
            projection = {"_id": 0, x_field: 1}
            
            if y_field: projection[y_field] = 1
            if color_field: projection[color_field] = 1
            if size_field: projection[size_field] = 1
            
            vis_pipeline.append({"$project": projection})
            vis_pipeline.append({"$limit": 1000})
            
            results = list(collection.aggregate(vis_pipeline))
            if not results:
                st.warning("No data available for visualization")
                return
                
            data = [{k: convert_value(v) for k, v in doc.items()} for doc in results]
            
            # Field validation
            required_fields = [x_field]
            if y_field: required_fields.append(y_field)
            if color_field: required_fields.append(color_field)
            if size_field: required_fields.append(size_field)
            
            if not validate_fields(data, required_fields):
                return

            # Create visualization
            fig_map = {
                "scatter": px.scatter(data, x=x_field, y=y_field, 
                                    color=color_field, size=size_field),
                "bar": px.bar(data, x=x_field, y=y_field, color=color_field),
                "line": px.line(data, x=x_field, y=y_field, color=color_field),
                "histogram": px.histogram(data, x=x_field, color=color_field),
                "box": px.box(data, x=x_field, y=y_field, color=color_field),
                "pie": px.pie(data, names=x_field, values=y_field)
            }
            
            fig = fig_map.get(chart_type)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("View Raw Data"):
                    st.write(data[:100])
                    
        except Exception as e:
            st.error(f"Visualization error: {str(e)}")

if __name__ == "__main__":
    main()
