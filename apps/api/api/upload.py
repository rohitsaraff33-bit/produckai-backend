"""File upload API endpoints."""

from typing import List

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.database import get_db
from apps.api.services.file_upload import get_upload_service

logger = structlog.get_logger()
router = APIRouter()


class UploadResponse(BaseModel):
    """Response from file upload operation."""

    total_files: int
    successful_files: int
    failed_files: int
    total_feedback_items: int
    errors: List[dict]
    message: str

    class Config:
        from_attributes = True


@router.post("/upload-feedback", response_model=UploadResponse)
async def upload_feedback_files(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Upload customer feedback files for ingestion.

    Supports:
    - CSV files with feedback/text column
    - PDF documents
    - DOC/DOCX documents
    - Plain text files

    Args:
        files: List of uploaded files (single or multiple)
        background_tasks: Background tasks for async processing
        db: Database session

    Returns:
        Upload summary with counts and any errors
    """
    try:
        logger.info(f"Received {len(files)} file(s) for upload")

        # Validate files
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        # Read file contents
        file_data = []
        for upload_file in files:
            content = await upload_file.read()
            file_data.append((
                upload_file.filename,
                upload_file.content_type,
                content
            ))

        # Process files through upload service
        upload_service = get_upload_service()
        results = await upload_service.process_uploaded_files(file_data, db)

        # Build response message
        if results["successful_files"] == 0:
            message = "All files failed to process"
        elif results["failed_files"] == 0:
            message = f"Successfully processed all {results['successful_files']} file(s)"
        else:
            message = f"Processed {results['successful_files']}/{results['total_files']} file(s) successfully"

        # Trigger clustering if feedback was successfully ingested
        if results["total_feedback_items"] > 0 and background_tasks:
            from apps.api.api.clustering import run_clustering_task, get_clustering_status
            from apps.api.config import get_settings

            settings = get_settings()

            # Only trigger if not already running
            status = get_clustering_status()
            if not status.get("is_running"):
                logger.info(f"Triggering clustering pipeline after ingesting {results['total_feedback_items']} feedback items")
                background_tasks.add_task(run_clustering_task, settings.database_url)

        return UploadResponse(
            total_files=results["total_files"],
            successful_files=results["successful_files"],
            failed_files=results["failed_files"],
            total_feedback_items=results["total_feedback_items"],
            errors=results["errors"],
            message=message,
        )

    except Exception as e:
        logger.error("File upload failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/supported-formats")
async def get_supported_formats():
    """
    Get list of supported file formats for feedback upload.

    Returns:
        Dictionary of supported formats with descriptions
    """
    return {
        "supported_formats": [
            {
                "format": "CSV",
                "extensions": [".csv"],
                "mime_types": ["text/csv"],
                "description": "CSV file with 'feedback' or 'text' column",
                "example_columns": ["feedback", "customer", "date"]
            },
            {
                "format": "PDF",
                "extensions": [".pdf"],
                "mime_types": ["application/pdf"],
                "description": "PDF document with text content"
            },
            {
                "format": "DOC/DOCX",
                "extensions": [".doc", ".docx"],
                "mime_types": [
                    "application/msword",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ],
                "description": "Microsoft Word document"
            },
            {
                "format": "TXT",
                "extensions": [".txt"],
                "mime_types": ["text/plain"],
                "description": "Plain text file with feedback items"
            }
        ],
        "max_file_size": "50MB",
        "max_files_per_upload": 10
    }
