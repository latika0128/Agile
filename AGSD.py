
#!/usr/bin/env python3
"""
jira_phonepe_setup.py

Creates Epics, Stories, Subtasks, two Sprints, attaches screenshots, and fetches basic reports.
Requires: requests, python-dotenv (optional)

Before running, set environment variables:
  JIRA_URL (e.g. https://yourdomain.atlassian.net)
  JIRA_EMAIL (your Atlassian account email)
  JIRA_API_TOKEN (API token from Atlassian)
  PROJECT_KEY (e.g. PHON)
  BOARD_ID (the Scrum board id associated with the project)

Run:
  pip install requests python-dotenv
  python jira_phonepe_setup.py
"""

import os
import json
from datetime import datetime, timedelta
from time import sleep

# Optional dependencies: fail fast for required ones, warn for optional
try:
    import requests
except Exception:
    print("Missing required package 'requests'. Install with: pip install requests")
    raise SystemExit(1)

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv():
        return None
    print("Optional package 'python-dotenv' not installed; continuing without loading .env file.")

# Load environment variables from a local .env file when present
load_dotenv()

# Local screenshot file paths (from your session)
SCREENSHOT_PATHS = [
    "/mnt/data/c4637667-912d-473a-99a8-2596acfd8ed4.png",
    "/mnt/data/9d490c95-50a1-44c6-a9c7-e3874177ebdf.png"
]

# Load configuration from environment variables
JIRA_URL = os.getenv("JIRA_URL")  # e.g. https://your-org.atlassian.net
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
PROJECT_KEY = os.getenv("PROJECT_KEY", "PHON")  # default
BOARD_ID = os.getenv("BOARD_ID")  # Agile board ID required to create sprints

if not (JIRA_URL and JIRA_EMAIL and JIRA_API_TOKEN and PROJECT_KEY):
    raise SystemExit("Please set JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN environment variables. Optionally BOARD_ID.")

# Setup requests session with auth
session = requests.Session()
session.auth = (JIRA_EMAIL, JIRA_API_TOKEN)
session.headers.update({
    "Accept": "application/json",
    "Content-Type": "application/json"
})

# Helper functions
def create_issue(issue_type, summary, description="", fields_extra=None):
    """
    Create an issue and return the returned issue JSON.
    fields_extra: dict of additional fields (like "customfield_10011" for Epic Link in some instances)
    """
    url = f"{JIRA_URL}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issue_type}
        }
    }
    if fields_extra:
        payload["fields"].update(fields_extra)

    r = session.post(url, data=json.dumps(payload))
    if r.status_code not in (200, 201):
        print("Error creating issue:", r.status_code, r.text)
        raise SystemExit("Issue creation failed. Check credentials/permissions.")
    return r.json()

def add_attachment(issue_key, filepath):
    """
    Attach a local file to given issue_key.
    """
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}/attachments"
    headers = {"X-Atlassian-Token": "no-check"}
    if not os.path.exists(filepath):
        print(f"Attachment file not found: {filepath}")
        return None
    try:
        with open(filepath, "rb") as f:
            files = {'file': (os.path.basename(filepath), f, "application/octet-stream")}
            # session already has auth configured
            r = session.post(url, files=files, headers=headers)
    except Exception as e:
        print(f"Error attaching file {filepath}: {e}")
        return None
    if r.status_code not in (200, 201):
        print(f"Failed to attach {filepath} to {issue_key}: {r.status_code} {r.text}")
        return None
    print(f"Attached {filepath} to {issue_key}")
    return r.json()

def create_epic(name, summary):
    """
    Create an Epic issue. In Jira Cloud the Epic Issue Type usually requires 'customfield_10011' (Epic Name).
    We set the 'epic name' field commonly used by Jira: 'customfield_10011' or search via metadata if needed.
    NOTE: You may have to update the custom field key if your instance uses different id.
    """
    # Epic Name field key may vary. Many Jira Cloud instances use 'customfield_10011'. We'll attempt that and fall back otherwise.
    epic_field_name = "customfield_10011"  # common fallback; change if your instance differs.
    fields_extra = {
        epic_field_name: name  # sets 'Epic Name'
    }
    issue = create_issue("Epic", summary, description=f"Epic: {name}", fields_extra=fields_extra)
    print("Created Epic:", issue["key"])
    return issue

