import streamlit as st
import requests
import json

API_URL = "http://localhost:8000/chat"

st.set_page_config(page_title="Universal Data Connector", page_icon="🤖", layout="wide")

st.title("🤖 Universal Data Connector")
st.caption("LLM Function Calling Demo: Weather • News • Currency Conversion")

# Sidebar examples
st.sidebar.header("Examples")
examples = [
    "What's the weather in Pune today?",
    "Give me news of Mumbai",
    "Convert 500 INR to USD",
    "Convert 1 EUR to INR",
]
example = st.sidebar.radio("Try one:", examples)

# Input
user_message = st.text_input("Enter your query:", value=example)

col1, col2 = st.columns([1, 1])

if st.button("Send 🚀"):
    with st.spinner("Thinking..."):
        try:
            r = requests.post(API_URL, json={"user_id": "streamlit_user", "message": user_message}, timeout=300)
        except Exception as e:
            st.error(f"Backend not reachable: {e}")
            st.stop()

    if r.status_code != 200:
        st.error(f"Error {r.status_code}: {r.text}")
        st.stop()

    data = r.json()

    # Display output
    st.success("Response received!")

    # Human response
    st.subheader("✅ Human Readable Response")
    st.write(data.get("response", ""))

    # Tool info
    st.subheader("🛠️ Tool Execution Details")

    if data.get("type") == "function_call":
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Tool Called")
            st.code(data.get("function"))

            st.markdown("### Tool Arguments")
            st.json(data.get("function_args"))

        with col2:
            st.markdown("### Tool Result (Raw JSON)")
            st.json(data.get("function_result"))

    else:
        st.info("No tool call was required for this query.")
        st.json(data)
