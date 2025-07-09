import requests
import json
import os
from dotenv import load_dotenv
from zoho_auth import get_access_token # Import the auth function

load_dotenv()
ZOHO_API_URL = os.getenv("ZOHO_API_URL")

def search_lead_by_phone(phone_number: str) -> dict | None:
    """
    Searches for a lead in Zoho CRM by phone number.
    Args:
        phone_number (str): The phone number to search for.
    Returns:
        dict | None: The lead record if found, otherwise None.
    """
    access_token = get_access_token()
    if not access_token:
        print("[Zoho Leads ERROR] Could not get access token for searching leads.")
        return None

    # Zoho CRM API for searching records (CRM.coql module or search endpoint)
    # Using search records endpoint for simplicity
    search_url = f"{ZOHO_API_URL}/crm/v2/Leads/search"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    params = {
        "phone": phone_number # Assuming 'Phone' is the field for search
    }

    try:
        print(f"[Zoho Leads] Searching for lead with phone: {phone_number}")
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get('data') and len(data['data']) > 0:
            print(f"[Zoho Leads] Lead found: {data['data'][0].get('Full_Name', 'Unknown')}")
            return data['data'][0] # Return the first lead found
        else:
            print(f"[Zoho Leads] No lead found for phone: {phone_number}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[Zoho Leads ERROR] HTTP error during lead search: {e}")
        if response and response.text:
            print(f"[Zoho Leads ERROR] Zoho API Response: {response.text}")
        return None
    except json.JSONDecodeError:
        print(f"[Zoho Leads ERROR] Invalid JSON response during lead search: {response.text}")
        return None
    except Exception as e:
        print(f"[Zoho Leads ERROR] An unexpected error occurred during lead search: {e}")
        return None

def create_lead(first_name: str, email: str, phone: str, last_name: str = None) -> dict | None:
    """
    Creates a new lead in Zoho CRM.
    Args:
        first_name (str): The first name of the lead.
        email (str): The email of the lead.
        phone (str): The phone number of the lead.
        last_name (str, optional): The last name of the lead. If None, derived from first_name.
    Returns:
        dict | None: The created lead record if successful, otherwise None.
    """
    access_token = get_access_token()
    if not access_token:
        print("[Zoho Leads ERROR] Could not get access token for creating lead.")
        return None

    # Derive last_name if not provided
    if last_name is None:
        name_parts = first_name.strip().split()
        if len(name_parts) > 1:
            # If multiple words, assume last word is last name
            derived_last_name = name_parts[-1]
            first_name_for_zoho = " ".join(name_parts[:-1]) # Use all but last word for first name
        else:
            # If only one word, use it for both first and last name (Zoho mandatory)
            derived_last_name = first_name
            first_name_for_zoho = first_name
    else:
        derived_last_name = last_name
        first_name_for_zoho = first_name

    create_url = f"{ZOHO_API_URL}/crm/v2/Leads"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }

    # Construct the lead data payload
    lead_data = {
        "data": [
            {
                "First_Name": first_name_for_zoho,
                "Last_Name": derived_last_name, # Use derived or provided last name
                "Email": email,
                "Phone": phone,
                # Add other fields as needed, e.g., "Lead_Source": "WhatsApp Chatbot"
            }
        ]
    }

    try:
        print(f"[Zoho Leads] Creating new lead: {first_name_for_zoho} {derived_last_name} ({phone})")
        response = requests.post(create_url, headers=headers, json=lead_data)
        response.raise_for_status()
        data = response.json()

        if data.get('data') and len(data['data']) > 0 and data['data'][0].get('status') == 'success':
            created_lead_id = data['data'][0]['details']['id']
            print(f"[Zoho Leads] Lead created successfully with ID: {created_lead_id}")
            return data['data'][0]['details']
        else:
            print(f"[Zoho Leads ERROR] Failed to create lead: {data.get('message', 'Unknown error')}")
            if response and response.text:
                print(f"[Zoho Leads ERROR] Zoho API Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[Zoho Leads ERROR] HTTP error during lead creation: {e}")
        if response and response.text:
            print(f"[Zoho Leads ERROR] Zoho API Response: {response.text}")
        return None
    except json.JSONDecodeError:
        print(f"[Zoho Leads ERROR] Invalid JSON response during lead creation: {response.text}")
        return None
    except Exception as e:
        print(f"[Zoho Leads ERROR] An unexpected error occurred during lead creation: {e}")
        return None

