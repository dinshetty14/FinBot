"""
FinBot Seed Users Script
Seeds the database with 5 demo users, one for each role.

Usage:
    cd backend
    python seed_users.py
"""

import sys
sys.path.insert(0, ".")

from app.database import init_db, get_user_by_username, create_user
from app.auth import hash_password

DEMO_USERS = [
    {
        "username": "john_employee",
        "password": "employee123",
        "role": "employee",
        "department": "General",
    },
    {
        "username": "jane_finance",
        "password": "finance123",
        "role": "finance",
        "department": "Finance",
    },
    {
        "username": "bob_engineer",
        "password": "engineer123",
        "role": "engineering",
        "department": "Engineering",
    },
    {
        "username": "alice_marketing",
        "password": "marketing123",
        "role": "marketing",
        "department": "Marketing",
    },
    {
        "username": "ceo_sarah",
        "password": "clevel123",
        "role": "c_level",
        "department": "Executive",
    },
]


def seed():
    print("Initializing database...")
    init_db()

    for user_data in DEMO_USERS:
        existing = get_user_by_username(user_data["username"])
        if existing:
            print(f"  ⏭ User '{user_data['username']}' already exists (skipped)")
            continue

        pw_hash = hash_password(user_data["password"])
        user_id = create_user(
            username=user_data["username"],
            password_hash=pw_hash,
            role=user_data["role"],
            department=user_data["department"],
        )
        print(
            f"  ✓ Created user '{user_data['username']}' "
            f"(role={user_data['role']}, id={user_id})"
        )

    print("\nDemo accounts:")
    print("-" * 50)
    for u in DEMO_USERS:
        print(f"  Username: {u['username']:20s}  Password: {u['password']:15s}  Role: {u['role']}")
    print("-" * 50)
    print("Seed complete!")


if __name__ == "__main__":
    seed()
