import requests
from bs4 import BeautifulSoup
import re
import os
from fpdf import FPDF # We'll use FPDF for PDF generation as it's straightforward.

def get_page_content(url):
    """
    Fetches the HTML content of a given URL.
    Args:
        url (str): The URL of the webpage to fetch.
    Returns:
        str: The HTML content of the page, or None if an error occurs.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def extract_page_metadata(soup):
    """
    Extracts the page title and meta description from the BeautifulSoup object.
    Args:
        soup (BeautifulSoup): The BeautifulSoup object of the parsed HTML.
    Returns:
        dict: A dictionary containing the page title and meta description.
    """
    title = soup.title.string if soup.title else "No Title Found"
    meta_description = ""
    meta_tag = soup.find('meta', attrs={'name': 'description'})
    if meta_tag and meta_tag.get('content'):
        meta_description = meta_tag['content'].strip()
    return {"title": title, "meta_description": meta_description}

def extract_text_content(soup):
    """
    Extracts headings, their associated paragraphs, and standalone paragraphs.
    Args:
        soup (BeautifulSoup): The BeautifulSoup object of the parsed HTML.
    Returns:
        list: A list of dictionaries, where each dictionary represents a content block.
              Each block has a 'type' ('heading' or 'paragraph'), 'tag' (e.g., 'h1', 'p'),
              and 'text' content. Headings also have an associated 'level'.
    """
    content_blocks = []
    # Define tags that typically contain main content
    content_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'span', 'div']
    
    # Iterate through elements to maintain order and context
    for element in soup.find_all(content_tags):
        text = element.get_text(separator=" ", strip=True)
        if not text:
            continue

        if element.name.startswith('h') and len(element.name) == 2 and element.name[1].isdigit():
            level = int(element.name[1])
            content_blocks.append({"type": "heading", "tag": element.name, "level": level, "text": text})
        elif element.name == 'p':
            # Avoid adding duplicate paragraphs if they were already captured under a heading
            if not (content_blocks and content_blocks[-1]["type"] == "paragraph" and content_blocks[-1]["text"] == text):
                content_blocks.append({"type": "paragraph", "tag": element.name, "text": text})
        elif element.name == 'li':
            content_blocks.append({"type": "list_item", "tag": element.name, "text": text})
        # Add other relevant tags if they contain significant standalone text
        elif element.name == 'span' and len(text) > 50: # Example: only capture longer spans
             content_blocks.append({"type": "text", "tag": element.name, "text": text})
        elif element.name == 'div' and len(text) > 100 and not element.find('h1') and not element.find('p'): # Example: Capture larger div texts without nested main elements
             content_blocks.append({"type": "text", "tag": element.name, "text": text})

    return content_blocks

def extract_links(soup, base_url):
    """
    Extracts meaningful links (anchor text and destination URL).
    Args:
        soup (BeautifulSoup): The BeautifulSoup object of the parsed HTML.
        base_url (str): The base URL to resolve relative links.
    Returns:
        list: A list of dictionaries, each with 'anchor_text' and 'url'.
    """
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href'].strip()
        anchor_text = a_tag.get_text(strip=True)

        # Skip empty anchor text or purely icon links
        if not anchor_text or re.match(r'^\s*$', anchor_text):
            continue

        # Resolve relative URLs
        if not href.startswith(('http://', 'https://', 'mailto:', '#')):
            href = requests.compat.urljoin(base_url, href)
        
        # Basic filtering for meaningful links (can be enhanced)
        if not href.startswith('mailto:') and not href.startswith('#') and len(anchor_text) > 2:
            links.append({"anchor_text": anchor_text, "url": href})
    return links

def extract_downloadable_links(soup, base_url):
    """
    Extracts links to downloadable files (e.g., PDFs, documents).
    Args:
        soup (BeautifulSoup): The BeautifulSoup object of the parsed HTML.
        base_url (str): The base URL to resolve relative links.
    Returns:
        list: A list of dictionaries, each with 'anchor_text' and 'url'.
    """
    download_links = []
    download_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar']
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href'].strip()
        anchor_text = a_tag.get_text(strip=True)

        if not anchor_text:
            continue

        # Resolve relative URLs
        if not href.startswith(('http://', 'https://')):
            href = requests.compat.urljoin(base_url, href)

        if any(href.lower().endswith(ext) for ext in download_extensions):
            download_links.append({"anchor_text": anchor_text, "url": href})
    return download_links

def extract_tab_content(soup, base_url):
    """
    Extracts content from tabbed components. This is a highly generalized approach
    and might need specific adjustments based on the actual HTML structure of tabs.
    For the thirdeyedata.ai/contact-us/ example, it looks for specific IDs.
    Args:
        soup (BeautifulSoup): The BeautifulSoup object of the parsed HTML.
        base_url (str): The base URL of the page.
    Returns:
        dict: A dictionary where keys are tab titles and values are their content.
    """
    tab_content = {}
    # This part is highly dependent on the website's specific tab implementation.
    # For the thirdeyedata.ai/contact-us/ example, let's look for specific divs.
    
    # Example for thirdeyedata.ai/contact-us/
    # It seems the "Meet with US team" and "Meet with India team" are linked to sections
    # with IDs like 'us' and 'india'. The content is within those sections.
    
    us_team_section = soup.find(id='us')
    if us_team_section:
        us_text = us_team_section.get_text(separator="\n", strip=True)
        tab_content["Meet with US team"] = us_text

    india_team_section = soup.find(id='india')
    if india_team_section:
        india_text = india_team_section.get_text(separator="\n", strip=True)
        tab_content["Meet with India team"] = india_text
        
    # General approach for more common tab structures (e.g., using roles, data-attributes)
    # This is a conceptual example and might need refinement for other sites.
    # Look for tab buttons and their corresponding content panels
    # tab_buttons = soup.find_all(role='tab') or soup.find_all(class_=re.compile(r'tab-button'))
    # for button in tab_buttons:
    #     tab_name = button.get_text(strip=True)
    #     # Often, the button's href or data-target points to the content panel's ID
    #     target_id = button.get('href', '').lstrip('#') or button.get('data-target', '')
    #     if target_id:
    #         content_panel = soup.find(id=target_id)
    #         if content_panel:
    #             tab_content[tab_name] = content_panel.get_text(separator="\n", strip=True)

    return tab_content

def scrape_website_data(url):
    """
    Main function to scrape data from a given URL.
    Args:
        url (str): The URL of the webpage to scrape.
    Returns:
        dict: A dictionary containing all extracted and structured data.
    """
    html_content = get_page_content(url)
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')

    scraped_data = {
        "url": url,
        "metadata": extract_page_metadata(soup),
        "content_blocks": extract_text_content(soup),
        "links": extract_links(soup, url),
        "downloadable_links": extract_downloadable_links(soup, url),
        "tab_content": {}
    }
    
    # Only try to extract tab content if it's the contact-us page or another known tabbed page
    if "contact-us" in url:
        scraped_data["tab_content"] = extract_tab_content(soup, url)

    return scraped_data

if __name__ == "__main__":
    # Example usage for scraping:
    # This part will be used to demonstrate the data extraction
    # before we integrate with PDF generation.
    
    print("Scraping ThirdEye Data homepage...")
    homepage_url = "https://thirdeyedata.ai"
    homepage_data = scrape_website_data(homepage_url)

    if homepage_data:
        print("\n--- Scraped Homepage Data ---")
        print(f"URL: {homepage_data['url']}")
        print(f"Title: {homepage_data['metadata']['title']}")
        print(f"Meta Description: {homepage_data['metadata']['meta_description']}")
        
        print("\n--- Content Blocks ---")
        for block in homepage_data['content_blocks']:
            if block['type'] == 'heading':
                print(f"  {'#' * block['level']} {block['text']}")
            else:
                print(f"  {block['text']}")
        
        print("\n--- Links ---")
        for link in homepage_data['links']:
            print(f"  Anchor: {link['anchor_text']} -> URL: {link['url']}")

        print("\n--- Downloadable Links ---")
        if homepage_data['downloadable_links']:
            for link in homepage_data['downloadable_links']:
                print(f"  Download: {link['anchor_text']} -> URL: {link['url']}")
        else:
            print("  No downloadable links found.")

    print("\nScraping ThirdEye Data Contact Us page for tab content...")
    contact_us_url = "https://thirdeyedata.ai/contact-us/"
    contact_us_data = scrape_website_data(contact_us_url)

    if contact_us_data and contact_us_data["tab_content"]:
        print("\n--- Tab Content from Contact Us Page ---")
        for tab_name, content in contact_us_data["tab_content"].items():
            print(f"\nTab: {tab_name}")
            print(content)
    elif contact_us_data:
        print("\nNo specific tab content found on the Contact Us page using current logic.")
    else:
        print("\nCould not scrape Contact Us page.")