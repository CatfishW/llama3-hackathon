import requests
import json

BASE = "http://localhost:8000"

print("=" * 80)
print("Testing /api/driving endpoints")
print("=" * 80)

# Test 1: Stats endpoint
print("\n1. GET /api/driving/stats")
try:
    r = requests.get(f"{BASE}/api/driving/stats")
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 2: Leaderboard endpoint  
print("\n2. GET /api/driving/leaderboard")
try:
    r = requests.get(f"{BASE}/api/driving/leaderboard", params={"limit": 5, "skip": 0})
    print(f"   Status: {r.status_code}")
    print(f"   Response length: {len(r.json())}")
    print(f"   X-Total-Count: {r.headers.get('X-Total-Count')}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 3: Check available routes
print("\n3. GET /docs")
try:
    r = requests.get(f"{BASE}/docs")
    print(f"   Status: {r.status_code}")
    if "driving" in r.text.lower():
        print("   ✓ 'driving' found in docs")
    else:
        print("   ✗ 'driving' NOT found in docs")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 80)