def link_story_to_epic(story_issue_key, epic_key):
    """
    Link a story to an epic by setting the epic link custom field.
    The custom field id for Epic Link varies by instance; it's usually customfield_10014 or customfield_10011 variant.
    We'll try a small set of common field ids until success.
    """
    # common epic link field names to try (may differ)
    candidate_fields = ["customfield_10014", "customfield_10011", "Epic Link", "epic-link"]  # "Epic Link" is not an API field usually.
    # Get create metadata for stories to find exact fields (recommended)
    meta_url = f"{JIRA_URL}/rest/api/3/issue/createmeta?projectKeys={PROJECT_KEY}&issuetypeNames=Story&expand=projects.issuetypes.fields"
    meta_r = session.get(meta_url)
    if meta_r.status_code == 200:
        # try to detect epic link field name from metadata
        try:
            fields = meta_r.json()["projects"][0]["issuetypes"][0]["fields"]
            for k, v in fields.items():
                if v.get("name", "").lower() in ("epic link", "epic"):
                    candidate_fields.insert(0, k)
                    break
        except Exception:
            pass

    for field in candidate_fields:
        payload = {"fields": {field: epic_key}}
        url = f"{JIRA_URL}/rest/api/3/issue/{story_issue_key}"
        r = session.put(url, data=json.dumps(payload))
        if r.status_code in (200, 204):
            print(f"Linked story {story_issue_key} to epic {epic_key} using field {field}")
            return True
        # otherwise continue trying
    print("Failed to auto-link story to epic — you may need to update the custom field key for Epic Link in this script.")
    print("Response sample from last attempt:", r.status_code, r.text)
    return False

def create_subtask(parent_issue_key, summary, description=""):
    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "parent": {"key": parent_issue_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Sub-task"}
        }
    }
    url = f"{JIRA_URL}/rest/api/3/issue"
    r = session.post(url, data=json.dumps(payload))
    if r.status_code not in (200, 201):
        print("Subtask creation failed:", r.status_code, r.text)
        return None
    print("Created subtask:", r.json()["key"])
    return r.json()

def create_sprint(name, start_date, end_date, goal=None):
    """
    Create a sprint on given board. Board id must be provided.
    """
    if not BOARD_ID:
        raise SystemExit("BOARD_ID not set. Cannot create sprint.")
    url = f"{JIRA_URL}/rest/agile/1.0/sprint"
    payload = {
        "name": name,
        "startDate": start_date.isoformat() + "Z",
        "endDate": end_date.isoformat() + "Z",
        "originBoardId": int(BOARD_ID),
        "goal": goal or ""
    }
    r = session.post(url, data=json.dumps(payload))
    if r.status_code not in (200, 201):
        print("Sprint creation failed:", r.status_code, r.text)
        return None
    print("Created sprint:", r.json()["id"], name)
    return r.json()

def add_issues_to_sprint(sprint_id, issue_keys):
    url = f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue"
    payload = {"issues": issue_keys}
    r = session.post(url, data=json.dumps(payload))
    if r.status_code not in (200, 204):
        print("Failed to add issues to sprint:", r.status_code, r.text)
        return False
    print(f"Added {len(issue_keys)} issues to sprint {sprint_id}")
    return True

def get_board_for_project():
    """
    Attempt to find a board for the project. Returns first board id.
    """
    url = f"{JIRA_URL}/rest/agile/1.0/board?projectKeyOrId={PROJECT_KEY}"
    r = session.get(url)
    if r.status_code != 200:
        print("Cannot fetch board for project:", r.status_code, r.text)
        return None
    boards = r.json().get("values", [])
    if not boards:
        print("No boards found for project. You must create a Scrum board manually and set BOARD_ID env var.")
        return None
    print("Found board:", boards[0]["id"], boards[0]["name"])
    return boards[0]["id"]

