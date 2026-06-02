import os
import re
import html
import time
import mimetypes
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse, unquote
from html.parser import HTMLParser

BASE_URL = os.environ.get('LEARNKU_COURSE_URL', 'https://learnku.com/courses/go-basic/1.22').rstrip('/')
path_parts = [p for p in urlparse(BASE_URL).path.split('/') if p]
if len(path_parts) >= 3 and path_parts[0] == 'courses':
    default_out_dir = f'{path_parts[1]}-{path_parts[2]}'
else:
    default_out_dir = safe_part = re.sub(r'[^A-Za-z0-9._-]+', '-', urlparse(BASE_URL).path.strip('/')) or 'learnku-course'
OUT_DIR = Path(os.environ.get('LEARNKU_OUT_DIR', default_out_dir))
COOKIE = os.environ.get('LEARNKU_COOKIE', '')
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
}
if COOKIE:
    HEADERS['Cookie'] = COOKIE


def fetch(url, binary=False, referer=None):
    last = None
    headers = dict(HEADERS)
    if referer:
        headers['Referer'] = referer
        if binary:
            headers['Accept'] = 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
    for attempt in range(3):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=35) as resp:
                data = resp.read()
                if binary:
                    return data, dict(resp.headers)
                return data.decode('utf-8', 'ignore')
        except Exception as e:
            last = e
            time.sleep(0.8 + attempt)
    raise last


def clean_text(s):
    s = re.sub(r'<[^>]+>', '', s, flags=re.S)
    s = html.unescape(s)
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s*(上次阅读|免费)\s*$', '', s).strip()
    return s


