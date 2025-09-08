# Video Tools - Azure Speech-to-Text Transcription

A powerful video transcription tool that uses Azure Speech-to-Text and FFmpeg to extract audio and generate accurate transcriptions with timestamps.

## Features

- **Video to Audio Extraction**: Uses FFmpeg to extract high-quality audio from various video formats
- **URL Support**: Download and transcribe videos directly from YouTube, Vimeo, and other video platforms
- **Azure Speech-to-Text Integration**: Leverages Microsoft's advanced speech recognition technology
- **Multiple Output Formats**: Supports JSON, SRT, VTT, and plain text output
- **Audio Chunking**: Processes long videos by splitting audio into manageable chunks
- **Timestamp Support**: Maintains accurate timing information for subtitles and transcripts
- **Multi-language Support**: Supports various speech recognition languages
- **Command-line Interface**: Easy-to-use CLI for batch processing
- **PostgreSQL Database Storage**: Store transcription results in a structured database for easy retrieval and analysis
- **Document Management**: Track video metadata, authors, keywords, and transcription statistics
- **Simple Database Operations**: Uses aiosql for clean, maintainable SQL queries without complex ORM overhead

## Prerequisites

### 1. FFmpeg Installation

FFmpeg is required for audio extraction from video files.

**Windows:**
- Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
- Extract to a folder and add the `bin` directory to your system PATH
- Or use Chocolatey: `choco install ffmpeg`

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

### 2. Azure Speech Service

You'll need an Azure Speech Service subscription:

