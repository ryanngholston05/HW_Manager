import streamlit as st
from openai import OpenAI
import sys
import chromadb
from pathlib import Path
from bs4 import BeautifulSoup

SYSTEM_PROMPT = """

You are a helpful assistant for the iSchool at Syracuse University. 
You help students learn about student organizations and activities at the iSchool.

"""

__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

chroma_client = chromadb.PersistentClient(path='./ChromaDB_for_HW4')
collection = chroma_client.get_or_create_collection('HW4_iSchool_Orgs')


def extract_from_html(html_path):
   
    with open(html_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space
        lines = (line.strip() for line in text.splitlines())
        
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    

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



def load_htmls_to_collection(folder_path, collection):
    """
    Load all HTML files from a folder, chunk them, and add to the collection.
    Each HTML file is split into 2 chunks
    """
    folder = Path(folder_path)
    html_files = list(folder.glob("*.html"))  # Find all HTML files
    
    if not html_files:
        st.warning(f"No HTML files found in {folder_path}")
        return collection
    
    for html_file in html_files:
        # Extract text from HTML
        text = extract_from_html(html_file)
        
        # Chunk the document into 2 parts (as required by assignment)
        chunks = chunk_text_simple_split(text)
        
        # Add each chunk to collection with unique ID
        for i, chunk in enumerate(chunks):
            chunk_id = f"{html_file.name}_chunk_{i+1}"
            add_to_collection(collection, chunk, chunk_id)
    
    st.success(f"Loaded {len(html_files)} HTML files into the vector database")
    return collection




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
        load_htmls_to_collection('hw4-data/', collection)
    else:
        st.info(f"Vector database already exists with {existing_docs} documents")
    
    st.session_state.HW4_VectorDB = collection
else:
    collection = st.session_state.HW4_VectorDB







#### MAIN APP ####

st.title('Homework 4: Chatbot using RAG')


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
        {"role": "assistant", "content": "Hi! What question do you have about student organizations in the iSchool?"}
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
    rag_prompt = f"""Based on the following information about iSchool organizations:

{relevant_docs}

User question: {prompt}

Please answer the question using the information from the organization pages above. If you use information from these materials, mention that it comes from the iSchool organization pages."""
    
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
