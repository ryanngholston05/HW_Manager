import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup

from anthropic import Anthropic


def read_url_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for HTTP errors
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


# Show title and description.
st.title("Homework 2")
st.write(
    "Enter a URL below and choose a summary format in the sidebar."
)

url = st.text_input("Enter a URL to summarize:")



st.sidebar.header("Summary Options")

summary_style = st.sidebar.radio(
    "Choose a summary format:",
    (
        "100 words",
        "2 connecting paragraphs",
        "5 bullet points",
    ),
)

st.sidebar.header("Output Language")

language = st.sidebar.selectbox(
    "Select output language:",
    ["English", "French", "Spanish"]  
)


st.sidebar.header("LLM Provider")

llm_provider = st.sidebar.selectbox(
    "Choose an LLM:",
    ["OpenAI", "Claude (Anthropic)",]
)

use_advanced = st.sidebar.checkbox("Use advanced model", value=False)
model = "gpt-5-mini" if use_advanced else "gpt-5-nano"

if llm_provider == "OpenAI":
    model = "gpt-5-mini" if use_advanced else "gpt-5-nano"
else:  # Claude (Anthropic)
    model = "claude-sonnet-4-5-20250929" if use_advanced else "claude-opus-4-5-20251101"




# Load keys depending on provider selected
openai_client = None
anthropic_client = None

if llm_provider == "OpenAI":
    try:
        openai_api_key = st.secrets["OPENAI_KEY"]
    except KeyError:
        st.error("OpenAI API key not found in Streamlit secrets.", icon="❌")
        st.stop()

    try:
        openai_client = OpenAI(api_key=openai_api_key)
        openai_client.models.list()
        st.success("OpenAI key validated!", icon="✅")
    except Exception as e:
        st.error(f"Error connecting to OpenAI: {str(e)}", icon="❌")
        st.stop()

else:  # Claude (Anthropic)
    try:
        anthropic_api_key = st.secrets["ANTHROPIC_KEY"]
    except KeyError:
        st.error("Anthropic API key not found in Streamlit secrets.", icon="❌")
        st.stop()

    try:
        anthropic_client = validate_anthropic_key(anthropic_api_key)
        st.success("Anthropic key validated!", icon="✅")
    except Exception as e:
        st.error(f"Error connecting to Anthropic: {str(e)}", icon="❌")
        st.stop()


if summary_style == "100 words":
    instruction = (
        "Summarize the content in exactly 100 words. "
        "Write as one paragraph. Do not include a title."
    )
    instruction += f"\n\nIMPORTANT: Write the entire summary in {language}."

elif summary_style == "2 connecting paragraphs":
    instruction = (
        "Summarize the content in two connected paragraphs. "
        "Do not use bullet points."
    )
    instruction += f"\n\nIMPORTANT: Write the entire summary in {language}."

else:
    instruction = (
        "Summarize the content in exactly 5 bullet points. "
        "Each bullet should be one sentence."
    )
    instruction += f"\n\nIMPORTANT: Write the entire summary in {language}."


generate = st.button("Generate summary", disabled=not url)

if url and generate:
    # Read text from the URL
    document = read_url_content(url)

    if not document:
        st.stop()

    prompt = f"{instruction}\n\nURL CONTENT:\n{document}"

    # Call the selected LLM
    if llm_provider == "OpenAI":
        stream = openai_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You summarize web pages accurately and concisely.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            stream=True,
        )
        st.subheader("Your summary")
        st.write_stream(stream)

    else:
        llm_provider == "Claude (Anthropic)"
        msg = anthropic_client.messages.create(
            model=model,
            max_tokens=600,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        st.subheader("Your summary")
        st.write(msg.content[0].text)

   



# TEST
