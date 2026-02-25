import os
from pypdf import PdfReader


def extract_text_from_pdf(file_path):
    """
    Extract text from a single PDF file.
    """
    try:
        reader = PdfReader(file_path)
        text = ""

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        return text

    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""


def chunk_text(text, chunk_size=200):
    """
    Split text into chunks of given word size.
    """
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    return chunks


def load_documents(folder_path):
    """
    Load all PDFs from folder and return chunked documents.
    """
    documents = []

    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return documents

    print(f"Scanning folder: {folder_path}")
    print("Files found:", os.listdir(folder_path))

    for file in os.listdir(folder_path):
        if file.lower().endswith(".pdf"):
            file_path = os.path.join(folder_path, file)

            print(f"\nReading file: {file}")

            full_text = extract_text_from_pdf(file_path)

            if not full_text.strip():
                print(f"No text extracted from {file}")
                continue

            chunks = chunk_text(full_text)

            print(f"Chunks created from {file}: {len(chunks)}")

            for chunk in chunks:
                documents.append({
                    "doc_id": file.replace(".pdf", ""),
                    "content": chunk
                })

    print(f"\nTotal chunks from all documents: {len(documents)}")
    return documents


# ✅ This block allows standalone execution
if __name__ == "__main__":
    # Get project root directory safely
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    data_path = os.path.join(BASE_DIR, "data", "raw")

    print("Resolved data path:", data_path)

    docs = load_documents(data_path)

    if docs:
        print("\nFirst chunk preview:\n")
        print(docs[0]["content"][:500])
    else:
        print("No documents loaded.")