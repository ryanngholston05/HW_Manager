import streamlit as st
from openai import OpenAI
import pandas as pd
import chromadb
import sys

# fix sqlite issue on Streamlit Cloud
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

SYSTEM_PROMPT = """
You are a helpful assistant that answers questions about news articles.

Use the news dataset to answer the user's question.
If the answer comes from the dataset, mention that.
If the dataset does not have enough information, say that clearly.
"""


if "openai_client" not in st.session_state:
    api_key = st.secrets["OPENAI_KEY"]
    st.session_state.openai_client = OpenAI(api_key=api_key)

client = st.session_state.openai_client


chroma_client = chromadb.PersistentClient(path="./ChromaDB_for_HW7")
collection = chroma_client.get_or_create_collection("HW7_news")


def add_to_collection(text, doc_id):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )

    embedding = response.data[0].embedding

    collection.add(
        documents=[text],
        ids=[doc_id],
        embeddings=[embedding]
    )


if "data_loaded" not in st.session_state:
    if collection.count() == 0:
        df = pd.read_csv("news.csv")

        for i, row in df.iterrows():
            text = (
                "Company: " + str(row["company_name"]) + "\n"
                + "Date: " + str(row["Date"]) + "\n"
                + "Article: " + str(row["Document"]) + "\n"
                + "URL: " + str(row["URL"])
            )

            add_to_collection(text, "row_" + str(i))

        st.success("News data loaded into vector database.")
    else:
        st.info("Vector database already has data.")

    st.session_state["data_loaded"] = True

st.title("Homework 7: News Chatbot using RAG")

model_choice = st.sidebar.selectbox(
    "Which model?",
    ["mini", "regular"]
)

if model_choice == "mini":
    model_to_use = "gpt-4o-mini"
else:
    model_to_use = "gpt-4o-mini"


if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hi! Ask me a question about the news dataset."}
    ]

# show previous messages
for message in st.session_state["messages"]:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.write(message["content"])

prompt = st.chat_input("Ask a question about the news articles...")

if prompt:
    # show user message
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # create embedding for user question
    response = client.embeddings.create(
        input=prompt,
        model="text-embedding-3-small"
    )
    question_embedding = response.data[0].embedding

    # search vector db
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=3
    )

    # combine retrieved documents
    relevant_docs = "\n\n".join(results["documents"][0])

    # build prompt for model
    rag_prompt = f"""
Here is information from the news dataset:

{relevant_docs}

User question: {prompt}

Answer the question using the dataset information above.
Make it clear when your answer is based on the news dataset.
If the dataset does not contain enough information, say that.
"""

    # only send a simple set of messages to the model
    messages_for_model = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": rag_prompt}
    ]

    # get response
    stream = client.chat.completions.create(
        model=model_to_use,
        messages=messages_for_model,
        stream=True
    )

    with st.chat_message("assistant"):
        response_text = st.write_stream(stream)

    st.session_state["messages"].append(
        {"role": "assistant", "content": response_text}
    )