class ChatSession:
    """
    Manages the conversation history for a chatbot session.
    History is stored as a list of dictionaries, suitable for LLM APIs.
    Example: [{'role': 'user', 'content': 'Hello'}, {'role': 'model', 'content': 'Hi there!'}]
    """
    def __init__(self):
        self.history = []

    def add_message(self, role: str, content: str):
        """
        Adds a new message to the chat history.
        Args:
            role (str): The role of the message sender (e.g., 'user', 'model').
            content (str): The text content of the message.
        """
        self.history.append({'role': role, 'content': content})

    def get_history(self) -> list:
        """
        Returns the current chat history.
        Returns:
            list: A list of message dictionaries.
        """
        return self.history

    def clear_history(self):
        """
        Clears the entire chat history.
        """
        self.history = []
        print("[Chat history cleared.]")

