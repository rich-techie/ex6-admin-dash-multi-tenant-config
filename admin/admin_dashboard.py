import streamlit as st
import json
import os
import sys

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Import the tenant loader (for saving/loading tenants.json)
from utils.tenant_loader import load_all_tenants_config # Using this to ensure cache clearing

# Define the path to the tenants.json file
TENANTS_FILE_PATH = os.path.join(project_root, 'config', 'tenants.json')

def load_tenants_from_file():
    """Loads tenant data from tenants.json."""
    try:
        with open(TENANTS_FILE_PATH, 'r') as f:
            return json.load(f).get('tenants', [])
    except FileNotFoundError:
        st.error(f"Error: {TENANTS_FILE_PATH} not found. Please create it with an empty 'tenants' list if it's new.")
        return []
    except json.JSONDecodeError:
        st.error(f"Error: Invalid JSON in {TENANTS_FILE_PATH}. Please check its format.")
        return []

def save_tenants_to_file(tenants_list):
    """Saves tenant data to tenants.json."""
    try:
        with open(TENANTS_FILE_PATH, 'w') as f:
            json.dump({"tenants": tenants_list}, f, indent=2)
        st.success("Tenant configuration saved successfully!")
        # Crucial: Clear and reload the cache in tenant_loader to ensure consistency
        from utils.tenant_loader import _TENANTS_CACHE # Access the private cache
        _TENANTS_CACHE.clear()
        load_all_tenants_config() # Reload the cache with updated data
    except Exception as e:
        st.error(f"Error saving tenant configuration: {e}")

def get_empty_form_data_template():
    """Returns a template for new tenant form data, including all possible fields."""
    return {
        "tenant_id": "",
        "name": "",
        "crm": "none",
        "branding_welcome_message": "Welcome! How can I assist you today?",
        "branding_logo_url": "",
        "zoho_client_id": "",
        "zoho_client_secret": "",
        "zoho_refresh_token": "",
        "zoho_accounts_url": "https://accounts.zoho.in",
        "zoho_api_url": "https://www.zohoapis.in",
        "hubspot_api_key": ""
    }

def initialize_form_data_from_tenant(tenant_data):
    """
    Populates st.session_state.form_data with values from a given tenant dictionary.
    This is the core function for loading data into the form.
    """
    st.session_state.form_data['tenant_id'] = tenant_data.get("tenant_id", "")
    st.session_state.form_data['name'] = tenant_data.get("name", "")
    st.session_state.form_data['crm'] = tenant_data.get("crm", "none")
    st.session_state.form_data['branding_welcome_message'] = tenant_data.get("branding", {}).get("welcome_message", "")
    st.session_state.form_data['branding_logo_url'] = tenant_data.get("branding", {}).get("logo_url", "")

    # Always populate all CRM fields in form_data, regardless of current CRM choice
    st.session_state.form_data['zoho_client_id'] = tenant_data.get("zoho", {}).get("client_id", "")
    st.session_state.form_data['zoho_client_secret'] = tenant_data.get("zoho", {}).get("client_secret", "")
    st.session_state.form_data['zoho_refresh_token'] = tenant_data.get("zoho", {}).get("refresh_token", "")
    st.session_state.form_data['zoho_accounts_url'] = tenant_data.get("zoho", {}).get("accounts_url", "https://accounts.zoho.in")
    st.session_state.form_data['zoho_api_url'] = tenant_data.get("zoho", {}).get("api_url", "https://www.zohoapis.in")

    st.session_state.form_data['hubspot_api_key'] = tenant_data.get("hubspot", {}).get("api_key", "")

# Callback function to update st.session_state.form_data when a widget changes
def update_form_data_callback(key_in_form_data, widget_key):
    """
    Generic callback to update a specific field in st.session_state.form_data
    from the value of a Streamlit widget.
    """
    st.session_state.form_data[key_in_form_data] = st.session_state[widget_key]

