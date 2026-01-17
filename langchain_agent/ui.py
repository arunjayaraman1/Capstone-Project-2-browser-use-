import streamlit as st
import requests
import time
import json
from typing import List

# API endpoint
API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Amazon Cart Automation",
    page_icon="🛒",
    layout="wide"
)

st.title("🛒 Amazon Cart Automation")
st.markdown("Search for products on Amazon.in and add them to your cart automatically")

# Sidebar for API configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_url = st.text_input("API URL", value=API_URL, help="FastAPI backend URL")
    st.markdown("---")
    st.markdown("### 📝 Instructions")
    st.markdown("""
    1. Enter a product name
    2. Click 'Add to Cart'
    3. Wait for the agent to complete
    4. View the results below
    """)

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Product Search")
    product_name_input = st.text_input(
        "Enter product name",
        placeholder="e.g., laptop",
        help="Enter a product name to search and add to cart"
    )

with col2:
    st.subheader("Actions")
    add_button = st.button("🛒 Add to Cart", type="primary", use_container_width=True)
    check_health = st.button("🏥 Check API Health", use_container_width=True)

# Health check
if check_health:
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            st.success("✅ API is healthy and running!")
        else:
            st.error(f"❌ API returned status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Cannot connect to API at {api_url}")
        st.info("Make sure the FastAPI server is running: `python api.py`")

# Process add to cart request
if add_button:
    if not product_name_input or not product_name_input.strip():
        st.error("⚠️ Please enter a product name")
    else:
        product_name = product_name_input.strip()
        st.info(f"🔍 Searching for: {product_name}")
        
        # Create containers for real-time updates
        status_container = st.container()
        progress_container = st.container()
        cart_container = st.container()
        
        with status_container:
            status_placeholder = st.empty()
            progress_placeholder = st.empty()
            log_placeholder = st.empty()
        
        try:
            status_placeholder.info("🚀 Starting agent...")
            progress_placeholder.progress(0)
            
            # Make streaming API request
            response = requests.post(
                f"{api_url}/add-to-cart",
                json={"product_name": product_name},
                stream=True,
                timeout=300
            )
            
            if response.status_code == 200:
                    current_step = 0
                    cart_data = None
                    final_message = None
                    
                    # Process streaming response
                    for line in response.iter_lines():
                        if line:
                            line_str = line.decode('utf-8')
                            if line_str.startswith('data: '):
                                try:
                                    data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                                    event_type = data.get('type', '')
                                    
                                    if event_type == 'status':
                                        status_placeholder.info(f"📡 {data.get('message', 'Processing...')}")
                                    
                                    elif event_type == 'progress':
                                        current_step = data.get('step', 0)
                                        action = data.get('action', 'Processing...')
                                        status_placeholder.success(f"✅ Step {current_step}: {action}")
                                        # Update progress (estimate based on steps, max ~20 steps)
                                        progress = min(10 + (current_step * 4), 90)
                                        progress_placeholder.progress(progress / 100)
                                        
                                        # Show in log
                                        with log_placeholder.container():
                                            st.text(f"Step {current_step}: {action}")
                                    
                                    elif event_type == 'complete':
                                        progress_placeholder.progress(100)
                                        if data.get('success'):
                                            status_placeholder.success(f"✅ {data.get('message', 'Completed!')}")
                                            cart_data = data.get('cart')
                                            final_message = data.get('message')
                                        else:
                                            status_placeholder.error(f"❌ {data.get('message', 'Failed')}")
                                            if data.get('error'):
                                                st.error(f"Error: {data.get('error')}")
                                    
                                    elif event_type == 'error':
                                        status_placeholder.error(f"❌ {data.get('message', 'Error occurred')}")
                                        if data.get('error'):
                                            st.error(f"Error: {data.get('error')}")
                                
                                except json.JSONDecodeError:
                                    continue
                    
                    # Display cart result immediately after completion - only show "Added to cart" with link
                    if cart_data:
                        with cart_container:
                            st.subheader("✅ Added to Cart")
                            if cart_data.get("items"):
                                for item in cart_data.get("items", []):
                                    if item.get('url'):
                                        st.markdown(f"🔗 [Product Link]({item['url']})")
                                    else:
                                        st.markdown("🔗 Product link not available")
                            elif cart_data.get("product_name"):
                                # Fallback for old API format
                                st.success("✅ Product added to cart")
                                if cart_data.get("url"):
                                    st.markdown(f"🔗 [Product Link]({cart_data['url']})")
                    
            if final_message:
                st.success(final_message)
            
            else:
                status_placeholder.error("❌ API Error!")
                try:
                    error_data = response.json()
                    st.error(f"Error: {error_data.get('detail', 'Unknown error')}")
                except:
                    st.error(f"Error: {response.text}")
        
        except requests.exceptions.Timeout:
            status_placeholder.error("⏱️ Request timed out. The operation may still be running on the server.")
            st.info("Check the FastAPI server logs for more information.")
        
        except requests.exceptions.RequestException as e:
            status_placeholder.error("❌ Connection Error!")
            st.error(f"❌ Cannot connect to API: {str(e)}")
            st.info("Make sure the FastAPI server is running: `python api.py`")
        
        except Exception as e:
            status_placeholder.error("❌ Unexpected Error!")
            st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("### 📊 API Status")
try:
    response = requests.get(f"{api_url}/health", timeout=2)
    if response.status_code == 200:
        st.success("🟢 API is online")
    else:
        st.warning("🟡 API returned unexpected status")
except:
    st.error("🔴 API is offline")
