import streamlit as st
import requests
import time

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
    1. Enter product name
    2. Click 'Add to Cart'
    3. Wait for the agent to complete
    4. View the results below
    """)

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Product Search")
    items_input = st.text_input(
        "Enter product names",
        placeholder="e.g., Pen",
        help="Enter product name"
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
    if not items_input or not items_input.strip():
        st.error("⚠️ Please enter at least one product name")
    else:
        # Parse items
        items = [item.strip() for item in items_input.split(",") if item.strip()]
        
        if not items:
            st.error("⚠️ Please enter valid product names")
        else:
            st.info(f"🔍 Searching for {len(items)} product(s): {', '.join(items)}")
            
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("⏳ Sending request to API...")
                progress_bar.progress(20)
                
                # Make API request
                response = requests.post(
                    f"{api_url}/add-to-cart",
                    json={"items": items},
                    timeout=300  # 5 minutes timeout for long-running tasks
                )
                
                progress_bar.progress(60)
                status_text.text("⏳ Processing response...")
                
                if response.status_code == 200:
                    data = response.json()
                    progress_bar.progress(100)
                    status_text.text("✅ Complete!")
                    
                    if data.get("success"):
                        st.success(f"✅ {data.get('message', 'Items processed successfully')}")
                        
                        # Display cart items - only show "Added to cart" with product link
                        cart = data.get("cart")
                        if cart and cart.get("items"):
                            st.subheader("✅ Added to Cart")
                            
                            for item in cart["items"]:
                                if item.get('url'):
                                    st.markdown(f"🔗 [Product Link]({item['url']})")
                                else:
                                    st.markdown("🔗 Product link not available")
                        else:
                            st.warning("⚠️ No items were returned in the response")
                    else:
                        st.error(f"❌ {data.get('message', 'Request failed')}")
                        if data.get("error"):
                            st.code(data["error"])
                else:
                    progress_bar.progress(100)
                    status_text.text("❌ Error!")
                    st.error(f"❌ API returned status code: {response.status_code}")
                    try:
                        error_data = response.json()
                        st.error(f"Error: {error_data.get('detail', 'Unknown error')}")
                    except:
                        st.error(f"Error: {response.text}")
            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. The operation may still be running on the server.")
                st.info("Check the FastAPI server logs for more information.")
            except requests.exceptions.RequestException as e:
                progress_bar.progress(100)
                status_text.text("❌ Error!")
                st.error(f"❌ Cannot connect to API: {str(e)}")
                st.info("Make sure the FastAPI server is running: `python api.py`")
            except Exception as e:
                progress_bar.progress(100)
                status_text.text("❌ Unexpected Error!")
                st.error(f"Error: {str(e)}")
            finally:
                time.sleep(1)
                progress_bar.empty()
                status_text.empty()

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
