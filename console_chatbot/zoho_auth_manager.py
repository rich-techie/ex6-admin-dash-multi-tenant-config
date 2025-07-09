import os
import requests
import json
import time
import logging

logger = logging.getLogger(__name__)

class ZohoAuthManager:
    """
    Manages Zoho CRM OAuth2 authentication for a specific tenant.
    Handles access token retrieval and refresh using a tenant-specific refresh token file.
    """
    def __init__(self, client_id: str, client_secret: str, accounts_url: str, api_url: str, tenant_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.accounts_url = accounts_url
        self.api_url = api_url # Not directly used in auth, but useful for context
        self.tenant_id = tenant_id
        self.refresh_token_file = f"zoho_refresh_token_{self.tenant_id}.txt"

        self._current_access_token = None
        self._access_token_expiry_time = 0 # Unix timestamp when the token expires
        logger.info(f"[ZohoAuthManager] Initialized for tenant: {tenant_id}")

    def _load_refresh_token(self) -> str | None:
        """Loads refresh token from the tenant-specific file."""
        if os.path.exists(self.refresh_token_file):
            with open(self.refresh_token_file, "r") as f:
                token = f.read().strip()
                logger.debug(f"[ZohoAuthManager] Loaded refresh token from {self.refresh_token_file}")
                return token
        logger.warning(f"[ZohoAuthManager] No refresh token file found for tenant {self.tenant_id} at {self.refresh_token_file}")
        return None

    def _save_refresh_token(self, token: str):
        """Saves refresh token to the tenant-specific file."""
        with open(self.refresh_token_file, "w") as f:
            f.write(token)
        logger.info(f"[ZohoAuthManager] Refresh token saved for tenant {self.tenant_id} to {self.refresh_token_file}")

    def get_access_token(self) -> str | None:
        """
        Retrieves a valid Zoho CRM access token for this tenant.
        If the current token is expired or not available, it refreshes it using the refresh token.
        Returns:
            str: A valid Zoho CRM access token, or None if refresh fails.
        """
        # Check if the current token is still valid
        if self._current_access_token and time.time() < self._access_token_expiry_time:
            logger.debug(f"[ZohoAuthManager] Using cached access token for tenant {self.tenant_id}.")
            return self._current_access_token

        refresh_token = self._load_refresh_token()

        if not refresh_token:
            logger.error(f"[ZohoAuthManager ERROR] No refresh token found for tenant {self.tenant_id}. Please authorize the app first.")
            return None

        logger.info(f"[ZohoAuthManager] Access token expired or not found for tenant {self.tenant_id}. Attempting to refresh...")
        if not all([self.client_id, self.client_secret, refresh_token, self.accounts_url]):
            logger.error(f"[ZohoAuthManager ERROR] Missing Zoho credentials for tenant {self.tenant_id}. Cannot generate access token.")
            return None

        token_url = f"{self.accounts_url}/oauth/v2/token"
        payload = {
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post(token_url, data=payload, headers=headers)
            response.raise_for_status() # Raise an exception for HTTP errors
            token_data = response.json()

            if "access_token" in token_data:
                self._current_access_token = token_data["access_token"]
                # Zoho access tokens typically last 3600 seconds (1 hour)
                self._access_token_expiry_time = time.time() + token_data.get("expires_in", 3600) - 60 # Subtract 60s buffer
                logger.info(f"[ZohoAuthManager] Successfully refreshed access token for tenant {self.tenant_id}.")
                return self._current_access_token
            else:
                logger.error(f"[ZohoAuthManager ERROR] Failed to get access token for tenant {self.tenant_id}: {token_data.get('error', 'Unknown error')}")
                logger.error(f"[ZohoAuthManager ERROR] Full Zoho Response: {json.dumps(token_data, indent=2)}")
                # If refresh token is invalid, delete it so next time it prompts for re-auth
                if token_data.get('error') == 'invalid_code' or token_data.get('error') == 'invalid_grant':
                    logger.warning(f"[ZohoAuthManager] Invalid refresh token detected for tenant {self.tenant_id}. Deleting local token file.")
                    if os.path.exists(self.refresh_token_file):
                        os.remove(self.refresh_token_file)
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"[ZohoAuthManager ERROR] Network or HTTP error during token refresh for tenant {self.tenant_id}: {e}")
            return None
        except json.JSONDecodeError:
            logger.error(f"[ZohoAuthManager ERROR] Invalid JSON response from Zoho for tenant {self.tenant_id}: {response.text}")
            return None
        except Exception as e:
            logger.error(f"[ZohoAuthManager ERROR] An unexpected error occurred during token refresh for tenant {self.tenant_id}: {e}")
            return None

    def exchange_authorization_code_for_tokens(self, auth_code: str, redirect_uri: str) -> bool:
        """
        Exchanges an authorization code for access and refresh tokens.
        Saves the refresh token to a tenant-specific file.
        Args:
            auth_code (str): The authorization code received from Zoho.
            redirect_uri (str): The redirect URI used in the authorization request.
        Returns:
            bool: True if successful, False otherwise.
        """
        token_url = f"{self.accounts_url}/oauth/v2/token"
        payload = {
            "code": auth_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            logger.info(f"[ZohoAuthManager] Exchanging authorization code for tokens for tenant {self.tenant_id}...")
            response = requests.post(token_url, data=payload, headers=headers)
            response.raise_for_status()
            token_data = response.json()

            if "refresh_token" in token_data and "access_token" in token_data:
                self._save_refresh_token(token_data["refresh_token"])
                # Also set the current access token for immediate use
                self._current_access_token = token_data["access_token"]
                self._access_token_expiry_time = time.time() + token_data.get("expires_in", 3600) - 60
                logger.info(f"[ZohoAuthManager] Successfully obtained and saved refresh token for tenant {self.tenant_id}.")
                return True
            else:
                logger.error(f"[ZohoAuthManager ERROR] Failed to exchange code for tokens for tenant {self.tenant_id}: {token_data.get('error', 'Unknown error')}")
                logger.error(f"[ZohoAuthManager ERROR] Full Zoho Response: {json.dumps(token_data, indent=2)}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"[ZohoAuthManager ERROR] Network or HTTP error during code exchange for tenant {self.tenant_id}: {e}")
            return False
        except json.JSONDecodeError:
            logger.error(f"[ZohoAuthManager ERROR] Invalid JSON response from Zoho during code exchange for tenant {self.tenant_id}: {response.text}")
            return False
        except Exception as e:
            logger.error(f"[ZohoAuthManager ERROR] An unexpected error occurred during code exchange for tenant {self.tenant_id}: {e}")
            return False

