#!/usr/bin/env python3
"""
Example usage of the VideoTranscriber class.

This script demonstrates various ways to use the video transcription tool.
Make sure you have set up your Azure Speech Service credentials in a .env file.
"""

import os
from pathlib import Path
from video_tools.transcribevideo import VideoTranscriber

def example_basic_transcription():
    """Basic transcription example."""
    print("=== Basic Transcription Example ===")
    
    # Initialize transcriber (uses environment variables)
    transcriber = VideoTranscriber()
    
    # Example video path (replace with your actual video file)
    video_path = "example_video.mp4"
    
    if not Path(video_path).exists():
        print(f"Video file {video_path} not found. Please update the path.")
        return
    
    try:
        # Transcribe video with default settings
        result = transcriber.transcribe_video(
            video_path=video_path,
            output_format="json"
        )
        
        print("Transcription completed successfully!")
        print(f"Result preview: {result[:200]}...")
        
    except Exception as e:
        print(f"Transcription failed: {e}")

def example_subtitle_generation():
    """Generate subtitle files example."""
    print("\n=== Subtitle Generation Example ===")
    
    transcriber = VideoTranscriber()
    video_path = "example_video.mp4"
    
    if not Path(video_path).exists():
        print(f"Video file {video_path} not found. Please update the path.")
        return
    
    try:
        # Generate SRT subtitles
        srt_result = transcriber.transcribe_video(
            video_path=video_path,
            output_format="srt"
        )
        
        # Save to file
        with open("subtitles.srt", "w", encoding="utf-8") as f:
            f.write(srt_result)
        
        print("SRT subtitles saved to 'subtitles.srt'")
        
        # Generate VTT subtitles
        vtt_result = transcriber.transcribe_video(
            video_path=video_path,
            output_format="vtt"
        )
        
        with open("subtitles.vtt", "w", encoding="utf-8") as f:
            f.write(vtt_result)
        
        print("VTT subtitles saved to 'subtitles.vtt'")
        
    except Exception as e:
        print(f"Subtitle generation failed: {e}")

def example_custom_configuration():
    """Custom configuration example."""
    print("\n=== Custom Configuration Example ===")
    
    # Initialize with custom settings
    transcriber = VideoTranscriber(
        azure_key="your_custom_key",  # Override env var
        azure_region="eastus",        # Override env var
        ffmpeg_path="ffmpeg"          # Custom FFmpeg path if needed
    )
    
    video_path = "example_video.mp4"
    
    if not Path(video_path).exists():
        print(f"Video file {video_path} not found. Please update the path.")
        return
    
    try:
        # Transcribe with custom settings
        result = transcriber.transcribe_video(
            video_path=video_path,
            output_format="txt",
            language="es-ES",         # Spanish language
            chunk_duration=45         # 45-second chunks
        )
        
        print("Custom transcription completed!")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Custom transcription failed: {e}")

def example_audio_extraction_only():
    """Audio extraction example without transcription."""
    print("\n=== Audio Extraction Example ===")
    
    transcriber = VideoTranscriber()
    video_path = "example_video.mp4"
    
    if not Path(video_path).exists():
        print(f"Video file {video_path} not found. Please update the path.")
        return
    
    try:
        # Extract audio only
        audio_path = transcriber.extract_audio(video_path, output_format="wav")
        print(f"Audio extracted to: {audio_path}")
        
        # Clean up the extracted audio
        os.remove(audio_path)
        print("Extracted audio cleaned up")
        
    except Exception as e:
        print(f"Audio extraction failed: {e}")

def main():
    """Run all examples."""
    print("Video Transcription Tool Examples")
    print("=" * 40)
    
    # Check if Azure credentials are set
    if not os.getenv('AZURE_SPEECH_KEY') or not os.getenv('AZURE_SPEECH_REGION'):
        print("⚠️  Warning: Azure Speech Service credentials not found in environment variables.")
        print("   Please create a .env file with:")
        print("   AZURE_SPEECH_KEY=your_key_here")
        print("   AZURE_SPEECH_REGION=your_region_here")
        print()
    
    # Run examples
    example_basic_transcription()
    example_subtitle_generation()
    example_custom_configuration()
    example_audio_extraction_only()
    
    print("\n" + "=" * 40)
    print("Examples completed!")
    print("\nTo use the tool from command line:")
    print("python -m video_tools.transcribevideo your_video.mp4 -f srt -o output.srt")

if __name__ == "__main__":
    main()

