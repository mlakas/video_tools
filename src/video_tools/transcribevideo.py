from dotenv import load_dotenv
import os
import subprocess
import tempfile
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging
from datetime import datetime
import urllib.parse

import azure.cognitiveservices.speech as speechsdk
from tqdm import tqdm
import yt_dlp

from .database import DatabaseManager, create_document_from_video

# Load environment variables
load_dotenv()

class VideoTranscriber:
    """
    A class for transcribing videos using Azure Speech-to-Text and FFmpeg.
    
    This class handles:
    - Audio extraction from video files using FFmpeg
    - Audio preprocessing and chunking for optimal transcription
    - Azure Speech-to-Text transcription with configurable options
    - Output formatting in various formats (SRT, VTT, JSON)
    """
    
    def __init__(self, 
                 azure_key: Optional[str] = None,
                 azure_region: Optional[str] = None,
                 ffmpeg_path: Optional[str] = None,
                 database_url: Optional[str] = None):
        """
        Initialize the VideoTranscriber.
        
        Args:
            azure_key: Azure Speech Service key (defaults to AZURE_SPEECH_KEY env var)
            azure_region: Azure Speech Service region (defaults to AZURE_SPEECH_REGION env var)
            ffmpeg_path: Path to FFmpeg executable (defaults to system PATH)
            database_url: PostgreSQL connection string (defaults to DATABASE_URL env var)
        """
        self.azure_key = azure_key or os.getenv('AZURE_SPEECH_KEY')
        self.azure_region = azure_region or os.getenv('AZURE_SPEECH_REGION')
        self.ffmpeg_path = ffmpeg_path or 'ffmpeg'
        
        if not self.azure_key:
            raise ValueError("Azure Speech Service key is required. Set AZURE_SPEECH_KEY environment variable or pass azure_key parameter.")
        if not self.azure_region:
            raise ValueError("Azure Speech Service region is required. Set AZURE_SPEECH_REGION environment variable or pass azure_region parameter.")
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize database manager
        try:
            self.db_manager = DatabaseManager(database_url)
            self.logger.info("Database connection initialized")
        except Exception as e:
            self.logger.warning(f"Database connection failed: {e}. Transcription will work without database storage.")
            self.db_manager = None
        
        # Verify FFmpeg is available
        self._verify_ffmpeg()
    
    def _is_url(self, path: str) -> bool:
        """Check if the given path is a URL."""
        try:
            result = urllib.parse.urlparse(path)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _download_video_from_url(self, url: str) -> str:
        """
        Download video from URL using yt-dlp.
        
        Args:
            url: Video URL to download
            
        Returns:
            Path to the downloaded video file
        """
        self.logger.info(f"Downloading video from URL: {url}")
        
        # Create temporary directory for download
        temp_dir = tempfile.mkdtemp()
        
        # Configure yt-dlp options
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'format': 'best[ext=mp4]/best',  # Prefer mp4, fallback to best quality
            'noplaylist': True,  # Don't download playlists
            'quiet': True,  # Suppress output
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download the video
                ydl.download([url])
                
                # Find the downloaded file
                downloaded_files = [f for f in os.listdir(temp_dir) if f.endswith(('.mp4', '.webm', '.mkv', '.avi', '.mov'))]
                
                if not downloaded_files:
                    raise RuntimeError("No video file was downloaded")
                
                downloaded_path = os.path.join(temp_dir, downloaded_files[0])
                self.logger.info(f"Video downloaded successfully: {downloaded_path}")
                
                return downloaded_path
                
        except Exception as e:
            self.logger.error(f"Failed to download video from URL: {e}")
            raise RuntimeError(f"Video download failed: {e}")
    
    def _verify_ffmpeg(self) -> None:
        """Verify that FFmpeg is available and working."""
        try:
            result = subprocess.run([self.ffmpeg_path, '-version'], 
                                  capture_output=True, text=True, check=True)
            self.logger.info(f"FFmpeg version: {result.stdout.split('\n')[0]}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                f"FFmpeg not found or not working. Please ensure FFmpeg is installed and accessible at: {self.ffmpeg_path}"
            )
    
    def extract_audio(self, video_path: str, output_format: str = 'wav') -> str:
        """
        Extract audio from video file or URL using FFmpeg.
        
        Args:
            video_path: Path to the video file or URL
            output_format: Audio output format (wav, mp3, m4a, etc.)
            
        Returns:
            Path to the extracted audio file
        """
        # Handle URL input
        if self._is_url(video_path):
            self.logger.info(f"Processing video from URL: {video_path}")
            downloaded_path = self._download_video_from_url(video_path)
            video_path_obj = Path(downloaded_path)
            is_temporary = True
        else:
            video_path_obj = Path(video_path)
            if not video_path_obj.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            is_temporary = False
        
        # Create temporary file for audio
        temp_dir = tempfile.gettempdir()
        audio_filename = f"{video_path_obj.stem}_audio.{output_format}"
        audio_path = Path(temp_dir) / audio_filename
        
        # FFmpeg command for audio extraction
        cmd = [
            self.ffmpeg_path,
            '-i', str(video_path_obj),
            '-vn',  # No video
            '-acodec', 'pcm_s16le' if output_format == 'wav' else 'copy',
            '-ar', '16000',  # Sample rate for speech recognition
            '-ac', '1',      # Mono audio
            '-y',            # Overwrite output file
            str(audio_path)
        ]
        
        self.logger.info(f"Extracting audio from {video_path_obj.name}...")
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info(f"Audio extracted successfully to {audio_path}")
            
            # Clean up downloaded video file if it was temporary
            if is_temporary:
                try:
                    os.remove(video_path_obj)
                    # Also clean up the temporary directory
                    temp_dir = video_path_obj.parent
                    if temp_dir.exists() and temp_dir.is_dir():
                        os.rmdir(temp_dir)
                except OSError:
                    pass  # Ignore cleanup errors
            
            return str(audio_path)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg error: {e.stderr}")
            raise RuntimeError(f"Failed to extract audio: {e.stderr}")
    
    def chunk_audio(self, audio_path: str, chunk_duration: int = 30) -> List[str]:
        """
        Split audio into chunks for better transcription handling using FFmpeg.
        
        Args:
            audio_path: Path to the audio file
            chunk_duration: Duration of each chunk in seconds
            
        Returns:
            List of paths to audio chunks
        """
        self.logger.info(f"Chunking audio into {chunk_duration}-second segments...")
        
        try:
            # Use FFprobe to get duration (more reliable)
            probe_cmd = [
                self.ffmpeg_path.replace('ffmpeg', 'ffprobe'),
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                audio_path
            ]
            
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            total_duration = float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
            # Fallback: assume 30 seconds if we can't get duration
            self.logger.warning("Could not determine audio duration, using fallback chunking")
            total_duration = 30.0
        
        # Calculate number of chunks
        num_chunks = int(total_duration / chunk_duration) + 1
        
        chunks = []
        temp_dir = tempfile.gettempdir()
        
        for i in range(num_chunks):
            start_time = i * chunk_duration
            chunk_path = Path(temp_dir) / f"chunk_{i:03d}.wav"
            
            # Use FFmpeg to extract chunk
            chunk_cmd = [
                self.ffmpeg_path,
                '-i', audio_path,
                '-ss', str(start_time),
                '-t', str(chunk_duration),
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-y',
                str(chunk_path)
            ]
            
            try:
                subprocess.run(chunk_cmd, capture_output=True, text=True, check=True)
                chunks.append(str(chunk_path))
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Failed to create chunk {i}: {e}")
                continue
        
        self.logger.info(f"Created {len(chunks)} audio chunks")
        return chunks
    
    def transcribe_chunk(self, audio_chunk_path: str, 
                        language: str = 'en-US',
                        enable_continuous_recognition: bool = True) -> Dict:
        """
        Transcribe a single audio chunk using Azure Speech-to-Text.
        
        Args:
            audio_chunk_path: Path to the audio chunk
            language: Speech recognition language
            enable_continuous_recognition: Whether to use continuous recognition
            
        Returns:
            Dictionary containing transcription results
        """
        # Configure Azure Speech SDK
        speech_config = speechsdk.SpeechConfig(
            subscription=self.azure_key, 
            region=self.azure_region
        )
        speech_config.speech_recognition_language = language
        
        # Configure audio input
        audio_config = speechsdk.AudioConfig(filename=audio_chunk_path)
        
        # Create speech recognizer
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, 
            audio_config=audio_config
        )
        
        # Perform recognition
        if enable_continuous_recognition:
            return self._continuous_recognition(speech_recognizer)
        else:
            return self._single_recognition(speech_recognizer)
    
    def _continuous_recognition(self, speech_recognizer) -> Dict:
        """Perform continuous speech recognition."""
        results = []
        
        def handle_result(evt):
            if evt.result.text:
                results.append({
                    'text': evt.result.text,
                    'offset': evt.result.offset,
                    'duration': evt.result.duration
                })
        
        speech_recognizer.recognized.connect(handle_result)
        speech_recognizer.recognize_once()
        
        return {
            'transcriptions': results,
            'status': 'success'
        }
    
    def _single_recognition(self, speech_recognizer) -> Dict:
        """Perform single speech recognition."""
        result = speech_recognizer.recognize_once()
        
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return {
                'transcriptions': [{
                    'text': result.text,
                    'offset': result.offset,
                    'duration': result.duration
                }],
                'status': 'success'
            }
        else:
            return {
                'transcriptions': [],
                'status': 'failed',
                'reason': result.reason
            }
    
    def transcribe_video_to_database(self,
                                   video_path: str,
                                   language: str = 'en-US',
                                   chunk_duration: int = 30,
                                   doc_title: Optional[str] = None,
                                   doc_authors: Optional[List[str]] = None,
                                   doc_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Transcribe a video file and store results in the database.
        
        Args:
            video_path: Path to the video file
            language: Speech recognition language
            chunk_duration: Duration of audio chunks in seconds
            doc_title: Document title (defaults to filename)
            doc_authors: List of authors
            doc_keywords: List of keywords
            
        Returns:
            Dictionary containing transcription results and database info
        """
        if not self.db_manager:
            raise RuntimeError("Database connection not available. Cannot store transcription results.")
        
        self.logger.info(f"Starting transcription and database storage for {video_path}")
        
        try:
            # Create document record
            document_id = create_document_from_video(
                video_path=video_path,
                db_manager=self.db_manager,
                doc_title=doc_title,
                doc_authors=doc_authors,
                doc_keywords=doc_keywords
            )
            
            # Extract audio from video
            audio_path = self.extract_audio(video_path)
            
            # Chunk audio for processing
            audio_chunks = self.chunk_audio(audio_path, chunk_duration)
            
            # Transcribe each chunk and prepare for database storage
            all_transcriptions = []
            current_offset = 0
            
            for i, chunk_path in enumerate(tqdm(audio_chunks, desc="Transcribing chunks")):
                chunk_result = self.transcribe_chunk(chunk_path, language)
                
                if chunk_result['status'] == 'success':
                    for trans in chunk_result['transcriptions']:
                        # Adjust timestamps for chunk position
                        adjusted_trans = trans.copy()
                        adjusted_trans['offset'] += current_offset
                        
                        # Convert offset to datetime for database storage
                        chunk_timestamp = datetime.utcfromtimestamp(adjusted_trans['offset'] / 1000)
                        
                        all_transcriptions.append({
                            'text': adjusted_trans['text'],
                            'page': i + 1,  # Use chunk index as page number
                            'timestamp': chunk_timestamp
                        })
                
                current_offset += chunk_duration * 1000  # Convert to milliseconds
                
                # Clean up chunk file
                try:
                    os.remove(chunk_path)
                except OSError:
                    pass
            
            # Clean up extracted audio
            try:
                os.remove(audio_path)
            except OSError:
                pass
            
            # Store chunks in database
            chunk_ids = self.db_manager.create_chunks_batch(document_id, all_transcriptions)
            
            # Get document stats
            doc_stats = self.db_manager.get_document_stats(document_id)
            
            result = {
                'document_id': document_id,
                'chunk_count': len(chunk_ids),
                'transcription_segments': len(all_transcriptions),
                'document_stats': doc_stats,
                'status': 'success'
            }
            
            self.logger.info(f"Transcription completed and stored in database. Document ID: {document_id}")
            return result
                
        except Exception as e:
            self.logger.error(f"Transcription and database storage failed: {str(e)}")
            raise

    def transcribe_video(self, 
                        video_path: str,
                        output_format: str = 'json',
                        language: str = 'en-US',
                        chunk_duration: int = 30,
                        enable_timestamps: bool = True) -> str:
        """
        Transcribe a video file completely.
        
        Args:
            video_path: Path to the video file
            output_format: Output format (json, srt, vtt, txt)
            language: Speech recognition language
            chunk_duration: Duration of audio chunks in seconds
            enable_timestamps: Whether to include timestamps in output
            
        Returns:
            Transcribed text in the specified format
        """
        self.logger.info(f"Starting transcription of {video_path}")
        
        try:
            # Extract audio from video
            audio_path = self.extract_audio(video_path)
            
            # Chunk audio for processing
            audio_chunks = self.chunk_audio(audio_path, chunk_duration)
            
            # Transcribe each chunk
            all_transcriptions = []
            current_offset = 0
            
            for i, chunk_path in enumerate(tqdm(audio_chunks, desc="Transcribing chunks")):
                chunk_result = self.transcribe_chunk(chunk_path, language)
                
                if chunk_result['status'] == 'success':
                    for trans in chunk_result['transcriptions']:
                        # Adjust timestamps for chunk position
                        adjusted_trans = trans.copy()
                        adjusted_trans['offset'] += current_offset
                        all_transcriptions.append(adjusted_trans)
                
                current_offset += chunk_duration * 1000  # Convert to milliseconds
                
                # Clean up chunk file
                try:
                    os.remove(chunk_path)
                except OSError:
                    pass
            
            # Clean up extracted audio
            try:
                os.remove(audio_path)
            except OSError:
                pass
            
            # Format output
            if output_format == 'json':
                return self._format_json(all_transcriptions)
            elif output_format == 'srt':
                return self._format_srt(all_transcriptions)
            elif output_format == 'vtt':
                return self._format_vtt(all_transcriptions)
            elif output_format == 'txt':
                return self._format_txt(all_transcriptions)
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
                
        except Exception as e:
            self.logger.error(f"Transcription failed: {str(e)}")
            raise
    
    def _format_json(self, transcriptions: List[Dict]) -> str:
        """Format transcriptions as JSON."""
        return json.dumps({
            'transcriptions': transcriptions,
            'total_segments': len(transcriptions),
            'format': 'json'
        }, indent=2)
    
    def _format_srt(self, transcriptions: List[Dict]) -> str:
        """Format transcriptions as SRT subtitle format."""
        srt_content = []
        for i, trans in enumerate(transcriptions, 1):
            start_time = self._ms_to_srt_time(trans['offset'])
            end_time = self._ms_to_srt_time(trans['offset'] + trans['duration'])
            
            srt_content.append(f"{i}\n{start_time} --> {end_time}\n{trans['text']}\n")
        
        return '\n'.join(srt_content)
    
    def _format_vtt(self, transcriptions: List[Dict]) -> str:
        """Format transcriptions as WebVTT format."""
        vtt_content = ["WEBVTT\n"]
        
        for trans in transcriptions:
            start_time = self._ms_to_vtt_time(trans['offset'])
            end_time = self._ms_to_vtt_time(trans['offset'] + trans['duration'])
            
            vtt_content.append(f"{start_time} --> {end_time}\n{trans['text']}\n")
        
        return '\n'.join(vtt_content)
    
    def _format_txt(self, transcriptions: List[Dict]) -> str:
        """Format transcriptions as plain text."""
        return '\n'.join([trans['text'] for trans in transcriptions])
    
    def _ms_to_srt_time(self, milliseconds: int) -> str:
        """Convert milliseconds to SRT time format (HH:MM:SS,mmm)."""
        seconds, ms = divmod(milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"
    
    def _ms_to_vtt_time(self, milliseconds: int) -> str:
        """Convert milliseconds to WebVTT time format (HH:MM:SS.mmm)."""
        seconds, ms = divmod(milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Transcribe video files or URLs using Azure Speech-to-Text')
    parser.add_argument('video_path', help='Path to the video file or URL (YouTube, Vimeo, etc.)')
    parser.add_argument('-o', '--output', help='Output file path (optional)')
    parser.add_argument('-f', '--format', choices=['json', 'srt', 'vtt', 'txt'], 
                       default='json', help='Output format')
    parser.add_argument('-l', '--language', default='en-US', help='Speech recognition language')
    parser.add_argument('-c', '--chunk-duration', type=int, default=30, 
                       help='Audio chunk duration in seconds')
    parser.add_argument('--database', action='store_true', 
                       help='Store transcription results in database')
    parser.add_argument('--title', help='Document title for database storage')
    parser.add_argument('--authors', nargs='+', help='Document authors for database storage')
    parser.add_argument('--keywords', nargs='+', help='Document keywords for database storage')
    
    args = parser.parse_args()
    
    try:
        # Initialize transcriber
        transcriber = VideoTranscriber()
        
        if args.database:
            # Perform transcription and store in database
            result = transcriber.transcribe_video_to_database(
                video_path=args.video_path,
                language=args.language,
                chunk_duration=args.chunk_duration,
                doc_title=args.title,
                doc_authors=args.authors,
                doc_keywords=args.keywords
            )
            
            print("Transcription completed and stored in database:")
            print(f"Document ID: {result['document_id']}")
            print(f"Chunks created: {result['chunk_count']}")
            print(f"Transcription segments: {result['transcription_segments']}")
            
            # Also save to file if output specified
            if args.output:
                # Get the transcription text for file output
                file_result = transcriber.transcribe_video(
                    video_path=args.video_path,
                    output_format=args.format,
                    language=args.language,
                    chunk_duration=args.chunk_duration
                )
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(file_result)
                print(f"Transcription also saved to: {args.output}")
        else:
            # Perform transcription only
            result = transcriber.transcribe_video(
                video_path=args.video_path,
                output_format=args.format,
                language=args.language,
                chunk_duration=args.chunk_duration
            )
            
            # Output result
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"Transcription saved to: {args.output}")
            else:
                print(result)
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

