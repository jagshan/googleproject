# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo
import google.auth
from google.cloud import firestore, storage
from google import genai

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.tools.tool_context import ToolContext
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

# Hardcoded GCP Project ID (never read from google.auth.default() or GOOGLE_CLOUD_PROJECT)
PROJECT_ID = "qwiklabs-gcp-02-2e30ba48e9c5"

credentials, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
db = firestore.Client(project=PROJECT_ID, credentials=credentials)


def get_pantry_items(category: str = None) -> list[dict]:
    """Retrieves items from the pantry Firestore database.

    Args:
        category: Optional category filter (e.g. 'Grains & Pasta', 'Canned Goods', 'Oils & Condiments', 'Sweeteners').

    Returns:
        List of pantry item dictionaries containing item details.
    """
    collection_ref = db.collection("pantry_items")
    if category:
        query = collection_ref.where("category", "==", category)
        docs = query.stream()
    else:
        docs = collection_ref.stream()

    items = [doc.to_dict() for doc in docs]
    return items


def add_pantry_item(name: str, category: str, quantity: int, expiration_date: str = None) -> str:
    """Adds a new item or updates an existing item in the pantry Firestore database.

    Args:
        name: Name of the pantry item (e.g. 'Organic Whole Milk').
        category: Category of the item (e.g. 'Dairy', 'Produce', 'Grains & Pasta').
        quantity: Number of units available.
        expiration_date: Optional expiration date in YYYY-MM-DD format.

    Returns:
        Confirmation string indicating successful insertion or update.
    """
    item_id = name.lower().replace(" ", "-")
    doc_ref = db.collection("pantry_items").document(item_id)
    item_data = {
        "id": item_id,
        "name": name,
        "category": category,
        "quantity": int(quantity),
        "expiration_date": expiration_date or "N/A"
    }
    doc_ref.set(item_data)
    return f"Successfully saved '{name}' (Quantity: {quantity}, Category: '{category}') to pantry inventory."


def check_expiring_pantry_items(days_ahead: int = 7) -> list[dict]:
    """Finds pantry items expiring within the specified number of days from today.

    Args:
        days_ahead: Number of days ahead to check for expiring items (default is 7 days).

    Returns:
        List of pantry item dictionaries that are expiring soon or already expired.
    """
    today = datetime.date.today()
    cutoff_date = (today + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    docs = db.collection("pantry_items").stream()
    expiring = []
    for doc in docs:
        item = doc.to_dict()
        exp_date = item.get("expiration_date")
        if exp_date and exp_date != "N/A":
            if exp_date <= cutoff_date:
                expiring.append(item)
    return expiring


def search_recipes(query: str) -> list[dict]:
    """Searches online recipes by keyword or dish name using TheMealDB public API.

    Args:
        query: Recipe name or dish keyword (e.g. 'pasta', 'chicken', 'salad').

    Returns:
        List of recipe dictionaries containing dish name, category, area, instructions snippet, and source URL.
    """
    api_key = os.environ.get("MEALDB_API_KEY", "1")
    url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php?s={urllib.parse.quote(query)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            meals = data.get("meals") or []
            results = []
            for meal in meals[:3]:
                instructions = meal.get("strInstructions") or ""
                results.append({
                    "name": meal.get("strMeal"),
                    "category": meal.get("strCategory"),
                    "area": meal.get("strArea"),
                    "instructions": instructions[:300] + "..." if len(instructions) > 300 else instructions,
                    "source_url": meal.get("strSource") or meal.get("strYoutube") or "N/A"
                })
            return results
    except Exception as e:
        return [{"error": f"Failed to fetch recipes: {str(e)}"}]


def geocode_address(address: str) -> dict:
    """Converts a physical address or city name into geographical coordinates (latitude and longitude).

    Args:
        address: The address or place name to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'San Francisco').

    Returns:
        Dictionary containing formatted address, latitude, and longitude.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("results") or []
            if not results:
                return {"error": f"No coordinates found for address: {address}"}
            top_result = results[0]
            loc = top_result["geometry"]["location"]
            return {
                "address": top_result.get("formatted_address"),
                "location": {"latitude": loc["lat"], "longitude": loc["lng"]}
            }
    except Exception as e:
        return {"error": f"Geocoding failed: {str(e)}"}


def find_nearby_places(latitude: float, longitude: float, place_type: str = "supermarket", radius_meters: float = 1000.0) -> list[dict]:
    """Finds nearby places of a given type around a latitude/longitude using Google Places API (New).

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        place_type: Type of place to search for (e.g. 'supermarket', 'grocery_store', 'restaurant', 'bakery').
        radius_meters: Search radius in meters (default 1000 meters).

    Returns:
        List of place dictionaries containing place name, formatted address, and location coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
    }
    payload = {
        "includedTypes": [place_type],
        "locationRestriction": {
            "circle": {
                "center": {"latitude": float(latitude), "longitude": float(longitude)},
                "radius": float(radius_meters)
            }
        }
    }
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            res_data = json.loads(resp.read().decode())
            places = res_data.get("places") or []
            results = []
            for p in places[:5]:
                disp_name = p.get("displayName", {}).get("text", "Unknown")
                results.append({
                    "name": disp_name,
                    "address": p.get("formattedAddress"),
                    "location": p.get("location")
                })
            return results
    except Exception as e:
        return [{"error": f"Failed to search nearby places: {str(e)}"}]


def generate_food_image(item_name: str, tool_context: ToolContext = None) -> str:
    """Generates an image for a food or pantry item using gemini-3.1-flash-lite-image in the global region.
    Saves the image as an artifact and uploads it directly to a public Cloud Storage bucket.

    Args:
        item_name: Name of the food or dish to generate an image for (e.g. 'Fresh Organic Milk', 'Pasta Salad').

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage.
    """
    genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    res = genai_client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=f"High quality photo of {item_name}",
    )

    image_bytes = None
    for part in res.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            image_bytes = part.inline_data.data
            break

    if not image_bytes:
        return "Error: Failed to generate image bytes."

    filename = f"{item_name.lower().replace(' ', '_')}_{int(datetime.datetime.now().timestamp())}.jpg"

    if tool_context:
        tool_context.save_artifact(filename=filename, contents=image_bytes, mime_type="image/jpeg")

    BUCKET_NAME = "pantry-app-assets-qwiklabs-gcp-02-2e30ba48e9c5"
    storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/jpeg")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return public_url


