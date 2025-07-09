import requests
from bs4 import BeautifulSoup
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.documents import Document
import time

def fetch_web_content(url: str) -> str:
    """
    Fetches the main text content from a given URL.
    Args:
        url (str): The URL of the webpage to fetch.
    Returns:
        str: The extracted text content, or an empty string if fetching fails.
    """
    print(f"[DEBUG] Starting fetch for {url}")
    fetch_start_time = time.time()
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        for script_or_style in soup(['script', 'style']):
            script_or_style.extract()

        text = soup.get_text(separator=' ', strip=True)
        fetch_end_time = time.time()
        print(f"[DEBUG] Finished fetching content ({len(text)} chars) in {fetch_end_time - fetch_start_time:.2f}s")
        return text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return ""
    except Exception as e:
        print(f"An unexpected error occurred while processing URL {url}: {e}")
        return ""

def create_vector_store_from_web(url: str):
    """
    Fetches web content, splits it into chunks, and creates a FAISS vector store.
    Args:
        url (str): The URL to process.
    Returns:
        FAISS: A FAISS vector store, or None if processing fails.
        str: An error message if something goes wrong, None otherwise.
    """
    print(f"[Fetching content from: {url}]")
    raw_text = fetch_web_content(url)

    if not raw_text:
        return None, "Could not fetch content from the URL or URL is empty."

    documents = [Document(page_content=raw_text, metadata={"source": url})]

    print("[Splitting document into chunks...]")
    split_start_time = time.time()
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(documents)
    split_end_time = time.time()
    print(f"[DEBUG] Finished splitting into {len(docs)} chunks in {split_end_time - split_start_time:.2f}s")

    if not docs:
        return None, "Document splitting resulted in no chunks. Content might be too small or text splitter issue."

    print("[Creating vector store with Ollama Embeddings (phi3:mini)]")
    embed_start_time = time.time()
    embeddings = OllamaEmbeddings(model="phi3:mini")
    vectorstore = FAISS.from_documents(docs, embeddings)
    embed_end_time = time.time()
    print(f"[DEBUG] Finished creating vector store in {embed_end_time - embed_start_time:.2f}s")

    try:
        print("[Vector store created successfully.]")
        return vectorstore, None
    except Exception as e:
        return None, f"Error creating vector store: {e}"

def retrieve_context_from_vector_store(vectorstore, query: str, k=3) -> str:
    """
    Retrieves relevant document chunks from the vector store based on the query.
    Args:
        vectorstore (FAISS): The FAISS vector store.
        query (str): The user's query.
        k (int): The number of top relevant chunks to retrieve.
    Returns:
        str: Concatenated text of the retrieved chunks.
    """
    if vectorstore is None:
        return ""

    print(f"[DEBUG] Retrieving context for query: {query[:50]}...")
    retrieve_start_time = time.time()
    try:
        retrieved_docs = vectorstore.similarity_search(query, k=k)
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        retrieve_end_time = time.time()
        print(f"[DEBUG] Finished retrieving context in {retrieve_end_time - retrieve_start_time:.2f}s")
        return context
    except Exception as e:
        print(f"Error retrieving context from vector store: {e}")
        return ""

