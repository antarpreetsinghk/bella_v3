#!/usr/bin/env python3
"""Test database connection with URL encoding"""
import urllib.parse

# Test the password encoding
password = "BellaPostgres2025!"
encoded_password = urllib.parse.quote_plus(password)
print(f"Original password: {password}")
print(f"URL-encoded password: {encoded_password}")

# Test the connection string
sync_url = f"postgresql://postgres:{encoded_password}@bella-db.cvc86oiqsam9.ca-central-1.rds.amazonaws.com:5432/postgres"
print(f"Sync URL: {sync_url}")

# Test if ConfigParser would have issues
import configparser
config = configparser.ConfigParser()

try:
    # This is what Alembic does internally
    config.read_string(f"""
[test]
sqlalchemy.url = {sync_url}
""")
    print("✅ ConfigParser can handle this URL")
    print(f"Retrieved URL: {config.get('test', 'sqlalchemy.url')}")
except Exception as e:
    print(f"❌ ConfigParser error: {e}")
    print("The issue is with % character interpretation")

    # Try with escaped %
    escaped_url = sync_url.replace('%', '%%')
    print(f"Escaped URL: {escaped_url}")

    try:
        config.read_string(f"""
[test]
sqlalchemy.url = {escaped_url}
""")
        print("✅ Escaped URL works!")
        print(f"Retrieved URL: {config.get('test', 'sqlalchemy.url')}")
    except Exception as e2:
        print(f"❌ Even escaped doesn't work: {e2}")