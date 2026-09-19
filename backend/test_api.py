import urllib.request
import urllib.parse
import json

BASE_URL = "http://127.0.0.1:8000/api"

def run_tests():
    print("1. Testing Auth Login...")
    login_data = urllib.parse.urlencode({"username": "admin@clubops.ai", "password": "admin123"}).encode()
    req = urllib.request.Request(f"{BASE_URL}/auth/login", data=login_data)
    with urllib.request.urlopen(req) as res:
        login_res = json.loads(res.read().decode())
        token = login_res["access_token"]
        print("  -> Login OK, token received!")

    headers = {"Authorization": f"Bearer {token}"}

    def get(endpoint):
        req = urllib.request.Request(f"{BASE_URL}{endpoint}", headers=headers)
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode())

    print("2. Testing /auth/me...")
    me = get("/auth/me")
    print(f"  -> Me: {me['full_name']} ({me['email']})")

    print("3. Testing /auth/users...")
    users = get("/auth/users")
    print(f"  -> Users count: {len(users)}")

    print("4. Testing /events...")
    events = get("/events")
    print(f"  -> Events count: {len(events)}")
    first_event_id = events[0]["id"] if events else None

    print("5. Testing /volunteers...")
    volunteers = get("/volunteers")
    print(f"  -> Volunteers count: {len(volunteers)}")
    first_vol_id = volunteers[0]["id"] if volunteers else None

    print("6. Testing /tasks...")
    tasks = get("/tasks")
    print(f"  -> Tasks count: {len(tasks)}")

    print("7. Testing /announcements...")
    announcements = get("/announcements")
    print(f"  -> Announcements count: {len(announcements)}")

    if first_event_id:
        print(f"8. Testing /events/{first_event_id}...")
        ev = get(f"/events/{first_event_id}")
        print(f"  -> Event details: {ev['title']}")

        print(f"9. Testing /tasks?event_id={first_event_id}...")
        ev_tasks = get(f"/tasks?event_id={first_event_id}")
        print(f"  -> Event tasks count: {len(ev_tasks)}")

    if first_vol_id:
        print(f"10. Testing /volunteers/{first_vol_id}...")
        vol = get(f"/volunteers/{first_vol_id}")
        print(f"  -> Volunteer: {vol['user']['full_name']}")

        print(f"11. Testing /volunteers/{first_vol_id}/tasks...")
        vol_tasks = get(f"/volunteers/{first_vol_id}/tasks")
        print(f"  -> Volunteer tasks count: {len(vol_tasks)}")

    print("ALL API ENDPOINTS ARE ASSOCIATED AND WORKING PERFECTLY!")

if __name__ == "__main__":
    run_tests()
