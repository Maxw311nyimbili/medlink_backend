from app.db.session import SessionLocal
from app.db.models import Announcement, ConsentVersion, User
from datetime import datetime

db = SessionLocal()

print("Seeding test data...")

# Create test user (for testing with mock token)
test_user = db.query(User).filter(User.id == "test-user-123").first()
if not test_user:
    test_user = User(
        id="test-user-123",
        email="test@medlink.com",
        display_name="Test User",
        preferred_language="en"
    )
    db.add(test_user)
    print("✓ Created test user")
else:
    print("✓ Test user already exists")

# Create announcements
ann1 = db.query(Announcement).filter(Announcement.title == "Welcome to MedLink!").first()
if not ann1:
    ann1 = Announcement(
        title="Welcome to MedLink!",
        content="Your trusted source for medical information. Always consult healthcare professionals for medical advice.",
        language="en",
        priority=10,
        is_active=True
    )
    db.add(ann1)
    print("✓ Created announcement 1")
else:
    print("✓ Announcement 1 already exists")

ann2 = db.query(Announcement).filter(Announcement.title == "New Features Available").first()
if not ann2:
    ann2 = Announcement(
        title="New Features Available",
        content="Check out our updated forum and chat features. Share experiences and ask questions safely.",
        language="en",
        priority=5,
        is_active=True
    )
    db.add(ann2)
    print("✓ Created announcement 2")
else:
    print("✓ Announcement 2 already exists")

# Create consent document
consent = db.query(ConsentVersion).filter(ConsentVersion.version == "1.0").first()
if not consent:
    consent = ConsentVersion(
        version="1.0",
        content='''# Terms of Service and Privacy Policy

By using MedLink, you agree to the following:

1. **Medical Disclaimer**: Information provided is for educational purposes only and does not constitute medical advice.
2. **Privacy**: We collect minimal data and never share personal health information.
3. **User Content**: Forum posts are moderated and may be removed if inappropriate.
4. **Accuracy**: While we strive for accuracy, always verify medical information with healthcare professionals.

Last updated: January 2025''',
        language="en",
        is_active=True
    )
    db.add(consent)
    print("✓ Created consent document v1.0")
else:
    print("✓ Consent v1.0 already exists")

db.commit()
db.close()

print("\n Database seeded successfully!")
