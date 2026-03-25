"""
build_db.py — Run this ONCE offline before launching the app.
It reads news.csv, embeds each article, and stores them in ChromaDB.

Usage:
    pip install openai chromadb pandas
    OPENAI_API_KEY=sk-... python build_db.py
"""

import os
import sys
import pandas as pd
import chromadb
from openai import OpenAI

__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

CSV_PATH = "news.csv"
CHROMA_PATH = "./ChromaDB_HW7"
COLLECTION_NAME = "HW7_News"
EMBED_MODEL = "text-embedding-3-small"

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# ── Load CSV ──────────────────────────────────────────────────────────────────
df = pd.read_csv(CSV_PATH)
print(f"Loaded {len(df)} rows from {CSV_PATH}")

# Drop rows with no Document text
df = df.dropna(subset=["Document"])
df = df.reset_index(drop=True)
print(f"{len(df)} rows after dropping empty documents")

# ── Connect to ChromaDB ───────────────────────────────────────────────────────
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(COLLECTION_NAME)

if collection.count() > 0:
    print(f"Collection already has {collection.count()} docs. Delete {CHROMA_PATH} to rebuild.")
    sys.exit(0)

# ── Embed and store in batches ────────────────────────────────────────────────
BATCH_SIZE = 50

documents = []
embeddings = []
ids = []
metadatas = []

for i, row in df.iterrows():
    doc_text = str(row["Document"]).strip()
    doc_id = f"article_{i}"
    metadata = {
        "company": str(row.get("company_name", "")),
        "date": str(row.get("Date", "")),
        "url": str(row.get("URL", "")),
    }

    documents.append(doc_text)
    ids.append(doc_id)
    metadatas.append(metadata)

    # Embed in batches
    if len(documents) == BATCH_SIZE or i == len(df) - 1:
        print(f"  Embedding articles {i - len(documents) + 1} – {i} ...")
        response = client.embeddings.create(input=documents, model=EMBED_MODEL)
        batch_embeddings = [r.embedding for r in response.data]

        collection.add(
            documents=documents,
            embeddings=batch_embeddings,
            ids=ids,
            metadatas=metadatas,
        )

        documents, embeddings, ids, metadatas = [], [], [], []

print(f"\n✅ Done. {collection.count()} articles stored in {CHROMA_PATH}")
