<div contenteditable="true" translate="no" class="ProseMirror"><h1>Multi-Tenant Admin Dashboard with WhatsApp Bot Integration (Exercise 6)</h1><p>This project builds upon the CRM-agnostic chatbot from Exercise 5 by introducing a <strong>multi-tenant architecture</strong> managed via a Streamlit administrative dashboard. This allows different "tenants" (e.g., businesses, departments) to use the same chatbot infrastructure with their own distinct configurations, including CRM integrations and branding.</p><h2>Features</h2><ul><li><p><strong>Multi-Tenant Support:</strong> The bot can serve multiple tenants, each with its own configuration.</p></li><li><p><strong>Streamlit Admin Dashboard:</strong> A user-friendly web interface to:</p><ul><li><p>Add new tenants.</p></li><li><p>View and edit existing tenant configurations (name, branding, CRM type).</p></li><li><p>Configure CRM credentials (Zoho Client ID/Secret, HubSpot API Key) per tenant.</p></li><li><p>Delete tenants.</p></li></ul></li><li><p><strong>Dynamic Tenant Loading:</strong> The WhatsApp bot loads its active tenant's configuration dynamically from <code>tenants.json</code> at startup based on an environment variable.</p></li><li><p><strong>Dynamic Branding:</strong> The WhatsApp bot sends a tenant-specific logo URL configured in <code>tenants.json</code>.</p></li><li><p><strong>CRM Integration (Tenant-Specific):</strong></p><ul><li><p><strong>Lead Capture/Recognition:</strong> Functions as in Exercise 5, but now the specific CRM (Zoho or HubSpot) used is determined by the active tenant's configuration.</p></li><li><p><strong>Zoho CRM:</strong> Full integration for creating and searching leads, with tenant-specific OAuth token management.</p></li><li><p><strong>HubSpot CRM:</strong> Functional integration for creating and searching contacts.</p></li></ul></li><li><p><strong>LLM Selection:</strong> Supports Google Gemini 1.5 Flash API and local Ollama (phi3:mini).</p></li><li><p><strong>Retrieval-Augmented Generation (RAG):</strong> Integrates web-based RAG for contextual answers.</p></li></ul><h2>Project Structure</h2><pre><code>ex6-admin-dash-multi-tenant-config/
├── .env                  # Environment variables (API keys, secrets, active tenant ID)
├── .gitignore            # Specifies files/folders to ignore in Git
├── requirements.txt      # Python dependencies
├── README.md             # This documentation file
├── admin/
│   └── admin_dashboard.py # Streamlit Admin Dashboard UI
├── config/
│   └── tenants.json      # Stores multi-tenant configurations (managed by Streamlit UI, IGNORED by Git)
├── console_chatbot/
│   ├── bot_handler.py    # Manages conversation flow, state, and integrates RAG/CRM
│   ├── chat_session.py   # Manages chat history
│   ├── gemini_bot.py     # Handles Gemini LLM interactions
│   ├── ollama_bot.py     # Handles Ollama LLM interactions
│   ├── web_rag_utils.py  # Utilities for fetching web content and creating vector stores
│   ├── whatsapp_bot_main.py # Main Flask application for WhatsApp webhook
│   └── zoho_auth_manager.py # Handles Zoho OAuth2 authentication and token management (tenant-specific)
│   └── zoho_refresh_token_*.txt # Stores tenant-specific Zoho refresh tokens (e.g., zoho_refresh_token_lifecode_india.txt)
├── integrations/
│   ├── crm_router.py     # Routes CRM operations to the active CRM based on tenant config
│   ├── hubspot_crm.py    # HubSpot CRM API integration
│   └── zoho_crm.py       # Zoho CRM API integration
├── parsers/
│   └── lead_parser.py    # Normalizes lead data from user input
└── utils/
    └── tenant_loader.py  # Utility to load tenants.json
