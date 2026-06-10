#!/usr/bin/env python3
"""
Garmin Connect authentication helper.
Handles login and stores session tokens.
"""

import json
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
import argparse

try:
    from garminconnect import Garmin, GarminConnectAuthenticationError, GarminConnectConnectionError
except ImportError:
    print("❌ garminconnect library not installed", file=sys.stderr)
    print("Install with: pip3 install garminconnect", file=sys.stderr)
    sys.exit(1)

DEFAULT_PROFILE = "cn"
PROFILES = ("cn", "global")
TOKEN_BASE_DIR = Path.home() / ".config" / "garmin"
LEGACY_GLOBAL_TOKEN_DIR = Path.home() / ".clawdbot" / "garmin"
CONFIG_FILE = Path(__file__).parent.parent / "config.json"


def resolve_profile(profile=None, allow_all=False):
    """Resolve profile from CLI arg, env var, or default."""
    raw_profile = profile or os.getenv("GARMIN_PROFILE") or DEFAULT_PROFILE
    raw_profile = raw_profile.lower()

    if allow_all and raw_profile == "all":
        return raw_profile
    if raw_profile not in PROFILES:
        valid = ", ".join(("all", *PROFILES) if allow_all else PROFILES)
        raise ValueError(f"Invalid Garmin profile '{raw_profile}'. Use one of: {valid}")
    return raw_profile


def get_token_dir(profile):
    """Return profile-specific token directory."""
    return TOKEN_BASE_DIR / profile


def migrate_legacy_global_tokens():
    """Copy the old global tokenstore to the new global profile directory."""
    token_dir = get_token_dir("global")
    if token_dir.exists() or not LEGACY_GLOBAL_TOKEN_DIR.exists():
        return token_dir

    try:
        token_dir.parent.mkdir(parents=True, exist_ok=True)
        if LEGACY_GLOBAL_TOKEN_DIR.is_dir():
            shutil.copytree(LEGACY_GLOBAL_TOKEN_DIR, token_dir)
        else:
            token_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LEGACY_GLOBAL_TOKEN_DIR, token_dir / LEGACY_GLOBAL_TOKEN_DIR.name)
        token_dir.chmod(0o700)
        print(f"↪️  Migrated legacy global tokens to {token_dir}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Failed to migrate legacy global tokens: {e}", file=sys.stderr)
    return token_dir


def ensure_token_dir(profile):
    if profile == "global":
        return migrate_legacy_global_tokens()
    return get_token_dir(profile)


def create_client(profile, email=None, password=None):
    """Create a Garmin client for the selected profile."""
    return Garmin(email, password, is_cn=(profile == "cn"))


def load_config():
    """Load credentials from config file."""
    if not CONFIG_FILE.exists():
        return None
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Failed to load config: {e}", file=sys.stderr)
        return None


def login(email, password, profile=None):
    """Perform login and save tokens using garminconnect's tokenstore."""
    try:
        profile = resolve_profile(profile)
        print(f"🔐 Logging in as {email} using profile '{profile}'...", file=sys.stderr)
        
        # Create token directory
        token_dir = get_token_dir(profile)
        token_dir.mkdir(parents=True, exist_ok=True)
        tokenstore = str(token_dir)
        
        # Create client and login (don't pass tokenstore on first login)
        client = create_client(profile, email, password)
        client.login()  # Initial login without tokenstore
        
        # Save tokens to tokenstore
        client.garth.dump(tokenstore)
        print(f"✅ Tokens saved to {tokenstore}", file=sys.stderr)
        
        # Test the connection
        try:
            profile = client.get_user_summary(datetime.now().strftime("%Y-%m-%d"))
            print(f"✅ Login successful! User: {profile.get('displayName', 'Unknown')}", file=sys.stderr)
        except Exception as e:
            print(f"✅ Login successful! (Unable to fetch profile: {e})", file=sys.stderr)
        
        # Make tokenstore directory secure
        token_dir.chmod(0o700)
        
        return True
        
    except GarminConnectAuthenticationError as e:
        print(f"❌ Authentication failed: {e}", file=sys.stderr)
        print("Check your email/password and try again.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Login error: {e}", file=sys.stderr)
        return False


