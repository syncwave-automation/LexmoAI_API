import concurrent.futures
import os
import json
import openai
import concurrent.futures
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

# Set your OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')  # or: openai.api_key = "YOUR_API_KEY"
client = openai  # alias for clarity

search_results = []
seen_lengths = set()

def search_vector_store(store_name, store_id, query, max_results):
    """
    Queries a vector store and returns the (store_name, response_data).
    """
    response = client.vector_stores.search(
        vector_store_id=store_id,
        query=query,
        max_num_results=max_results,
        rewrite_query=True
    )
    return store_name, response.data

def format_raw_retrieved_data(results_list):
    """
    Create a human-readable string of all retrieved data from the vector stores
    so the final LLM can reference them internally. 
    (We will instruct it NOT to show these filenames in the final output.)
    """
    sections = []
    for (score, store_name, filename, content_obj) in results_list:
        text_chunks = "\n".join([cont.text for cont in content_obj])
        section_str = (
            f"Filename: {filename}\n"
            f"VectorStore: {store_name}\n"
            f"RelevanceScore: {score}\n"
            f"Text:\n{text_chunks}\n"
            + "-"*70 + "\n"
        )
        sections.append(section_str)
    
    return "\n".join(sections)


def generate_combined_summary(results, user_query, max_output_tokens):
    """
    Combines multiple law references into a single structured text 
    that will be fed into the final LLM for generating a cohesive response.
    """

    prompt = (
        "You are given the following items:\n"
        f"1. A user query: {user_query}\n"
        "2. A set of law-related information retrieved by a vector search (each entry has a filename and text snippet):\n"
        "Your task is to:\n"
        "- Read and understand all the law-related information provided.\n"
        "- Combine and reorganize the information into one clear, logically structured text.\n"
        "- Focus on clarity and factual accuracy.\n"
        "- Retain key legal references, definitions, or citations without adding your own commentary or speculation.\n"
        "- Do not add new information that is not in the provided materials.\n"
        "- Do not omit essential parts: the user wants a combined text, not a mere summary.\n"
        "- If multiple sources contain duplicate info, consolidate them.\n"
        "Format:\n"
        "Present your final output as a single coherent document, combining all important details. Avoid repetition.\n"
        "Important:\n"
        "Your response here will be passed to another language model along with the user’s original query. "
        "That model will generate the final answer to the user.\n"
        "Hence, your job is purely to compile, unify, and condense references.\n"
        "Output:\n"
        "A single, well-detailed, structured text containing the combined legal references.\n"
        f"Maximum length of the output is {max_output_tokens} tokens.\n"
    )

    structured_info_list = []
    for item in results:
        score, store_name, filename, content_obj = item
        text_snippets = "\n".join([cont.text for cont in content_obj])
        structured_info_list.append(
            f"Filename: {filename}\n"
            f"VectorStore: {store_name}\n"
            f"RelevanceScore: {score}\n"
            f"FullText:\n{text_snippets}\n"
            + "-"*50 + "\n"
        )

    combined_law_text = "\n".join(structured_info_list)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": prompt + "\n" + combined_law_text
            },
        ],
        max_tokens=max_output_tokens,
    )

    return response.choices[0].message.content

main_llm_prompt_template = """
You are a compassionate, empathetic legal assistant. The user’s question is:
"{user_query}"

You have a combined set of legal knowledge (cited from various sources), 
and the following raw references (verbatim) from the vector store are also at your disposal:

{raw_data}

Important instructions for your final answer:
1. Do NOT mention or reveal any specific filenames or source names in your response.
2. Provide a detailed, thorough explanation of any relevant legal procedures, requirements, or considerations based on the materials.
3. If the combined summary or raw references mention **specific laws or acts by name** (e.g. "Hindu Marriage Act, 1955"), please include them in your explanation so the user knows which legislation is relevant.
4. Express empathy and understanding for the user's situation.
5. Offer disclaimers where needed (e.g., not a substitute for a professional legal advisor).
6. Conclude by asking one or two clarifying questions that could help you provide a more targeted answer if the user decides to respond with more details.

Answer structure:
- **An empathetic opening**: acknowledge the user's situation and feelings.
- **A detailed explanation**: share any relevant legal information or processes found in your references (without citing filenames), 
  specifically naming any Acts or Laws that appear in your materials (e.g., "Under the Hindu Marriage Act, 1955...").
- **A short disclaimer**: clarify your role and the limitations of the information provided.
- **A brief set of clarifying questions**: help refine the user’s query by prompting them for additional information.

Remember:
- Do NOT introduce new information beyond what is in the combined summary or raw references.
- Do NOT mention or show the filenames from the raw references.
- Maintain a warm, helpful tone.
"""

def generate_final_response(user_query, combined_summary, raw_retrieved_data):
    """
    Generates the final user-facing answer using the refined prompt template,
    referencing both the combined summary and the original raw data,
    but not revealing the filenames to the user.
    """

    main_prompt = main_llm_prompt_template.format(
        user_query=user_query,
        raw_data=raw_retrieved_data
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a legal assistant providing comprehensive, empathetic responses. "
                "Do not reveal or mention specific filenames or store references."
            )
        },
        {
            "role": "user",
            "content": (
                main_prompt 
                + "\n\n"
                + "Here is the combined summary of all relevant legal material you can reference:\n"
                + combined_summary
            )
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return response.choices[0].message.content

def custom_response(text: str) -> str:
    """
    Remove references to OpenAI, GPT, ChatGPT, or LLM from the text.
    Replace them with 'Lexmo' or attribute them to Syncwave Automation.
    """
    replacements = {
        "OpenAI": "Syncwave Automation",
        "openai": "Syncwave Automation",
        "GPT-4o-mini": "Lexmo",
        "GPT-4": "Lexmo",
        "ChatGPT": "Lexmo",
        "LLM": "Lexmo",
        "OpenAI's": "Syncwave Automation",
    }
    for key, val in replacements.items():
        text = text.replace(key, val)
    return text