<br class="ProseMirror-trailingBreak"></code></pre><h2>Setup and Installation</h2><h3>1. Create the Project Structure</h3><p>If you're setting up this project for the first time, create the main directory and its subdirectories:</p><pre><code>mkdir C:\Data\tutorials\python\gemini\Local LLM\ex6-admin-dash-multi-tenant-config
cd C:\Data\tutorials\python\gemini\Local LLM\ex6-admin-dash-multi-tenant-config
# Manually create the directories and files as per the project structure above
<br class="ProseMirror-trailingBreak"></code></pre><p>Then, populate all files as provided in the previous turns of our conversation.</p><h3>2. Create and Populate <code>.env</code> File</h3><p>Create a file named <code>.env</code> in the <strong>root directory</strong> (<code>ex6-admin-dash-multi-tenant-config/</code>) and populate it with your API keys and the active tenant ID for the WhatsApp bot.</p><pre><code># --- LLM API Keys ---
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE

# --- WhatsApp Channel Configuration ---
WHATSAPP_ACCESS_TOKEN=YOUR_WHATSAPP_TEMPORARY_ACCESS_TOKEN_HERE
WHATSAPP_PHONE_NUMBER_ID=YOUR_WHATSAPP_PHONE_NUMBER_ID_HERE
WHATSAPP_WEBHOOK_VERIFY_TOKEN=YOUR_SECRET_WEBHOOK_VERIFY_TOKEN_HERE