def safe_name(name):
    name = clean_text(name)
    name = re.sub(r'[\\/:*?"<>|]', '-', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.rstrip('.')
    return name or 'untitled'


def parse_course(html_text):
    chapters = []
    course_prefix = re.escape(BASE_URL)
    chapter_re = re.compile(
        r'<li class="item"\s+data-itemId="(?P<id>\d+)"\s+data-fileType=\'chapter\'\s+data-chapterId="\d+">\s*'
        r'<i[^>]*></i>\s*(?P<title>.*?)\s*<ol[^>]*class="chapter-container"[^>]*>(?P<body>.*?)</ol>\s*</li>',
        re.S,
    )
    article_re = re.compile(
        r'<li class="item"\s+data-itemId="(?P<id>\d+)"\s+data-fileType=\'file\'\s+data-chapterId="(?P<chapter_id>\d+)">.*?'
        r'<a\s+href="(?P<href>' + course_prefix + r'/[^"#?]+/\d+)"[^>]*>(?P<title>.*?)</a>',
        re.S,
    )
    seen = set()
    for cm in chapter_re.finditer(html_text):
        chapter = {'id': cm.group('id'), 'title': clean_text(cm.group('title')), 'articles': []}
        for am in article_re.finditer(cm.group('body')):
            href = html.unescape(am.group('href'))
            if href in seen:
                continue
            seen.add(href)
            chapter['articles'].append({'id': am.group('id'), 'title': clean_text(am.group('title')), 'url': href})
        chapters.append(chapter)
    return chapters


def page_title(page):
    match = re.search(r'<title[^>]*>(.*?)</title>', page, re.S | re.I)
    if not match:
        return OUT_DIR.name
    title = clean_text(match.group(1))
    title = re.sub(r'\s*\|\s*Go 技术论坛\s*$', '', title).strip()
    return title or OUT_DIR.name


def extract_article_body(page):
    marker = '<div class="ui readme markdown-body content-body fluidbox-content">'
    start = page.find(marker)
    if start < 0:
        return ''
    start += len(marker)
    end = page.find('<div style="position: absolute!important', start)
    if end < 0:
        end = page.find('<div class="ui message basic share-wrap"', start)
    if end < 0:
        end = page.find('</main>', start)
    if end < 0:
        end = len(page)
    body = page[start:end]
    body = re.sub(r'<div class="toc-wraper.*?</div>\s*</div>', '', body, flags=re.S)
    body = re.sub(r'<script\b.*?</script>|<style\b.*?</style>', '', body, flags=re.S | re.I)
    return body


class MarkdownConverter(HTMLParser):
    def __init__(self, page_url, assets_dir, article_id):
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.assets_dir = assets_dir
        self.article_id = article_id
        self.parts = []
        self.link_stack = []
        self.list_stack = []
        self.in_pre = False
        self.skip_stack = []
        self.image_count = 0
        self.downloaded = []

    def text(self):
        text = ''.join(self.parts)
        text = re.sub(r'\n[ \t]+', '\n', text)
        text = re.sub(r'[ \t]+\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip() + '\n'

    def attrs(self, attrs):
        return {k.lower(): v for k, v in attrs if k}

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = self.attrs(attrs)
        if tag in {'script', 'style'}:
            self.skip_stack.append(tag)
            return
        if self.skip_stack:
            return
        if tag == 'pre':
            self.parts.append('\n```\n')
            self.in_pre = True
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
            data, headers = fetch(url, binary=True, referer=self.page_url)
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


def article_to_markdown(article, chapter_dir):
    page = fetch(article['url'])
    body = extract_article_body(page)
    if not body.strip():
        raise RuntimeError('正文为空或未找到正文容器')
    converter = MarkdownConverter(article['url'], chapter_dir / 'assets', article['id'])
    converter.feed(body)
    content = converter.text()
    front = f"# {article['title']}\n\n原文链接：{article['url']}\n\n"
    return front + content, len(converter.downloaded)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    home = fetch(BASE_URL)
    chapters = parse_course(home)
    total_articles = sum(len(c['articles']) for c in chapters)
    if not chapters or total_articles == 0:
        raise RuntimeError(f'目录解析异常：chapters={len(chapters)} articles={total_articles}')
    print(f'Parsed chapters={len(chapters)} articles={total_articles}', flush=True)
    total_images = 0
    failures = []
    for ci, chapter in enumerate(chapters, 1):
        chapter_dir = OUT_DIR / safe_name(chapter['title'])
        chapter_dir.mkdir(parents=True, exist_ok=True)
        print(f'[{ci}/{len(chapters)}] {chapter["title"]} ({len(chapter["articles"])} articles)', flush=True)
        for ai, article in enumerate(chapter['articles'], 1):
            filename = safe_name(article['title']) + '.md'
            path = chapter_dir / filename
            try:
                md, images = article_to_markdown(article, chapter_dir)
                path.write_text(md, encoding='utf-8')
                total_images += images
                print(f'  [{ai}/{len(chapter["articles"])}] OK {article["title"]} images={images}', flush=True)
                time.sleep(0.08)
            except Exception as e:
                failures.append((article['title'], article['url'], str(e)))
                print(f'  [{ai}/{len(chapter["articles"])}] FAIL {article["title"]}: {e}', flush=True)
    index_lines = [f'# {page_title(home)}', '', f'课程首页：{BASE_URL}', '']
    for chapter in chapters:
        index_lines.append(f'## {chapter["title"]}')
        chapter_dir_name = safe_name(chapter['title'])
        for article in chapter['articles']:
            index_lines.append(f'- [{article["title"]}]({chapter_dir_name}/{safe_name(article["title"])}.md)')
        index_lines.append('')
    (OUT_DIR / 'README.md').write_text('\n'.join(index_lines), encoding='utf-8')
    print(f'DONE chapters={len(chapters)} articles={total_articles} images={total_images} failures={len(failures)} out={OUT_DIR}', flush=True)
    failures_path = OUT_DIR / 'failures.txt'
    if failures:
        fail_text = '\n'.join(f'- {t} {u} {err}' for t, u, err in failures)
        failures_path.write_text(fail_text, encoding='utf-8')
        raise SystemExit(1)
    if failures_path.exists():
        failures_path.unlink()


if __name__ == '__main__':
    main()