def generate_food_video(item_name: str, tool_context: ToolContext = None) -> str:
    """Generates a short video for a food or pantry item using gemini-omni-flash-preview in the global region.
    Saves the video as an artifact and uploads it directly to a public Cloud Storage bucket.

    Args:
        item_name: Name of the food or dish to generate a video for (e.g. 'Steaming Hot Pasta', 'Fresh Organic Milk').

    Returns:
        The public HTTPS URL of the uploaded video in Cloud Storage.
    """
    import base64
    genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    interaction = genai_client.interactions.create(
        model="gemini-omni-flash-preview",
        input=f"Generate a short video showing {item_name}",
        response_format={"type": "video"}
    )

    video_bytes = None
    if interaction.output_video:
        b64_str = getattr(interaction.output_video, "data", None) or interaction.output_video.model_dump().get("data")
        if b64_str:
            if isinstance(b64_str, str):
                video_bytes = base64.b64decode(b64_str)
            elif isinstance(b64_str, bytes):
                video_bytes = b64_str

    if not video_bytes:
        return "Error: Failed to generate video bytes."

    filename = f"{item_name.lower().replace(' ', '_')}_{int(datetime.datetime.now().timestamp())}.mp4"

    if tool_context:
        tool_context.save_artifact(filename=filename, contents=video_bytes, mime_type="video/mp4")

    BUCKET_NAME = "pantry-app-assets-qwiklabs-gcp-02-2e30ba48e9c5"
    storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type="video/mp4")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return public_url


def get_weather(query: str) -> str:
    """Fetches real current weather information for a specified location using the public wttr.in API.

    Args:
        query: A string containing the city name or location (e.g. 'San Francisco', 'New York', 'London').

    Returns:
        A string summarizing the real-time temperature, condition, and humidity.
    """
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if api_key:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={urllib.parse.quote(query)}&appid={api_key}&units=imperial"
    else:
        url = f"https://wttr.in/{urllib.parse.quote(query)}?format=j1"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if api_key:
                temp = data["main"]["temp"]
                desc = data["weather"][0]["description"]
                humidity = data["main"]["humidity"]
                return f"Weather for {query}: {temp}°F, {desc}, Humidity: {humidity}%."
            else:
                curr = data["current_condition"][0]
                temp_f = curr.get("temp_F")
                weather_desc = curr.get("weatherDesc", [{}])[0].get("value")
                humidity = curr.get("humidity")
                return f"Weather for {query}: {temp_f}°F, {weather_desc}, Humidity: {humidity}%."
    except Exception as e:
        return f"Failed to fetch real-time weather for '{query}': {str(e)}"



def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are a Smart Pantry & Weather Assistant designed to manage pantry inventory, "
        "check expiring food items, search online recipes, geocode locations, find nearby "
        "supermarkets, generate food images, generate food videos, run Python code safely in a sandbox, and "
        "remember all user food allergies, dietary restrictions, and preferences across sessions. "
        "CRITICAL SAFETY RULE: You must remember every food allergy or dietary sensitivity the user "
        "mentions (e.g. peanuts, gluten, dairy, shellfish). Always check preloaded memory for user "
        "allergies before suggesting recipes or pantry items, and NEVER recommend any food containing "
        "an ingredient to which the user is allergic."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

code_executor = AgentEngineSandboxCodeExecutor(project=PROJECT_ID, location="us-east1")

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        get_weather,
        get_current_time,
        get_pantry_items,
        add_pantry_item,
        check_expiring_pantry_items,
        search_recipes,
        geocode_address,
        find_nearby_places,
        generate_food_image,
        generate_food_video,
        PreloadMemoryTool(),
    ],
    code_executor=code_executor,
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)


