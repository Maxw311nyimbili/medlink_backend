from app.db.session import SessionLocal
from app.db.models import User
from datetime import datetime

db = SessionLocal()

# Create test user
test_user = User(
    id="test-firebase-uid-123",
    email="test@medlink.com",
    display_name="Test User",
    photo_url="https://example.com/photo.jpg",
    preferred_language="en",
    onboarding_completed=False
)

db.add(test_user)
db.commit()
db.refresh(test_user)

print(f" Created user: {test_user.email}")
print(f"   ID: {test_user.id}")
print(f"   Created at: {test_user.created_at}")

# Query back
user = db.query(User).filter(User.email == "test@medlink.com").first()
print(f"\n Retrieved user: {user.display_name}")

# Clean up
db.delete(user)
db.commit()
print(f"\n Deleted test user")

db.close()