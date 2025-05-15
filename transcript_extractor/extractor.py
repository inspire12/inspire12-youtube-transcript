import datetime
import os
import re
import sys
from urllib.parse import urlparse, parse_qs

from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
from googletrans import Translator

def extract_video_id(input_str):
    """
    입력값이 전체 URL인 경우 정규표현식을 사용해 영상 ID(11자리)를 추출합니다.
    만약 추출에 실패하면 원본 문자열을 반환합니다.
    """
    # 정규표현식 패턴: v= 또는 youtu.be/ 뒤에 오는 11자리 ID
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:\?|&|\/|$)"
    match = re.search(pattern, input_str)
    if match:
        return match.group(1)
    return input_str

def format_timestamp(seconds):
    """
    초 단위의 시간을 HH:MM:SS 형식으로 변환합니다.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def get_transcript(video_id, translate=False):
    """
    주어진 유튜브 영상 ID의 트랜스크립트를 추출합니다.
    각 구간에 대해 timestamp를 클릭 가능한 링크와 함께 포맷합니다.
    translate=True이면 한글 번역도 포함합니다.
    """

    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'ko'])
    lines = []
    translator = Translator() if translate else None
    base_url = f"https://www.youtube.com/watch?v={video_id}"
    for entry in transcript_list:
        start_sec = int(entry["start"])
        timestamp = format_timestamp(entry["start"])
        # Markdown 링크: [HH:MM:SS](영상URL&t=초단위시간s)
        timestamp_link = f"[{timestamp}]({base_url}&t={start_sec}s)"
        text = entry["text"]
        lines.append(f"{timestamp_link} {text}")
        if translate:
            try:
                translated = translator.translate(text, dest='ko').text
                lines.append(f"{timestamp_link} (한글 번역) {translated}")
            except Exception:
                lines.append(f"{timestamp_link} (한글 번역) 오류 발생")
    return "\n".join(lines)


def get_video_metadata(video_id):
    """
    pytube를 이용해 영상의 제목, 채널명, URL을 가져옵니다.
    실패할 경우 환경변수(YOUTUBE_API_KEY)에 API 키가 있다면 pyyoutube로 재시도합니다.
    모두 실패하면 None을 반환합니다.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    # 우선 pytube 사용
    try:
        yt = YouTube(url)
        metadata = {
            "title": yt.title,
            "channel": yt.author,
            "url": url
        }
        if metadata["title"]:  # 기본적으로 제목이 존재하면 성공한 것으로 간주
            return metadata
    except Exception:
        pass

    # pytube 실패 시 pyyoutube 재시도 (API 키 필요)
    api_key = os.getenv("YOUTUBE_API_KEY")
    if api_key:
        try:
            import pyyoutube  # API 키가 있을 때만 임포트
            api = pyyoutube.Api(api_key=api_key)
            response = api.get_video_by_id(video_id=video_id)
            if response.items:
                item = response.items[0]
                metadata = {
                    "title": item.snippet.title,
                    "channel": item.snippet.channelTitle,
                    "url": url
                }
                return metadata
        except Exception:
            pass
    return None

def sanitize_filename(filename):
    """
    파일 이름에 사용할 수 없는 문자를 제거합니다.
    """
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def save_to_markdown(metadata, transcript):
    """
    영상 메타데이터와 트랜스크립트를 Markdown 파일로 저장합니다.
    파일 이름은 현재 시간과 영상 제목을 포함한 형식입니다.
    """
    now = datetime.datetime.now()
    time_str = now.strftime("%Y%m%d_%H%M%S")
    title_sanitized = sanitize_filename(metadata['title'])
    file_name = f"{time_str}_{title_sanitized}.md"
    with open(f"output/{file_name}", "w", encoding="utf-8") as f:
        f.write(f"# {metadata['title']}\n\n")
        f.write(f"**채널명:** {metadata['channel']}\n\n")
        f.write(f"**URL:** {metadata['url']}\n\n")
        f.write("---\n\n")
        f.write("## 트랜스크립트\n\n")
        f.write(transcript)
    return file_name

def main():
    # 커맨드라인 인자로 영상 ID 또는 URL을 받지 않으면 사용자 입력
    if len(sys.argv) < 2:
        raw_input_value = input("유튜브 영상 ID 또는 URL을 입력하세요: ").strip()
    else:
        raw_input_value = sys.argv[1]

    if not raw_input_value:
        return

    video_id = extract_video_id(raw_input_value)
    # '--translate' 또는 '-t' 옵션이 있으면 한글 번역 활성화 (저장은 기본 동작)
    translate = any(arg in ('--translate', '-t') for arg in sys.argv[2:])

    metadata = get_video_metadata(video_id)
    transcript = get_transcript(video_id, translate=translate)
    print(metadata)
    if transcript:
        # 메타데이터가 None인 경우 기본값 사용
        if metadata is None:
            metadata = {
                "title": video_id,
                "channel": "Unknown",
                "url": f"https://www.youtube.com/watch?v={video_id}"
            }
        save_to_markdown(metadata, transcript)

if __name__ == "__main__":
    main()
