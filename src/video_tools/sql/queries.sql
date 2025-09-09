-- name: create_document
-- Create a new document record
INSERT INTO document (id, name, "URL_internal", "URL_external", upload_time, file_size, sha_hash, is_archived, is_deleted, doc_title, doc_authors, doc_keywords, doc_year)
VALUES (:id, :name, :url_internal, :url_external, :upload_time, :file_size, :sha_hash, :is_archived, :is_deleted, :doc_title, :doc_authors, :doc_keywords, :doc_year)
RETURNING id;

-- name: get_document
-- Get a document by ID
SELECT * FROM document WHERE id = :document_id;

-- name: create_chunk
-- Create a new chunk record
INSERT INTO chunk (id, document_id, chunk_text, chunk_page, chunk_timestamp, token_count, word_count, start_offset, end_offset)
VALUES (:id, :document_id, :chunk_text, :chunk_page, :chunk_timestamp, :token_count, :word_count, :start_offset, :end_offset)
RETURNING id;

-- name: create_chunks_batch
-- Create multiple chunks in a batch operation
INSERT INTO chunk (id, document_id, chunk_text, chunk_page, chunk_timestamp, token_count, word_count, start_offset, end_offset)
VALUES (:id, :document_id, :chunk_text, :chunk_page, :chunk_timestamp, :token_count, :word_count, :start_offset, :end_offset)
RETURNING id;

-- name: get_chunks_by_document
-- Get all chunks for a document
SELECT * FROM chunk WHERE document_id = :document_id ORDER BY chunk_page;

-- name: update_document
-- Update a document record
UPDATE document 
SET name = COALESCE(:name, name),
    "URL_internal" = COALESCE(:url_internal, "URL_internal"),
    "URL_external" = COALESCE(:url_external, "URL_external"),
    file_size = COALESCE(:file_size, file_size),
    sha_hash = COALESCE(:sha_hash, sha_hash),
    is_archived = COALESCE(:is_archived, is_archived),
    is_deleted = COALESCE(:is_deleted, is_deleted),
    doc_title = COALESCE(:doc_title, doc_title),
    doc_authors = COALESCE(:doc_authors, doc_authors),
    doc_keywords = COALESCE(:doc_keywords, doc_keywords),
    doc_year = COALESCE(:doc_year, doc_year)
WHERE id = :document_id
RETURNING id;

-- name: delete_document_soft
-- Soft delete a document (mark as deleted)
UPDATE document SET is_deleted = true WHERE id = :document_id
RETURNING id;

-- name: delete_document_hard
-- Hard delete a document and its chunks
DELETE FROM chunk WHERE document_id = :document_id;
DELETE FROM document WHERE id = :document_id
RETURNING id;

-- name: get_document_stats
-- Get statistics for a document
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
WHERE d.id = :document_id
GROUP BY d.id, d.name, d.upload_time, d.file_size, d.is_archived, d.is_deleted;
