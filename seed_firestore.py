import google.auth
from google.cloud import firestore

# Hardcode project ID as a string (never read from google.auth.default() or GOOGLE_CLOUD_PROJECT)
PROJECT_ID = "qwiklabs-gcp-02-2e30ba48e9c5"

credentials, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
db = firestore.Client(project=PROJECT_ID, credentials=credentials)

pantry_items = [
    {
        "id": "item-001",
        "name": "Extra Virgin Olive Oil",
        "category": "Oils & Condiments",
        "quantity": 2,
        "expiration_date": "2027-05-15",
    },
    {
        "id": "item-002",
        "name": "Organic Penne Pasta",
        "category": "Grains & Pasta",
        "quantity": 5,
        "expiration_date": "2027-01-20",
    },
    {
        "id": "item-003",
        "name": "San Marzano Tomato Sauce",
        "category": "Canned Goods",
        "quantity": 4,
        "expiration_date": "2026-11-30",
    },
    {
        "id": "item-004",
        "name": "Wildflower Honey",
        "category": "Sweeteners",
        "quantity": 1,
        "expiration_date": "2028-09-10",
    },
    {
        "id": "item-005",
        "name": "Rolled Oats",
        "category": "Grains & Pasta",
        "quantity": 3,
        "expiration_date": "2026-12-15",
    },
]


def seed():
    collection_ref = db.collection("pantry_items")
    for item in pantry_items:
        doc_ref = collection_ref.document(item["id"])
        doc_ref.set(item)
        print(f"Seeded item: {item['name']} ({item['id']})")
    print("Firestore seeding completed successfully!")


if __name__ == "__main__":
    seed()
