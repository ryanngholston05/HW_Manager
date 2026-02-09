import streamlit as st
from openai import OpenAI

SYSTEM_PROMPT = """
You are a helpful chatbot for a student.
Explain things so a 10-year-old can understand.
Use short sentences and simple words.
After you answer, ALWAYS ask: "Do you want more info?"
If the user says "Yes" (or anything similar like "yeah", "sure", "please"), give more info and ask again.
If the user says "No" (or anything similar like "nope", "no thanks"), ask what you can help with next.

Keep following this pattern for every interaction.
"""



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



st.title("My Lab3 question answering chatbot")
openAI_Model = st.sidebar.selectbox("Which model?",
                                    ("mini", "regular"))
if openAI_Model == "mini":
    model_to_use = "gpt-4o-mini"
else:
    model_to_use = "gpt-4o-mini"


#create an OpenAI client
if 'client' not in st.session_state:
    api_key = st.secrets["OPENAI_KEY"]
    st.session_state.client = OpenAI(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hi! What question do you have?"}
    ]

for msg in st.session_state.messages:
    if msg["role"] != "system":  # Don't display system message
        chat_msg = st.chat_message(msg["role"])
        chat_msg.write(msg["content"])

if prompt:= st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    client = st.session_state.client

    # Only send the last 2 user turns (conversation buffer)
    messages_for_llm = keep_last_n_user_turns(
        st.session_state.messages,
        n_user_turns=2
    )

    stream = client.chat.completions.create(
        model=model_to_use,
        messages=messages_for_llm,
        stream=True
    )

    
    with st.chat_message("assistant"):
        response = st.write_stream(stream)

    st.session_state.messages.append({"role": "assistant", "content": response})

    st.session_state.messages = keep_last_n_user_turns(st.session_state.messages, n_user_turns=2)