1. Go to [Azure Portal](https://portal.azure.com)
2. Create a new Speech Service resource
3. Note your **Key** and **Region** (e.g., `eastus`, `westeurope`)

## Installation

1. **Clone or download this repository**
2. **Install dependencies:**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -e .
   ```

3. **Set up environment variables:**
   Create a `.env` file in your project root:
   ```env
   AZURE_SPEECH_KEY=your_azure_speech_key_here
   AZURE_SPEECH_REGION=your_azure_region_here
   DATABASE_URL=postgresql://username:password@host:port/database
   ```

### 3. PostgreSQL Database (Optional)

For database storage functionality, you'll need a PostgreSQL database:

1. **Set up PostgreSQL database** with the following tables:
   ```sql
   CREATE TABLE document (
       id character varying(36) NOT NULL,
       name character varying(256) NOT NULL,
       "URL_internal" character varying(4096),
       "URL_external" character varying(4096),
       upload_time timestamp with time zone,
       file_size integer,
       sha_hash text,
       is_archived boolean NOT NULL DEFAULT false,
       is_deleted boolean NOT NULL DEFAULT false,
       doc_title text,
       doc_authors text[],
       doc_keywords text[],
       doc_year integer
   );

   CREATE TABLE chunk (
       id character varying(36) NOT NULL,
       document_id character varying(36) NOT NULL,
       chunk_text text NOT NULL,
       chunk_page integer,
       chunk_timestamp timestamp
   );
   ```

2. **Add DATABASE_URL** to your `.env` file with your PostgreSQL connection string

## Usage

### Command Line Interface

The tool provides a comprehensive CLI for easy video transcription:

```bash
# Basic transcription (outputs to console in JSON format)
python -m video_tools.transcribevideo path/to/video.mp4

# Transcribe from YouTube URL
python -m video_tools.transcribevideo "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Transcribe from Vimeo URL
python -m video_tools.transcribevideo "https://vimeo.com/123456789"

# Save transcription to file
python -m video_tools.transcribevideo path/to/video.mp4 -o transcript.json

# Generate SRT subtitle file
python -m video_tools.transcribevideo path/to/video.mp4 -f srt -o subtitles.srt

# Generate VTT file for web
python -m video_tools.transcribevideo path/to/video.mp4 -f vtt -o subtitles.vtt

# Plain text output
python -m video_tools.transcribevideo path/to/video.mp4 -f txt -o transcript.txt

# Custom language and chunk duration
python -m video_tools.transcribevideo path/to/video.mp4 -l es-ES -c 45

# Store transcription in database
python -m video_tools.transcribevideo path/to/video.mp4 --database --title "My Video" --authors "John Doe" --keywords "training" "video"

# Store in database AND save to file
python -m video_tools.transcribevideo path/to/video.mp4 --database -o transcript.json
```

### Command Line Options

- `video_path`: Path to the video file or URL (YouTube, Vimeo, etc.) (required)
- `-o, --output`: Output file path (optional)
- `-f, --format`: Output format: `json`, `srt`, `vtt`, `txt` (default: `json`)
- `-l, --language`: Speech recognition language (default: `en-US`)
- `-c, --chunk-duration`: Audio chunk duration in seconds (default: `30`)
- `--database`: Store transcription results in PostgreSQL database
- `--title`: Document title for database storage
- `--authors`: Document authors (space-separated list)
- `--keywords`: Document keywords (space-separated list)

### Programmatic Usage

```python
from video_tools.transcribevideo import VideoTranscriber

# Initialize transcriber
transcriber = VideoTranscriber(
    azure_key="your_key",  # Optional if using env vars
    azure_region="eastus"   # Optional if using env vars
)

# Transcribe local video file
result = transcriber.transcribe_video(
    video_path="path/to/video.mp4",
    output_format="srt",
    language="en-US",
    chunk_duration=30
)

print(result)

# Transcribe from URL
result = transcriber.transcribe_video(
    video_path="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    output_format="json",
    language="en-US",
    chunk_duration=30
)

print(result)

# Transcribe and store in database (works with both files and URLs)
result = transcriber.transcribe_video_to_database(
    video_path="https://vimeo.com/123456789",
    language="en-US",
    chunk_duration=30,
    doc_title="My Video Title",
    doc_authors=["John Doe", "Jane Smith"],
    doc_keywords=["training", "video", "tutorial"]
)

print(f"Document ID: {result['document_id']}")
print(f"Chunks created: {result['chunk_count']}")
```

## Supported Formats

### Input Video Formats
- **Local Files**: MP4, AVI, MOV, MKV, WMV, FLV, and more (anything FFmpeg supports)
- **URLs**: YouTube, Vimeo, Twitch, and other platforms supported by yt-dlp

### Output Formats

**JSON** (default):
```json
{
  "transcriptions": [
    {
      "text": "Hello, this is a test transcription.",
      "offset": 0,
      "duration": 3000
    }
  ],
  "total_segments": 1,
  "format": "json"
}
```

**SRT (SubRip)**:
```
1
00:00:00,000 --> 00:00:03,000
Hello, this is a test transcription.
```

**VTT (WebVTT)**:
```
WEBVTT

00:00:00.000 --> 00:00:03.000
Hello, this is a test transcription.
```

**TXT (Plain Text)**:
```
Hello, this is a test transcription.
```

## Language Support

The tool supports all languages available in Azure Speech Service, including:

- **English**: `en-US`, `en-GB`, `en-AU`, `en-CA`, `en-IN`
- **Spanish**: `es-ES`, `es-MX`, `es-AR`
- **French**: `fr-FR`, `fr-CA`
- **German**: `de-DE`, `de-AT`, `de-CH`
- **Chinese**: `zh-CN`, `zh-TW`, `zh-HK`
- **Japanese**: `ja-JP`
- **Korean**: `ko-KR`
- **And many more...**

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_SPEECH_KEY` | Your Azure Speech Service key | Yes |
| `AZURE_SPEECH_REGION` | Your Azure Speech Service region | Yes |
| `DATABASE_URL` | PostgreSQL connection string for database storage | No (optional) |

### Custom FFmpeg Path

If FFmpeg is not in your system PATH, you can specify the path:

```python
transcriber = VideoTranscriber(ffmpeg_path="C:/path/to/ffmpeg.exe")
```

## Performance Tips

1. **Chunk Duration**: For long videos, use larger chunk durations (45-60 seconds) to reduce API calls
2. **Audio Quality**: The tool automatically optimizes audio for speech recognition (16kHz, mono)
3. **Temporary Files**: Audio chunks are automatically cleaned up after processing
4. **Batch Processing**: Process multiple videos in a loop for efficiency

## Error Handling

The tool includes comprehensive error handling for:

- Missing FFmpeg installation
- Invalid Azure credentials
- Corrupted video files
- Network connectivity issues
- Audio processing errors

## Troubleshooting

### Common Issues

**"FFmpeg not found" error:**
- Ensure FFmpeg is installed and in your system PATH
- Or specify the full path to FFmpeg executable

**"Azure Speech Service key is required" error:**
- Check your `.env` file has the correct variables
- Verify your Azure Speech Service is active

**Audio extraction fails:**
- Ensure the video file is not corrupted
- Check if the video has an audio track
- Verify FFmpeg supports the video format

**Transcription quality issues:**
- Try different chunk durations
- Ensure audio is clear and not too noisy
- Check if the language setting matches the spoken language

**URL download issues:**
- Ensure you have a stable internet connection
- Some videos may be geo-restricted or require authentication
- Very large videos may take time to download
- Check if the URL is accessible and the video is not private

## Database Storage

The tool can store transcription results in a PostgreSQL database for easy retrieval and analysis:

### Database Schema

**Document Table**: Stores video metadata
- `id`: Unique document identifier
- `name`: Original filename
- `doc_title`: Human-readable title
- `doc_authors`: Array of author names
- `doc_keywords`: Array of keywords/tags
- `upload_time`: When the video was processed
- `file_size`: Size of the original video file
- `sha_hash`: SHA-256 hash of the file

**Chunk Table**: Stores transcription segments
- `id`: Unique chunk identifier
- `document_id`: Links to parent document
- `chunk_text`: Transcribed text content
- `chunk_page`: Sequential page/chunk number
- `chunk_timestamp`: When this segment occurs in the video

### Database Usage Examples

```python
from video_tools.database import DatabaseManager

# Initialize database manager (uses aiosql for clean SQL queries)
db = DatabaseManager()

# Get document statistics
stats = db.get_document_stats("document-id-here")
print(f"Document: {stats['name']}")
print(f"Chunks: {stats['chunk_count']}")

# Retrieve all chunks for a document
chunks = db.get_chunks_by_document("document-id-here")
for chunk in chunks:
    print(f"Chunk {chunk['chunk_page']}: {chunk['chunk_text'][:100]}...")

# Create a new document
doc_id = db.create_document(
    name="My Video",
    doc_title="Training Video",
    doc_authors=["John Doe"],
    doc_keywords=["training", "video"]
)

# Create chunks for the document
chunk_ids = db.create_chunks_batch(doc_id, [
    {"text": "First chunk of transcription", "page": 1},
    {"text": "Second chunk of transcription", "page": 2}
])
```

## Examples

### Example 1: Basic Transcription
```bash
python -m video_tools.transcribevideo meeting_recording.mp4
```

### Example 2: Generate Subtitles
```bash
python -m video_tools.transcribevideo presentation.mp4 -f srt -o presentation.srt
```

### Example 3: Spanish Language
```bash
python -m video_tools.transcribevideo spanish_video.mp4 -l es-ES -f vtt -o spanish.vtt
```

### Example 4: Long Video with Custom Chunks
```bash
python -m video_tools.transcribevideo long_video.mp4 -c 60 -f json -o long_video_transcript.json
```

### Example 5: Database Storage
```bash
python -m video_tools.transcribevideo training_video.mp4 --database --title "Employee Training" --authors "HR Department" --keywords "training" "onboarding" "video"
```

### Example 6: Database + File Output
```bash
python -m video_tools.transcribevideo meeting.mp4 --database -o meeting_transcript.json --title "Weekly Meeting" --authors "Team Lead"
```

### Example 7: YouTube URL Transcription
```bash
python -m video_tools.transcribevideo "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -f srt -o youtube_transcript.srt
```

### Example 8: Vimeo URL with Database Storage
```bash
python -m video_tools.transcribevideo "https://vimeo.com/123456789" --database --title "Training Video" --keywords "education" "online"
```

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this tool!

## License

This project is open source and available under the MIT License.

## Support

For issues related to:
- **Azure Speech Service**: Check [Azure documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/)
- **FFmpeg**: Visit [FFmpeg documentation](https://ffmpeg.org/documentation.html)
- **This tool**: Open an issue in this repository

