import sys
from pathlib import Path
from datetime import datetime, timedelta

# Ensure backend path is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal, init_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.event import Event, EventStatus
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.task import Task, TaskStatus, TaskPriority, TaskPhase, TaskAssignment
from app.models.announcement import Announcement
import json

def seed():
    init_db()
    db = SessionLocal()
    try:
        # Check if users already exist
        if db.query(User).count() > 0:
            print("Database already has data. Skipping seed.")
            return

        print("Seeding initial data...")
        # 1. Users
        admin_user = User(
            email="admin@clubops.ai",
            full_name="Alex Rivera",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True
        )
        lead_user = User(
            email="priya@clubops.ai",
            full_name="Priya Sharma",
            hashed_password=get_password_hash("password123"),
            role=UserRole.CLUB_MANAGER,
            is_active=True
        )
        vol_user1 = User(
            email="rahul@clubops.ai",
            full_name="Rahul Verma",
            hashed_password=get_password_hash("password123"),
            role=UserRole.VOLUNTEER,
            is_active=True
        )
        vol_user2 = User(
            email="ananya@clubops.ai",
            full_name="Ananya Iyer",
            hashed_password=get_password_hash("password123"),
            role=UserRole.VOLUNTEER,
            is_active=True
        )
        db.add_all([admin_user, lead_user, vol_user1, vol_user2])
        db.commit()

        # 2. Volunteers
        vol1 = Volunteer(
            user_id=vol_user1.id,
            skills="Audio/Visual, Stage Setup, Logistics, Photography",
            availability="Weekends, Friday afternoons",
            status=VolunteerStatus.ACTIVE
        )
        vol2 = Volunteer(
            user_id=vol_user2.id,
            skills="Social Media Marketing, Graphic Design, Content Writing",
            availability="All weekdays after 4 PM",
            status=VolunteerStatus.ACTIVE
        )
        vol3 = Volunteer(
            user_id=lead_user.id,
            skills="Event Planning, Budgeting, Sponsorships, Leadership",
            availability="Full time",
            status=VolunteerStatus.ACTIVE
        )
        db.add_all([vol1, vol2, vol3])
        db.commit()

        # 3. Events
        now = datetime.utcnow()
        event1 = Event(
            title="AI Odyssey Hackathon 2026",
            description="A 36-hour flagship hackathon bringing together over 300 student developers to build AI solutions for real-world impact.",
            date=now + timedelta(days=14),
            venue="Auditorium Hall A & Innovation Lab",
            budget=50000.0,
            budget_spent=18500.0,
            expected_attendance=350,
            status=EventStatus.PUBLISHED,
            created_by=admin_user.id
        )
        event2 = Event(
            title="Autonomous Robotics Workshop",
            description="Hands-on workshop covering ROS2, SLAM algorithms, and edge AI vision for autonomous wheeled robots.",
            date=now + timedelta(days=28),
            venue="Robotics Lab 3",
            budget=20000.0,
            budget_spent=4200.0,
            expected_attendance=80,
            status=EventStatus.PUBLISHED,
            created_by=lead_user.id
        )
        db.add_all([event1, event2])
        db.commit()

        # 4. Tasks for Event 1
        t1 = Task(
            event_id=event1.id,
            title="Finalize Keynote Speaker & Jury Panel",
            description="Confirm travel logistics and honorarium details for AI researchers from Google & IIT.",
            status=TaskStatus.DONE,
            priority=TaskPriority.HIGH,
            phase=TaskPhase.PLANNING,
            due_date=now - timedelta(days=2)
        )
        t2 = Task(
            event_id=event1.id,
            title="Procure High-Speed WiFi & Backup Routers",
            description="Coordinate with IT dept to provide dedicated 1 Gbps lease line for 350 hackathon participants.",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.URGENT,
            phase=TaskPhase.EXECUTION,
            due_date=now + timedelta(days=4)
        )
        t3 = Task(
            event_id=event1.id,
            title="Design and Print Badges & Swag Kits",
            description="Coordinate T-shirts, stickers, notebooks, and lanyard printing with vendor.",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            phase=TaskPhase.EXECUTION,
            due_date=now + timedelta(days=7)
        )
        t4 = Task(
            event_id=event1.id,
            title="Organize Catering & Midnight Snacks",
            description="Arrange 4 meals and coffee stations for the 36-hour hackathon schedule.",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            phase=TaskPhase.EXECUTION,
            due_date=now + timedelta(days=10)
        )
        db.add_all([t1, t2, t3, t4])
        db.commit()

        # Assign volunteers to tasks
        db.add(TaskAssignment(task_id=t2.id, volunteer_id=vol1.id))
        db.add(TaskAssignment(task_id=t3.id, volunteer_id=vol2.id))
        db.add(TaskAssignment(task_id=t4.id, volunteer_id=vol1.id))
        db.commit()

        # 5. Announcements
        a1 = Announcement(
            title="Registrations Live: AI Odyssey Hackathon 2026! 🚀",
            content="Get ready for the biggest AI hackathon of the semester! 36 hours of non-stop coding, mentorship from top researchers, and over ₹1,00,00,000 in prizes. Register your team today at clubops.ai/hackathon.",
            target_audience="All CS & Engineering Students",
            event_id=event1.id,
            created_by=admin_user.id,
            status="PUBLISHED",
            variants=json.dumps({
                "whatsapp": "🚀 *AI Odyssey Hackathon 2026 Registrations Open!* \n36h coding marathon, ₹1L+ cash prizes, free food & swag! \nRegister now: clubops.ai/hackathon",
                "email": {
                    "subject": "Register Now: AI Odyssey Hackathon 2026",
                    "body": "Hi students,\n\nWe are excited to announce AI Odyssey Hackathon 2026! Join us for an exhilarating 36-hour hackathon with industry mentors.\n\nBest,\nClubOps Team"
                },
                "instagram": {
                    "caption": "⚡ 36 Hours. Endless Innovation. Are you ready for AI Odyssey 2026? Link in bio to register!",
                    "hashtags": ["#AI", "#Hackathon2026", "#ClubOps", "#StudentDevelopers", "#Coding"]
                }
            })
        )
        db.add(a1)
        db.commit()

        print("Seeding completed successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
