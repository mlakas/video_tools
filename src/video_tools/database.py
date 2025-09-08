"""
Database management module for video transcription data using aiosql.

This module provides:
- Simple database connection management with psycopg2
- CRUD operations for documents and chunks using aiosql
- Integration with video transcription workflow
"""

import os
import uuid
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import urllib.parse

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
import aiosql
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database manager for handling PostgreSQL operations using aiosql."""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize the database manager.
        
        Args:
            database_url: PostgreSQL connection string (defaults to DATABASE_URL env var)
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        
        if not self.database_url:
            raise ValueError("Database URL is required. Set DATABASE_URL environment variable or pass database_url parameter.")
        
        # Parse database URL for psycopg2
        parsed = urllib.parse.urlparse(self.database_url)
        self.connection_params = {
            'host': parsed.hostname,
            'port': parsed.port,
            'database': parsed.path[1:],  # Remove leading slash
            'user': parsed.username,
            'password': parsed.password
        }
        
        # Load SQL queries
        sql_file = Path(__file__).parent / 'sql' / 'queries.sql'
        self.queries = aiosql.from_path(sql_file, 'psycopg2')
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self) -> None:
        """Test database connection."""
        try:
            with psycopg2.connect(**self.connection_params) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise RuntimeError(f"Failed to connect to database: {e}")
    
    def _get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(**self.connection_params)
    
    def create_document(self, 
                       name: str,
                       url_internal: Optional[str] = None,
                       url_external: Optional[str] = None,
                       file_size: Optional[int] = None,
                       sha_hash: Optional[str] = None,
                       doc_title: Optional[str] = None,
                       doc_authors: Optional[List[str]] = None,
                       doc_keywords: Optional[List[str]] = None,
                       doc_year: Optional[int] = None) -> str:
        """
        Create a new document record.
        
        Args:
            name: Document name
            url_internal: Internal URL
            url_external: External URL
            file_size: File size in bytes
            sha_hash: SHA hash of the file
            doc_title: Document title
            doc_authors: List of authors
            doc_keywords: List of keywords
            doc_year: Publication year
            
        Returns:
            Document ID
        """
        document_id = str(uuid.uuid4())
        
        with self._get_connection() as conn:
            try:
                result = list(self.queries.create_document(
                    conn,
                    id=document_id,
                    name=name,
                    url_internal=url_internal,
                    url_external=url_external,
                    upload_time=datetime.utcnow(),
                    file_size=file_size,
                    sha_hash=sha_hash,
                    is_archived=False,
                    is_deleted=False,
                    doc_title=doc_title,
                    doc_authors=doc_authors,
                    doc_keywords=doc_keywords,
                    doc_year=doc_year
                ))
                conn.commit()
                logger.info(f"Created document: {document_id}")
                return document_id
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to create document: {e}")
                raise
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document dictionary or None if not found
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM document WHERE id = %s", (document_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
    
    def create_chunk(self,
                    document_id: str,
                    chunk_text: str,
                    chunk_page: Optional[int] = None,
                    chunk_timestamp: Optional[datetime] = None) -> str:
        """
        Create a new chunk record.
        
        Args:
            document_id: ID of the parent document
            chunk_text: Text content of the chunk
            chunk_page: Page number (optional)
            chunk_timestamp: Timestamp for the chunk (optional)
            
        Returns:
            Chunk ID
        """
        chunk_id = str(uuid.uuid4())
        
        with self._get_connection() as conn:
            try:
                result = list(self.queries.create_chunk(
                    conn,
                    id=chunk_id,
                    document_id=document_id,
                    chunk_text=chunk_text,
                    chunk_page=chunk_page,
                    chunk_timestamp=chunk_timestamp or datetime.utcnow()
                ))
                conn.commit()
                logger.info(f"Created chunk: {chunk_id}")
                return chunk_id
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to create chunk: {e}")
                raise
    
    def create_chunks_batch(self, 
                           document_id: str,
                           chunks_data: List[Dict[str, Any]]) -> List[str]:
        """
        Create multiple chunks in a batch operation.
        
        Args:
            document_id: ID of the parent document
            chunks_data: List of chunk data dictionaries
            
        Returns:
            List of created chunk IDs
        """
        chunk_ids = []
        
        with self._get_connection() as conn:
            try:
                for chunk_data in chunks_data:
                    chunk_id = str(uuid.uuid4())
                    result = list(self.queries.create_chunk(
                        conn,
                        id=chunk_id,
                        document_id=document_id,
                        chunk_text=chunk_data['text'],
                        chunk_page=chunk_data.get('page'),
                        chunk_timestamp=chunk_data.get('timestamp', datetime.utcnow())
                    ))
                    chunk_ids.append(chunk_id)
                
                conn.commit()
                logger.info(f"Created {len(chunk_ids)} chunks for document: {document_id}")
                return chunk_ids
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to create chunks batch: {e}")
                raise
    
    def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of chunk dictionaries
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM chunk WHERE document_id = %s ORDER BY chunk_page", (document_id,))
                result = cursor.fetchall()
                return [dict(row) for row in result]
    
    def update_document(self, document_id: str, **kwargs) -> bool:
        """
        Update a document record.
        
        Args:
            document_id: Document ID
            **kwargs: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        with self._get_connection() as conn:
            try:
                result = list(self.queries.update_document(
                    conn,
                    document_id=document_id,
                    **kwargs
                ))
                conn.commit()
                logger.info(f"Updated document: {document_id}")
                return bool(result)
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to update document: {e}")
                return False
    
    def delete_document(self, document_id: str, soft_delete: bool = True) -> bool:
        """
        Delete a document (soft delete by default).
        
        Args:
            document_id: Document ID
            soft_delete: If True, mark as deleted; if False, hard delete
            
        Returns:
            True if successful, False otherwise
        """
        with self._get_connection() as conn:
            try:
                if soft_delete:
                    result = list(self.queries.delete_document_soft(conn, document_id=document_id))
                    logger.info(f"Soft deleted document: {document_id}")
                else:
                    result = list(self.queries.delete_document_hard(conn, document_id=document_id))
                    logger.info(f"Hard deleted document: {document_id}")
                
                conn.commit()
                return bool(result)
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to delete document: {e}")
                return False
    
    def get_document_stats(self, document_id: str) -> Dict[str, Any]:
        """
        Get statistics for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Dictionary with document statistics
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        d.id as document_id,
                        d.name,
                        d.upload_time,
                        d.file_size,
                        COUNT(c.id) as chunk_count,
                        d.is_archived,
                        d.is_deleted
                    FROM document d
                    LEFT JOIN chunk c ON d.id = c.document_id
                    WHERE d.id = %s
                    GROUP BY d.id, d.name, d.upload_time, d.file_size, d.is_archived, d.is_deleted
                """, (document_id,))
                result = cursor.fetchone()
                return dict(result) if result else {}


