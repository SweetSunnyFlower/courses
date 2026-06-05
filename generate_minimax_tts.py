import argparse
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen

API_URL = 'https://api.minimax.chat/v1/t2a_v2'
VOICE_ID = 'Chinese (Mandarin)_Reliable_Executive'
MAX_CHUNK_LENGTH = 4500
RATE_LIMIT_RETRIES = 6
RATE_LIMIT_WAIT_SECONDS = 60
REQUEST_DELAY_SECONDS = 3


def extract_text(markdown: str) -> str:
    markdown = re.sub(r'```.*?```', '', markdown, flags=re.S)
    markdown = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', markdown)
    markdown = re.sub(r'\[[^\]]+\]\([^)]*\)', lambda m: m.group(0).split('](', 1)[0][1:], markdown)
    markdown = re.sub(r'^#{1,6}\s*', '', markdown, flags=re.M)
    markdown = re.sub(r'<[^>]+>', '', markdown)
    markdown = re.sub(r'[*_`>\-|]+', ' ', markdown)
    markdown = re.sub(r'\s+', ' ', markdown)
    return markdown.strip()


def split_text(text: str, max_length: int = MAX_CHUNK_LENGTH) -> list[str]:
    if len(text) <= max_length:
        return [text]

    sentences = re.split(r'(?<=[。！？；.!?;])\s*', text)
    chunks: list[str] = []
    current = ''
    for sentence in sentences:
        if not sentence:
            continue
        if len(sentence) > max_length:
            if current:
                chunks.append(current)
                current = ''
            chunks.extend(sentence[i:i + max_length] for i in range(0, len(sentence), max_length))
            continue
        if len(current) + len(sentence) > max_length:
            if current:
                chunks.append(current)
            current = sentence
        else:
            current += sentence
    if current:
        chunks.append(current)
    return chunks


def request_audio_url(api_key: str, text: str) -> str:
    payload = {
        'model': 'speech-2.6-hd',
        'text': text,
        'stream': False,
        'language_boost': 'auto',
        'output_format': 'url',
        'voice_setting': {
            'voice_id': VOICE_ID,
            'speed': 1,
            'vol': 1,
            'pitch': 0,
        },
        'pronunciation_dict': {
            'tone': [],
        },
        'audio_setting': {
            'sample_rate': 32000,
            'bitrate': 128000,
            'format': 'mp3',
            'channel': 1,
        },
        'voice_modify': {
            'pitch': 0,
            'intensity': 0,
            'timbre': 0,
        },
    }

    for attempt in range(RATE_LIMIT_RETRIES + 1):
        req = Request(
            API_URL,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urlopen(req, timeout=180) as response:
            data = json.loads(response.read().decode('utf-8'))

        base_resp = data.get('base_resp', {})
        status_code = base_resp.get('status_code')
        if status_code in (0, None):
            audio_url = data.get('data', {}).get('audio') or data.get('data', {}).get('audio_url') or data.get('audio_file')
            if not audio_url:
                raise RuntimeError(json.dumps(data, ensure_ascii=False, indent=2))
            return audio_url

        if status_code == 1039 and attempt < RATE_LIMIT_RETRIES:
            print(f'  rate limited, wait {RATE_LIMIT_WAIT_SECONDS}s and retry {attempt + 1}/{RATE_LIMIT_RETRIES}')
            time.sleep(RATE_LIMIT_WAIT_SECONDS)
            continue

        raise RuntimeError(json.dumps(data, ensure_ascii=False, indent=2))

    raise RuntimeError('unreachable')


def download(url: str, output: Path) -> None:
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req, timeout=180) as response:
        output.write_bytes(response.read())


def merge_mp3(parts: list[Path], output: Path) -> None:
    if len(parts) == 1:
        output.write_bytes(parts[0].read_bytes())
        return

    list_file = output.with_suffix('.ffconcat.txt')
    list_file.write_text(''.join(f"file '{part.resolve()}'\n" for part in parts), encoding='utf-8')
    try:
        subprocess.run(
            ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(list_file), '-c', 'copy', str(output)],
            check=True,
        )
    finally:
        list_file.unlink(missing_ok=True)


def generate_file(api_key: str, input_path: Path, output_path: Path, force: bool = False) -> None:
    if output_path.exists() and not force:
        print(f'skip {output_path.name}')
        return

    text = extract_text(input_path.read_text(encoding='utf-8'))
    if not text:
        print(f'skip empty {input_path}')
        return

    chunks = split_text(text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        parts: list[Path] = []
        for index, chunk in enumerate(chunks, 1):
            part = tmp_dir / f'{index:03d}.mp3'
            audio_url = request_audio_url(api_key, chunk)
            download(audio_url, part)
            parts.append(part)
            print(f'  chunk {index}/{len(chunks)} chars={len(chunk)} bytes={part.stat().st_size}')
            time.sleep(REQUEST_DELAY_SECONDS)
        merge_mp3(parts, output_path)
    print(f'generated {output_path} bytes={output_path.stat().st_size} chunks={len(chunks)} chars={len(text)}')


def iter_markdown_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.glob('*.md') if p.name != 'index.md')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='Markdown file or course directory')
    parser.add_argument('output', nargs='?', help='Output mp3 for single-file mode')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    api_key = os.environ.get('MINIMAX_API_KEY')
    if not api_key:
        raise SystemExit('MINIMAX_API_KEY is required')

    input_path = Path(args.input)
    files = iter_markdown_files(input_path)
    if input_path.is_file():
        if not args.output:
            raise SystemExit('Output mp3 is required for single-file mode')
        generate_file(api_key, input_path, Path(args.output), force=args.force)
        return

    output_dir = input_path / 'mp3'
    for index, file in enumerate(files, 1):
        print(f'[{index}/{len(files)}] {file.name}')
        generate_file(api_key, file, output_dir / f'{file.stem}.mp3', force=args.force)


if __name__ == '__main__':
    main()
