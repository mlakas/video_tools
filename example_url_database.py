#!/usr/bin/env python3
"""
Example script demonstrating video transcription with URL support and database storage.

This script shows how to:
1. Transcribe videos from URLs (YouTube, Vimeo, etc.)
2. Transcribe local video files
3. Store the results in PostgreSQL database
4. Retrieve and display transcription data
"""

import os
from pathlib import Path
from video_tools.transcribevideo import VideoTranscriber
from video_tools.database import DatabaseManager

def main():
    """Example usage of video transcription with URL and database support."""
    
    # Example URLs and local file paths
    examples = [
        {
            "name": "YouTube Video",
            "path": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Replace with actual URL
            "title": "Sample YouTube Video",
            "authors": ["YouTube Creator"],
            "keywords": ["music", "video", "entertainment"]
        },
        {
            "name": "Local Video File",
            "path": "Building Tomorrows Workforce.mp4",  # Your local file
            "title": "Building Tomorrow's Workforce",
            "authors": ["Mike Lakas"],
            "keywords": ["workforce", "training", "development"]
        }
    ]
    
    try:
        # Initialize the transcriber
        print("Initializing video transcriber...")
        transcriber = VideoTranscriber()
        
        for example in examples:
            print(f"\n{'='*60}")
            print(f"Processing: {example['name']}")
            print(f"Source: {example['path']}")
            print(f"{'='*60}")
            
            # Check if it's a URL or local file
            if example['path'].startswith(('http://', 'https://')):
                print("Detected URL - will download video first")
            else:
                if not Path(example['path']).exists():
                    print(f"Local file not found: {example['path']}")
                    print("Skipping this example...")
                    continue
                print("Detected local file")
            
            # Transcribe video and store in database
            print(f"Transcribing: {example['name']}")
            result = transcriber.transcribe_video_to_database(
                video_path=example['path'],
                language='en-US',
                chunk_duration=30,
                doc_title=example['title'],
                doc_authors=example['authors'],
                doc_keywords=example['keywords']
            )
            
            print(f"\n=== Transcription Results ===")
            print(f"Document ID: {result['document_id']}")
            print(f"Chunks created: {result['chunk_count']}")
            print(f"Transcription segments: {result['transcription_segments']}")
            
            # Display document stats
            doc_stats = result['document_stats']
            print(f"\n=== Document Statistics ===")
            print(f"Name: {doc_stats['name']}")
            print(f"Upload time: {doc_stats['upload_time']}")
            print(f"File size: {doc_stats['file_size']} bytes" if doc_stats['file_size'] else "File size: Unknown (URL)")
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
        
        print(f"\n{'='*60}")
        print("=== All Transcriptions Complete ===")
        print("All transcription data has been stored in the PostgreSQL database.")
        print("You can now query the 'document' and 'chunk' tables to retrieve this data.")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
