"""
Test script to diagnose Supabase Cloud database connection issues.
Run this script to test your database connection and get detailed diagnostics.

Usage:
    python scripts/test_db_connection.py
"""
import logging
import socket
import sys
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from pydantic_settings import BaseSettings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    database_url: str

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


def parse_database_url(url: str) -> dict:
    """Parse database URL and return connection details (without password)."""
    try:
        parsed = urlparse(url)
        
        # Validate hostname for common issues
        hostname = parsed.hostname
        if hostname:
            # Check for double dots (common typo)
            if '..' in hostname:
                logger.error(f"❌ Invalid hostname detected: '{hostname}'")
                logger.error("   Found double dots (..) - this is likely a typo!")
                logger.error(f"   Suggested fix: Replace '..' with '.'")
                raise ValueError(f"Invalid hostname: double dots detected in '{hostname}'")
            
            # Check for leading/trailing dots
            if hostname.startswith('.') or hostname.endswith('.'):
                logger.warning(f"⚠️ Hostname has leading/trailing dot: '{hostname}'")
        
        return {
            "scheme": parsed.scheme,
            "host": hostname,
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip('/') if parsed.path else 'postgres',
            "username": parsed.username,
            "has_password": bool(parsed.password),
            "password_length": len(parsed.password) if parsed.password else 0
        }
    except Exception as e:
        logger.error(f"Failed to parse DATABASE_URL: {e}")
        return {}


def mask_database_url(url: str) -> str:
    """Mask password in database URL for safe logging."""
    try:
        parsed = urlparse(url)
        if parsed.password:
            masked_password = "*" * min(len(parsed.password), 10)
            netloc = f"{parsed.username}:{masked_password}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return f"{parsed.scheme}://{netloc}{parsed.path}"
        return url
    except Exception:
        return "***MASKED***"


def test_dns_resolution(hostname: str) -> bool:
    """Test if hostname can be resolved via DNS (supports both IPv4 and IPv6)."""
    try:
        # Try IPv4 first
        try:
            ipv4 = socket.gethostbyname(hostname)
            logger.info(f"✅ IPv4 resolution successful: {ipv4}")
            return True
        except socket.gaierror:
            # IPv4 failed, try IPv6
            pass
        
        # Try IPv6 using getaddrinfo (supports both)
        try:
            addrinfo = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            if addrinfo:
                ip_addresses = [addr[4][0] for addr in addrinfo]
                logger.info(f"✅ DNS resolution successful (IPv6/IPv4): {', '.join(ip_addresses[:3])}")
                if len(ip_addresses) > 3:
                    logger.info(f"   ... and {len(ip_addresses) - 3} more addresses")
                return True
        except socket.gaierror as e:
            logger.error(f"DNS resolution failed for '{hostname}': {e}")
            logger.error("   Note: Hostname might only resolve to IPv6, but psycopg2 may need IPv4")
            return False
        
        return False
    except Exception as e:
        logger.error(f"Unexpected error during DNS resolution: {e}")
        return False


def test_database_connection(database_url: str) -> bool:
    """Test actual database connection."""
    try:
        logger.info("\n" + "=" * 60)
        logger.info("TESTING DATABASE CONNECTION")
        logger.info("=" * 60)
        
        engine = create_engine(database_url, pool_pre_ping=True)
        
        logger.info("⏳ Attempting connection...")
        with engine.connect() as conn:
            logger.info("✅ Connection established!")
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"✅ Database version: {version[:50]}...")
            
            # Test a simple query
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            logger.info("✅ Test query successful")
        
        logger.info("=" * 60)
        return True
    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error("DATABASE CONNECTION FAILED")
        logger.error("=" * 60)
        logger.error(f"❌ Error Type: {type(e).__name__}")
        logger.error(f"❌ Error Message: {str(e)}")
        
        # Provide specific guidance based on error type
        error_str = str(e).lower()
        if "could not translate host name" in error_str or "name or service not known" in error_str:
            logger.error("\n💡 DNS Resolution Error Detected!")
            logger.error("   This means your computer cannot resolve the hostname.")
            logger.error("   Common fixes:")
            logger.error("   1. Check if Supabase project is paused → Resume it")
            logger.error("   2. Verify PROJECT_REF in DATABASE_URL matches your Supabase project")
            logger.error("   3. Check internet connection")
            logger.error("   4. Try: nslookup db.YOUR_PROJECT_REF.supabase.co")
            logger.error("   5. Flush DNS cache: ipconfig /flushdns (Windows)")
        elif "password authentication failed" in error_str:
            logger.error("\n💡 Authentication Error Detected!")
            logger.error("   The database password is incorrect.")
            logger.error("   Fix: Update DATABASE_URL with correct password from Supabase Dashboard")
        elif "connection refused" in error_str:
            logger.error("\n💡 Connection Refused Error!")
            logger.error("   The database server is not accepting connections.")
            logger.error("   Check if project is paused or port is blocked by firewall")
        elif "timeout" in error_str:
            logger.error("\n💡 Connection Timeout!")
            logger.error("   The connection attempt timed out.")
            logger.error("   Check network connectivity and firewall settings")
        elif "ipv6" in error_str or "ipv4" in error_str or "could not translate host name" in error_str:
            logger.error("\n💡 IPv6/IPv4 Mismatch Detected!")
            logger.error("   Your database hostname only resolves to IPv6, but your network needs IPv4.")
            logger.error("   SOLUTION: Use Session Pooler connection string:")
            logger.error("   1. Supabase Dashboard → Settings → Database → Connection string")
            logger.error("   2. Select 'Session mode' tab (Connection pooler)")
            logger.error("   3. Copy the connection string (uses port 6543)")
            logger.error("   4. Update DATABASE_URL in .env file")
            logger.error("   The Session Pooler works with IPv4 networks!")
        
        logger.error("=" * 60)
        return False


