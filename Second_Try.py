import asyncio
import sys
from bs4 import BeautifulSoup
from fpdf import FPDF
from urllib.parse import urljoin, urlparse

# Try to import Playwright for JS rendering
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
import requests

def prompt_user():
    url = input('Enter the URL of the webpage to scrape: ').strip()
    output = input('Enter output PDF filename (default: output.pdf): ').strip()
    if not output:
        output = 'output.pdf'
    return url, output

async def fetch_with_playwright(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(3000)
        html = await page.content()
        await browser.close()
        return html

def fetch_with_requests(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def extract_metadata(soup, url):
    title = soup.title.string.strip() if soup.title else "No Title"
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    meta_desc = meta_desc['content'].strip() if meta_desc else "No Description"
    return {'title': title, 'url': url, 'meta_desc': meta_desc}

def extract_headings_and_content(soup):
    content = []
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        heading_text = heading.get_text().strip()
        section = {'heading': heading_text, 'content': []}
        next_elem = heading.next_sibling
        while next_elem:
            if getattr(next_elem, 'name', None) and next_elem.name.startswith('h'):
                break
            if getattr(next_elem, 'name', None) == 'p':
                section['content'].append(next_elem.get_text().strip())
            elif getattr(next_elem, 'name', None) == 'ul':
                for li in next_elem.find_all('li'):
                    section['content'].append(f"- {li.get_text().strip()}")
            next_elem = next_elem.next_sibling
        content.append(section)
    return content

def extract_links(soup, base_url):
    links = []
    for link in soup.find_all('a', href=True):
        href = link['href'].strip()
        if (
            not href.startswith('javascript:') and
            not href.startswith('mailto:') and
            not href.startswith('tel:') and
            href.strip() != '#'
        ):
            link_text = link.get_text().strip() or href
            full_url = urljoin(base_url, href) if href.startswith('/') else href
            links.append({'text': link_text, 'url': full_url})
    return links

async def extract_tab_content_playwright(page):
    tab_data = []
    try:
        tabs = await page.query_selector_all('[role="tab"]')
        for i, tab in enumerate(tabs):
            tab_name = await tab.inner_text()
            await tab.click()
            await page.wait_for_timeout(1000)
            panel = await page.query_selector('[role="tabpanel"]:not([hidden])')
            if panel:
                panel_text = await panel.inner_text()
                if panel_text.strip():
                    tab_data.append({'tab_name': tab_name.strip(), 'content': panel_text.strip()})
    except Exception:
        pass
    return tab_data

def clean_text(text):
    if not text:
        return ""
    replacements = {
        '\u2192': '->', '\u2190': '<-', '\u2013': '-', '\u2014': '--',
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2022': '*', '\u2026': '...'
    }
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    try:
        text.encode('latin-1')
        return text
    except UnicodeEncodeError:
        return text.encode('latin-1', errors='ignore').decode('latin-1')

def generate_pdf(metadata, headings, links, tab_data, output_file):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    page_width = pdf.w - 2 * pdf.l_margin
    # Metadata
    pdf.set_font("Arial", 'B', 16)
    pdf.multi_cell(page_width, 10, clean_text(metadata['title']), align='C')
    pdf.ln(2)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(page_width, 8, clean_text(metadata['url']), align='C')
    pdf.ln(2)
    pdf.multi_cell(page_width, 8, clean_text(metadata['meta_desc']), align='C')
    pdf.ln(8)
    # Headings and content
    for section in headings:
        pdf.set_font("Arial", 'B', 14)
        pdf.multi_cell(page_width, 9, clean_text(section['heading']))
        pdf.ln(1)
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(page_width, 8, clean_text("\n".join(section['content'])))
        pdf.ln(4)
    # Links
    if links:
        pdf.set_font("Arial", 'B', 14)
        pdf.multi_cell(page_width, 9, "Links:")
        pdf.set_font("Arial", '', 12)
        for link in links:
            pdf.set_text_color(0, 0, 255)
            pdf.multi_cell(page_width, 8, clean_text(f"{link['text']} -> {link['url']}"))
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
    # Tab content
    if tab_data:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.multi_cell(page_width, 10, "Tabbed Content")
        pdf.ln(4)
        for tab in tab_data:
            pdf.set_font("Arial", 'B', 14)
            pdf.multi_cell(page_width, 9, clean_text(tab['tab_name']))
            pdf.ln(1)
            pdf.set_font("Arial", '', 12)
            pdf.multi_cell(page_width, 8, clean_text(tab['content']))
            pdf.ln(4)
    pdf.output(output_file)
    print(f"PDF generated successfully: {output_file}")

async def main():
    url, output = prompt_user()
    html = None
    tab_data = []
    if PLAYWRIGHT_AVAILABLE:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url)
                await page.wait_for_timeout(3000)
                html = await page.content()
                tab_data = await extract_tab_content_playwright(page)
                await browser.close()
        except Exception as e:
            print(f"Playwright failed: {e}\nFalling back to requests.")
    if not html:
        html = fetch_with_requests(url)
    if not html:
        print("Failed to fetch the page. Exiting.")
        sys.exit(1)
    soup = BeautifulSoup(html, 'html.parser')
    metadata = extract_metadata(soup, url)
    headings = extract_headings_and_content(soup)
    links = extract_links(soup, url)
    generate_pdf(metadata, headings, links, tab_data, output)

if __name__ == "__main__":
    if PLAYWRIGHT_AVAILABLE:
        asyncio.run(main())
    else:
        # fallback to sync main if Playwright is not installed
        url, output = prompt_user()
        html = fetch_with_requests(url)
        if not html:
            print("Failed to fetch the page. Exiting.")
            sys.exit(1)
        soup = BeautifulSoup(html, 'html.parser')
        metadata = extract_metadata(soup, url)
        headings = extract_headings_and_content(soup)
        links = extract_links(soup, url)
        generate_pdf(metadata, headings, links, [], output)