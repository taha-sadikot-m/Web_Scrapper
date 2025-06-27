#python web_scraper.py https://thirdeyedata.ai -o thirdeye.pdf


import argparse
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fpdf import FPDF
from urllib.parse import urljoin, urlparse

class WebScraperPDFGenerator:
    def __init__(self, url):
        self.url = url
        self.domain = urlparse(url).netloc
        self.content_data = []
        self.tab_data = []
        self.driver = None
        self.soup = None
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.add_page()
        self.pdf.set_font("Arial", size=12)
        self.setup_selenium()

    def setup_selenium(self):
        """Initialize headless Chrome browser"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920x1080")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.get(self.url)
        time.sleep(3)  # Allow JavaScript rendering

    def extract_content(self):
        """Extract all required content from the page"""
        self.soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Extract metadata
        title = self.soup.title.string.strip() if self.soup.title else "No Title"
        meta_desc = self.soup.find('meta', attrs={'name': 'description'})
        meta_desc = meta_desc['content'].strip() if meta_desc else "No Description"
        
        # Add metadata to content
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
        
        # Extract tab content
        self.extract_tab_content()

    def extract_associated_content(self, heading):
        """Extract content associated with a heading"""
        content = []
        next_elem = heading.next_sibling
        
        while next_elem:
            if next_elem.name and next_elem.name.startswith('h'):
                break
            
            if next_elem.name == 'p':
                content.append(next_elem.get_text().strip())
            elif next_elem.name == 'ul':
                for li in next_elem.find_all('li'):
                    content.append(f"- {li.get_text().strip()}")
            
            next_elem = next_elem.next_sibling
        
        return "\n".join(content)

    def extract_tab_content(self):
        """Extract content from tab components"""
        try:
            tabs = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[role="tab"]'))
            )
            
            for i in range(len(tabs)):
                tabs = self.driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
                if i >= len(tabs):
                    continue
                
                tab = tabs[i]
                tab_name = tab.text.strip()
                tab.click()
                time.sleep(1)  # Wait for content to load
                
                # Find active tab panel
                active_panel = self.driver.find_element(By.CSS_SELECTOR, '[role="tabpanel"]:not([hidden])')
                panel_text = active_panel.text.strip()
                
                if panel_text:
                    self.tab_data.append({
                        'tab_name': tab_name,
                        'content': panel_text
                    })
        except Exception:
            pass  # No tab components found

    def is_valid_link(self, href):
        """Check if link should be included"""
        return (
            not href.startswith('javascript:') and
            not href.startswith('mailto:') and
            not href.startswith('tel:') and
            href.strip() != '#'
        )

    def normalize_url(self, url):
        """Convert relative URLs to absolute"""
        return urljoin(self.url, url) if url.startswith('/') else url

    def clean_text(self, text):
        """Clean text to remove characters that can't be encoded in Latin-1"""
        if not text:
            return ""
        
        # Replace common Unicode characters with ASCII equivalents
        replacements = {
            '\u2192': '->',  # right arrow
            '\u2190': '<-',  # left arrow
            '\u2013': '-',   # en dash
            '\u2014': '--',  # em dash
            '\u2018': "'",   # left single quotation mark
            '\u2019': "'",   # right single quotation mark
            '\u201c': '"',   # left double quotation mark
            '\u201d': '"',   # right double quotation mark
            '\u2022': '*',   # bullet
            '\u2026': '...',  # horizontal ellipsis
        }
        
        for unicode_char, ascii_char in replacements.items():
            text = text.replace(unicode_char, ascii_char)
        
        # Remove any remaining non-Latin-1 characters
        try:
            text.encode('latin-1')
            return text
        except UnicodeEncodeError:
            # If there are still problematic characters, encode and decode to remove them
            return text.encode('latin-1', errors='ignore').decode('latin-1')

    def generate_pdf(self, output_file):
        """Generate PDF report"""
        # Add metadata
        metadata = next(item for item in self.content_data if item['type'] == 'metadata')
        self.pdf.set_font("Arial", 'B', 16)
        self.pdf.cell(0, 10, self.clean_text(metadata['title']), 0, 1, 'C')
        self.pdf.set_font("Arial", '', 12)
        self.pdf.cell(0, 10, self.clean_text(metadata['url']), 0, 1, 'C')
        self.pdf.cell(0, 10, self.clean_text(metadata['meta_desc']), 0, 1, 'C')
        self.pdf.ln(10)
        
        # Add main content
        for item in self.content_data:
            if item['type'] == 'heading_content':
                self.pdf.set_font("Arial", 'B', 14)
                self.pdf.cell(0, 10, self.clean_text(item['heading']), 0, 1)
                self.pdf.set_font("Arial", '', 12)
                self.pdf.multi_cell(0, 8, self.clean_text(item['content']))
                self.pdf.ln(5)
            elif item['type'] == 'link':
                self.pdf.set_text_color(0, 0, 255)
                self.pdf.cell(0, 8, self.clean_text(f"{item['text']} -> {item['url']}"), 0, 1)
                self.pdf.set_text_color(0, 0, 0)
        
        # Add tab content if exists
        if self.tab_data:
            self.pdf.add_page()
            self.pdf.set_font("Arial", 'B', 16)
            self.pdf.cell(0, 10, "Tabbed Content", 0, 1)
            self.pdf.ln(5)
            
            for tab in self.tab_data:
                self.pdf.set_font("Arial", 'B', 14)
                self.pdf.cell(0, 10, self.clean_text(tab['tab_name']), 0, 1)
                self.pdf.set_font("Arial", '', 12)
                self.pdf.multi_cell(0, 8, self.clean_text(tab['content']))
                self.pdf.ln(5)
        
        # Save PDF
        self.pdf.output(output_file)
        self.driver.quit()
        print(f"PDF generated successfully: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Web Scraper and PDF Generator')
    parser.add_argument('url', help='URL of the webpage to scrape')
    parser.add_argument('-o', '--output', default='output.pdf', help='Output PDF filename')
    args = parser.parse_args()

    scraper = WebScraperPDFGenerator(args.url)
    scraper.extract_content()
    scraper.generate_pdf(args.output)

if __name__ == "__main__":
    main()