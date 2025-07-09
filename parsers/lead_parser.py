import re

class LeadParser:
    def __init__(self):
        print("[LeadParser] Initialized.")

    def parse_full_name(self, full_name_str: str) -> tuple[str, str | None]:
        """
        Parses a full name string into first name and an optional last name.
        If only one word, first_name = word, last_name = None.
        If multiple words, first_name = all but last word, last_name = last word.
        """
        name_parts = full_name_str.strip().split()
        if len(name_parts) == 0:
            return "", None
        elif len(name_parts) == 1:
            return name_parts[0], None
        else:
            first_name = " ".join(name_parts[:-1])
            last_name = name_parts[-1]
            return first_name, last_name

    def normalize_lead_data(self, name: str, email: str, phone: str) -> dict:
        """
        Normalizes raw user input into a common lead data structure.
        Args:
            name (str): Full name of the user.
            email (str): Email address of the user.
            phone (str): Phone number of the user.
        Returns:
            dict: A dictionary with normalized lead fields.
        """
        first_name, last_name = self.parse_full_name(name)

        normalized_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email.lower().strip(), # Standardize email to lowercase
            "phone": re.sub(r'\D', '', phone) # Remove non-digits from phone number
        }
        print(f"[LeadParser] Normalized lead data: {normalized_data}")
        return normalized_data

