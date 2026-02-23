import streamlit as st
from openai import OpenAI
import sys
import chromadb
from pathlib import Path
from PyPDF2 import PdfReader

SYSTEM_PROMPT = """

You are a helpful course assistant for IST 488 - Building Human-Centered AI Applications. 
You help students understand course concepts by answering questions based on the course materials provided.
When answering questions, clearly indicate when you're using information from the course materials.
If the course materials don't contain the answer, you can say so and offer general knowledge if appropriate.

"""

__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

chroma_client = chromadb.PersistentClient(path='./ChromaDB_for_Lab')
collection = chroma_client.get_or_create_collection('Lab4collection')


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


def extract_from_pdf(pdf_path):
    text = ""
    
    reader = PdfReader(pdf_path)
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    
    return text


def load_pdfs_to_collection(folder_path, collection):
    folder = Path(folder_path)
    pdf_files = list(folder.glob("*.pdf"))
    
    for pdf_file in pdf_files:
        # Extract text from PDF
        text = extract_from_pdf(pdf_file)
        
        # Add to collection with filename as ID
        add_to_collection(collection, text, pdf_file.name)
    
    return collection

    
if 'openai_client' not in st.session_state:
    api_key = st.secrets["OPENAI_KEY"]
    st.session_state.openai_client = OpenAI(api_key=api_key)


# Load PDFs to collection (only once)
if 'Lab4_VectorDB' not in st.session_state:
    load_pdfs_to_collection('Lab-04-Data/', collection)
    st.session_state.Lab4_VectorDB = collection
else:
    collection = st.session_state.Lab4_VectorDB






#### MAIN APP ####

st.title('Lab 4: Chatbot using RAG')

#### QUERYING A COLLECTION -- ONLY USED FOR TESTING ####

topic = st.sidebar.text_input('Topic', placeholder='Type your topic (e.g., GenAI)...')

if topic:
    client = st.session_state.openai_client
    response = client.embeddings.create(
        input=topic,
        model='text-embedding-3-small')
    
    # Get the embedding
    query_embedding = response.data[0].embedding
    
    # Get the text related to this question (this prompt)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3  # The number of closest documents to return
    )
    
    # Display the results
    st.subheader(f'Results for: {topic}')
    
    for i in range(len(results['documents'][0])):
        doc = results['documents'][0][i]
        doc_id = results['ids'][0][i]
        
        st.write(f'**{i+1}. {doc_id}**')

else:
    st.info('Enter a topic in the sidebar to search the collection')


#### END OF TESTING SECTION ####





#make sure to store vector database in session state





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
        {"role": "assistant", "content": "Hi! What question do you have about IST 488?"}
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
    collection = st.session_state.Lab4_VectorDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    # Get the relevant documents
    relevant_docs = "\n\n".join(results['documents'][0])
        
    # Create enhanced prompt with RAG context
    rag_prompt = f"""Based on the following course materials:

{relevant_docs}



User question: {prompt}

Please answer the question using the information from the course materials above. If you use information from these materials, mention that it comes from the course content."""

    # Replace the user's prompt with the RAG-enhanced version
    st.session_state.messages[-1]["content"] = rag_prompt

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
