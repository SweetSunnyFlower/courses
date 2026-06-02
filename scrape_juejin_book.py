import json
import os
import re
import html
import time
import mimetypes
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import Request, urlopen
from html.parser import HTMLParser

BOOKLET_ID = os.environ.get('JUEJIN_BOOKLET_ID', '6963277002044342311')
OUT_DIR = Path(os.environ.get('JUEJIN_OUT_DIR', 'courses/go/im-go'))
COOKIE = os.environ.get('JUEJIN_COOKIE', '')
BOOKLET_URL = f'https://juejin.cn/book/{BOOKLET_ID}'
API_BASE = 'https://api.juejin.cn'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Content-Type': 'application/json',
    'Origin': 'https://juejin.cn',
    'Referer': BOOKLET_URL,
}
if COOKIE:
    HEADERS['Cookie'] = COOKIE


def fetch_json(path, payload):
    url = urljoin(API_BASE, path)
    last = None
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    for attempt in range(3):
        try:
            req = Request(url, data=data, headers=HEADERS, method='POST')
            with urlopen(req, timeout=35) as resp:
                body = resp.read().decode('utf-8', 'ignore')
            result = json.loads(body)
            if result.get('err_no') not in (0, None):
                raise RuntimeError(f"{result.get('err_no')} {result.get('err_msg')}")
            return result
        except Exception as e:
            last = e
            time.sleep(0.8 + attempt)
    raise last


def fetch_binary(url, referer):
    last = None
    headers = dict(HEADERS)
    headers.update({
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Referer': referer,
    })
    headers.pop('Content-Type', None)
    headers.pop('Origin', None)
    for attempt in range(3):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=35) as resp:
                return resp.read(), dict(resp.headers)
        except Exception as e:
            last = e
            time.sleep(0.8 + attempt)
    raise last


def clean_text(text):
    text = re.sub(r'<[^>]+>', '', str(text), flags=re.S)
    text = html.unescape(text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def safe_name(name):
    name = clean_text(name)
    name = re.sub(r'[\\/:*?"<>|]', '-', name)
    name = re.sub(r'\s+', ' ', name).strip().rstrip('.')
    return name or 'untitled'


def pick_first(data, key):
    if isinstance(data, dict):
        if key in data and data[key]:
            return data[key]
        for value in data.values():
            found = pick_first(value, key)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = pick_first(item, key)
            if found:
                return found
    return None


def collect_sections(data):
    candidates = []

    def walk(value):
        if isinstance(value, list):
            section_like = [item for item in value if isinstance(item, dict) and (item.get('section_id') or item.get('id')) and (item.get('title') or item.get('draft_title'))]
            if len(section_like) >= 2:
                candidates.append(section_like)
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)

    walk(data)
    if not candidates:
        raise RuntimeError('未找到小册章节列表')
    sections = max(candidates, key=len)
    result = []
    seen = set()
    for item in sections:
        section_id = str(item.get('section_id') or item.get('id') or '')
        title = clean_text(item.get('title') or item.get('draft_title') or '')
        if not section_id or not title or section_id in seen:
            continue
        seen.add(section_id)
        result.append({'section_id': section_id, 'title': title})
    return result


def get_booklet():
    result = fetch_json('/booklet_api/v1/booklet/get', {'booklet_id': BOOKLET_ID})
    data = result.get('data') or result
    title = clean_text(pick_first(data, 'booklet_title') or pick_first(data, 'title') or f'掘金小册 {BOOKLET_ID}')
    return title, collect_sections(data)


def get_section(section_id):
    result = fetch_json('/booklet_api/v1/section/get', {'section_id': section_id})
    data = result.get('data') or result
    if isinstance(data, dict) and 'section' in data:
        data = data['section']
    title = clean_text(data.get('title') or data.get('draft_title') or section_id)
    content = data.get('content') or data.get('app_html_content') or data.get('markdown_show') or ''
    if not content.strip():
        raise RuntimeError('正文为空')
    return {'title': title, 'content': content}


