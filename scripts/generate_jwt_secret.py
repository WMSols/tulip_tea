"""
Generate a secure JWT secret key for use in .env file.

Usage:
    python scripts/generate_jwt_secret.py

This will generate a secure random string suitable for JWT_SECRET_KEY.
"""
import secrets
import sys

def generate_jwt_secret():
    """Generate a secure random JWT secret key."""
    # Generate a URL-safe random string (32 bytes = 256 bits of entropy)
    secret_key = secrets.token_urlsafe(32)
    
    print("=" * 60)
    print("JWT Secret Key Generated")
    print("=" * 60)
    print()
    print("Add this to your .env file:")
    print()
    print(f"JWT_SECRET_KEY={secret_key}")
    print()
    print("=" * 60)
    print("IMPORTANT:")
    print("- Keep this secret key secure and never commit it to git")
    print("- Use different keys for development and production")
    print("- If this key is compromised, regenerate it immediately")
    print("=" * 60)
    
    return secret_key

if __name__ == "__main__":
    try:
        generate_jwt_secret()
    except Exception as e:
        print(f"Error generating secret key: {e}", file=sys.stderr)
        sys.exit(1)


