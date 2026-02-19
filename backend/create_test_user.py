"""
Create a quick test user in the local sqlite DB (chatlog.db).
Run this from the backend folder with the backend venv activated.

Example:
  cd /d/transparent-chat/backend
  source venv/Scripts/activate   # (Git Bash) or Activate.ps1 in PowerShell
    python create_test_user.py --username tester --password secret123

If user exists the script will report and not create duplicate.
"""
import argparse
from passlib.context import CryptContext
import database

# Use pbkdf2_sha256 to avoid potential bcrypt binary issues in some environments
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--username", default="tester")
    p.add_argument("--password", default="secret123")
    args = p.parse_args()

    # check existing
    existing = database.get_user_by_username(args.username)
    if existing:
        print(f"User already exists: id={existing['id']}, username={existing['username']}")
        return

    hashed = pwd_context.hash(args.password)
    user_id = database.save_user(args.username, hashed)
    if user_id:
        print(f"Created user id={user_id}, username={args.username}")
    else:
        print("Failed to create user (maybe duplicate)")

if __name__ == '__main__':
    main()
