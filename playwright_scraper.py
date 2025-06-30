import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from fpdf import FPDF
from urllib.parse import urljoin, urlparse

class PlaywrightPDFScraper:
    def __init__(self, url):
        self.url = url
        self.domain = urlparse(url).netloc
        self.content_data = []
        self.tab_data = []
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.add_page()
        self.pdf.set_font("Arial", size=12)

    async def fetch_page(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(self.url)
            await page.wait_for_timeout(3000)  # Wait for JS rendering
            html = await page.content()
            self.soup = BeautifulSoup(html, 'html.parser')
            await self.extract_tab_content(page)
            await browser.close()

    def extract_content(self):
        # Extract metadata
        title = self.soup.title.string.strip() if self.soup.title else "No Title"
        meta_desc = self.soup.find('meta', attrs={'name': 'description'})
        meta_desc = meta_desc['content'].strip() if meta_desc else "No Description"
        self.content_data.append({
            'type': 'metadata',
            'title': title,
            'url': self.url,
            'meta_desc': meta_desc
        })
        # Extract headings and content
        for heading in self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            heading_text = heading.get_text().strip()
            content = self.extract_associated_content(heading)
            self.content_data.append({
                'type': 'heading_content',
                'heading': heading_text,
                'content': content
            })
        # Extract links
        for link in self.soup.find_all('a', href=True):
            if self.is_valid_link(link['href']):
                link_text = link.get_text().strip() or link['href']
                self.content_data.append({
                    'type': 'link',
                    'text': link_text,
                    'url': self.normalize_url(link['href'])
                })

    def extract_associated_content(self, heading):
        content = []
        next_elem = heading.next_sibling
        while next_elem:
            if getattr(next_elem, 'name', None) and next_elem.name.startswith('h'):
                break
            if getattr(next_elem, 'name', None) == 'p':
                content.append(next_elem.get_text().strip())
            elif getattr(next_elem, 'name', None) == 'ul':
                for li in next_elem.find_all('li'):
                    content.append(f"- {li.get_text().strip()}")
            next_elem = next_elem.next_sibling
        return "\n".join(content)

    async def extract_tab_content(self, page):
        # Try to click through tabs if present
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
                        self.tab_data.append({
                            'tab_name': tab_name.strip(),
                            'content': panel_text.strip()
                        })
        except Exception:
            pass

    def is_valid_link(self, href):
        return (
            not href.startswith('javascript:') and
            not href.startswith('mailto:') and
            not href.startswith('tel:') and
            href.strip() != '#'
        )

    def normalize_url(self, url):
        return urljoin(self.url, url) if url.startswith('/') else url

    def clean_text(self, text):
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

    def generate_pdf(self, output_file):
        page_width = self.pdf.w - 2 * self.pdf.l_margin
        metadata = next(item for item in self.content_data if item['type'] == 'metadata')
        self.pdf.set_font("Arial", 'B', 16)
        self.pdf.multi_cell(page_width, 10, self.clean_text(metadata['title']), align='C')
        self.pdf.ln(2)
        self.pdf.set_font("Arial", '', 12)
        self.pdf.multi_cell(page_width, 8, self.clean_text(metadata['url']), align='C')
        self.pdf.ln(2)
        self.pdf.multi_cell(page_width, 8, self.clean_text(metadata['meta_desc']), align='C')
        self.pdf.ln(8)
        for item in self.content_data:
            if item['type'] == 'heading_content':
                self.pdf.set_font("Arial", 'B', 14)
                self.pdf.multi_cell(page_width, 9, self.clean_text(item['heading']))
                self.pdf.ln(1)
                self.pdf.set_font("Arial", '', 12)
                self.pdf.multi_cell(page_width, 8, self.clean_text(item['content']))
                self.pdf.ln(4)
            elif item['type'] == 'link':
                self.pdf.set_text_color(0, 0, 255)
                self.pdf.set_font("Arial", '', 12)
                self.pdf.multi_cell(page_width, 8, self.clean_text(f"{item['text']} -> {item['url']}"))
                self.pdf.set_text_color(0, 0, 0)
                self.pdf.ln(2)
        if self.tab_data:
            self.pdf.add_page()
            self.pdf.set_font("Arial", 'B', 16)
            self.pdf.multi_cell(page_width, 10, "Tabbed Content")
            self.pdf.ln(4)
            for tab in self.tab_data:
                self.pdf.set_font("Arial", 'B', 14)
                self.pdf.multi_cell(page_width, 9, self.clean_text(tab['tab_name']))
                self.pdf.ln(1)
                self.pdf.set_font("Arial", '', 12)
                self.pdf.multi_cell(page_width, 8, self.clean_text(tab['content']))
                self.pdf.ln(4)
        self.pdf.output(output_file)
        print(f"PDF generated successfully: {output_file}")

async def main():
    url = input('Enter the URL of the webpage to scrape: ').strip()
    output = input('Enter output PDF filename (default: output.pdf): ').strip()
    if not output:
        output = 'output.pdf'
    scraper = PlaywrightPDFScraper(url)
    await scraper.fetch_page()
    scraper.extract_content()
    scraper.generate_pdf(output)

if __name__ == "__main__":
    asyncio.run(main()) 