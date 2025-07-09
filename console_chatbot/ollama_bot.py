import ollama
import time # NEW: Import time for duration tracking

class OllamaBot:
    """
    Handles interactions with a local Ollama model (e.g., phi3:mini).
    Manages model initialization and response generation with chat history.
    """
    def __init__(self, model_name='phi3:mini'):
        self.model_name = model_name
        print(f"[Ollama bot initialized with model: {self.model_name}]")

    def get_response(self, chat_history: list, context: str = None) -> tuple[str, float, int, int, str | None]:
        """
        Gets a response from the Ollama model based on the provided chat history and optional context.
        Args:
            chat_history (list): A list of message dictionaries representing the conversation.
            context (str, optional): Additional context to prepend to the last user message.
        Returns:
            tuple: (response_text, duration_seconds, input_tokens, output_tokens, error_message)
        """
        start_time = time.time() # Start timer
        try:
            # Prepare the messages list for the LLM
            messages_for_llm = []

            # Add all historical messages except the very last one (which is the current user query)
            historical_messages = chat_history[:-1]

            for msg in historical_messages:
                # Map 'model' to 'assistant' for Ollama
                role = 'assistant' if msg['role'] == 'model' else msg['role']
                messages_for_llm.append({'role': role, 'content': msg['content']})

            # Get the current user's actual query
            current_user_query = chat_history[-1]['content']

            # Construct the final user message with context if provided
            if context:
                final_user_message_content = f"Context: {context}\n\nQuestion: {current_user_query}"
            else:
                final_user_message_content = current_user_query

            messages_for_llm.append({'role': 'user', 'content': final_user_message_content})

            print("\n[DEBUG] Messages sent to Ollama LLM:")
            for msg in messages_for_llm:
                print(f"  Role: {msg['role']}, Content: {msg['content'][:100]}...") # Print first 100 chars
            print("[DEBUG] End LLM messages.\n")

            response = ollama.chat(model=self.model_name, messages=messages_for_llm, options={'num_predict': 4000}) # Added num_predict for token limit

            end_time = time.time() # End timer
            duration = end_time - start_time

            # Ollama response might have 'prompt_eval_count' and 'eval_count' (for completion)
            # which are similar to input/output tokens.
            input_tokens = response.get('prompt_eval_count', 0)
            output_tokens = response.get('eval_count', 0)

            if response and 'message' in response and 'content' in response['message']:
                return response['message']['content'], duration, input_tokens, output_tokens, None
            else:
                return "No text response received from Ollama.", duration, input_tokens, 0, "No text response"
        except ollama.ResponseError as e:
            end_time = time.time() # End timer even on error
            duration = end_time - start_time
            return f"Error with Ollama (ResponseError): {e}. Ensure Ollama server is running and '{self.model_name}' model is pulled.", duration, 0, 0, str(e)
        except Exception as e:
            end_time = time.time() # End timer even on error
            duration = end_time - start_time
            return f"An unexpected error occurred with Ollama: {e}", duration, 0, 0, str(e)

