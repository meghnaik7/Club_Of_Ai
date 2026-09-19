"""
Seed script for ClubOps AI Hierarchical Authorization System.
Creates the Club, sub-teams, Club Leader, Team Leaders, and Team Members.
"""
from datetime import datetime, timedelta
from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.core.permissions import seed_permissions
from app.models.user import User, UserRole
from app.models.team import Club, Team, TeamMembership, ClubMembership, TeamRole, ClubRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.event import Event, EventStatus
from app.models.task import Task, TaskStatus, TaskPriority


def seed_demo_data():
    db = SessionLocal()
    try:
        # Seed permissions first
        seed_permissions(db)

        # 1. Create Club
        club = db.query(Club).first()
        if not club:
            club = Club(name="Club of AI", description="Premier College AI & Engineering Club")
            db.add(club)
            db.flush()
            print(f"[+] Created Club: {club.name}")

        # Helper to get or create user
        def get_or_create_user(email, full_name, role_name="VOLUNTEER"):
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    hashed_password=get_password_hash("password123"),
                    full_name=full_name,
                    role=role_name,
                    is_active=True
                )
                db.add(user)
                db.flush()
                print(f"[+] Created User: {full_name} ({email})")
            return user

        # 2. Users
        club_leader = get_or_create_user("leader@clubops.ai", "Priya Sharma (Club Leader)")
        rahul_aws = get_or_create_user("rahul@clubops.ai", "Rahul Verma (AWS Lead)")
        sneha_ml = get_or_create_user("sneha@clubops.ai", "Sneha Patel (ML Lead)")
        arjun_web = get_or_create_user("arjun@clubops.ai", "Arjun Mehta (Web Dev Lead)")
        rohan_aws = get_or_create_user("rohan@clubops.ai", "Rohan Roy (AWS Member)")
        tanvi_ml = get_or_create_user("tanvi@clubops.ai", "Tanvi Gupta (ML Member)")
        ananya_web = get_or_create_user("ananya@clubops.ai", "Ananya Sen (Web Dev Member)")

        # Assign Club Leader
        existing_lead = db.query(ClubMembership).filter(
            ClubMembership.club_id == club.id,
            ClubMembership.user_id == club_leader.id
        ).first()
        if not existing_lead:
            db.add(ClubMembership(club_id=club.id, user_id=club_leader.id, role=ClubRole.CLUB_LEADER))
            print(f"[+] Assigned {club_leader.full_name} as CLUB_LEADER")

        # 3. Create Teams
        team_defs = [
            ("AWS Team", "Cloud architecture, deployment, infrastructure & security", rahul_aws, [rohan_aws]),
            ("ML Team", "Machine learning research, model development, computer vision & NLP", sneha_ml, [tanvi_ml]),
            ("Web Development Team", "Frontend, backend, APIs, and portals", arjun_web, [ananya_web]),
            ("Design Team", "UI/UX, graphics, brand identity, and social assets", None, []),
            ("Sponsorship Team", "Corporate partnerships, funding, grants and swag", None, []),
            ("Marketing Team", "Social media campaigns, outreach and announcements", None, []),
            ("Logistics Team", "Venue, audiovisual, equipment and hospitality", None, []),
            ("Content Team", "Technical writing, newsletters, documentation and blogs", None, []),
        ]

        created_teams = {}
        for team_name, desc, leader_user, member_users in team_defs:
            team = db.query(Team).filter(Team.name == team_name).first()
            if not team:
                team = Team(club_id=club.id, name=team_name, description=desc)
                db.add(team)
                db.flush()
                print(f"[+] Created Team: {team.name}")
            created_teams[team_name] = team

            # Assign Team Leader
            if leader_user:
                existing_m = db.query(TeamMembership).filter(
                    TeamMembership.team_id == team.id,
                    TeamMembership.user_id == leader_user.id
                ).first()
                if not existing_m:
                    db.add(TeamMembership(team_id=team.id, user_id=leader_user.id, role=TeamRole.TEAM_LEADER))
                    print(f"    - Assigned Leader: {leader_user.full_name}")

            # Assign Team Members
            for m_user in member_users:
                existing_m = db.query(TeamMembership).filter(
                    TeamMembership.team_id == team.id,
                    TeamMembership.user_id == m_user.id
                ).first()
                if not existing_m:
                    db.add(TeamMembership(team_id=team.id, user_id=m_user.id, role=TeamRole.TEAM_MEMBER))
                    print(f"    - Assigned Member: {m_user.full_name}")

        # 4. Create Volunteer Profiles
        for u, skills in [
            (rohan_aws, "AWS, Docker, Terraform, CloudWatch"),
            (tanvi_ml, "PyTorch, HuggingFace, Scikit-learn, LangChain"),
            (ananya_web, "React, TypeScript, FastAPI, Tailwind/CSS"),
            (rahul_aws, "Cloud Architecture, DevOps, Security"),
            (sneha_ml, "LLMs, Model Evaluation, Python"),
            (arjun_web, "Fullstack Web, Next.js, Node.js")
        ]:
            v = db.query(Volunteer).filter(Volunteer.user_id == u.id).first()
            if not v:
                db.add(Volunteer(user_id=u.id, skills=skills, availability="Weekdays & Weekends", status=VolunteerStatus.ACTIVE))
                print(f"[+] Created Volunteer profile for {u.full_name}")

        # 5. Create Flagship Event
        event = db.query(Event).filter(Event.title == "AI Summit & Hackathon 2026").first()
        if not event:
            event = Event(
                title="AI Summit & Hackathon 2026",
                description="Annual flagship AI conference and 24-hour agentic hackathon.",
                date=datetime.utcnow() + timedelta(days=21),
                venue="Main Campus Auditorium & Tech Hub",
                budget=15000.0,
                expected_attendance=250,
                status=EventStatus.PUBLISHED,
                created_by=club_leader.id
            )
            db.add(event)
            db.flush()
            print(f"[+] Created Event: {event.title}")

        # 6. Sample Tasks scoped to Teams
        sample_tasks = [
            ("Configure AWS ECS Cluster & VPC", "Setup private subnets, load balancer and monitoring", created_teams["AWS Team"].id, rahul_aws.id),
            ("Deploy S3 Storage & CloudFront CDN", "Asset storage for summit recordings and datasets", created_teams["AWS Team"].id, rahul_aws.id),
            ("Fine-tune Hackathon Evaluation LLM", "Prompt engineering and judge scoring rubric", created_teams["ML Team"].id, sneha_ml.id),
            ("Build Hackathon Leaderboard API", "Real-time submission scoring and ranking endpoint", created_teams["Web Development Team"].id, arjun_web.id),
            ("Design Event Badges and Swag", "T-shirt designs, stickers, and stage banner", created_teams["Design Team"].id, club_leader.id),
        ]

        for title, desc, t_id, creator_id in sample_tasks:
            task = db.query(Task).filter(Task.title == title).first()
            if not task:
                db.add(Task(
                    event_id=event.id,
                    team_id=t_id,
                    created_by=creator_id,
                    title=title,
                    description=desc,
                    status=TaskStatus.TODO,
                    priority=TaskPriority.HIGH
                ))
                print(f"[+] Created Task: {title}")

        db.commit()
        print("\n=== Demo seeding completed successfully! ===")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
