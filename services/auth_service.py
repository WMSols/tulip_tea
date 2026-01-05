"""
Authentication Service
======================
Handles JWT token generation and password hashing/verification.

This service provides core authentication utilities used by all user roles:
- Password hashing (bcrypt with 12 rounds)
- Password verification
- JWT token creation and decoding

FLOW:
1. User registration: get_password_hash() → stores hashed password in DB
2. User login: verify_password() → validates credentials
3. On successful login: create_access_token() → returns JWT for API access
4. API requests: decode_access_token() → validates JWT in protected routes
"""
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from config.database import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    FLOW:
    1. Converts plain password string to bytes
    2. Converts hashed password (if string) to bytes
    3. Uses bcrypt.checkpw() to compare
    4. Returns True if match, False otherwise
    
    Args:
        plain_password: User's input password (plain text)
        hashed_password: Stored password hash from database
    
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        # Convert string password to bytes (bcrypt requires bytes)
        password_bytes = plain_password.encode('utf-8')
        # Convert hashed password string to bytes if needed
        if isinstance(hashed_password, str):
            hashed_bytes = hashed_password.encode('utf-8')
        else:
            hashed_bytes = hashed_password
        # bcrypt.checkpw() securely compares password with hash
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        # Return False on any error (invalid hash format, etc.)
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    FLOW:
    1. Converts password string to bytes
    2. Generates a random salt (12 rounds = secure but not too slow)
    3. Hashes password with salt using bcrypt
    4. Returns hash as string for database storage
    
    Args:
        password: Plain text password to hash
    
    Returns:
        str: Hashed password (can be stored in database)
    
    Note:
        - Uses 12 rounds (good balance of security vs performance)
        - Salt is automatically generated and included in hash
        - Same password will produce different hashes (due to random salt)
    """
    # Convert password to bytes (bcrypt requires bytes)
    password_bytes = password.encode('utf-8')
    # Generate salt with 12 rounds (higher = more secure but slower)
    salt = bcrypt.gensalt(rounds=12)
    # Hash password with salt
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string for database storage
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a JWT (JSON Web Token) access token for authenticated users.
    
    FLOW:
    1. Copies user data (user_id, role, phone) into token payload
    2. Adds expiration time (default from settings or custom)
    3. Signs token with secret key using HS256 algorithm
    4. Returns encoded token string
    
    Args:
        data: Dictionary containing user data:
            - "sub": user_id (subject)
            - "role": user role (distributor/order_booker/delivery_man)
            - "phone": user phone number
        expires_delta: Optional custom expiration time (defaults to settings.jwt_expiration_hours)
    
    Returns:
        str: Encoded JWT token string (sent to client, stored in localStorage)
    
    Example:
        token = create_access_token({
            "sub": "1",
            "role": "distributor",
            "phone": "03001234567"
        })
    """
    # Copy data to avoid modifying original
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Use default expiration from settings (typically 24 hours)
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    
    # Add expiration to token payload
    to_encode.update({"exp": expire})
    
    # Encode and sign token with secret key
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,  # Secret key from .env
        algorithm=settings.jwt_algorithm  # HS256
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT token.
    
    FLOW:
    1. Decodes token using secret key
    2. Verifies signature (ensures token wasn't tampered with)
    3. Checks expiration (raises error if expired)
    4. Returns decoded payload with user info
    
    Args:
        token: JWT token string (from Authorization header)
    
    Returns:
        dict: Decoded token payload containing:
            - "sub": user_id
            - "role": user role
            - "phone": user phone
            - "exp": expiration timestamp
    
    Raises:
        JWTError: If token is:
            - Invalid format
            - Expired
            - Signature doesn't match (tampered)
    
    Usage:
        Used in protected routes to extract user info from token
    """
    try:
        # Decode and verify token
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,  # Must match key used to encode
            algorithms=[settings.jwt_algorithm]  # HS256
        )
        return payload
    except JWTError:
        # Re-raise to let caller handle (usually returns 401 Unauthorized)
        raise

