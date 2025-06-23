import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import folium
from streamlit_folium import st_folium

# --- CONFIG ---
st.set_page_config(page_title="Spacini Rental Listings", layout="wide")
IMGBB_API_KEY = "6f3e33650b7ef74b16ca7f86b228932c"
submission_url = "https://script.google.com/macros/s/AKfycbwimMNyOufyTa02wJkBBL163mKQW6-H0pGJre3rnNUqbKyzvpgzil9PkLbqizjszkDNvw/exec"

# --- GOOGLE SHEET CSV LINK ---
sheet_url = "https://docs.google.com/spreadsheets/d/1tE88_gTRykmT9hiMzNNLxlwfbygWcwUe6j7nFfOL0yw/export?format=csv"
df = pd.read_csv(sheet_url)

# --- CLEAN & FORMAT DATA ---
df.dropna(subset=["Title", "Image URLs", "Location"], inplace=True)
df["Price"] = pd.to_numeric(df["Price"], errors='coerce')
df = df.dropna(subset=["Price"])
df["Type"] = df["Type"].fillna("Unspecified")

min_price_val = int(df["Price"].min()) if not df["Price"].isnull().all() else 0
max_price_val = int(df["Price"].max()) if not df["Price"].isnull().all() else 1000

# --- SIDEBAR FILTERS ---
st.sidebar.title("🔎 Filter Listings")
search = st.sidebar.text_input("Search by Name or Location").lower()
min_price, max_price = st.sidebar.slider("Price Range (RM)", min_value=min_price_val, max_value=max_price_val, value=(min_price_val, max_price_val))
type_filter = st.sidebar.multiselect("Type", options=df["Type"].unique(), default=list(df["Type"].unique()))

# --- FILTER DATA ---
filtered_df = df[
    df["Price"].between(min_price, max_price) &
    df["Type"].isin(type_filter) &
    (
        df["Title"].str.lower().str.contains(search) |
        df["Location"].str.lower().str.contains(search)
    )
]

# --- PAGINATION CONFIG ---
ITEMS_PER_PAGE = 8
page = st.sidebar.number_input("Page", min_value=1, max_value=max(1, (len(filtered_df) - 1) // ITEMS_PER_PAGE + 1), step=1)
start = (page - 1) * ITEMS_PER_PAGE
end = start + ITEMS_PER_PAGE
current_page_df = filtered_df.iloc[start:end]

# --- DISPLAY PROPERTY CARDS ---
st.title("🏠 Spacini – Find Your Perfect Stay")
cols = st.columns(2)

for i, (_, row) in enumerate(current_page_df.iterrows()):
    with cols[i % 2]:
        with st.container():
            image_urls = str(row["Image URLs"]).split(",")
            st.image(image_urls, caption=[f"Image {j+1}" for j in range(len(image_urls))], use_column_width="always")
            st.markdown(f"### {row['Title']}")
            st.markdown(f"**📍 Location:** {row['Location']}")
            st.markdown(f"**💰 Price:** RM {int(row['Price'])}")
            st.markdown(f"**🏷️ Type:** {row['Type']}")
            if "Latitude" in row and "Longitude" in row:
                st.markdown(f"🌐 **Lat/Lon:** {row['Latitude']}, {row['Longitude']}")
            with st.expander("📄 View Details"):
                st.write(row["Description"])
                st.markdown(f"📞 **Contact:** {row['Contact']}")
                if "DateTime" in row:
                    st.markdown(f"🕒 **Posted on:** {row['DateTime']}")

# --- SUBMIT NEW LISTING FORM ---
st.markdown("---")
st.header("📤 Submit a New Listing")

if "map_lat" not in st.session_state:
    st.session_state.map_lat = None
    st.session_state.map_lon = None

with st.form("listing_form"):
    title = st.text_input("Title")
    price = st.number_input("Price (RM)", min_value=0)

    location = st.text_input("Location (e.g., Wakaf Bharu)")
    states = [
        "Johor", "Kedah", "Kelantan", "Melaka", "Negeri Sembilan", "Pahang",
        "Perak", "Perlis", "Penang", "Sabah", "Sarawak", "Selangor", "Terengganu",
        "Kuala Lumpur", "Labuan", "Putrajaya"
    ]
    selected_state = st.selectbox("State", states)

    type_ = st.selectbox("Type", ["Short-term", "Long-term", "Room", "Apartment", "Other"])
    description = st.text_area("Description")
    contact = st.text_input("Contact Info (Phone/Email)")
    st.markdown("#### Upload up to 5 Images")
    image_files = st.file_uploader("", type=["jpg", "jpeg", "png"], accept_multiple_files=True, label_visibility="collapsed")

    if image_files:
        preview_images = [img.read() for img in image_files[:5]]
        st.image(preview_images, caption=[f"Image {i+1}" for i in range(len(preview_images))], use_column_width=True)

    st.markdown("### 🗺️ Pin Location")

    if st.form_submit_button("📍 Find on Map"):
        if location.strip() != "":
            full_query = f"{location}, {selected_state}, Malaysia"
            geocode_url = f"https://nominatim.openstreetmap.org/search?format=json&q={full_query}"
            headers = {"User-Agent": "spacini-app/1.0"}
            response = requests.get(geocode_url, headers=headers)
            if response.status_code == 200 and len(response.json()) > 0:
                coords = response.json()[0]
                st.session_state.map_lat = float(coords["lat"])
                st.session_state.map_lon = float(coords["lon"])
                st.success(f"📍 Found: {st.session_state.map_lat:.5f}, {st.session_state.map_lon:.5f}")
            else:
                st.error("❌ Location not found. Try a full town name or be more specific.")
        else:
            st.warning("Please enter a location name.")

    lat = st.session_state.map_lat
    lon = st.session_state.map_lon

    if lat and lon:
        m = folium.Map(location=[lat, lon], zoom_start=16)
        marker = folium.Marker(
            location=[lat, lon],
            draggable=True,
            popup="Drag to exact location",
            icon=folium.Icon(color="blue", icon="home")
        )
        m.add_child(marker)
        map_data = st_folium(m, height=400, returned_objects=["all_markers"])
        if map_data and map_data.get("all_markers"):
            lat = map_data["all_markers"][0]["lat"]
            lon = map_data["all_markers"][0]["lng"]
            st.success(f"📍 Final Pin Location: {lat:.5f}, {lon:.5f}")

    submitted = st.form_submit_button("📩 Submit Listing")

    if submitted:
        if not all([title, price, location, contact]) or not image_files:
            st.error("❌ Please fill in all required fields and upload at least one image.")
        elif lat is None or lon is None:
            st.error("📍 Use 'Find on Map' and drag pin to set location.")
        else:
            image_urls = []
            with st.spinner("📤 Uploading images..."):
                for img in image_files[:5]:
                    response = requests.post(
                        "https://api.imgbb.com/1/upload",
                        params={"key": IMGBB_API_KEY},
                        files={"image": img}
                    )
                    if response.status_code == 200:
                        image_url = response.json()["data"]["url"]
                        image_urls.append(image_url)

            if len(image_urls) == 0:
                st.error("❌ Failed to upload any images.")
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = {
                    "Title": title,
                    "Price": price,
                    "Location": f"{location}, {selected_state}",
                    "Type": type_,
                    "Image URLs": ",".join(image_urls),
                    "Description": description,
                    "Contact": contact,
                    "DateTime": timestamp,
                    "Latitude": lat,
                    "Longitude": lon
                }
                requests.post(submission_url, json=new_row)
                st.success("✅ Listing submitted successfully!")
                st.session_state.map_lat = None
                st.session_state.map_lon = None
