import json
import os
import logging

logger = logging.getLogger(__name__)

# Define the path to the tenants.json file relative to the project root
# Assuming utils/tenant_loader.py is in chat_rag_app_exercise6/utils/
# and tenants.json is in chat_rag_app_exercise6/config/
_TENANTS_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'tenants.json')

_TENANTS_CACHE = {} # Cache to store loaded tenant configurations

def load_all_tenants_config() -> dict:
    """
    Loads all tenant configurations from the tenants.json file.
    Returns:
        dict: A dictionary containing all tenant configurations.
    """
    if not os.path.exists(_TENANTS_CONFIG_PATH):
        logger.error(f"Tenants configuration file not found at: {_TENANTS_CONFIG_PATH}")
        return {"tenants": []} # Return empty list if file not found

    try:
        with open(_TENANTS_CONFIG_PATH, 'r') as f:
            config = json.load(f)

        # Populate cache
        _TENANTS_CACHE.clear()
        for tenant in config.get('tenants', []):
            tenant_id = tenant.get('tenant_id')
            if tenant_id:
                _TENANTS_CACHE[tenant_id] = tenant

        logger.info(f"Loaded {len(_TENANTS_CACHE)} tenant configurations from {_TENANTS_CONFIG_PATH}")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding tenants.json: {e}")
        return {"tenants": []}
    except Exception as e:
        logger.error(f"An unexpected error occurred loading tenants.json: {e}")
        return {"tenants": []}

def get_tenant_config(tenant_id: str) -> dict | None:
    """
    Retrieves the configuration for a specific tenant ID.
    Args:
        tenant_id (str): The ID of the tenant to retrieve.
    Returns:
        dict | None: The tenant's configuration dictionary if found, otherwise None.
    """
    if not _TENANTS_CACHE: # Load if cache is empty
        load_all_tenants_config()

    return _TENANTS_CACHE.get(tenant_id)

# Load tenants on module import
load_all_tenants_config()