def app():
    st.set_page_config(page_title="Multi-Tenant Admin Dashboard", layout="wide")
    st.title("Admin Dashboard: Manage Tenants")

    # --- Session State Initialization (Centralized) ---
    if 'tenants' not in st.session_state:
        st.session_state.tenants = load_tenants_from_file()

    # 'current_editing_tenant_id' stores the ID of the tenant currently loaded into the form for editing
    # None means "Add New Tenant" mode.
    if 'current_editing_tenant_id' not in st.session_state:
        st.session_state.current_editing_tenant_id = None

    # 'form_data' is the single source of truth for all form field values
    if 'form_data' not in st.session_state:
        st.session_state.form_data = get_empty_form_data_template()
        # Initialize form data on first load
        initialize_form_data_from_tenant(get_empty_form_data_template())

    # --- Tenant List and Selection ---
    st.header("Existing Tenants")

    tenant_display_names = ["-- Add New Tenant --"] + [f"{t['name']} ({t['tenant_id']})" for t in st.session_state.tenants]

    # Determine the initial index for the selectbox based on the last edited/selected tenant
    initial_selectbox_index = 0
    if st.session_state.current_editing_tenant_id:
        try:
            # Find the index of the previously selected tenant in the new list
            # +1 because of "-- Add New Tenant --" at index 0
            idx = next(i for i, t in enumerate(st.session_state.tenants) if t['tenant_id'] == st.session_state.current_editing_tenant_id)
            initial_selectbox_index = idx + 1
        except StopIteration:
            # If the previously selected tenant was deleted or not found, default to "Add New Tenant"
            initial_selectbox_index = 0

    # Capture the value of the selectbox from the previous run for change detection
    # This ensures we only re-initialize form_data when the selectbox selection actually changes
    previous_selected_tenant_display = st.session_state.get('tenant_selector_value_on_last_run', tenant_display_names[initial_selectbox_index])

    selected_tenant_display = st.selectbox(
        "Select a Tenant to Edit:",
        tenant_display_names,
        index=initial_selectbox_index,
        key="tenant_selector" # This key holds the current selection
    )

    # Store the current selectbox value for comparison in the next rerun
    st.session_state.tenant_selector_value_on_last_run = selected_tenant_display

    # Logic to re-populate form_data only when the tenant selection changes
    # This is crucial for loading correct data when switching tenants.
    if selected_tenant_display != previous_selected_tenant_display:
        if selected_tenant_display == "-- Add New Tenant --":
            st.session_state.current_editing_tenant_id = None
            initialize_form_data_from_tenant(get_empty_form_data_template())
            st.rerun() # Force rerun to clear form fields
        else:
            # Extract tenant_id from selected_tenant_display (e.g., "Tenant Name (tenant_id)")
            selected_tenant_id_from_display = selected_tenant_display.split('(')[1].rstrip(')')
            found_tenant = next((t for t in st.session_state.tenants if t['tenant_id'] == selected_tenant_id_from_display), None)

            if found_tenant:
                st.session_state.current_editing_tenant_id = found_tenant['tenant_id']
                initialize_form_data_from_tenant(found_tenant.copy()) # Use a copy to avoid direct modification
                st.rerun() # Force rerun to populate form fields
            else:
                # Fallback if selected tenant not found (e.g., deleted by another session)
                st.session_state.current_editing_tenant_id = None
                initialize_form_data_from_tenant(get_empty_form_data_template())
                st.rerun() # Reset to Add New Tenant

    # Set the subheader based on current mode
    if st.session_state.current_editing_tenant_id is None:
        st.subheader("Add New Tenant")
    else:
        st.subheader(f"Edit Tenant: {st.session_state.form_data['name']}")

    # --- Tenant Configuration Form Fields ---
    # These fields are outside the st.form to allow immediate updates to session state
    # and dynamic rendering of CRM fields.

    col_main_form, col_crm_fields = st.columns([1, 1])

    with col_main_form:
        st.markdown("---")
        st.subheader("Tenant Details")

        st.text_input(
            "Tenant ID (Unique Identifier):",
            value=st.session_state.form_data['tenant_id'],
            key="tenant_id_input",
            on_change=update_form_data_callback, args=('tenant_id', "tenant_id_input")
        )
        st.text_input(
            "Tenant Name:",
            value=st.session_state.form_data['name'],
            key="tenant_name_input",
            on_change=update_form_data_callback, args=('name', "tenant_name_input")
        )

        crm_options = ["none", "zoho", "hubspot"]
        current_crm_choice_index = crm_options.index(st.session_state.form_data['crm'])
        st.selectbox(
            "CRM Choice:",
            crm_options,
            index=current_crm_choice_index,
            key="crm_choice_select", # This key holds the selected CRM
            on_change=update_form_data_callback, args=('crm', "crm_choice_select")
        )

        st.subheader("Branding")
        st.text_area(
            "Welcome Message:",
            value=st.session_state.form_data['branding_welcome_message'],
            key="welcome_message_input",
            on_change=update_form_data_callback, args=('branding_welcome_message', "welcome_message_input")
        )
        st.text_input(
            "Logo URL:",
            value=st.session_state.form_data['branding_logo_url'],
            key="logo_url_input",
            on_change=update_form_data_callback, args=('branding_logo_url', "logo_url_input")
        )

    with col_crm_fields:
        st.markdown("---")
        st.subheader("CRM Credentials")

        # Use the current CRM choice from st.session_state.form_data for conditional rendering
        current_crm_selection_for_display = st.session_state.form_data['crm']

        if current_crm_selection_for_display == "zoho":
            st.info("Ensure you have generated a Zoho Refresh Token for this tenant via Zoho API Console and a manual OAuth flow if needed.")
            st.text_input(
                "Zoho Client ID:",
                value=st.session_state.form_data['zoho_client_id'],
                key="zoho_client_id_input",
                on_change=update_form_data_callback, args=('zoho_client_id', "zoho_client_id_input")
            )
            st.text_input(
                "Zoho Client Secret:",
                value=st.session_state.form_data['zoho_client_secret'],
                type="password",
                key="zoho_client_secret_input",
                on_change=update_form_data_callback, args=('zoho_client_secret', "zoho_client_secret_input")
            )
            st.text_input(
                "Zoho Refresh Token:",
                value=st.session_state.form_data['zoho_refresh_token'],
                type="password", help="This token is long-lived and used to get new access tokens.",
                key="zoho_refresh_token_input",
                on_change=update_form_data_callback, args=('zoho_refresh_token', "zoho_refresh_token_input")
            )
            st.text_input(
                "Zoho Accounts URL:",
                value=st.session_state.form_data['zoho_accounts_url'],
                key="zoho_accounts_url_input",
                on_change=update_form_data_callback, args=('zoho_accounts_url', "zoho_accounts_url_input")
            )
            st.text_input(
                "Zoho API URL:",
                value=st.session_state.form_data['zoho_api_url'],
                key="zoho_api_url_input",
                on_change=update_form_data_callback, args=('zoho_api_url', "zoho_api_url_input")
            )

        elif current_crm_selection_for_display == "hubspot":
            st.info("Ensure you have created a HubSpot Private App for this tenant and granted `crm.objects.contacts.read` and `crm.objects.contacts.write` scopes.")
            st.text_input(
                "HubSpot API Key (Private App Access Token):",
                value=st.session_state.form_data['hubspot_api_key'],
                type="password",
                key="hubspot_api_key_input",
                on_change=update_form_data_callback, args=('hubspot_api_key', "hubspot_api_key_input")
            )

        else: # crm_choice == "none"
            st.info("No CRM selected. No credentials required.")

    # --- Save and Delete Buttons (in their own form) ---
    with st.form("save_delete_form", clear_on_submit=False):
        st.markdown("---")

        # The submit button for saving
        submitted = st.form_submit_button("Save Tenant Configuration", type="primary")

        if submitted:
            # Construct new_tenant_data by reading directly from st.session_state.form_data.
            # This ensures that even fields that were not currently visible (e.g., Zoho fields when HubSpot was selected)
            # still have their values retained and saved.
            new_tenant_data = {
                "tenant_id": st.session_state.form_data['tenant_id'],
                "name": st.session_state.form_data['name'],
                "crm": st.session_state.form_data['crm'],
                "branding": {
                    "welcome_message": st.session_state.form_data['branding_welcome_message'],
                    "logo_url": st.session_state.form_data['branding_logo_url']
                },
                # Always include both CRM credential dictionaries,
                # populated with their current values from st.session_state.form_data
                "zoho": {
                    "client_id": st.session_state.form_data['zoho_client_id'],
                    "client_secret": st.session_state.form_data['zoho_client_secret'],
                    "refresh_token": st.session_state.form_data['zoho_refresh_token'],
                    "accounts_url": st.session_state.form_data['zoho_accounts_url'],
                    "api_url": st.session_state.form_data['zoho_api_url']
                },
                "hubspot": {
                    "api_key": st.session_state.form_data['hubspot_api_key']
                }
            }

            # Validation
            if not new_tenant_data["tenant_id"] or not new_tenant_data["name"]:
                st.error("Tenant ID and Tenant Name cannot be empty.")
            elif new_tenant_data["crm"] == "zoho" and (
                not new_tenant_data["zoho"]["client_id"] or
                not new_tenant_data["zoho"]["client_secret"] or
                not new_tenant_data["zoho"]["refresh_token"]
            ):
                st.error("Zoho CRM selected: Client ID, Client Secret, and Refresh Token are required.")
            elif new_tenant_data["crm"] == "hubspot" and not new_tenant_data["hubspot"]["api_key"]:
                st.error("HubSpot CRM selected: API Key is required.")
            else:
                if st.session_state.current_editing_tenant_id is None:
                    # Add new tenant
                    if any(t['tenant_id'] == new_tenant_data["tenant_id"] for t in st.session_state.tenants):
                        st.error(f"Tenant ID '{new_tenant_data['tenant_id']}' already exists. Please choose a unique ID.")
                    else:
                        st.session_state.tenants.append(new_tenant_data)
                        save_tenants_to_file(st.session_state.tenants)
                        # Reset form and selection for adding another new tenant
                        st.session_state.current_editing_tenant_id = None
                        initialize_form_data_from_tenant(get_empty_form_data_template())
                        st.rerun() # Rerun to clear form and update selectbox
                else:
                    # Edit existing tenant
                    # Find the index of the tenant being edited by its ID
                    idx_to_update = next((i for i, t in enumerate(st.session_state.tenants) if t['tenant_id'] == st.session_state.current_editing_tenant_id), -1)
                    if idx_to_update != -1:
                        st.session_state.tenants[idx_to_update] = new_tenant_data
                        save_tenants_to_file(st.session_state.tenants)
                        # Keep the same tenant selected after edit, but re-populate form to ensure consistency
                        initialize_form_data_from_tenant(new_tenant_data)
                        st.rerun() # Rerun to update selectbox (if name changed) and ensure form is consistent
                    else:
                        st.error("Error: Could not find the tenant to update. It might have been deleted.")

    # Delete Tenant Button (outside the form)
    # This button needs to be outside the 'st.form' that contains st.form_submit_button
    if st.session_state.current_editing_tenant_id is not None:
        st.markdown("---") # Add a separator for clarity
        if st.button(f"Delete Tenant: {st.session_state.form_data['name']}", type="secondary", key="delete_button"):
            st.warning(f"Deleting tenant '{st.session_state.form_data['name']}'. This action is irreversible.")

            # Remove the tenant from the list
            st.session_state.tenants = [
                t for t in st.session_state.tenants
                if t['tenant_id'] != st.session_state.current_editing_tenant_id
            ]
            save_tenants_to_file(st.session_state.tenants)

            # After deleting, reset the form to "Add New Tenant" mode
            st.session_state.current_editing_tenant_id = None
            initialize_form_data_from_tenant(get_empty_form_data_template())
            st.rerun() # Rerun to update selectbox and clear form

if __name__ == "__main__":
    app()