def get_client(profile=None):
    """Get authenticated Garmin client, using saved tokens if available."""
    try:
        profile = resolve_profile(profile)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return None

    token_dir = ensure_token_dir(profile)
    tokenstore = str(token_dir)

    if not token_dir.exists():
        print(f"⚠️  No token store for profile '{profile}' at {tokenstore}", file=sys.stderr)
        return None
    
    try:
        # Try to use saved tokens
        client = create_client(profile)
        client.login(tokenstore=tokenstore)
        
        # Test if tokens still work
        client.get_user_summary(datetime.now().strftime("%Y-%m-%d"))
        return client
        
    except Exception as e:
        print(f"⚠️  Saved tokens expired or invalid: {e}", file=sys.stderr)
        return None


def check_status(profile=None):
    """Check if we have valid authentication."""
    try:
        profile = resolve_profile(profile, allow_all=True)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return False

    if profile == "all":
        results = []
        for profile_name in PROFILES:
            print(f"\n== {profile_name} ==", file=sys.stderr)
            results.append(check_status(profile_name))
        return all(results)

    token_dir = ensure_token_dir(profile)
    tokenstore = str(token_dir)
    
    if not token_dir.exists():
        print(f"❌ Not authenticated for profile '{profile}'", file=sys.stderr)
        print(f"Run: python3 scripts/garmin_auth.py login --profile {profile}", file=sys.stderr)
        return False
    
    print(f"✅ Token store found for profile '{profile}' at {tokenstore}", file=sys.stderr)
    
    # Test if they work
    client = get_client(profile)
    if client:
        try:
            profile = client.get_user_summary(datetime.now().strftime("%Y-%m-%d"))
            print(f"✅ Authentication valid! User: {profile.get('displayName', 'Unknown')}", file=sys.stderr)
            return True
        except Exception as e:
            print(f"⚠️  Tokens may be expired: {e}", file=sys.stderr)
            return False
    
    print("❌ Authentication invalid. Please login again.", file=sys.stderr)
    return False


def add_profile_arg(parser, allow_all=False):
    choices = ["cn", "global"]
    if allow_all:
        choices.append("all")
    parser.add_argument(
        "--profile",
        choices=choices,
        default=None,
        help=f"Garmin profile (default: GARMIN_PROFILE or {DEFAULT_PROFILE})",
    )


def main():
    parser = argparse.ArgumentParser(description="Garmin Connect authentication")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Login command
    login_parser = subparsers.add_parser("login", help="Login to Garmin Connect")
    login_parser.add_argument("--email", help="Garmin account email (or set via env/config)")
    login_parser.add_argument("--password", help="Garmin account password (or set via env/config)")
    add_profile_arg(login_parser)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check authentication status")
    add_profile_arg(status_parser, allow_all=True)
    
    args = parser.parse_args()
    
    if args.command == "login":
        email = args.email
        password = args.password
        
        # Priority: CLI args > config.json > environment variables
        if not email or not password:
            config = load_config()
            if config:
                email = email or config.get("email")
                password = password or config.get("password")
        
        if not email or not password:
            email = email or os.getenv("GARMIN_EMAIL")
            password = password or os.getenv("GARMIN_PASSWORD")
        
        if not email or not password:
            print("❌ Email and password required", file=sys.stderr)
            print("Set via:", file=sys.stderr)
            print("  1. CLI: --email and --password", file=sys.stderr)
            print("  2. Config: create config.json from config.example.json", file=sys.stderr)
            print("  3. Env vars: GARMIN_EMAIL and GARMIN_PASSWORD", file=sys.stderr)
            print("  4. Clawdbot config: skills.entries.garmin-health-analysis.env", file=sys.stderr)
            sys.exit(1)
        
        success = login(email, password, args.profile)
        sys.exit(0 if success else 1)
    
    elif args.command == "status":
        success = check_status(args.profile)
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