class MarkdownConverter(HTMLParser):
    def __init__(self, page_url, assets_dir, article_id):
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.assets_dir = assets_dir
        self.article_id = article_id
        self.parts = []
        self.link_stack = []
        self.list_stack = []
        self.skip_stack = []
        self.in_pre = False
        self.pre_lang = ''
        self.image_count = 0
        self.downloaded = []

    def attrs(self, attrs):
        return {k.lower(): v for k, v in attrs if k}

    def text(self):
        text = ''.join(self.parts)
        text = re.sub(r'\n[ \t]+', '\n', text)
        text = re.sub(r'[ \t]+\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip() + '\n'

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = self.attrs(attrs)
        if tag in {'script', 'style'}:
            self.skip_stack.append(tag)
            return
        if self.skip_stack:
            return
        if tag == 'pre':
            self.in_pre = True
            self.pre_lang = ''
            self.parts.append('\n```')
        elif tag == 'code' and self.in_pre:
            cls = attrs.get('class', '')
            match = re.search(r'language-([A-Za-z0-9_+-]+)', cls)
            if match and not self.pre_lang:
                self.pre_lang = match.group(1)
                if self.parts and self.parts[-1] == '\n```':
                    self.parts[-1] = f'\n```{self.pre_lang}'
            self.parts.append('\n')
        elif tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.parts.append('\n' + '#' * int(tag[1]) + ' ')
        elif tag == 'p':
            self.parts.append('\n')
        elif tag == 'br':
            self.parts.append('\n')
        elif tag in {'ul', 'ol'}:
            self.list_stack.append({'tag': tag, 'i': 0})
            self.parts.append('\n')
        elif tag == 'li':
            indent = '  ' * max(0, len(self.list_stack) - 1)
            if self.list_stack and self.list_stack[-1]['tag'] == 'ol':
                self.list_stack[-1]['i'] += 1
                bullet = f"{self.list_stack[-1]['i']}. "
            else:
                bullet = '- '
            self.parts.append('\n' + indent + bullet)
        elif tag == 'a' and not self.in_pre:
            self.link_stack.append((attrs.get('href', ''), self.parts))
            self.parts = []
        elif tag == 'img' and not self.in_pre:
            alt = attrs.get('alt') or ''
            src = attrs.get('data-src') or attrs.get('src') or ''
            md_src = self.download_image(src)
            if md_src:
                self.parts.append(f'![{alt}]({md_src})')
        elif tag == 'blockquote':
            self.parts.append('\n> ')
        elif tag == 'code' and not self.in_pre:
            self.parts.append('`')
        elif tag == 'tr':
            self.parts.append('\n')
        elif tag in {'td', 'th'}:
            self.parts.append(' | ')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.skip_stack:
            if tag == self.skip_stack[-1]:
                self.skip_stack.pop()
            return
        if tag == 'pre':
            self.parts.append('\n```\n\n')
            self.in_pre = False
        elif tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.parts.append('\n\n')
        elif tag == 'p':
            self.parts.append('\n\n')
        elif tag in {'ul', 'ol'}:
            if self.list_stack:
                self.list_stack.pop()
            self.parts.append('\n')
        elif tag == 'li':
            self.parts.append('\n')
        elif tag == 'a' and self.link_stack and not self.in_pre:
            href, old_parts = self.link_stack.pop()
            label = ''.join(self.parts).strip()
            self.parts = old_parts
            if label and href and not href.startswith('javascript:'):
                self.parts.append(f'[{label}]({urljoin(self.page_url, href)})')
            else:
                self.parts.append(label)
        elif tag == 'code' and not self.in_pre:
            self.parts.append('`')
        elif tag == 'blockquote':
            self.parts.append('\n\n')

    def handle_data(self, data):
        if self.skip_stack:
            return
        self.parts.append(data)

    def download_image(self, src):
        if not src or src.startswith('data:'):
            return src
        url = urljoin(self.page_url, html.unescape(src))
        self.image_count += 1
        parsed = urlparse(url)
        raw_name = Path(unquote(parsed.path)).name.split('!')[0]
        ext = Path(raw_name).suffix.lower()
        if ext not in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.avif'}:
            ext = ''
        try:
            data, headers = fetch_binary(url, self.page_url)
            if not ext:
                ctype = headers.get('Content-Type', '').split(';')[0].strip().lower()
                ext = mimetypes.guess_extension(ctype) or '.img'
                if ext == '.jpe':
                    ext = '.jpg'
            filename = f'{self.article_id}-{self.image_count:02d}{ext}'
            self.assets_dir.mkdir(parents=True, exist_ok=True)
            path = self.assets_dir / filename
            path.write_bytes(data)
            rel = f'assets/{filename}'
            self.downloaded.append(rel)
            return rel
        except Exception as e:
            print(f'    WARN image failed: {url} ({e})', flush=True)
            return url


def section_to_markdown(section, order):
    page_url = f'{BOOKLET_URL}/section/{section["section_id"]}'
    detail = get_section(section['section_id'])
    title = detail['title'] or section['title']
    converter = MarkdownConverter(page_url, OUT_DIR / 'assets', f'{order:02d}-{section["section_id"]}')
    converter.feed(detail['content'])
    body = converter.text()
    front = f'# {title}\n\n原文链接：{page_url}\n\n'
    return title, front + body, len(converter.downloaded)


def main():
    if not COOKIE:
        raise RuntimeError('请通过 JUEJIN_COOKIE 环境变量提供掘金 Cookie')
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    book_title, sections = get_booklet()
    print(f'Parsed book="{book_title}" sections={len(sections)}', flush=True)
    total_images = 0
    failures = []
    index_lines = [f'# {book_title}', '', f'小册首页：{BOOKLET_URL}', '']
    for idx, section in enumerate(sections, 1):
        try:
            title, md, images = section_to_markdown(section, idx)
            filename = f'{idx:02d}. {safe_name(title)}.md'
            (OUT_DIR / filename).write_text(md, encoding='utf-8')
            index_lines.append(f'- [{title}]({filename})')
            total_images += images
            print(f'  [{idx}/{len(sections)}] OK {title} images={images}', flush=True)
            time.sleep(0.12)
        except Exception as e:
            failures.append((section['title'], section['section_id'], str(e)))
            print(f'  [{idx}/{len(sections)}] FAIL {section["title"]}: {e}', flush=True)
    (OUT_DIR / 'index.md').write_text('\n'.join(index_lines) + '\n', encoding='utf-8')
    failures_path = OUT_DIR / 'failures.txt'
    if failures:
        failures_path.write_text('\n'.join(f'- {t} {sid} {err}' for t, sid, err in failures), encoding='utf-8')
        print(f'DONE sections={len(sections)} images={total_images} failures={len(failures)} out={OUT_DIR}', flush=True)
        raise SystemExit(1)
    if failures_path.exists():
        failures_path.unlink()
    print(f'DONE sections={len(sections)} images={total_images} failures=0 out={OUT_DIR}', flush=True)


if __name__ == '__main__':
    main()
