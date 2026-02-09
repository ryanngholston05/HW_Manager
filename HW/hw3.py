import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
from anthropic import Anthropic

SYSTEM_PROMPT = """
You are a helpful chatbot for a student.
Explain things so a 10-year-old can understand.
Use short sentences and simple words.
After you answer, ALWAYS ask: "Do you want more info?"
If the user says "Yes" (or anything similar like "yeah", "sure", "please"), give more info and ask again.
If the user says "No" (or anything similar like "nope", "no thanks"), ask what you can help with next.

Keep following this pattern for every interaction.
"""

@st.cache_data(show_spinner=False)
def get_baseball_context(which: str) -> str:
    url1 = "https://www.howbaseballworks.com/TheBasics.htm"
    url2 = "https://www.pbs.org/kenburns/baseball/baseball-for-beginners"

    texts = []
    if which in ("URL 1", "Both"):
        t1 = read_url_content(url1)
        if t1: texts.append(f"[SOURCE 1: {url1}]\n{t1}")
    if which in ("URL 2", "Both"):
        t2 = read_url_content(url2)
        if t2: texts.append(f"[SOURCE 2: {url2}]\n{t2}")

    return "\n\n".join(texts)




def read_url_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.get_text()
    except requests.RequestException as e:
        st.error(f"Error reading {url}: {e}", icon="❌")
        return None

def validate_anthropic_key(key: str) -> Anthropic:
    client = Anthropic(api_key=key)
    client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=5,
        messages=[{"role": "user", "content": "Hi"}],
    )
    return client

def keep_last_n_user_turns(messages, n_user_turns=2, keep_first_assistant=True):
    """
    Keep only the last n user turns in the conversation.
    Always preserves the system message.
    Optionally preserves the first assistant message.
    """
    if not messages:
        return messages

    preserved = []
    start_idx = 0

    if messages[0]["role"] == "system":
        preserved = [messages[0]]
        start_idx = 1

    if keep_first_assistant and start_idx < len(messages) and messages[start_idx]["role"] == "assistant":
        preserved.append(messages[start_idx])
        start_idx += 1

    # Find indices of user messages
    user_idxs = [i for i in range(start_idx, len(messages)) if messages[i]["role"] == "user"]
    if len(user_idxs) <= n_user_turns:
        return preserved + messages[start_idx:]

    # Only keep last n user messages
    keep_user_idxs = set(user_idxs[-n_user_turns:])

    # Keep those user messages and the assistant message immediately after each (if any)
    kept = []
    i = start_idx
    while i < len(messages):
        if i in keep_user_idxs:
            kept.append(messages[i])  # user
            if i + 1 < len(messages) and messages[i + 1]["role"] == "assistant":
                kept.append(messages[i + 1])  # assistant response
            i += 2
        else:
            i += 1

    return preserved + kept

st.title("Homework 3 Answering Chatbot")


st.write(
    "This chatbot answers questions using rules in a permanent system prompt. "
    "It explains baseball in simple, kid-friendly language and always asks "
    "\"Do you want more info?\" after each answer. "
    "It also uses webpage context from the selected baseball source(s). "
    "Conversation memory: the bot keeps the last 6 messages (3 user–assistant exchanges), "
    "while the system prompt + baseball sources are never discarded."
)


st.sidebar.header("LLM Provider")

llm_provider = st.sidebar.selectbox(
    "Choose an LLM:",
    ["OpenAI", "Claude (Anthropic)"]
)

st.sidebar.header("Baseball Context")
context_choice = st.sidebar.selectbox("Use which sources?", ["URL 1", "URL 2", "Both"])
baseball_context = get_baseball_context(context_choice)

SYSTEM_WITH_CONTEXT = SYSTEM_PROMPT + "\n\nIMPORTANT BASEBALL REFERENCE (use this to answer):\n" + baseball_context



if llm_provider == "OpenAI":
    model_to_use = "gpt-5-mini"
else:
    model_to_use = "claude-opus-4-5-20251101"

# If the user changes the provider, reset the client so we rebuild it correctly
if "provider" not in st.session_state or st.session_state.provider != llm_provider:
    st.session_state.provider = llm_provider
    st.session_state.client = None  # force rebuild

# Build/validate the client
if st.session_state.client is None:
    if llm_provider == "OpenAI":
        try:
            openai_api_key = st.secrets["OPENAI_KEY"]
            st.session_state.client = OpenAI(api_key=openai_api_key)
            st.session_state.client.models.list()
            st.success("OpenAI key validated!", icon="✅")
        except KeyError:
            st.error("OpenAI API key not found in Streamlit secrets.", icon="❌")
            st.stop()
        except Exception as e:
            st.error(f"Error connecting to OpenAI: {str(e)}", icon="❌")
            st.stop()
    else:
        try:
            anthropic_api_key = st.secrets["ANTHROPIC_KEY"]
            st.session_state.client = validate_anthropic_key(anthropic_api_key)
            st.success("Anthropic key validated!", icon="✅")
        except KeyError:
            st.error("Anthropic API key not found in Streamlit secrets.", icon="❌")
            st.stop()
        except Exception as e:
            st.error(f"Error connecting to Anthropic: {str(e)}", icon="❌")
            st.stop()


# Initialize messages
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_WITH_CONTEXT},
        {"role": "assistant", "content": "Hi! What question do you have?"}
    ]
else:
    # Always keep system prompt updated (never discarded)
    st.session_state.messages[0]["content"] = SYSTEM_WITH_CONTEXT

# Display conversation history
for msg in st.session_state.messages:
    if msg["role"] != "system":
        chat_msg = st.chat_message(msg["role"])
        chat_msg.write(msg["content"])


# Handle user input
if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Only send the last 2 user turns (conversation buffer)
    messages_for_llm = keep_last_n_user_turns(
        st.session_state.messages,
        n_user_turns=3
    )

    # Get response (non-streaming)
    if llm_provider == "OpenAI":
        completion = st.session_state.client.chat.completions.create(
            model=model_to_use,
            messages=messages_for_llm
        )
        response = completion.choices[0].message.content

    else:
        # Anthropic expects system separately, and only user/assistant in messages
        system_text = ""
        converted = []

        for m in messages_for_llm:
            if m["role"] == "system":
                system_text = m["content"]
            elif m["role"] in ("user", "assistant"):
                converted.append({"role": m["role"], "content": m["content"]})

        completion = st.session_state.client.messages.create(
            model=model_to_use,
            max_tokens=800,
            system=system_text,
            messages=converted,
        )

        # Anthropic returns a list of content blocks; grab the text
        response = completion.content[0].text

    with st.chat_message("assistant"):
        st.write(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.messages = keep_last_n_user_turns(st.session_state.messages, n_user_turns=2)
