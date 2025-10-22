from fastapi import APIRouter, HTTPException
from loguru import logger

from db.database import get_db
from db.repository import DataSourceRepository
from api.schemas import DataSourceResponse, DataSourceApiKeyRequest

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[DataSourceResponse])
async def list_sources(active_only: bool = True):
    """
    List all data sources and their API key requirements
    """
    async with get_db() as db:
        sources = await DataSourceRepository.get_all(db, active_only=active_only)
    
    return [DataSourceResponse.model_validate(source) for source in sources]


@router.post("/{source_name}/api-key")
async def set_source_api_key(source_name: str, request: DataSourceApiKeyRequest):
    """
    Set API key for a data source
    """
    async with get_db() as db:
        source = await DataSourceRepository.set_api_key(
            db=db,
            source_name=source_name,
            api_key=request.api_key
        )
        
        if not source:
            raise HTTPException(
                status_code=404,
                detail=f"Data source '{source_name}' not found"
            )
    
    logger.info(f"API key set for source: {source_name}")
    
    return {
        "status": "success",
        "message": f"API key set for {source_name}",
        "source_name": source_name,
    }


@router.get("/status")
async def get_sources_status():
    """
    Get status of all data sources (which are active, which need API keys)
    """
    async with get_db() as db:
        sources = await DataSourceRepository.get_all(db, active_only=False)
    
    status_summary = {
        "total_sources": len(sources),
        "active_sources": sum(1 for s in sources if s.is_active),
        "sources_needing_keys": [],
        "sources_ready": [],
    }
    
    for source in sources:
        source_info = {
            "name": source.source_name,
            "display_name": source.display_name,
            "requires_api_key": source.requires_api_key,
            "has_api_key": bool(source.user_api_key),
            "is_active": source.is_active,
        }
        
        if source.requires_api_key and not source.user_api_key:
            status_summary["sources_needing_keys"].append(source_info)
        elif source.is_active:
            status_summary["sources_ready"].append(source_info)
    
    return status_summary

