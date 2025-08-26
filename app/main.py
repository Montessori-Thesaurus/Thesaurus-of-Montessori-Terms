from __future__ import annotations

from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.responses import HTMLResponse, ORJSONResponse, PlainTextResponse, Response
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.skos.graph import SKOSGraphService


settings = get_settings()
app = FastAPI(title="Montessori Glossary - SKOS",
              version="0.1.0",
              docs_url="/api/docs",
              redoc_url="/api/redoc")

templates = Jinja2Templates(directory="templates")

skos_service = SKOSGraphService(ttl_path=settings.data_ttl_path,
                                default_language=settings.default_language)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, q: Optional[str] = Query(default=None, description="Search query")) -> HTMLResponse:
    language = request.headers.get("accept-language", settings.default_language)
    if q:
        results = skos_service.search_concepts(q, language=language)
    else:
        results, total = skos_service.list_concepts(limit=50, language=language)
    return templates.TemplateResponse("index.html", {"request": request, "query": q, "results": results})


@app.get("/concepts", response_class=ORJSONResponse)
async def list_concepts(q: Optional[str] = Query(default=None), limit: int = 50, offset: int = 0) -> ORJSONResponse:
    if q:
        results = skos_service.search_concepts(q, limit=limit)
        return ORJSONResponse([r.__dict__ for r in results])
    results, total = skos_service.list_concepts(limit=limit, offset=offset)
    return ORJSONResponse({"total": total, "items": [r.__dict__ for r in results]})


@app.get("/concepts/{iri_encoded}")
async def get_concept(iri_encoded: str) -> ORJSONResponse:
    iri = unquote(iri_encoded)
    detail = skos_service.get_concept_detail(iri)
    if detail is None:
        raise HTTPException(status_code=404, detail="Concept not found")
    return ORJSONResponse(detail)


@app.get("/c/{iri_encoded}", response_class=HTMLResponse)
async def concept_page(request: Request, iri_encoded: str) -> HTMLResponse:
    iri = unquote(iri_encoded)
    detail = skos_service.get_concept_detail(iri)
    if detail is None:
        raise HTTPException(status_code=404, detail="Concept not found")
    return templates.TemplateResponse("concept.html", {"request": request, "concept": detail})


@app.get("/download.{fmt}")
async def download_dataset(fmt: str) -> Response:
    try:
        data, content_type = skos_service.serialize(fmt)
        return PlainTextResponse(content=data, media_type=content_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/reload")
async def reload_data() -> dict:
    skos_service.reload()
    return {"status": "reloaded"}