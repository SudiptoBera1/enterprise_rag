from ingestion.loader import load_documents
from retriever.vector_store import VectorStore
from retriever.keyword_search import KeywordSearch
from retriever.hybrid import HybridRetriever
from llm.prompt import build_prompt
from llm.generator import generate_response

print("🚀 Starting Full Hybrid RAG Pipeline...")

# Step 1: Load documents
documents = load_documents("data/raw")
print("Documents loaded:", len(documents))

if len(documents) == 0:
    print("No documents found. Stopping execution.")
    exit()

# Step 2: Build vector store
vector_store = VectorStore()
vector_store.build_index(documents)
vector_store.save()
vector_store.load()

# Step 3: Build keyword search
keyword_search = KeywordSearch(documents)

# Step 4: Hybrid retriever
hybrid = HybridRetriever(vector_store, keyword_search)

# Step 5: Query
query = "Explain AI governance policy classification"
print(f"\n🔎 Running hybrid retrieval for: {query}")

contexts = hybrid.retrieve(query, k=3)

print("\n📄 Retrieved Documents:")
for c in contexts:
    print("-", c["doc_id"])

# Step 6: Build grounded prompt
prompt = build_prompt(query, contexts)

# Step 7: Generate LLM answer
print("\n🧠 Generating grounded response...\n")

answer = generate_response(prompt)

print("📢 FINAL ANSWER:\n")
print(answer)

print("\n✅ Full RAG pipeline completed.")