def fetch_sprint_report(sprint_id, board_id):
    url = f"{JIRA_URL}/rest/greenhopper/1.0/rapid/charts/sprintreport?rapidViewId={board_id}&sprintId={sprint_id}"
    r = session.get(url)
    if r.status_code != 200:
        print("Failed to fetch sprint report:", r.status_code, r.text)
        return None
    return r.json()

def fetch_velocity_chart(board_id):
    url = f"{JIRA_URL}/rest/greenhopper/1.0/rapid/charts/velocity?rapidViewId={board_id}"
    r = session.get(url)
    if r.status_code != 200:
        print("Failed to fetch velocity chart:", r.status_code, r.text)
        return None
    return r.json()

# ----- Data to create (Epics, Stories, Subtasks) -----
EPICS = [
    {"key_name": "EPIC-Auth", "name": "User Authentication and Onboarding", "summary": "Signup, login, and bank linking"},
    {"key_name": "EPIC-UPI", "name": "Money Transfer and UPI Payments", "summary": "Send, receive, and track UPI payments"},
    {"key_name": "EPIC-Bill", "name": "Recharge and Bill Payments", "summary": "Mobile recharge and utility payments"},
    {"key_name": "EPIC-History", "name": "Transaction History and Analytics", "summary": "History, statements, analytics"},
    {"key_name": "EPIC-Security", "name": "Security, Notifications, and Support", "summary": "Notifications, PIN, and support"}
]

STORIES = [
    # (title, epic_name, story_points)
    ("Signup with mobile number", "EPIC-Auth", 3),
    ("Login using OTP/Biometric", "EPIC-Auth", 2),
    ("Link bank account for UPI", "EPIC-Auth", 3),
    ("Send money using UPI", "EPIC-UPI", 5),
    ("Request money via UPI", "EPIC-UPI", 3),
    ("View transaction status", "EPIC-UPI", 2),
    ("Mobile recharge", "EPIC-Bill", 3),
    ("Pay electricity/water/DTH bills", "EPIC-Bill", 5),
    ("View past bills & recharges", "EPIC-Bill", 2),
    ("Transaction history view", "EPIC-History", 3),
    ("Download monthly statement", "EPIC-History", 2),
    ("Spending insights (charts)", "EPIC-History", 5),
    ("Notifications for transactions", "EPIC-Security", 2),
    ("Customer support and complaints", "EPIC-Security", 3),
    ("Set PIN and biometric security", "EPIC-Security", 3),
]

SUBTASKS_TEMPLATES = {
    # story summary -> list of subtask summaries
    "Signup with mobile number": [
        "Design signup UI",
        "Implement OTP verification",
        "Store user data in DB"
    ],
    "Login using OTP/Biometric": [
        "Create login UI",
        "Integrate biometric API",
        "Validate OTP flow"
    ],
    "Link bank account for UPI": [
        "Integrate with UPI provider API",
        "Implement bank account verification",
        "Store linked bank info securely"
    ],
    "Send money using UPI": [
        "Create Send Money screen",
        "Integrate UPI transaction API",
        "Add success/failure messages"
    ],
    # ... default fallback for others
}

