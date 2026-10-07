import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the project root is importable when running as a script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database import Base, engine, SessionLocal
from backend.routes.routes import router as api_router
from backend.services.document_service import document_service
from backend.services.vector_service import vector_service
from backend.models.models import User

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed curated documents and initialize FAISS index
    db = SessionLocal()
    try:
        # 1. Ensure a default user exists
        if db.query(User).count() == 0:
            default_user = User(
                name="Alex Smith",
                email="alex@example.com",
                role="Machine Learning Engineer",
                experience_level="Mid-Level",
                technical_background="Python, Transformers, PyTorch, RAG",
                networking_goal="Career Growth & Collaboration"
            )
            db.add(default_user)
            db.commit()

        # 2. Seed curated knowledge documents
        document_service.seed_curated_knowledge(db)

        # 3. Build/initialize FAISS and BM25 index
        vector_service.rebuild_index(db)
    except Exception as e:
        print(f"[Warning] Startup seeding/indexing error: {e}")
    finally:
        db.close()

    yield
    # Shutdown logic if any

app = FastAPI(
    title="Intelligent Networking Assistant",
    description="AI-powered assistant for personalized professional communication, RAG, and knowledge verification.",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS so Streamlit client can interact with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

# Mount static files and frontend UI
STATIC_DIR = ROOT_DIR / "frontend" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_frontend(request: Request):
    accept = request.headers.get("accept", "")
    index_file = STATIC_DIR / "index.html"

    # Return HTML web app if browser requests text/html, otherwise return JSON status for API clients
    if index_file.exists() and "text/html" in accept:
        try:
            content = index_file.read_text(encoding="utf-8")
            return HTMLResponse(content=content)
        except Exception:
            return FileResponse(index_file)

    return {
        "message": "Intelligent Networking Assistant API is running.",
        "docs_url": "/docs",
        "version": "2.0.0"
    }

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
