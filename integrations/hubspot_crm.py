import os
import requests
import json
import logging

logger = logging.getLogger(__name__)

class HubSpotCRM:
    def __init__(self, api_key: str, tenant_id: str):
        self.hubspot_api_key = api_key
        self.tenant_id = tenant_id
        if not self.hubspot_api_key:
            raise ValueError("HubSpot API Key is not provided for HubSpotCRM initialization.")

        self.hubspot_api_url = "https://api.hubapi.com/crm/v3/objects/contacts"
        logger.info(f"[HubSpotCRM] Initialized for tenant: {tenant_id}.")

    def search_lead(self, phone_number: str) -> dict | None:
        """
        Searches for a contact in HubSpot by phone number.
        Args:
            phone_number (str): The phone number to search for.
        Returns:
            dict | None: The contact record if found, otherwise None.
        """
        search_url = f"{self.hubspot_api_url}/search"
        headers = {
            "Authorization": f"Bearer {self.hubspot_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "phone",
                            "operator": "EQ",
                            "value": phone_number
                        }
                    ]
                }
            ],
            "properties": ["firstname", "lastname", "email", "phone"], # Properties to return
            "limit": 1 # We only need one match
        }

        try:
            logger.info(f"[HubSpotCRM] Searching for contact with phone: {phone_number} for tenant {self.tenant_id}.")
            response = requests.post(search_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get('results') and len(data['results']) > 0:
                contact = data['results'][0]
                logger.info(f"[HubSpotCRM] Contact found for tenant {self.tenant_id}: {contact['properties'].get('firstname', '')} {contact['properties'].get('lastname', '')}")
                return contact['properties'] # Return the properties dictionary
            else:
                logger.info(f"[HubSpotCRM] No contact found for phone: {phone_number} for tenant {self.tenant_id}.")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"[HubSpotCRM ERROR] HTTP error during contact search for tenant {self.tenant_id}: {e}")
            if response and response.text:
                logger.error(f"[HubSpotCRM ERROR] HubSpot API Response: {response.text}")
            return None
        except json.JSONDecodeError:
            logger.error(f"[HubSpotCRM ERROR] Invalid JSON response during contact search for tenant {self.tenant_id}: {response.text}")
            return None
        except Exception as e:
            logger.error(f"[HubSpotCRM ERROR] An unexpected error occurred during contact search for tenant {self.tenant_id}: {e}")
            return None

    def create_lead(self, lead_data: dict) -> dict | None:
        """
        Creates a new contact in HubSpot from a normalized lead_data dictionary.
        Args:
            lead_data (dict): Normalized lead data containing 'first_name', 'last_name', 'email', 'phone'.
        Returns:
            dict | None: The created contact record details if successful, otherwise None.
        """
        create_url = self.hubspot_api_url
        headers = {
            "Authorization": f"Bearer {self.hubspot_api_key}",
            "Content-Type": "application/json"
        }

        properties = {
            "firstname": lead_data.get('first_name', ''),
            "lastname": lead_data.get('last_name', ''),
            "email": lead_data.get('email', ''),
            "phone": lead_data.get('phone', '')
            # You can add other properties here, e.g., "lead_source": "WhatsApp Bot"
        }

        # Filter out empty properties to avoid issues with HubSpot API if a field is not required
        properties = {k: v for k, v in properties.items() if v}

        payload = {
            "properties": properties
        }

        try:
            logger.info(f"[HubSpotCRM] Creating new contact: {properties.get('firstname', '')} {properties.get('lastname', '')} ({properties.get('phone', '')}) for tenant {self.tenant_id}.")
            response = requests.post(create_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get('id'): # HubSpot returns the created contact object directly
                created_contact_id = data['id']
                logger.info(f"[HubSpotCRM] Contact created successfully with ID: {created_contact_id} for tenant {self.tenant_id}.")
                return data['properties'] # Return the properties of the created contact
            else:
                logger.error(f"[HubSpotCRM ERROR] Failed to create contact for tenant {self.tenant_id}: {data.get('message', 'Unknown error')}")
                if response and response.text:
                    logger.error(f"[HubSpotCRM ERROR] HubSpot API Response: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"[HubSpotCRM ERROR] HTTP error during contact creation for tenant {self.tenant_id}: {e}")
            if response and response.text:
                logger.error(f"[HubSpotCRM ERROR] HubSpot API Response: {response.text}")
            return None
        except json.JSONDecodeError:
            logger.error(f"[HubSpotCRM ERROR] Invalid JSON response during contact creation for tenant {self.tenant_id}: {response.text}")
            return None
        except Exception as e:
            logger.error(f"[HubSpotCRM ERROR] An unexpected error occurred during contact creation for tenant {self.tenant_id}: {e}")
            return None

