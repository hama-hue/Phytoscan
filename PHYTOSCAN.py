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
PLANT_ID_ENDPOINT = "https://api.plant.id/v2/health-assessment"

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
        "plant_details": [
    "common_names",
    "url",
    "wiki_description",
    "edible_parts",
    "medicinal_properties",
    "taxonomy",
    "growth_habit",
    "propagation_methods",
    "distribution",
    "watering",
    "sunlight",
    "soil",
    "conservation_status"
],
        "disease_details": ["common_names", "description", "treatment"]
    }

    response = requests.post(PLANT_ID_ENDPOINT, json=payload, headers=headers)

    if response.status_code != 200:
        st.error(f"API Error: {response.status_code} - {response.text}")
        st.stop()
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
                    
                    if details.get("edible_parts"):
                        st.write(f"**Edible Parts**: {', '.join(details['edible_parts'])}")

                    if details.get("medicinal_properties"):
                        st.write("**Medicinal Properties**:")
                        for prop in details["medicinal_properties"]:
                            st.write(f"- {prop}")

                    if details.get("taxonomy"):
                        st.write("**Taxonomy**:")
                        for key, value in details["taxonomy"].items():
                            st.write(f"- {key.capitalize()}: {value}")

                    st.write(f"[More Info on Wikipedia]({details.get('url', '#')})")

                    # Disease Detection
                    disease_data = result.get("disease", {})
                    is_healthy = disease_data.get("is_healthy", {}).get("probability", 0)

                    if disease_data.get("suggestions"):
                        st.subheader("🦠 Possible Diseases Detected")
                        for disease in disease_data["suggestions"]:
                            name = disease.get("name", "Unknown Disease")
                            prob = disease.get("probability", 0)
                            desc = disease.get("description", "No description available.")
                            treatment = disease.get("treatment", "No treatment info available.")

                            st.warning(f"⚠️ {name} ({prob*100:.2f}% confidence)")
                            st.write(f"**Description**: {desc}")
                            st.write(f"**Treatment**: {treatment}")
                    else:
                        st.success("✅ The plant appears to be perfectly healthy!")
                        st.write(f"**Health Confidence**: {is_healthy*100:.2f}%")

                    break

            if not flag:
                st.warning("A plant was detected, but none of the suggestions were confident enough.Please try a clearer photo")
        else:
            st.error("No plant detected in the image. Please try a clearer photo.")
