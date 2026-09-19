"""
Seed script for ClubOps AI Hierarchical Authorization System.
Creates:
- System Administrator (ADMIN)
- Club of AI with Club Head, SubTeams, SubTeam Leads, SubTeam Volunteers (Case 2)
- Direct Club Volunteers (Case 1)
- Second Club (Club of Robotics) to verify cross-club isolation
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

        # 1. Create System Administrator
        admin = db.query(User).filter(User.email == "admin@clubops.ai").first()
        if not admin:
            admin = User(
                email="admin@clubops.ai",
                hashed_password=get_password_hash("password123"),
                full_name="System Administrator",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            db.flush()
            print(f"[+] Created Admin: {admin.full_name} ({admin.email})")

        # 2. Create Club 1: Club of AI
        club = db.query(Club).filter(Club.name == "Club of AI").first()
        if not club:
            club = Club(name="Club of AI", description="Premier College AI & Engineering Club")
            db.add(club)
            db.flush()
            print(f"[+] Created Club: {club.name}")

        # Helper to get or create user
        def get_or_create_user(email, full_name, role=UserRole.VOLUNTEER, club_id=None, subteam_id=None):
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    hashed_password=get_password_hash("password123"),
                    full_name=full_name,
                    role=role,
                    club_id=club_id,
                    subteam_id=subteam_id,
                    is_active=True
                )
                db.add(user)
                db.flush()
                print(f"[+] Created User: {full_name} ({email}) [{role.value}]")
            else:
                user.role = role
                if club_id is not None:
                    user.club_id = club_id
                if subteam_id is not None:
                    user.subteam_id = subteam_id
            return user

        # 3. Users for Club of AI
        club_leader = get_or_create_user("leader@clubops.ai", "Priya Sharma (Club Leader)", UserRole.CLUB_HEAD, club_id=club.id)
        rahul_aws = get_or_create_user("rahul@clubops.ai", "Rahul Verma (AWS Lead)", UserRole.SUBTEAM_LEAD, club_id=club.id)
        sneha_ml = get_or_create_user("sneha@clubops.ai", "Sneha Patel (ML Lead)", UserRole.SUBTEAM_LEAD, club_id=club.id)
        arjun_web = get_or_create_user("arjun@clubops.ai", "Arjun Mehta (Web Dev Lead)", UserRole.SUBTEAM_LEAD, club_id=club.id)
        rohan_aws = get_or_create_user("rohan@clubops.ai", "Rohan Roy (AWS Member)", UserRole.VOLUNTEER, club_id=club.id)
        tanvi_ml = get_or_create_user("tanvi@clubops.ai", "Tanvi Gupta (ML Member)", UserRole.VOLUNTEER, club_id=club.id)
        ananya_web = get_or_create_user("ananya@clubops.ai", "Ananya Sen (Web Dev Member)", UserRole.VOLUNTEER, club_id=club.id)
        
        # Case 1 Direct Volunteer (belongs directly to Club, no SubTeam)
        dev_direct = get_or_create_user("dev@clubops.ai", "Dev Patel (Direct Club Volunteer)", UserRole.VOLUNTEER, club_id=club.id, subteam_id=None)

        # Assign Club Leader membership
        existing_lead = db.query(ClubMembership).filter(
            ClubMembership.club_id == club.id,
            ClubMembership.user_id == club_leader.id
        ).first()
        if not existing_lead:
            db.add(ClubMembership(club_id=club.id, user_id=club_leader.id, role=ClubRole.CLUB_HEAD))
            print(f"[+] Assigned {club_leader.full_name} as CLUB_HEAD")

        # 4. Create SubTeams (Case 2 Structure)
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
            team = db.query(Team).filter(Team.name == team_name, Team.club_id == club.id).first()
            lead_id = leader_user.id if leader_user else None
            if not team:
                team = Team(club_id=club.id, name=team_name, description=desc, lead_id=lead_id)
                db.add(team)
                db.flush()
                print(f"[+] Created Team: {team.name}")
            else:
                team.lead_id = lead_id

            created_teams[team_name] = team

            if leader_user:
                leader_user.subteam_id = team.id
                existing_m = db.query(TeamMembership).filter(
                    TeamMembership.team_id == team.id,
                    TeamMembership.user_id == leader_user.id
                ).first()
                if not existing_m:
                    db.add(TeamMembership(team_id=team.id, user_id=leader_user.id, role=TeamRole.SUBTEAM_LEAD))

            for m_user in member_users:
                m_user.subteam_id = team.id
                existing_m = db.query(TeamMembership).filter(
                    TeamMembership.team_id == team.id,
                    TeamMembership.user_id == m_user.id
                ).first()
                if not existing_m:
                    db.add(TeamMembership(team_id=team.id, user_id=m_user.id, role=TeamRole.VOLUNTEER))

        # 5. Volunteer Profiles
        all_vol_users = [
            (rohan_aws, created_teams["AWS Team"].id),
            (tanvi_ml, created_teams["ML Team"].id),
            (ananya_web, created_teams["Web Development Team"].id),
            (dev_direct, None),  # Case 1 direct volunteer
        ]
        for v_user, s_id in all_vol_users:
            vol = db.query(Volunteer).filter(Volunteer.user_id == v_user.id).first()
            if not vol:
                vol = Volunteer(
                    user_id=v_user.id,
                    club_id=club.id,
                    subteam_id=s_id,
                    skills="Python, AI, Cloud" if s_id else "Event Operations, Coordination",
                    availability="WEEKDAYS,WEEKENDS",
                    max_capacity=15,
                    status=VolunteerStatus.ACTIVE
                )
                db.add(vol)
                db.flush()
                print(f"[+] Created Volunteer profile for: {v_user.full_name} (SubTeam: {s_id})")
            else:
                vol.club_id = club.id
                vol.subteam_id = s_id

        # 6. Event for Club of AI
        event = db.query(Event).filter(Event.title == "AI Genesis Hackathon 2026", Event.club_id == club.id).first()
        if not event:
            event = Event(
                title="AI Genesis Hackathon 2026",
                description="Annual college hackathon exploring generative AI, agents, and cloud computing.",
                date=datetime.utcnow() + timedelta(days=21),
                venue="Main Tech Auditorium & Virtual",
                budget=5000.0,
                status=EventStatus.PUBLISHED,
                created_by=club_leader.id,
                club_id=club.id
            )
            db.add(event)
            db.flush()
            print(f"[+] Created Event: {event.title} in {club.name}")

        # 7. Create Second Club: Club of Robotics (To test multi-club tenant isolation)
        robotics_club = db.query(Club).filter(Club.name == "Club of Robotics").first()
        if not robotics_club:
            robotics_club = Club(name="Club of Robotics", description="Hardware, microcontrollers, and autonomous robotics")
            db.add(robotics_club)
            db.flush()
            print(f"[+] Created Second Club: {robotics_club.name}")

        robotics_lead = get_or_create_user("robotics_head@clubops.ai", "Kunal Shah (Robotics Head)", UserRole.CLUB_HEAD, club_id=robotics_club.id)
        existing_cm = db.query(ClubMembership).filter(ClubMembership.club_id == robotics_club.id, ClubMembership.user_id == robotics_lead.id).first()
        if not existing_cm:
            db.add(ClubMembership(club_id=robotics_club.id, user_id=robotics_lead.id, role=ClubRole.CLUB_HEAD))

        db.commit()
        print("\n=== Hierarchical RBAC Seeding Completed Successfully! ===")

    except Exception as e:
        db.rollback()
        print(f"[-] Error seeding demo data: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
