import streamlit as st
from openai import OpenAI
import sys
import chromadb
from pathlib import Path
from bs4 import BeautifulSoup

SYSTEM_PROMPT = """

You are a helpful assistant that answers questions about news articles.

Use the provided news dataset to answer user questions.
If the answer comes from the dataset, clearly mention that.

"""

__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

chroma_client = chromadb.PersistentClient(path='./ChromaDB_for_HW4')
collection = chroma_client.get_or_create_collection('HW7_News')


import pandas as pd

csv_path = 'news.csv'
def load_csv_to_collection(csv_path, collection):
    df = pd.read_csv(csv_path)

    st.write(df.columns)  
    st.write(df.head())

    for idx, row in df.iterrows():
        # Combine relevant columns
        text = f"Title: {row['title']}\nContent: {row['text']}"

        # Optional: chunk (depends on assignment)
        chunks = chunk_text_simple_split(text)

        for i, chunk in enumerate(chunks):
            chunk_id = f"row_{idx}_chunk_{i+1}"
            add_to_collection(collection, chunk, chunk_id)

    st.success(f"Loaded {len(df)} rows into vector database")
    

def chunk_text_simple_split(text):

    """
        CHUNKING METHOD: Simple split into two equal parts
        
        WHY THIS METHOD:
        - requirement of creating exactly 2 chunks per document
        - preserves document context by keeping each half together
        - splitting in the middle usually keeps related information together
        - easier to understand and debug
    """


    words = text.split()
    mid_point = len(words) // 2
    
    chunk1 = ' '.join(words[:mid_point])
    chunk2 = ' '.join(words[mid_point:])
    
    return [chunk1, chunk2]





def keep_last_n_user_turns(messages, n_user_turns):
    # Keep system message
    result = [msg for msg in messages if msg["role"] == "system"]
    
    # Count user messages
    user_messages = [msg for msg in messages if msg["role"] == "user"]
    
    if len(user_messages) <= n_user_turns:
        # Keep all messages
        result.extend([msg for msg in messages if msg["role"] != "system"])
    else:
        # Keep only last n user turns and their responses
        user_count = 0
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_count += 1
            if user_count <= n_user_turns:
                result.insert(1, msg)  # Insert after system message
    
    return result




def add_to_collection(collection, text, file_name):

    #create an emmbedding
    client = st.session_state.openai_client
    response = client.embeddings.create(
        input=text,
        model='text-embedding-3-small'
    )

    #get the embedding
    embedding = response.data[0].embedding

    collection.add(
        documents=[text],
        ids=[file_name],
        embeddings=[embedding]
    )




    
if 'openai_client' not in st.session_state:
    api_key = st.secrets["OPENAI_KEY"]
    st.session_state.openai_client = OpenAI(api_key=api_key)


# Load htmls to collection (only once)
if 'HW4_VectorDB' not in st.session_state:
    # Check if collection already has documents
    existing_docs = collection.count()
    
    if existing_docs == 0:
        st.info("Creating vector database from HTML files...")
        load_csv_to_collection('news.csv', collection)
    else:
        st.info(f"Vector database already exists with {existing_docs} documents")
    
    st.session_state.HW4_VectorDB = collection
else:
    collection = st.session_state.HW4_VectorDB







#### MAIN APP ####

st.title('Homework 7: News Chatbot using RAG')


openAI_Model = st.sidebar.selectbox("Which model?",
                                    ("mini", "regular"))
if openAI_Model == "mini":
    model_to_use = "gpt-4o-mini"
else:
    model_to_use = "gpt-4o-mini"



# Initialize messages
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hi! Ask me anything about the news articles dataset."}
    ]


for msg in st.session_state.messages:
    if msg["role"] != "system":  # Don't display system message
        chat_msg = st.chat_message(msg["role"])
        chat_msg.write(msg["content"])

if prompt:= st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    
     # RAG: Get relevant documents from ChromaDB
    client = st.session_state.openai_client
    response = client.embeddings.create(
        input=prompt,
        model='text-embedding-3-small')
    
    query_embedding = response.data[0].embedding


    # Query the collection
    collection = st.session_state.HW4_VectorDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    # Get the relevant documents
    relevant_docs = "\n\n".join(results['documents'][0])
        
    # Create enhanced prompt with RAG context
    rag_prompt = f"""Based on the following news articles:

{relevant_docs}

User question: {prompt}

Answer using the articles above. If the information comes from the dataset, mention it explicitly.
"""
    
    # Replace the user's prompt with the RAG-enhanced version
    st.session_state.messages[-1]["content"] = rag_prompt
    
    # Only send the last 5 user turns (conversation buffer as required)
    messages_for_llm = keep_last_n_user_turns(
        st.session_state.messages,
        n_user_turns=5
    )
    
    # Generate response with streaming
    stream = client.chat.completions.create(
        model=model_to_use,
        messages=messages_for_llm,
        stream=True
    )
    
    with st.chat_message("assistant"):
        response_text = st.write_stream(stream)


    st.session_state.messages.append({"role": "assistant", "content": response_text})

    st.session_state.messages = keep_last_n_user_turns(st.session_state.messages, n_user_turns=5)
