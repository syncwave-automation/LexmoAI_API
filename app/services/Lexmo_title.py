import os
import openai
from dotenv import load_dotenv

# Load environment variables and set OpenAI API key
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

def generate_chat_title(user_query: str, max_tokens: int = None) -> str:
    """
    Generate a concise and descriptive title for a chat session based on the provided inputs.
    
    Parameters:
      - user_query (str): The query that initiated the chat.
      - context (str): The current conversation context or history.
      - knowledge (str): Relevant knowledge (e.g., legal texts, acts, or facts) retrieved for the conversation.
      - max_tokens (int): The maximum tokens allowed for the title generation (default is 20).
      
    Returns:
      - str: The generated chat title.
    """
    

    
    # Construct the prompt to guide title generation
    prompt = (
        "You are Lexmo, a legal assistant developed by Syncwave Automation Pvt Ltd. "
        "Your task is to generate a concise, descriptive title for a chat session based on the inputs provided. "
        "The title should accurately summarize the legal issue or inquiry without any extraneous detail.\n\n"
        "User Query: " + user_query + "\n\n"
        # "Relevant Knowledge: " + knowledge + "\n\n"
        "Generate a short title (maximum " + str(max_tokens) + " tokens) that captures the essence of the conversation."
    )
    
    # Call the OpenAI Chat API with the custom prompt
    response = openai.chat.completions.create(
        model="gpt-4o-mini",  # or the model you are using
        messages=[
            {"role": "system", "content": "You are a creative title generator."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5
    )
    
    # Extract and return the title (strip extra whitespace)
    title = response.choices[0].message.content.strip()
    return title

# For testing purposes, you can run this module standalone.
# if __name__ == "__main__":
#     sample_user_query = "What are the legal implications of breach of contract under Indian law?"
#     sample_context = "Earlier the user discussed issues related to contract disputes and remedies available under the Indian Contract Act."
#     sample_knowledge = (
#         "Key legal texts include the Indian Contract Act, Section 73 regarding compensation for breach, "
#         "and recent judgments clarifying the elements of breach and remedies."
#     )
    
#     generated_title = generate_chat_title(sample_user_query, sample_context, sample_knowledge)
#     print("Generated Chat Title:")
#     print(generated_title)