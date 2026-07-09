#!/usr/bin/env python3
"""Generate admin password hash and update .env file."""

import os
from werkzeug.security import generate_password_hash

def update_env_password():
    # change-this-password
    password = input("Enter new admin password: ").strip()
    if not password:
        print("❌ Password cannot be empty")
        return
    
    hash_code = generate_password_hash(password, method="pbkdf2:sha256")
    print(f"\n✓ Generated hash:\n{hash_code}\n")
    
    env_path = ".env"
    env_content = ""
    
    # Read existing .env if it exists
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            env_content = f.read()
    
    # Update or add ADMIN_PASSWORD_HASH
    if "ADMIN_PASSWORD_HASH=" in env_content:
        lines = env_content.split("\n")
        lines = [line for line in lines if not line.startswith("ADMIN_PASSWORD_HASH=")]
        env_content = "\n".join(lines)
    
    # Append the new hash
    if env_content and not env_content.endswith("\n"):
        env_content += "\n"
    env_content += f"ADMIN_PASSWORD_HASH={hash_code}\n"
    
    # Write back to .env
    with open(env_path, "w") as f:
        f.write(env_content)
    
    print(f"✓ Updated {env_path} with new ADMIN_PASSWORD_HASH")

if __name__ == "__main__":
    update_env_password()