def main():
    """Main function to run database connection diagnostics."""
    logger.info("=" * 60)
    logger.info("SUPABASE CLOUD DATABASE CONNECTION TEST")
    logger.info("=" * 60)
    
    # Load settings
    try:
        settings = Settings()
        if not settings.database_url:
            logger.error("❌ DATABASE_URL is not set in .env file!")
            logger.error("   Please add DATABASE_URL to your .env file")
            return 1
    except Exception as e:
        logger.error(f"❌ Failed to load settings: {e}")
        logger.error("   Make sure .env file exists and contains DATABASE_URL")
        return 1
    
    logger.info(f"✅ DATABASE_URL is set (length: {len(settings.database_url)} characters)")
    
    # Parse and display connection details (without password)
    conn_details = parse_database_url(settings.database_url)
    if not conn_details:
        logger.error("❌ Failed to parse DATABASE_URL")
        return 1
    
    logger.info(f"\n📋 Connection Details:")
    logger.info(f"   Scheme: {conn_details.get('scheme', 'N/A')}")
    logger.info(f"   Host: {conn_details.get('host', 'N/A')}")
    logger.info(f"   Port: {conn_details.get('port', 'N/A')}")
    logger.info(f"   Database: {conn_details.get('database', 'N/A')}")
    logger.info(f"   Username: {conn_details.get('username', 'N/A')}")
    logger.info(f"   Password: {'✅ Set' if conn_details.get('has_password') else '❌ Missing'}")
    if conn_details.get('has_password'):
        logger.info(f"   Password Length: {conn_details.get('password_length', 0)} characters")
    
    # Show masked URL
    masked_url = mask_database_url(settings.database_url)
    logger.info(f"\n🔐 Masked DATABASE_URL: {masked_url}")
    
    # Test DNS resolution
    hostname = conn_details.get('host')
    if hostname:
        logger.info(f"\n🔍 Testing DNS Resolution for '{hostname}'...")
        dns_success = test_dns_resolution(hostname)
        if not dns_success:
            logger.error(f"❌ DNS resolution FAILED for '{hostname}'")
            logger.error("   Possible causes:")
            logger.error("   1. Project is paused in Supabase Dashboard")
            logger.error("   2. Incorrect PROJECT_REF in hostname")
            logger.error("   3. Network/DNS issues (IPv6 vs IPv4 mismatch)")
            logger.error("   4. Firewall blocking the connection")
            logger.error("\n   💡 IMPORTANT: Your database hostname is IPv6-only!")
            logger.error("      Supabase shows: 'Not IPv4 compatible'")
            logger.error("      SOLUTION: Use Session Pooler connection string instead:")
            logger.error("      1. Go to Supabase Dashboard → Settings → Database")
            logger.error("      2. Click 'Connection string' tab")
            logger.error("      3. Select 'Session mode' (Connection pooler)")
            logger.error("      4. Copy that connection string (uses port 6543)")
            logger.error("      5. Update DATABASE_URL in .env file with that string")
            return 1
    
    # Test actual database connection
    connection_success = test_database_connection(settings.database_url)
    
    if connection_success:
        logger.info("\n" + "=" * 60)
        logger.info("✅ ALL TESTS PASSED - Database connection is working!")
        logger.info("=" * 60)
        return 0
    else:
        logger.info("\n" + "=" * 60)
        logger.info("❌ CONNECTION TEST FAILED")
        logger.info("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

