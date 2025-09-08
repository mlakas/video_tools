#!/usr/bin/env python3
"""
Example script demonstrating video transcription with database storage.

This script shows how to:
1. Transcribe a video file
2. Store the results in PostgreSQL database
3. Retrieve and display transcription data
"""

import os
from pathlib import Path
from video_tools.transcribevideo import VideoTranscriber
from video_tools.database import DatabaseManager

def main():
    """Example usage of video transcription with database storage."""
    
    # Example video file path (update this to your actual video file)
    video_path = "Building Tomorrows Workforce.mp4"
    
    if not Path(video_path).exists():
        print(f"Video file not found: {video_path}")
        print("Please update the video_path variable with a valid video file.")
        return
    
    try:
        # Initialize the transcriber
        print("Initializing video transcriber...")
        transcriber = VideoTranscriber()
        
        # Transcribe video and store in database
        print(f"Transcribing video: {video_path}")
        result = transcriber.transcribe_video_to_database(
            video_path=video_path,
            language='en-US',
            chunk_duration=30,
            doc_title="Building Tomorrow's Workforce",
            doc_authors=["Mike Lakas"],
            doc_keywords=["workforce", "training", "development", "video"]
        )
        
        print("\n=== Transcription Results ===")
        print(f"Document ID: {result['document_id']}")
        print(f"Chunks created: {result['chunk_count']}")
        print(f"Transcription segments: {result['transcription_segments']}")
        
        # Display document stats
        doc_stats = result['document_stats']
        print(f"\n=== Document Statistics ===")
        print(f"Name: {doc_stats['name']}")
        print(f"Upload time: {doc_stats['upload_time']}")
        print(f"File size: {doc_stats['file_size']} bytes")
        print(f"Chunk count: {doc_stats['chunk_count']}")
        
        # Retrieve and display some chunks
        print(f"\n=== Sample Transcription Chunks ===")
        chunks = transcriber.db_manager.get_chunks_by_document(result['document_id'])
        
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            print(f"\nChunk {i+1} (Page {chunk.chunk_page}):")
            print(f"Timestamp: {chunk.chunk_timestamp}")
            print(f"Text: {chunk.chunk_text[:200]}{'...' if len(chunk.chunk_text) > 200 else ''}")
        
        if len(chunks) > 3:
            print(f"\n... and {len(chunks) - 3} more chunks")
        
        print(f"\n=== Database Storage Complete ===")
        print(f"All transcription data has been stored in the PostgreSQL database.")
        print(f"You can now query the 'document' and 'chunk' tables to retrieve this data.")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
