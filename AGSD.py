import argparse
import json
import os
import sys
import uuid
import time
try:
    import requests
except Exception:
    requests = None

# -------------------------
# 1. CONFIGURATION / CLI
# -------------------------
parser = argparse.ArgumentParser(description="Create Jira Epics/Stories/Subtasks and sprints (or dry-run)")
parser.add_argument("--domain", help="JIRA domain, e.g. your-org.atlassian.net")
parser.add_argument("--email", help="JIRA account email")
parser.add_argument("--token", help="JIRA API token")
parser.add_argument("--board", help="Board ID (integer)")
parser.add_argument("--project", help="Project key (e.g. SCRUM)", default="SCRUM")
parser.add_argument("--dry-run", help="Run without calling Jira (simulate)", action="store_true")
args = parser.parse_args()

JIRA_DOMAIN = args.domain or os.getenv("JIRA_DOMAIN")
JIRA_EMAIL = args.email or os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = args.token or os.getenv("JIRA_API_TOKEN")
BOARD_ID = int(args.board) if args.board else (int(os.getenv("BOARD_ID")) if os.getenv("BOARD_ID") else None)
PROJECT_KEY = args.project or os.getenv("PROJECT_KEY") or "SCRUM"
DRY_RUN = args.dry_run

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

if not DRY_RUN and not (JIRA_DOMAIN and JIRA_EMAIL and JIRA_API_TOKEN):
    print("Missing Jira configuration. Provide --domain,--email,--token or run with --dry-run to simulate.")
    sys.exit(1)

# Prepare a requests.Session or a MockSession for dry-run
class MockResponse:
    def __init__(self, status_code=201, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

class MockSession:
    def __init__(self):
        self._epic_counter = 1
        self._issue_counter = 1

    def post(self, url, json=None, headers=None):
        # Simulate create issue and sprint endpoints
        payload = {}
        if "/rest/api/3/issue" in url:
            key = f"DEMO-{self._issue_counter}"
            self._issue_counter += 1
            payload = {"key": key, "id": str(uuid.uuid4())}
            return MockResponse(201, payload)
        if "/rest/agile/1.0/sprint" in url:
            payload = {"id": self._epic_counter}
            self._epic_counter += 1
            return MockResponse(201, payload)
        # default
        return MockResponse(200, {})

    def get(self, url, params=None):
        return MockResponse(200, {})

    def put(self, url, json=None, headers=None):
        return MockResponse(204, {})

if DRY_RUN:
    session = MockSession()
    print("Running in dry-run mode: no Jira API calls will be performed.")
else:
    if requests is None:
        print("The 'requests' library is required when not running in dry-run mode. Install with: pip install requests")
        sys.exit(1)
    session = requests.Session()
    session.auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    session.headers.update(HEADERS)


# -------------------------
# 2. CREATE EPIC
# -------------------------
def create_epic(summary, description):
    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue"

    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Epic"},
            # Epic Name custom field may vary by instance; common keys include customfield_10014/10011
        }
    }

    r = session.post(url, json=payload)
    if r is None or getattr(r, 'status_code', None) not in (200, 201):
        print(f"Failed to create epic '{summary}':", getattr(r, 'status_code', None), getattr(r, 'text', ''))
        return None
    return r.json()


# -------------------------
# 3. CREATE USER STORY
# -------------------------
def create_story(summary, description, epic_key):
    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue"

    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Story"}
        }
    }

    r = session.post(url, json=payload)
    if r is None or getattr(r, 'status_code', None) not in (200, 201):
        print(f"Failed to create story '{summary}':", getattr(r, 'status_code', None), getattr(r, 'text', ''))
        return None
    issue = r.json()
    # linking to epic requires the Epic Link custom field id which varies by instance.
    # We'll attempt to set it via a separate edit if epic_key is provided and we're not in dry-run.
    if epic_key and not DRY_RUN:
        # Try a best-effort update using a common field name 'customfield_10014' or 'customfield_10011'
        link_fields = ["customfield_10014", "customfield_10011"]
        for lf in link_fields:
            upd = {"fields": {lf: epic_key}}
            upd_r = session.put(f"{url}/{issue.get('key')}", json=upd)
            if getattr(upd_r, 'status_code', None) in (200, 204):
                break
    return issue


# -------------------------
# 4. CREATE SUBTASK
# -------------------------
def create_subtask(summary, parent_story_key):
    url = f"https://{JIRA_DOMAIN}/rest/api/3/issue"

    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "issuetype": {"name": "Sub-task"},
            "parent": {"key": parent_story_key}
        }
    }

    r = session.post(url, json=payload)
    if r is None or getattr(r, 'status_code', None) not in (200, 201):
        print(f"Failed to create subtask '{summary}' for {parent_story_key}:", getattr(r, 'status_code', None))
        return None
    return r.json()