def create_document_from_video(video_path: str, 
                             db_manager: DatabaseManager,
                             doc_title: Optional[str] = None,
                             doc_authors: Optional[List[str]] = None,
                             doc_keywords: Optional[List[str]] = None) -> str:
    """
    Create a document record from a video file or URL.
    
    Args:
        video_path: Path to the video file or URL
        db_manager: Database manager instance
        doc_title: Document title (defaults to filename or URL)
        doc_authors: List of authors
        doc_keywords: List of keywords
        
    Returns:
        Document ID
    """
    # Check if it's a URL
    try:
        result = urllib.parse.urlparse(video_path)
        is_url = all([result.scheme, result.netloc])
    except Exception:
        is_url = False
    
    if is_url:
        # Handle URL case
        url_parts = urllib.parse.urlparse(video_path)
        filename = os.path.basename(url_parts.path) or f"video_from_{url_parts.netloc}"
        if not filename or '.' not in filename:
            filename = f"video_from_{url_parts.netloc}.mp4"
        
        return db_manager.create_document(
            name=filename,
            url_external=video_path,
            file_size=None,  # Unknown for URLs
            sha_hash=None,   # Cannot hash URL content
            doc_title=doc_title or filename,
            doc_authors=doc_authors,
            doc_keywords=doc_keywords
        )
    else:
        # Handle local file case
        video_path_obj = Path(video_path)
        
        # Get file size
        file_size = video_path_obj.stat().st_size if video_path_obj.exists() else None
        
        # Generate SHA hash (simplified - in production you'd want to use hashlib)
        sha_hash = None
        if video_path_obj.exists():
            try:
                import hashlib
                with open(video_path_obj, 'rb') as f:
                    sha_hash = hashlib.sha256(f.read()).hexdigest()
            except Exception:
                pass
        
        return db_manager.create_document(
            name=video_path_obj.name,
            url_internal=str(video_path_obj.absolute()),
            file_size=file_size,
            sha_hash=sha_hash,
            doc_title=doc_title or video_path_obj.stem,
            doc_authors=doc_authors,
            doc_keywords=doc_keywords
        )