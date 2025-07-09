import requests
import json
import os
# Removed: from dotenv import load_dotenv # Load dotenv only in main entry point
from console_chatbot.zoho_auth_manager import ZohoAuthManager # Import the new ZohoAuthManager class

class ZohoCRM:
    def __init__(self, auth_manager: ZohoAuthManager, api_url: str):
        self.auth_manager = auth_manager
        self.api_url = api_url
        if not self.api_url:
            raise ValueError("ZOHO_API_URL is not set for ZohoCRM initialization.")
        print(f"[ZohoCRM] Initialized for tenant: {auth_manager.tenant_id}.")

    def search_lead(self, phone_number: str) -> dict | None:
        """
        Searches for a lead in Zoho CRM by phone number.
        Args:
            phone_number (str): The phone number to search for.
        Returns:
            dict | None: The lead record if found, otherwise None.
        """
        access_token = self.auth_manager.get_access_token()
        if not access_token:
            print(f"[ZohoCRM ERROR] Could not get access token for searching leads for tenant {self.auth_manager.tenant_id}.")
            return None

        search_url = f"{self.api_url}/crm/v2/Leads/search"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}"
        }
        params = {
            "phone": phone_number # Assuming 'Phone' is the field for search
        }

        try:
            print(f"[ZohoCRM] Searching for lead with phone: {phone_number} for tenant {self.auth_manager.tenant_id}.")
            response = requests.get(search_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get('data') and len(data['data']) > 0:
                print(f"[ZohoCRM] Lead found for tenant {self.auth_manager.tenant_id}: {data['data'][0].get('Full_Name', 'Unknown')}")
                return data['data'][0] # Return the first lead found
            else:
                print(f"[ZohoCRM] No lead found for phone: {phone_number} for tenant {self.auth_manager.tenant_id}.")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ZohoCRM ERROR] HTTP error during lead search for tenant {self.auth_manager.tenant_id}: {e}")
            if response and response.text:
                print(f"[ZohoCRM ERROR] Zoho API Response: {response.text}")
            return None
        except json.JSONDecodeError:
            print(f"[ZohoCRM ERROR] Invalid JSON response during lead search for tenant {self.auth_manager.tenant_id}: {response.text}")
            return None
        except Exception as e:
            print(f"[ZohoCRM ERROR] An unexpected error occurred during lead search for tenant {self.auth_manager.tenant_id}: {e}")
            return None

    def create_lead(self, lead_data: dict) -> dict | None:
        """
        Creates a new lead in Zoho CRM from a normalized lead_data dictionary.
        Args:
            lead_data (dict): Normalized lead data containing 'first_name', 'last_name', 'email', 'phone'.
        Returns:
            dict | None: The created lead record if successful, otherwise None.
        """
        access_token = self.auth_manager.get_access_token()
        if not access_token:
            print(f"[ZohoCRM ERROR] Could not get access token for creating lead for tenant {self.auth_manager.tenant_id}.")
            return None

        # Extract data from the normalized lead_data
        first_name = lead_data.get('first_name', '')
        last_name = lead_data.get('last_name', '')
        email = lead_data.get('email', '')
        phone = lead_data.get('phone', '')

        # Zoho's Last_Name is mandatory. If not provided, use first_name as fallback.
        if not last_name and first_name:
            last_name = first_name
        elif not last_name and not first_name:
            # Fallback if both are missing, though parser should prevent this
            last_name = "Unknown"

        create_url = f"{self.api_url}/crm/v2/Leads"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "data": [
                {
                    "First_Name": first_name,
                    "Last_Name": last_name,
                    "Email": email,
                    "Phone": phone,
                    # Add other fields as needed, e.g., "Lead_Source": "WhatsApp Chatbot"
                }
            ]
        }

        try:
            print(f"[ZohoCRM] Creating new lead: {first_name} {last_name} ({phone}) for tenant {self.auth_manager.tenant_id}.")
            response = requests.post(create_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get('data') and len(data['data']) > 0 and data['data'][0].get('status') == 'success':
                created_lead_id = data['data'][0]['details']['id']
                print(f"[ZohoCRM] Lead created successfully with ID: {created_lead_id} for tenant {self.auth_manager.tenant_id}.")
                return data['data'][0]['details']
            else:
                print(f"[ZohoCRM ERROR] Failed to create lead for tenant {self.auth_manager.tenant_id}: {data.get('message', 'Unknown error')}")
                if response and response.text:
                    print(f"[ZohoCRM ERROR] Zoho API Response: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ZohoCRM ERROR] HTTP error during lead creation for tenant {self.auth_manager.tenant_id}: {e}")
            if response and response.text:
                print(f"[ZohoCRM ERROR] Zoho API Response: {response.text}")
            return None
        except json.JSONDecodeError:
            print(f"[ZohoCRM ERROR] Invalid JSON response during lead creation for tenant {self.auth_manager.tenant_id}: {response.text}")
            return None
        except Exception as e:
            print(f"[ZohoCRM ERROR] An unexpected error occurred during lead creation for tenant {self.auth_manager.tenant_id}: {e}")
            return None