# Specify which tenant this WhatsApp bot instance should serve
# IMPORTANT: This ID MUST match a 'tenant_id' defined in config/tenants.json
BOT_ACTIVE_TENANT_ID=lifecode_india # Example: 'lifecode_india' or 'hubspot_test_tenant'
<br class="ProseMirror-trailingBreak"></code></pre><ul><li><p><strong>WhatsApp:</strong> Obtain from <a href="https://developers.facebook.com/" title="null">Meta for Developers</a> -&gt; Your App -&gt; WhatsApp -&gt; Getting Started. Remember temporary tokens expire every 24 hours.</p></li><li><p><strong>Gemini:</strong> Obtain from <a href="https://aistudio.google.com/app/apikey" title="null">Google AI Studio</a>.</p></li></ul><h3>3. Install Dependencies</h3><p>Navigate to the project root directory (<code>ex6-admin-dash-multi-tenant-config/</code>) in your terminal and install the required Python packages:</p><pre><code>pip install -r requirements.txt
<br class="ProseMirror-trailingBreak"></code></pre><h3>4. Configure Tenants via Streamlit Admin Dashboard</h3><p>This is the primary way to manage your tenant configurations.</p><ol><li><p>Navigate to the <code>admin</code> directory:</p><pre><code>cd admin
<br class="ProseMirror-trailingBreak"></code></pre></li><li><p>Run the Streamlit dashboard:</p><pre><code>streamlit run admin_dashboard.py
<br class="ProseMirror-trailingBreak"></code></pre></li><li><p><strong>Access the UI:</strong> Your browser will open to the Streamlit dashboard (usually <code>http://localhost:8501</code>).</p></li><li><p><strong>Add/Edit Tenants:</strong></p><ul><li><p>Use the "Add New Tenant" section to create new tenants.</p></li><li><p>For each tenant, provide a <code>Tenant ID</code> (e.g., <code>lifecode_india</code>, <code>hubspot_test_tenant</code>), a <code>Tenant Name</code>, a <code>Logo URL</code> (e.g., <code>https://placehold.co/100x50/FF0000/FFFFFF?text=LifeCode</code>), and select its <code>CRM</code> (Zoho or HubSpot).</p></li><li><p><strong>For Zoho CRM:</strong> Enter your Zoho Client ID, Client Secret, Accounts URL (e.g., <code>https://accounts.zoho.in</code>), and API URL (e.g., <code>https://www.zohoapis.in</code>).</p></li><li><p><strong>For HubSpot CRM:</strong> Enter your HubSpot Private App Access Token.</p></li><li><p>Click "Save Tenant Configuration" or "Add Tenant".</p></li><li><p>The configurations will be saved to <code>config/tenants.json</code>.</p></li></ul></li></ol><h3>5. Authorize Zoho CRM (One-Time Setup per Tenant)</h3><p>If any of your tenants use Zoho CRM, you need to authorize the application once for that specific tenant to obtain and save its refresh token.</p><ol><li><p><strong>Ensure your <code>BOT_ACTIVE_TENANT_ID</code> in <code>.env</code> is set to the Zoho-enabled tenant you want to authorize.</strong></p></li><li><p><strong>Start the Flask application:</strong></p><pre><code>cd console_chatbot
python whatsapp_bot_main.py
<br class="ProseMirror-trailingBreak"></code></pre></li><li><p><strong>Start Ngrok</strong> in a separate terminal to expose your Flask server:</p><pre><code>ngrok http 5000
<br class="ProseMirror-trailingBreak"></code></pre><p>Copy the <code>https://</code> forwarding URL.</p></li><li><p>Open your web browser and go to <code>YOUR_NGROK_HTTPS_URL/authorize_zoho</code> (e.g., <code>https://abcdef12345.ngrok-free.app/authorize_zoho</code>).</p></li><li><p>Follow the prompts to enter your Ngrok URL and then click the authorization link.</p></li><li><p>You will be redirected to Zoho for approval. Grant access.</p></li><li><p>Upon successful authorization, a tenant-specific refresh token file (e.g., <code>zoho_refresh_token_lifecode_india.txt</code>) will be created in your <code>console_chatbot/</code> directory.</p></li></ol><h3>6. Configure Meta for Developers Webhook</h3><ol><li><p>Go to <a href="https://developers.facebook.com/" title="null">Meta for Developers</a> -&gt; Your App -&gt; WhatsApp -&gt; Getting Started.</p></li><li><p>Under <strong>"Step 3: Configure webhooks"</strong>, click "Edit".</p></li><li><p>Paste your Ngrok HTTPS forwarding URL into the <strong>"Callback URL"</strong> field.</p></li><li><p>Enter your <code>WHATSAPP_WEBHOOK_VERIFY_TOKEN</code> into the <strong>"Verify token"</strong> field.</p></li><li><p>Click "Verify and save".</p></li><li><p>Click "Manage" next to the webhook URL.</p></li><li><p>Subscribe to the <code>messages</code> field.</p></li></ol><h2>How to Use and Test</h2><ol><li><p><strong>Ensure your <code>.env</code> file's <code>BOT_ACTIVE_TENANT_ID</code> is set to the tenant you wish to test.</strong></p></li><li><p><strong>Start the bot</strong> by running <code>whatsapp_bot_main.py</code> and <code>ngrok</code>.</p></li><li><p><strong>Ensure Ngrok is running</strong> and forwarding to port 5000.</p></li><li><p><strong>Send a message</strong> (e.g., "Hi") to your WhatsApp Business number.</p></li><li><p>The bot will prompt you to <strong>choose an LLM</strong>. Send <code>/set_llm gemini</code> or <code>/set_llm ollama</code>.</p></li><li><p><strong>Tenant-Specific Behavior:</strong></p><ul><li><p><strong>CRM Lead Flow:</strong></p><ul><li><p>If no lead is found for your phone number in the <em>active tenant's CRM</em>, the bot will ask for your full name and then email.</p></li><li><p>Provide the details. The bot will then attempt to create a lead/contact in the CRM configured for the <em>active tenant</em>.</p></li><li><p><strong>Verify in CRM:</strong> Log in to your Zoho CRM or HubSpot account and check if the lead/contact was successfully created.</p></li><li><p>If a lead is found, the bot will greet you by name (retrieved from the active tenant's CRM) and skip the lead capture questions.</p></li></ul></li><li><p><strong>Dynamic Branding:</strong> After LLM selection and initial greeting, the bot should send the <strong>logo image</strong> configured for the <code>BOT_ACTIVE_TENANT_ID</code> in <code>tenants.json</code>.</p></li></ul></li><li><p><strong>RAG Functionality:</strong></p><ul><li><p>Send <code>/enable_rag</code>.</p></li><li><p>Provide a URL (e.g., <code>https://www.lifecode.life</code>).</p></li><li><p>Once the knowledge base is loaded, ask questions related to the content of the URL (e.g., "What is Lifecode Genorex?").</p></li><li><p>Send <code>/disable_rag</code> to stop using the RAG context.</p></li></ul></li><li><p><strong>Commands:</strong></p><ul><li><p><code>/reset</code>: Clears chat history and RAG state.</p></li><li><p><code>/set_llm [gemini|ollama]</code>: Changes the active LLM.</p></li><li><p><code>/enable_rag</code>: Initiates Web RAG setup.</p></li><li><p><code>/disable_rag</code>: Disables Web RAG.</p></li></ul></li></ol><h2>Sample <code>config/tenants.json</code> Structure</h2><p>This file is managed by the Streamlit Admin Dashboard and is <strong>ignored by Git</strong> for security reasons. It provides the structure for how tenant configurations are stored.</p><pre><code>
```json
{
    "tenants": [
        {
            "tenant_id": "lifecode_india",
            "name": "Lifecode India",
            "crm": "zoho",
            "zoho": {
                "client_id": "YOUR_LIFECODE_ZOHO_CLIENT_ID",
                "client_secret": "YOUR_LIFECODE_ZOHO_CLIENT_SECRET",
                "accounts_url": "https://accounts.zoho.in",
                "api_url": "https://www.zohoapis.in"
            },
            "branding": {
                "welcome_message": "Welcome to Lifecode! How can I assist you today?",
                "logo_url": "https://placehold.co/100x50/FF0000/FFFFFF?text=Lifecode"
            }
        },
        {
            "tenant_id": "genetics_uk",
            "name": "Genetics UK",
            "crm": "hubspot",
            "hubspot": {
                "api_key": "YOUR_GENETICS_HUBSPOT_API_KEY"
            },
            "branding": {
                "welcome_message": "Hi there! We’re Genetics UK. How can I help?",
                "logo_url": "https://placehold.co/100x50/00F/FFF?text=GeneticsUK"
            }
        }
    ]
}
```
<br class="ProseMirror-trailingBreak"></code></pre><p><strong>Note:</strong> The <code>refresh_token</code> for Zoho is <em>not</em> stored directly in <code>tenants.json</code>. It's managed and saved to a tenant-specific file (e.g., <code>console_chatbot/zoho_refresh_token_lifecode_india.txt</code>) by the <code>zoho_auth_manager.py</code> after the OAuth authorization flow.</p><h2>Secure Token Management &amp; Deployment Considerations</h2><ul><li><p><strong>Temporary WhatsApp Token:</strong> The <code>WHATSAPP_ACCESS_TOKEN</code> is temporary (24 hours). For production, you'd need to implement a system to generate and refresh permanent access tokens.</p></li><li><p><strong>Zoho Refresh Token:</strong> The <code>zoho_refresh_token_*.txt</code> files store your Zoho refresh tokens. In a production environment, these should be stored securely (e.g., in a cloud secret manager like Google Secret Manager, AWS Secrets Manager, or Azure Key Vault) rather than plain text files.</p></li><li><p><strong>HubSpot API Key:</strong> The <code>HUBSPOT_API_KEY</code> is a long-lived private app token. Similarly, for production, it should be managed via a secrets management service.</p></li><li><p><strong>Environment Variables:</strong> Best practice is to set environment variables directly in your deployment environment (e.g., Heroku, Google Cloud Run, AWS ECS, Kubernetes) rather than relying on a <code>.env</code> file.</p></li><li><p><strong>Deployment:</strong> For stable deployment, you would typically run the Flask application using a production-ready WSGI server like Gunicorn (as hinted in <code>requirements.txt</code>) behind a reverse proxy (like Nginx) or on a serverless platform (e.g., Google Cloud Run, AWS Lambda + API Gateway) that handles scaling and HTTPS.</p></li></ul></div>
