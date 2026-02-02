import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup


def read_url_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.get_text()
    except requests.RequestException as e:
        st.error(f"Error reading {url}: {e}", icon="❌")
        return None



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

use_advanced = st.sidebar.checkbox("Use advanced model", value=False)
model = "gpt-5-mini" if use_advanced else "gpt-5-nano"



try:
    openai_api_key = st.secrets["API_KEY"]
except KeyError:
    st.error("OpenAI API key not found in Streamlit secrets.", icon="❌")
    st.stop()



try:
    client = OpenAI(api_key=openai_api_key)
    client.models.list()
    st.success("API key loaded from secrets and validated!", icon="✅")
except Exception as e:
    st.error(f"Error connecting to OpenAI: {str(e)}", icon="❌")
    st.stop()


if summary_style == "100 words":
    instruction = (
        "Summarize the content in exactly 100 words. "
        "Write as one paragraph. Do not include a title."
    )
elif summary_style == "2 connecting paragraphs":
    instruction = (
        "Summarize the content in two connected paragraphs. "
        "Do not use bullet points."
    )
else:
    instruction = (
        "Summarize the content in exactly 5 bullet points. "
        "Each bullet should be one sentence."
    )

generate = st.button("Generate summary", disabled=not url)

if url and generate:
    document = read_url_content(url)

    if not document:
        st.stop()

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that summarizes web content accurately and concisely.",
        },
        {
            "role": "user",
            "content": f"{instruction}\n\nURL CONTENT:\n{document}",
        },
    ]

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )

    st.subheader("Your summary")
    st.write_stream(stream)







# try:
#     # Create OpenAI client using secret key
#     client = OpenAI(api_key=openai_api_key)

#     # Validate API key
#     client.models.list()
#     st.success("API key loaded from secrets and validated!", icon="✅")

#     # File uploader
#     uploaded_file = st.file_uploader(
#         "Upload a document (.txt or .pdf)", type=("txt", "pdf")
#     )



#     if summary_style == "100 words":
#         instruction = (
#             "Summarize the document in exactly 100 words. "
#             "Write as one paragraph. Do not include a title."
#         )
#     elif summary_style == "2 connecting paragraphs":
#         instruction = (
#             "Summarize the document in two connected paragraphs. "
#             "Keep the tone clear and professional. Do not use bullet points."
#         )
#     else:  # "5 bullet points"
#         instruction = (
#             "Summarize the document in exactly 5 bullet points. "
#             "Each bullet should be one sentence. Do not include extra bullets."
#         )

#     generate = st.button("Generate summary", disabled=not uploaded_file)

#     if uploaded_file and generate:
#          # Process the uploaded file (txt or pdf)
#         file_extension = uploaded_file.name.split('.')[-1].lower()

#         if file_extension == 'txt':
#             document = uploaded_file.read().decode("utf-8", errors="ignore")
#         elif file_extension == 'pdf':
#             document = read_pdf(uploaded_file)
#         else:
#             st.error("Unsupported file type.")
#             st.stop()
            
#         messages = [
#             {
#                 "role": "system",
#                 "content": "You are a helpful assistant that summarizes documents accurately and concisely.",
#             },
#             {
#                 "role": "user",
#                 "content": f"{instruction}\n\nDOCUMENT:\n{document}",
#             },
#              ] 
#         stream = client.chat.completions.create(
#             model=model,
#             messages=messages,
#             stream=True,
#         )
#         st.subheader("Your summary")
#         st.write_stream(stream)
         

# except Exception as e:
#     st.error(f"Error connecting to OpenAI: {str(e)}", icon="❌")