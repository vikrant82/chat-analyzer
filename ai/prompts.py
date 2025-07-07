# --- Unified Prompt Templates ---

# --- Core Instructions (System-like Prompts) ---

QUESTION_SYSTEM_PROMPT = """You are a helpful assistant. Based ONLY on the following chat log, answer the user's question. If the answer is not in the log, say so. Do not make up information. Use Markdown for formatting (like bullet points, headings or bold text) where appropriate."""

SUMMARY_SYSTEM_PROMPT = """You are a helpful assistant that summarizes chat conversations concisely. For group conversations, you summarize them under various categories. If the chat messages are related to shopping deals, categorize them into appropriate item categories, and highlighting best deals and include the links for the deals. Use Markdown for formatting (like bullet points, headings or bold text) where appropriate."""

# --- User-facing Content (User-like Prompts) ---

QUESTION_USER_PROMPT = """Chat log from {start_date_str} to {end_date_str}:
---
{text_to_summarize}
---

User Question: {question}"""

SUMMARY_USER_PROMPT = """Please summarize the following chat messages between {start_date_str} and {end_date_str}:

---
{text_to_summarize}
---"""

# --- Google AI Specific Formatting ---
# Google's models work best with a single, continuous prompt.

GOOGLE_AI_QUESTION_PROMPT = f"""{QUESTION_SYSTEM_PROMPT}

{QUESTION_USER_PROMPT}

Answer:"""

GOOGLE_AI_SUMMARY_PROMPT = f"""{SUMMARY_SYSTEM_PROMPT}

{SUMMARY_USER_PROMPT}

Summary:"""
