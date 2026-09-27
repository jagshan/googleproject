# Smart Pantry & Weather Assistant

A conversational AI agent built with Google ADK (Agent Development Kit) that helps users manage their pantry inventory, track expiring food items, generate dish photos and video previews, find nearby supermarkets, and check weather conditions while respecting long-term dietary restrictions and allergies.

![Agent Demo](./demo.gif)

## 🌟 Key Features & Tools Implemented

Based directly on the codebase in `app/` and `agents-cli-manifest.yaml`, the agent implements the following integrated tools and services:

- **📦 Pantry Inventory Management (Google Cloud Firestore)**
  - `get_pantry_items`: Queries the `pantry_items` Firestore collection for active inventory.
  - `add_pantry_item`: Adds new items (name, category, quantity, expiration date) to Firestore.
  - `check_expiring_pantry_items`: Identifies items expiring within 7 days.

- **🎨 Image & Video Generation (Vertex AI & Cloud Storage)**
  - `generate_food_image`: Generates dish photos using Imagen (`gemini-3.1-flash-lite-image`) in the `global` region, saves artifacts, and uploads directly to Google Cloud Storage.
  - `generate_food_video`: Generates short video clips using `gemini-omni-flash-preview` via the Vertex AI Interactions API in the `global` region, saves artifacts, and uploads directly to Google Cloud Storage.

- **🧠 Memory & Allergy Safety (ADK Memory Bank)**
  - `PreloadMemoryTool` & `generate_memories_callback`: Persists user allergies, dietary restrictions, and location preferences across sessions to enforce strict allergy safety before suggesting recipes.

- **📍 Maps & Local Supermarket Discovery (Google Maps API)**
  - `geocode_address`: Converts address strings to latitude/longitude coordinates via Google Maps Geocoding API.
  - `find_nearby_places`: Discovers nearby grocery stores and supermarkets using Google Maps Places API.

- **🌤️ Weather & Time Utilities**
  - `get_weather`: Retrieves real-time weather information (temperature, condition, humidity) for requested locations.
  - `get_current_time`: Returns current time and timezone information.

- **💻 Code Execution Sandbox**
  - `AgentEngineSandboxCodeExecutor`: Executes Python code safely in a Vertex AI Agent Engine Sandbox (`us-east1`).

- **📱 Agent-to-User Interface (A2UI v0.8)**
  - `A2uiSchemaManager`: Generates structured, responsive card layouts (`Card`, `Column`, `Row`, `Text`, `Image`) rendered directly in the user interface.

---

## 🛠️ Infrastructure & Google Cloud Services
- **Agent Framework**: Google Agent Development Kit (ADK) Python SDK
- **Deployment Target**: Vertex AI Agent Engine / Agent Runtime (`us-east1`)
- **Database**: Google Cloud Firestore (`pantry_items` collection)
- **Asset Bucket**: Google Cloud Storage public asset bucket
- **Generative AI Models**:
  - `gemini-flash-latest` (Core Reasoning & Orchestration)
  - `gemini-3.1-flash-lite-image` (Dish Photo Generation)
  - `gemini-omni-flash-preview` (Video Preview Generation)

---

## 🚀 Setup & Local Execution

### Prerequisites
- Python 3.11+
- `uv` package manager (`pip install uv`)
- Google Cloud Platform project with Vertex AI, Firestore, and Google Maps APIs enabled

### Installation & Run Steps

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   ```bash
   export GOOGLE_CLOUD_PROJECT="<your-gcp-project-id>"
   export GOOGLE_MAPS_API_KEY="<your-google-maps-api-key>"
   ```

3. **Run Locally**:
   ```bash
   uv run python main.py
   ```
   The local application server will start listening on port 8080.

4. **Deploy to Vertex AI Agent Platform**:
   ```bash
   agents-cli deploy --project <your-gcp-project-id> --update-env-vars GOOGLE_MAPS_API_KEY=<your-google-maps-api-key>
   ```
