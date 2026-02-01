import streamlit as st
from openai import OpenAI
import pdfplumber

def read_pdf(uploaded_file):
    text = ""

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

    return text




# Show title and description.
st.title("Lab 2")
st.write(
    "Upload a document below and ask a question about it – GPT will answer! "
)


st.sidebar.header("Summary Options")

summary_style = st.sidebar.radio(
    "Choose a summary format:",
    (
        "100 words",
        "2 connecting paragraphs",
        "5 bullet points",
    ),
)

use_advanced = st.sidebar.checkbox("Use advanced model", value=False)
model = "gpt-5-mini" if use_advanced else "gpt-5-nano"


# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management


try:
    openai_api_key = st.secrets["API_KEY"]
except KeyError:
    st.error("OpenAI API key not found in Streamlit secrets.", icon="❌")
    st.stop()






try:
    # Create OpenAI client using secret key
    client = OpenAI(api_key=openai_api_key)

    # Validate API key
    client.models.list()
    st.success("API key loaded from secrets and validated!", icon="✅")

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload a document (.txt or .pdf)", type=("txt", "pdf")
    )



    if summary_style == "100 words":
        instruction = (
            "Summarize the document in exactly 100 words. "
            "Write as one paragraph. Do not include a title."
        )
    elif summary_style == "2 connecting paragraphs":
        instruction = (
            "Summarize the document in two connected paragraphs. "
            "Keep the tone clear and professional. Do not use bullet points."
        )
    else:  # "5 bullet points"
        instruction = (
            "Summarize the document in exactly 5 bullet points. "
            "Each bullet should be one sentence. Do not include extra bullets."
        )

    generate = st.button("Generate summary", disabled=not uploaded_file)

    if uploaded_file and generate:
         # Process the uploaded file (txt or pdf)
        file_extension = uploaded_file.name.split('.')[-1].lower()

        if file_extension == 'txt':
            document = uploaded_file.read().decode("utf-8", errors="ignore")
        elif file_extension == 'pdf':
            document = read_pdf(uploaded_file)
        else:
            st.error("Unsupported file type.")
            st.stop()
            
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that summarizes documents accurately and concisely.",
            },
            {
                "role": "user",
                "content": f"{instruction}\n\nDOCUMENT:\n{document}",
            },
             ] 
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        st.subheader("Your summary")
        st.write_stream(stream)
         

except Exception as e:
    st.error(f"Error connecting to OpenAI: {str(e)}", icon="❌")