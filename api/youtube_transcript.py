import sys
import json
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^[a-zA-Z0-9_-]{11}$'  # Direct video ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1) if len(match.groups()) > 0 else match.group(0)
    
    return None

def get_transcript(youtube_url):
    """Get YouTube transcript and return structured result"""
    try:
        video_id = extract_video_id(youtube_url)
        if not video_id:
            return {
                "success": False,
                "error": "Invalid YouTube URL or video ID",
                "videoId": None
            }

        print(f"🔍 Extracting transcript for video ID: {video_id}")

        # Get available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to get manually created transcript first (more accurate)
        transcript = None
        transcript_language = None
        
        try:
            # Look for manually created transcripts in preferred order
            for lang_code in ['en', 'en-US', 'en-GB']:
                try:
                    manual_transcripts = transcript_list.find_manually_created_transcript([lang_code])
                    transcript = manual_transcripts.fetch()
                    transcript_language = lang_code
                    print(f"✅ Found manual transcript in {lang_code}")
                    break
                except:
                    continue
                    
            # If no manual transcript, try auto-generated
            if not transcript:
                try:
                    auto_transcript = transcript_list.find_generated_transcript(['en'])
                    transcript = auto_transcript.fetch()
                    transcript_language = 'en (auto-generated)'
                    print("✅ Using auto-generated English transcript")
                except:
                    # Last resort: get any available transcript
                    available_transcripts = list(transcript_list)
                    if available_transcripts:
                        transcript = available_transcripts[0].fetch()
                        transcript_language = available_transcripts[0].language_code
                        print(f"✅ Using available transcript in {transcript_language}")
                    else:
                        raise Exception("No transcripts available")
                        
        except Exception as transcript_error:
            return {
                "success": False,
                "error": f"Could not fetch transcript: {str(transcript_error)}",
                "videoId": video_id
            }

        # Format transcript
        formatter = TextFormatter()
        formatted_text = formatter.format_transcript(transcript)
        
        # Get video title (basic extraction from first transcript entry or use video ID)
        video_title = f"YouTube Video {video_id}"
        
        print(f"📄 Transcript extracted: {len(formatted_text)} characters")
        
        return {
            "success": True,
            "transcript": formatted_text,
            "videoTitle": video_title,
            "videoId": video_id,
            "language": transcript_language,
            "wordCount": len(formatted_text.split())
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "videoId": video_id if 'video_id' in locals() else None
        }

def handler(event, context):
    """Vercel serverless function handler"""
    
    # CORS headers
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    
    # Handle OPTIONS request (CORS preflight)
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({"message": "CORS preflight"})
        }
    
    # Only allow POST requests
    if event.get("httpMethod") != "POST":
        return {
            "statusCode": 405,
            "headers": {**cors_headers, "Content-Type": "application/json"},
            "body": json.dumps({"error": "Method not allowed"})
        }
    
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        youtube_url = body.get("youtubeUrl")
        
        if not youtube_url:
            return {
                "statusCode": 400,
                "headers": {**cors_headers, "Content-Type": "application/json"},
                "body": json.dumps({"error": "youtubeUrl is required"})
            }
        
        # Get transcript
        result = get_transcript(youtube_url)
        
        # Return appropriate status code
        status_code = 200 if result.get("success") else 400
        
        return {
            "statusCode": status_code,
            "headers": {**cors_headers, "Content-Type": "application/json"},
            "body": json.dumps(result)
        }
        
    except Exception as e:
        print(f"❌ Handler error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {**cors_headers, "Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error"})
        } 