"""
Seed script for ClubOps AI Hierarchical Authorization System.
Creates:
- System Administrator (ADMIN)
- Club of AI with Club Head, SubTeams, SubTeam Leads, SubTeam Volunteers (Case 2)
- Direct Club Volunteers (Case 1)
- Second Club (Club of Robotics) to verify cross-club isolation
"""
from datetime import datetime, timedelta
import app.db.base
from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.core.permissions import seed_permissions
from app.models.user import User, UserRole
from app.models.team import Club, Team, TeamMembership, ClubMembership, TeamRole, ClubRole
from app.models.volunteer import Volunteer, VolunteerStatus
from app.models.event import Event, EventStatus
from app.models.task import Task, TaskStatus, TaskPriority, TaskAssignment


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

        # 8. Seed dedicated Demo Accounts & GDG Demo Club (Feature 2)
        seed_demo_accounts_and_org(db)

        db.commit()
        print("\n=== Hierarchical RBAC Seeding Completed Successfully! ===")

    except Exception as e:
        db.rollback()
        print(f"[-] Error seeding demo data: {e}")
        raise e
    finally:
        db.close()


def seed_demo_accounts_and_org(db):
    """
    Seeds realistic GDG Demo Club organizational hierarchy, demo accounts,
    events, tasks, risks, and audit logs.
    """
    import os
    from app.models.risk import EventRisk
    from app.models.audit_log import AuditLog

    demo_pw = os.getenv("DEMO_PASSWORD", "demo123")
    hashed_demo_pw = get_password_hash(demo_pw)

    # 1. Demo Admin
    admin_email = os.getenv("DEMO_ADMIN_EMAIL", "admin@demo.local")
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin:
        admin = User(
            email=admin_email,
            username="demoadmin",
            full_name="Demo Administrator",
            hashed_password=hashed_demo_pw,
            role=UserRole.ADMIN,
            phone="+1-555-0199",
            bio="System Administrator overseeing university club operations, permissions, and security.",
            is_active=True
        )
        db.add(admin)
        db.flush()
        print(f"[+] Created Demo Admin: {admin.email}")
    else:
        admin.role = UserRole.ADMIN
        admin.hashed_password = hashed_demo_pw

    # 2. GDG Demo Club
    gdg_club = db.query(Club).filter(Club.name == "GDG Demo Club").first()
    if not gdg_club:
        gdg_club = Club(
            name="GDG Demo Club",
            description="Google Developer Groups - Premier campus technology and developer community"
        )
        db.add(gdg_club)
        db.flush()
        print(f"[+] Created Demo Club: {gdg_club.name}")

    # Helper for demo user creation
    def ensure_demo_user(email, username, full_name, role, club_id=None, subteam_id=None, phone=None, bio=None, skills=None, availability=None):
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(
                email=email,
                username=username,
                full_name=full_name,
                hashed_password=hashed_demo_pw,
                role=role,
                club_id=club_id,
                subteam_id=subteam_id,
                phone=phone,
                bio=bio,
                skills=skills,
                availability=availability,
                is_active=True
            )
            db.add(u)
            db.flush()
            print(f"[+] Created Demo User: {full_name} ({email}) [{role.value}]")
        else:
            u.role = role
            u.full_name = full_name
            u.hashed_password = hashed_demo_pw
            if club_id is not None:
                u.club_id = club_id
            if subteam_id is not None:
                u.subteam_id = subteam_id
            if phone:
                u.phone = phone
            if bio:
                u.bio = bio
            if skills:
                u.skills = skills
            if availability:
                u.availability = availability
        return u

    # 3. Demo Club Head
    head_email = os.getenv("DEMO_CLUB_HEAD_EMAIL", "clubhead@demo.local")
    club_head = ensure_demo_user(
        email=head_email,
        username="clubhead",
        full_name="Demo Club Head",
        role=UserRole.CLUB_HEAD,
        club_id=gdg_club.id,
        phone="+1-555-0101",
        bio="Club Head directing strategy, operations, and cross-team execution for GDG Demo Club.",
        skills="Leadership, Event Operations, Community Management, Public Speaking",
        availability="WEEKDAYS,WEEKENDS"
    )

    # Assign Club Head membership
    cm = db.query(ClubMembership).filter(
        ClubMembership.club_id == gdg_club.id,
        ClubMembership.user_id == club_head.id
    ).first()
    if not cm:
        db.add(ClubMembership(club_id=gdg_club.id, user_id=club_head.id, role=ClubRole.CLUB_HEAD))

    # 4. Demo SubTeams
    # AI/ML Team
    ai_team = db.query(Team).filter(Team.name == "AI/ML Team", Team.club_id == gdg_club.id).first()
    if not ai_team:
        ai_team = Team(
            club_id=gdg_club.id,
            name="AI/ML Team",
            description="Machine learning research, generative AI agents, and computer vision workshops"
        )
        db.add(ai_team)
        db.flush()

    # Web Team
    web_team = db.query(Team).filter(Team.name == "Web Team", Team.club_id == gdg_club.id).first()
    if not web_team:
        web_team = Team(
            club_id=gdg_club.id,
            name="Web Team",
            description="Modern web development, fullstack portals, cloud deployments, and UI/UX design"
        )
        db.add(web_team)
        db.flush()

    # 5. Demo SubTeam Leads
    lead_email = os.getenv("DEMO_SUBTEAM_LEAD_EMAIL", "teamlead@demo.local")
    ai_lead = ensure_demo_user(
        email=lead_email,
        username="teamlead",
        full_name="Demo AI Lead",
        role=UserRole.SUBTEAM_LEAD,
        club_id=gdg_club.id,
        subteam_id=ai_team.id,
        phone="+1-555-0102",
        bio="AI/ML SubTeam Lead coordinating workshop curriculum, agentic workflows, and volunteer tasks.",
        skills="Python, PyTorch, LangChain, TensorFlow, Agentic AI",
        availability="WEEKDAYS"
    )
    ai_team.lead_id = ai_lead.id

    # Web Lead
    web_lead = ensure_demo_user(
        email="weblead@demo.local",
        username="weblead",
        full_name="Demo Web Lead",
        role=UserRole.SUBTEAM_LEAD,
        club_id=gdg_club.id,
        subteam_id=web_team.id,
        phone="+1-555-0103",
        bio="Web SubTeam Lead architecting club digital applications and cloud infrastructure.",
        skills="React, TypeScript, Next.js, FastAPI, Cloud Architecture",
        availability="WEEKDAYS,WEEKENDS"
    )
    web_team.lead_id = web_lead.id

    # Memberships for leads
    for lead_u, team_obj in [(ai_lead, ai_team), (web_lead, web_team)]:
        tm = db.query(TeamMembership).filter(TeamMembership.team_id == team_obj.id, TeamMembership.user_id == lead_u.id).first()
        if not tm:
            db.add(TeamMembership(team_id=team_obj.id, user_id=lead_u.id, role=TeamRole.SUBTEAM_LEAD))

    # 6. Demo Volunteers
    vol_email = os.getenv("DEMO_VOLUNTEER_EMAIL", "volunteer@demo.local")
    vol1 = ensure_demo_user(
        email=vol_email,
        username="volunteer1",
        full_name="Demo Volunteer 1",
        role=UserRole.VOLUNTEER,
        club_id=gdg_club.id,
        subteam_id=ai_team.id,
        phone="+1-555-0104",
        bio="Passionate AI enthusiast contributing to hands-on workshop notebooks and model demonstrations.",
        skills="Python, AI/ML, PyTorch, LangChain, Git",
        availability="WEEKDAYS,WEEKENDS"
    )

    vol2 = ensure_demo_user(
        email="volunteer2@demo.local",
        username="volunteer2",
        full_name="Demo Volunteer 2",
        role=UserRole.VOLUNTEER,
        club_id=gdg_club.id,
        subteam_id=web_team.id,
        phone="+1-555-0105",
        bio="Frontend and UX builder creating responsive portals and event registration experiences.",
        skills="React, TypeScript, TailwindCSS, Node.js",
        availability="WEEKENDS"
    )

    vol3 = ensure_demo_user(
        email="volunteer3@demo.local",
        username="volunteer3",
        full_name="Demo Volunteer 3",
        role=UserRole.VOLUNTEER,
        club_id=gdg_club.id,
        subteam_id=None,  # Direct club volunteer
        phone="+1-555-0106",
        bio="Core operations volunteer assisting with stage management, catering, and venue logistics.",
        skills="Event Operations, Venue Logistics, Budget Tracking, Communication",
        availability="FLEXIBLE"
    )

    # Team memberships for volunteers
    for v_u, t_obj in [(vol1, ai_team), (vol2, web_team)]:
        tm = db.query(TeamMembership).filter(TeamMembership.team_id == t_obj.id, TeamMembership.user_id == v_u.id).first()
        if not tm:
            db.add(TeamMembership(team_id=t_obj.id, user_id=v_u.id, role=TeamRole.VOLUNTEER))

    # Volunteer profiles
    vol_profiles = [
        (vol1, gdg_club.id, ai_team.id, "Python, AI/ML, PyTorch, LangChain, Git", "WEEKDAYS,WEEKENDS", 15),
        (vol2, gdg_club.id, web_team.id, "React, TypeScript, TailwindCSS, Node.js", "WEEKENDS", 12),
        (vol3, gdg_club.id, None, "Event Operations, Venue Logistics, Budget Tracking, Communication", "FLEXIBLE", 10),
    ]
    created_vols = {}
    for user_obj, c_id, s_id, v_skills, v_avail, max_cap in vol_profiles:
        vp = db.query(Volunteer).filter(Volunteer.user_id == user_obj.id).first()
        if not vp:
            vp = Volunteer(
                user_id=user_obj.id,
                club_id=c_id,
                subteam_id=s_id,
                skills=v_skills,
                availability=v_avail,
                max_capacity=max_cap,
                status=VolunteerStatus.ACTIVE
            )
            db.add(vp)
            db.flush()
        else:
            vp.club_id = c_id
            vp.subteam_id = s_id
            vp.skills = v_skills
            vp.availability = v_avail
        created_vols[user_obj.id] = vp

    # 7. Demo Events
    # Upcoming: GDG DevFest 2026
    event_upcoming = db.query(Event).filter(Event.title == "GDG DevFest 2026", Event.club_id == gdg_club.id).first()
    if not event_upcoming:
        event_upcoming = Event(
            title="GDG DevFest 2026",
            description="Flagship annual campus developer conference focusing on GenAI, Cloud Computing, and Modern Web.",
            date=datetime.utcnow() + timedelta(days=14),
            venue="Main Tech Auditorium & Google Hall",
            budget=8000.0,
            budget_spent=2400.0,
            expected_attendance=350,
            status=EventStatus.PUBLISHED,
            created_by=club_head.id,
            club_id=gdg_club.id
        )
        db.add(event_upcoming)
        db.flush()
        print(f"[+] Created Event: {event_upcoming.title}")

    # Past / Completed Event: GDG AI & Cloud Bootcamp
    event_past = db.query(Event).filter(Event.title == "GDG AI & Cloud Bootcamp", Event.club_id == gdg_club.id).first()
    if not event_past:
        event_past = Event(
            title="GDG AI & Cloud Bootcamp",
            description="Hands-on intensive bootcamp training members on machine learning and cloud microservices.",
            date=datetime.utcnow() - timedelta(days=25),
            venue="Computer Science Lab 3",
            budget=3000.0,
            budget_spent=2850.0,
            expected_attendance=120,
            status=EventStatus.COMPLETED,
            created_by=club_head.id,
            club_id=gdg_club.id
        )
        db.add(event_past)
        db.flush()

    # 8. Demo Tasks for GDG DevFest 2026
    vp1 = created_vols.get(vol1.id)
    vp2 = created_vols.get(vol2.id)

    task_definitions = [
        ("Prepare AI Workshop Colab Notebooks", "Create end-to-end reproducible Jupyter notebooks demonstrating fine-tuning and retrieval.", TaskStatus.IN_PROGRESS, TaskPriority.HIGH, datetime.utcnow() + timedelta(days=3), ai_team.id, event_upcoming.id, [vp1]),
        ("Setup Stage Audio-Visual Equipment", "Coordinate with auditorium audio tech team for wireless microphones and backup HDMI switchers.", TaskStatus.BLOCKED, TaskPriority.URGENT, datetime.utcnow() + timedelta(days=7), ai_team.id, event_upcoming.id, [vp1]),
        ("Keynote Speaker Introduction Slides", "Design keynote intro deck highlighting speaker achievements and session timeline.", TaskStatus.DONE, TaskPriority.MEDIUM, datetime.utcnow() - timedelta(days=2), ai_team.id, event_upcoming.id, [vp1]),
        ("Finalize Catering Vendor Contracts", "Confirm dietary requirements, lunch count, and coffee stations for event morning.", TaskStatus.TODO, TaskPriority.HIGH, datetime.utcnow() - timedelta(days=3), ai_team.id, event_upcoming.id, [vp1]), # OVERDUE!
        ("Deploy Registration & RSVP Portal", "Launch registration web application with QR ticket confirmation email generator.", TaskStatus.IN_PROGRESS, TaskPriority.HIGH, datetime.utcnow() + timedelta(days=5), web_team.id, event_upcoming.id, [vp2]),
        ("Publish Social Media Launch Campaign", "Schedule countdown graphics and announcements across Twitter, LinkedIn, and Instagram.", TaskStatus.DONE, TaskPriority.LOW, datetime.utcnow() - timedelta(days=5), web_team.id, event_upcoming.id, [vp2]),
    ]

    for title, desc, status, priority, due, t_id, ev_id, assignees in task_definitions:
        t = db.query(Task).filter(Task.title == title, Task.event_id == ev_id).first()
        if not t:
            t = Task(
                title=title,
                description=desc,
                status=status,
                priority=priority,
                due_date=due,
                team_id=t_id,
                event_id=ev_id,
                created_by=club_head.id
            )
            db.add(t)
            db.flush()

            for vp in assignees:
                if vp:
                    db.add(TaskAssignment(task_id=t.id, volunteer_id=vp.id))
        else:
            t.status = status
            t.priority = priority
            t.due_date = due

    # 9. Demo Risks
    risk = db.query(EventRisk).filter(EventRisk.event_id == event_upcoming.id).first()
    if not risk:
        risk = EventRisk(
            event_id=event_upcoming.id,
            category="DEPENDENCY",
            severity="HIGH",
            title="Projector HDMI-matrix compatibility in Hall A",
            description="Auditorium HDMI splitter does not handshake properly with macOS 4K 60Hz outputs.",
            suggested_fix="Procure active EDID emulator dongle and test during rehearsal.",
            status="ACTIVE"
        )
        db.add(risk)
        db.flush()

    # 10. Audit Logs
    audit = db.query(AuditLog).filter(AuditLog.entity_type == "club", AuditLog.entity_id == gdg_club.id).first()
    if not audit:
        db.add(AuditLog(
            actor_id=admin.id,
            action="CREATE",
            entity_type="club",
            entity_id=gdg_club.id,
            scope_type="GLOBAL",
            scope_id=gdg_club.id,
            meta_data={"name": gdg_club.name, "note": "Seeded demo club"}
        ))
        db.add(AuditLog(
            actor_id=admin.id,
            action="ASSIGN",
            entity_type="user",
            entity_id=club_head.id,
            scope_type="CLUB",
            scope_id=gdg_club.id,
            meta_data={"role": "CLUB_HEAD", "club_name": gdg_club.name}
        ))

    db.commit()
    print("[+] Seeded demo system successfully!")
    return {
        "admin": admin,
        "club_head": club_head,
        "subteam_lead": ai_lead,
        "volunteer": vol1,
        "club": gdg_club
    }


if __name__ == "__main__":
    seed_demo_data()