# -------------------------
# 5. CREATE SPRINTS
# -------------------------
def create_sprint(name, goal):
    url = f"https://{JIRA_DOMAIN}/rest/agile/1.0/sprint"

    payload = {"name": name, "originBoardId": BOARD_ID, "goal": goal}
    r = session.post(url, json=payload)
    if r is None or getattr(r, 'status_code', None) not in (200, 201):
        print(f"Failed to create sprint '{name}':", getattr(r, 'status_code', None))
        return None
    return r.json()


# -------------------------
# 6. ADD ISSUE TO SPRINT
# -------------------------
def assign_issue_to_sprint(sprint_id, issue_id):
    url = f"https://{JIRA_DOMAIN}/rest/agile/1.0/sprint/{sprint_id}/issue"

    payload = {"issues": [issue_id]}
    r = session.post(url, json=payload)
    if r is None:
        return None
    return getattr(r, 'status_code', None)


# ---------------------------------------------------------
# 7. EXECUTE FULL IMPLEMENTATION
# ---------------------------------------------------------
if __name__ == "__main__":

    # -----------------------------
    # EPICS
    # -----------------------------
    epics = [
        ("Payments System", "UPI, recharge, bill payments etc."),
        ("Security & Authentication", "PIN, biometric, fraud detection"),
        ("Rewards & Cashback", "Scratch cards, loyalty system"),
        ("Transaction History", "Filters, monthly PDF, exports"),
        ("User Profile & KYC", "Profile update and verification")
    ]

    epic_keys = []
    for e in epics:
        res = create_epic(e[0], e[1])
        if res and res.get("key"):
            epic_keys.append(res["key"])
            print("Created EPIC:", res["key"])
        else:
            print("Failed to create epic:", e[0])


    # -----------------------------
    # USER STORIES
    # -----------------------------
    stories_data = [
        ("Send Money using UPI", "User should be able to transfer money", epic_keys[0]),
        ("Recharge Mobile", "User can recharge prepaid mobile", epic_keys[0]),
        ("Login with PIN", "User logs in using secure PIN", epic_keys[1]),
        ("Enable Biometric Login", "Fingerprint login support", epic_keys[1]),
        ("View Monthly Statement", "User can download monthly report", epic_keys[3]),
        ("Update Profile Photo", "User uploads new photo", epic_keys[4])
    ]

    story_keys = []
    for s in stories_data:
        res = create_story(s[0], s[1], s[2])
        if res and res.get("key"):
            story_keys.append(res["key"])
            print("Created STORY:", res["key"])
        else:
            print("Failed to create story:", s[0])


    # -----------------------------
    # SUBTASKS
    # -----------------------------
    subtasks_data = [
        ("Create UPI UI screen", story_keys[0]),
        ("Validate UPI PIN", story_keys[0]),
        ("Implement recharge API", story_keys[1]),
        ("Recharge success UI", story_keys[1]),
        ("Design PIN screen", story_keys[2]),
        ("Test biometric unlock", story_keys[3]),
        ("Generate PDF report", story_keys[4]),
        ("Implement sorting", story_keys[4]),
        ("Create upload endpoint", story_keys[5]),
        ("Crop and resize image", story_keys[5])
    ]

    for st in subtasks_data:
        res = create_subtask(st[0], st[1])
        if res and res.get("key"):
            print("Created SUBTASK:", res["key"])
        else:
            print("Failed to create subtask for:", st[1])


    # -----------------------------
    # SPRINTS
    # -----------------------------
    sprint1 = create_sprint("Sprint 1", "Payments + Login")
    sprint2 = create_sprint("Sprint 2", "Statements + Profile")

    if sprint1 and sprint1.get("id"):
        print("Sprint 1 ID:", sprint1["id"])
    else:
        print("Sprint 1 creation failed")
    if sprint2 and sprint2.get("id"):
        print("Sprint 2 ID:", sprint2["id"])
    else:
        print("Sprint 2 creation failed")

    # assign first 3 stories to sprint 1
    if sprint1 and sprint1.get("id"):
        for k in story_keys[:3]:
            status = assign_issue_to_sprint(sprint1["id"], k)
            print(f"Assign {k} to sprint {sprint1['id']}:", status)

    # next 3 stories to sprint 2
    if sprint2 and sprint2.get("id"):
        for k in story_keys[3:]:
            status = assign_issue_to_sprint(sprint2["id"], k)
            print(f"Assign {k} to sprint {sprint2['id']}:", status)

    print("Done.")