# Main process
def main():
    # Optionally find BOARD_ID if not provided
    global BOARD_ID
    if not BOARD_ID:
        print("BOARD_ID not provided — attempting to locate a board for the project.")
        found_board = get_board_for_project()
        if not found_board:
            print("No board found. Either create a board in Jira and set BOARD_ID env var, or provide BOARD_ID.")
            # continue but cannot create sprints
        else:
            BOARD_ID = str(found_board)

    created_epics = {}
    created_stories = {}

    # 1) Create Epics
    print("--- Creating Epics ---")
    for epic in EPICS:
        resp = create_epic(epic["name"], epic["summary"])
        epic_key = resp["key"]
        created_epics[epic["key_name"]] = {"key": epic_key, "name": epic["name"]}
        sleep(0.5)

    # 2) Create Stories and link to epics
    print("\n--- Creating Stories and linking to Epics ---")
    for title, epic_keyname, points in STORIES:
        # Add story points (field name is customfield_10002 in many instances; adjust if needed)
        # We'll attempt to find story points field via createmeta similarly to epic
        fields_extra = {}
        # Try to set story points via common field names:
        for sp_field in ["customfield_10002", "customfield_10026", "customfield_story_points"]:
            fields_extra[sp_field] = points
        try:
            story_issue = create_issue("Story", title, description=f"Story for {title}", fields_extra=fields_extra)
            story_key = story_issue["key"]
            created_stories[title] = {"key": story_key, "points": points}
            # link to epic
            epic_key = created_epics[epic_keyname]["key"]
            linked = link_story_to_epic(story_key, epic_key)
            sleep(0.5)
        except Exception as e:
            print(f"Failed to create story {title}: {e}")

    # 3) Create Subtasks
    print("\n--- Creating Subtasks ---")
    for story_title, story_info in created_stories.items():
        parent_key = story_info["key"]
        templates = SUBTASKS_TEMPLATES.get(story_title, [
            f"Design {story_title} UI",
            f"Implement backend for {story_title}",
            f"Add tests for {story_title}"
        ])
        for sub in templates:
            create_subtask(parent_key, sub, description=f"Subtask: {sub} for {story_title}")
            sleep(0.3)

    # 4) Create sprints (if board available)
    if BOARD_ID:
        print("\n--- Creating Sprints ---")
        now = datetime.utcnow()
        sprint1_start = now
        sprint1_end = sprint1_start + timedelta(days=14)
        sprint1 = create_sprint("Sprint 1 - Core Functionality", sprint1_start, sprint1_end, goal="Onboarding + UPI basics")
        sleep(1)
        sprint2_start = sprint1_end + timedelta(days=1)
        sprint2_end = sprint2_start + timedelta(days=14)
        sprint2 = create_sprint("Sprint 2 - Enhancements & Support", sprint2_start, sprint2_end, goal="Recharge, Analytics, Support")
        sleep(1)

        # Map a simple set of stories to sprint 1 and the rest to sprint 2
        sprint1_keys = []
        sprint2_keys = []
        for i, (title, _, _) in enumerate(STORIES):
            key = created_stories.get(title, {}).get("key")
            if not key:
                continue
            if i < 6:
                sprint1_keys.append(key)
            else:
                sprint2_keys.append(key)

        if sprint1 and sprint1.get("id"):
            add_issues_to_sprint(sprint1["id"], sprint1_keys)
        if sprint2 and sprint2.get("id"):
            add_issues_to_sprint(sprint2["id"], sprint2_keys)
    else:
        print("Skipping sprint creation (BOARD_ID missing).")

    # 5) Attach screenshots to first epic (demo)
    print("\n--- Attaching screenshots to first epic ---")
    if created_epics:
        first_epic_key = next(iter(created_epics.values()))["key"]
        for path in SCREENSHOT_PATHS:
            if os.path.exists(path):
                add_attachment(first_epic_key, path)
            else:
                print("Screenshot not found at path:", path)
    else:
        print("No epics were created; skipping attachment step.")

    # 6) Fetch reports (optional)
    if BOARD_ID and 'sprint1' in locals() and sprint1:
        print("\n--- Fetching Sprint Report and Velocity ---")
        sprint_report = fetch_sprint_report(sprint1["id"], BOARD_ID)
        open("sprint1_report.json", "w").write(json.dumps(sprint_report or {}, indent=2))
        print("Saved sprint1_report.json")
        velocity = fetch_velocity_chart(BOARD_ID)
        open("velocity.json", "w").write(json.dumps(velocity or {}, indent=2))
        print("Saved velocity.json")

    print("\n--- Done. Summary ---")
    print("Epics created:", {k: v['key'] for k, v in created_epics.items()})
    print("Sample stories created (first 5):", {k: v['key'] for k, v in list(created_stories.items())[:5]})
    print("If anything failed, inspect the printed errors above and adjust custom field ids in the script for your Jira instance.")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        raise SystemExit(1)
