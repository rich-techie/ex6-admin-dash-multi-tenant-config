import os
import requests
import json
import time

# Removed: from dotenv import load_dotenv # Load dotenv only in main entry point

# Zoho credentials will be accessed via os.getenv after main app loads them
# ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
# ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
# ZOHO_ACCOUNTS_URL = os.getenv("ZOHO_ACCOUNTS_URL")

# Path for the refresh token file relative to this script
REFRESH_TOKEN_FILE = os.path.join(os.path.dirname(__file__), "zoho_refresh_token.txt")

# In-memory storage for the current access token and its expiry time
_current_access_token = None
_access_token_expiry_time = 0 # Unix timestamp when the token expires

def _read_refresh_token():
    """Reads the refresh token from the local file."""
    if os.path.exists(REFRESH_TOKEN_FILE):
        with open(REFRESH_TOKEN_FILE, 'r') as f:
            return f.read().strip()
    return None

def _save_refresh_token(token: str):
    """Saves the refresh token to the local file."""
    with open(REFRESH_TOKEN_FILE, 'w') as f:
        f.write(token)

def get_access_token():
    """
    Retrieves a valid Zoho CRM access token.
    If the current token is expired or not available, it refreshes it using the refresh token.
    Returns:
        str: A valid Zoho CRM access token, or None if refresh fails.
    """
    global _current_access_token, _access_token_expiry_time

    # Check if the current token is still valid
    if _current_access_token and time.time() < _access_token_expiry_time:
        return _current_access_token

    # Try to get refresh token from file
    zoho_refresh_token_from_file = _read_refresh_token()

    # Get credentials from environment (loaded by main app)
    zoho_client_id = os.getenv("ZOHO_CLIENT_ID")
    zoho_client_secret = os.getenv("ZOHO_CLIENT_SECRET")
    zoho_accounts_url = os.getenv("ZOHO_ACCOUNTS_URL")

    if not all([zoho_client_id, zoho_client_secret, zoho_refresh_token_from_file, zoho_accounts_url]):
        print("[Zoho Auth ERROR] Missing Zoho credentials or refresh token. Cannot generate access token.")
        return None

    print("[Zoho Auth] Access token expired or not found. Attempting to refresh...")
    token_url = f"{zoho_accounts_url}/oauth/v2/token"
    payload = {
        "refresh_token": zoho_refresh_token_from_file,
        "client_id": zoho_client_id,
        "client_secret": zoho_client_secret,
        "grant_type": "refresh_token"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(token_url, data=payload, headers=headers)
        response.raise_for_status()
        token_data = response.json()

        if "access_token" in token_data:
            _current_access_token = token_data["access_token"]
            _access_token_expiry_time = time.time() + token_data.get("expires_in", 3600) - 60
            print("[Zoho Auth] Successfully refreshed access token.")
            return _current_access_token
        else:
            print(f"[Zoho Auth ERROR] Failed to get access token: {token_data.get('error', 'Unknown error')}")
            print(f"[Zoho Auth ERROR] Full Zoho Response: {json.dumps(token_data, indent=2)}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[Zoho Auth ERROR] Network or HTTP error during token refresh: {e}")
        return None
    except json.JSONDecodeError:
        print(f"[Zoho Auth ERROR] Invalid JSON response from Zoho: {response.text}")
        return None
    except Exception as e:
        print(f"[Zoho Auth ERROR] An unexpected error occurred during token refresh: {e}")
        return None

def exchange_authorization_code_for_tokens(auth_code: str, redirect_uri: str) -> bool:
    """
    Exchanges an authorization code for access and refresh tokens.
    Saves the refresh token to a file.
    Args:
        auth_code (str): The authorization code received from Zoho.
        redirect_uri (str): The redirect URI used in the authorization request.
    Returns:
        bool: True if tokens are successfully obtained and refresh token saved, False otherwise.
    """
    zoho_client_id = os.getenv("ZOHO_CLIENT_ID")
    zoho_client_secret = os.getenv("ZOHO_CLIENT_SECRET")
    zoho_accounts_url = os.getenv("ZOHO_ACCOUNTS_URL")

    if not all([zoho_client_id, zoho_client_secret, zoho_accounts_url]):
        print("[Zoho Auth ERROR] Missing Zoho credentials in .env. Cannot exchange authorization code.")
        return False

    token_url = f"{zoho_accounts_url}/oauth/v2/token"
    payload = {
        "code": auth_code,
        "client_id": zoho_client_id,
        "client_secret": zoho_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        print("[Zoho Auth] Exchanging authorization code for tokens...")
        response = requests.post(token_url, data=payload, headers=headers)
        response.raise_for_status()
        token_data = response.json()

        if "refresh_token" in token_data:
            _save_refresh_token(token_data["refresh_token"])
            print("[Zoho Auth] Refresh token saved to zoho_refresh_token.txt")
            return True
        else:
            print(f"[Zoho Auth ERROR] Failed to get refresh token: {token_data.get('error', 'Unknown error')}")
            print(f"[Zoho Auth ERROR] Full Zoho Response: {json.dumps(token_data, indent=2)}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[Zoho Auth ERROR] Network or HTTP error during code exchange: {e}")
        return False
    except json.JSONDecodeError:
        print(f"[Zoho Auth ERROR] Invalid JSON response from Zoho: {response.text}")
        return False
    except Exception as e:
        print(f"[Zoho Auth ERROR] An unexpected error occurred during code exchange: {e}")
        return False

# --- Test function for direct execution (for debugging) ---
if __name__ == "__main__":
    print("--- Testing Zoho Access Token Refresh ---")
    # For testing this script directly, you might temporarily load dotenv here
    # load_dotenv()
    # ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
    # ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
    # ZOHO_ACCOUNTS_URL = os.getenv("ZOHO_ACCOUNTS_URL")

    # print(f"Client ID: {ZOHO_CLIENT_ID}")
    # print(f"Client Secret: {ZOHO_CLIENT_SECRET[:5]}...{ZOHO_CLIENT_SECRET[-5:]}")
    # print(f"Accounts URL: {ZOHO_ACCOUNTS_URL}")
    # print(f"Refresh Token from file: {_read_refresh_token()[:5]}...{_read_refresh_token()[-5:]}" if _read_refresh_token() else "None")

    # if not all([ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, _read_refresh_token(), ZOHO_ACCOUNTS_URL]):
    #     print("ERROR: One or more Zoho environment variables or refresh token are missing. Please check your .env file and ensure zoho_refresh_token.txt exists.")
    # else:
    #     token = get_access_token()
    #     if token:
    #         print(f"\nSUCCESS: Obtained access token: {token[:30]}...")
    #     else:
    #         print("\nFAILURE: Could not obtain access token. Check the errors above.")
    print("This script is designed to be imported. Run whatsapp_bot_main.py to test full flow.")
    print("-----------------------------------------")

