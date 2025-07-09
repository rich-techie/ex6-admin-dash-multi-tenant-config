import json
import os
import logging
from integrations.zoho_crm import ZohoCRM
from integrations.hubspot_crm import HubSpotCRM
from console_chatbot.zoho_auth_manager import ZohoAuthManager # Import the new ZohoAuthManager

logger = logging.getLogger(__name__)

class CRMRouter:
    def __init__(self, active_tenant_config: dict):
        self.active_tenant_config = active_tenant_config
        self.active_crm_name = active_tenant_config.get('crm')
        self.tenant_id = active_tenant_config.get('tenant_id', 'default_tenant') # Get tenant_id
        self.crm_instances = {}
        self._initialize_active_crm()
        logger.info(f"[CRMRouter] Initialized for tenant: {self.tenant_id}. Active CRM: {self.active_crm_name}")

    def _initialize_active_crm(self):
        """Initializes only the active CRM instance based on tenant configuration."""
        if not self.active_crm_name or self.active_crm_name == 'none':
            logger.info(f"[CRMRouter] No CRM configured for tenant {self.tenant_id}.")
            return

        if self.active_crm_name == 'zoho':
            zoho_config = self.active_tenant_config.get('zoho', {})
            if not all([zoho_config.get('client_id'), zoho_config.get('client_secret'),
                        zoho_config.get('accounts_url'), zoho_config.get('api_url')]):
                logger.error(f"Zoho CRM credentials incomplete for tenant {self.tenant_id}. Zoho CRM will not be initialized.")
                return

            # Instantiate ZohoAuthManager for this tenant
            zoho_auth_manager = ZohoAuthManager(
                client_id=zoho_config['client_id'],
                client_secret=zoho_config['client_secret'],
                accounts_url=zoho_config['accounts_url'],
                api_url=zoho_config['api_url'], # Pass api_url for context, though auth manager doesn't use it directly
                tenant_id=self.tenant_id
            )
            self.crm_instances['zoho'] = ZohoCRM(auth_manager=zoho_auth_manager, api_url=zoho_config['api_url'])

        elif self.active_crm_name == 'hubspot':
            hubspot_config = self.active_tenant_config.get('hubspot', {})
            if not hubspot_config.get('api_key'):
                logger.error(f"HubSpot API Key incomplete for tenant {self.tenant_id}. HubSpot CRM will not be initialized.")
                return
            self.crm_instances['hubspot'] = HubSpotCRM(api_key=hubspot_config['api_key'], tenant_id=self.tenant_id)

        else:
            logger.error(f"Unsupported active CRM '{self.active_crm_name}' for tenant {self.tenant_id}.")

    def get_active_crm_instance(self):
        """Returns the initialized instance of the active CRM."""
        if self.active_crm_name == 'none' or self.active_crm_name not in self.crm_instances:
            return None # No active CRM or it failed to initialize
        return self.crm_instances[self.active_crm_name]

    def create_lead(self, normalized_lead_data: dict) -> dict | None:
        """
        Routes the normalized lead data to the active CRM for creation.
        """
        crm_instance = self.get_active_crm_instance()
        if crm_instance:
            logger.info(f"[CRMRouter] Routing lead creation to {self.active_crm_name} CRM for tenant {self.tenant_id}.")
            return crm_instance.create_lead(normalized_lead_data)
        logger.warning(f"[CRMRouter] No active CRM to create lead for tenant {self.tenant_id}.")
        return None

    def search_lead(self, phone_number: str) -> dict | None:
        """
        Routes the phone number to the active CRM for lead search.
        """
        crm_instance = self.get_active_crm_instance()
        if crm_instance:
            logger.info(f"[CRMRouter] Routing lead search to {self.active_crm_name} CRM for tenant {self.tenant_id}.")
            return crm_instance.search_lead(phone_number)
        logger.warning(f"[CRMRouter] No active CRM to search lead for tenant {self.tenant_id}.")
        return None

