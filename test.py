from models import Message
from utils import get_llm_sync, get_llm_stream
from models import Message

# Create a test message
test_messages = [Message(role="user", content="hi")]

# Call the LLM function
try:
    response = get_llm_sync(test_messages)
    print("\nLLM Response:")
    for msg in response:
        print(f"Role: {msg.role}, Content: {msg.content}")
except Exception as e:
    print(f"Error: {str(e)}")
