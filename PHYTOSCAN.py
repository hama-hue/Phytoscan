import streamlit as st
from PIL import Image
import requests
import time
import base64
import os

#Load API Key
API_KEY = os.getenv("PLANT_ID_API_KEY")
if not API_KEY:
    st.error("API Key not found. Please set the PLANT_ID_API_KEY environment variable.")
    st.stop()

# Plant.ID API endpoint
PLANT_ID_ENDPOINT = "https://api.plant.id/v2/identify"

#Encode Image to base64
def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode("utf-8")

#Call the plant ID API
def identify_plant(image_data_b64, api_key):
    headers = {
        "Content-Type": "application/json",
        "Api-Key": api_key
    }
    payload = {
        "images": [image_data_b64],
        "modifiers": ["crops_fast", "similar_images"],
        "plant_language": "en",
        "plant_details": ["common_names", "url", "wiki_description",]
    }

    response = requests.post(PLANT_ID_ENDPOINT, json=payload, headers=headers)

    if response.status_code != 200:
        st.error(f"API Error: {response.status_code} - {response.text}")
        return {}

    try:
        return response.json()
    except Exception as e:
        st.error("Failed to decode JSON from API response.")
        st.text(f"Raw response:\n{response.text}")
        return {}

#Page Setup
st.set_page_config(page_title="PhytoScan - Leaf Identifier", layout="centered")
st.title("🌿 PhytoScan - Identify a Leaf and Discover Its Uses")

#Image Upload
uploaded_file = st.file_uploader("Upload a leaf image.",type=["jpg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Leaf", use_container_width =True)
    uploaded_file.seek(0) 
    b64_image = encode_image(uploaded_file)

    #Rate limiting
    max_calls = 5
    seconds = 600 #10 minutes

    if "api_call_times" not in st.session_state:
        st.session_state["api_call_times"] = []

    now = time.time()
    call_times = [t for t in st.session_state["api_call_times"] if now - t < seconds]
    st.session_state["api_call_times"] = call_times

    #Remaining calls 
    st.info(f"You have {max_calls - len(st.session_state['api_call_times'])} identifications remaining in this 10-minute window.")

    if len(call_times) >= max_calls:
        st.warning("🚫 Rate limit exceeded: You can only make 5 identifications every 10 minutes.")
        st.stop()

    st.session_state["api_call_times"] = call_times

    #Button to trigger identification
    if st.button("🔍 Identify Leaf"):
        with st.spinner("Identifying plant..."):
            result = identify_plant(b64_image, API_KEY)
            
        st.session_state["api_call_times"].append(time.time())

        #Process API Response
        if result.get("suggestions"):
            flag = False
            for suggestion in result["suggestions"]:
                confidence = suggestion.get("probability", 0)
                plant_name = suggestion["plant_name"]

                if confidence > 0.2:
                    flag = True
                    st.success(f"🌿 Identified Plant: {plant_name} ({confidence*100:.2f}% confidence)")

                    #Display Plant Details
                    details = suggestion.get("plant_details", {})
                    st.write(f"**Common Names**: {', '.join(details.get('common_names', []))}")
                    st.write(f"**Description**: {details.get('wiki_description', {}).get('value', 'No description available.')}")
                    st.write(f"[More Info on Wikipedia]({details.get('url', '#')})")

                    break

            if not flag:
                st.warning("A plant was detected, but none of the suggestions were confident enough.")
        else:
            st.error("No plant detected in the image. Please try a clearer photo.")
