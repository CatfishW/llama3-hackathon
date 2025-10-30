"""
Test the leaderboard API directly to see what's happening
"""
import requests

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("TESTING LEADERBOARD API")
print("=" * 70)
print()

# Test 1: Get all scores (no filter)
print("[1] Testing: No mode filter")
response = requests.get(f"{BASE_URL}/api/leaderboard/")
print(f"    Status: {response.status_code}")
print(f"    Total: {response.headers.get('X-Total-Count', 'N/A')}")
print(f"    Entries returned: {len(response.json())}")
print()

# Test 2: Get LAM mode scores
print("[2] Testing: mode=lam")
response = requests.get(f"{BASE_URL}/api/leaderboard/?mode=lam")
print(f"    Status: {response.status_code}")
print(f"    Total: {response.headers.get('X-Total-Count', 'N/A')}")
print(f"    Entries returned: {len(response.json())}")
print()

# Test 3: Get Manual mode scores
print("[3] Testing: mode=manual")
response = requests.get(f"{BASE_URL}/api/leaderboard/?mode=manual")
print(f"    Status: {response.status_code}")
print(f"    Total: {response.headers.get('X-Total-Count', 'N/A')}")
print(f"    Entries returned: {len(response.json())}")
print()

# Test 4: Get Driving Game scores
print("[4] Testing: mode=driving_game")
response = requests.get(f"{BASE_URL}/api/leaderboard/?mode=driving_game")
print(f"    Status: {response.status_code}")
print(f"    Total: {response.headers.get('X-Total-Count', 'N/A')}")
print(f"    Entries returned: {len(response.json())}")
if len(response.json()) > 0:
    print("    [ERROR] Should be empty but got entries!")
    print("    First entry:")
    entry = response.json()[0]
    print(f"      Template: {entry.get('template_title')}")
    print(f"      Score: {entry.get('new_score')}")
    print(f"      DG Messages: {entry.get('driving_game_message_count')}")
else:
    print("    [OK] Correctly returns empty array")
print()

print("=" * 70)
print("DIAGNOSIS:")
print()
if response.status_code == 200 and len(response.json()) == 0:
    print("✓ API is working correctly!")
    print("✓ Filtering by mode=driving_game returns 0 entries")
    print()
    print("PROBLEM: Frontend might be:")
    print("  1. Not passing the mode parameter")
    print("  2. Using cached data")
    print("  3. Not refreshed properly (try Ctrl+Shift+Delete to clear cache)")
else:
    print("✗ API is not filtering correctly")
    print("  Check backend code and restart again")
print("=" * 70)

