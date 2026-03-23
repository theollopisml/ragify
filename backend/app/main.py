from fastapi import FastAPI

app = FastAPI(
    title="Ragify",
    description="Assistant IA RAG pour boutique Shopify",
)


@app.get("/health")
async def health():
    """Endpoint de santé — vérifie que le backend tourne."""
    return {"status": "ok"}
