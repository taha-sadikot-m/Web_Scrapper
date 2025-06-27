# Web_Scrapper

## Overview

**Web_Scrapper** is a Python project that allows users to scrape content from web pages and generate structured outputs, including PDF reports containing the extracted information. The project is designed to extract page metadata, headings, textual content, links, downloadable files, and even tabbed content from dynamic web pages. It leverages both static HTML parsing and browser automation for rich data acquisition.

## Features

- Scrapes webpage metadata (title & meta description).
- Extracts heading structures and associated content.
- Collects all links and downloadable resources (PDFs, DOCs, etc.).
- Handles tabbed content (e.g., switching between tabs on a contact page).
- Generates comprehensive PDF reports from the scraped data.
- Supports dynamic JavaScript-rendered content via Selenium.

## Technologies Used

- **Python 3**
- **BeautifulSoup** for HTML parsing
- **requests** for static page fetching
- **Selenium** for browser automation (handles dynamic content)
- **FPDF** for PDF generation

## Usage

### Prerequisites

- Python 3.x
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
  (Dependencies include `beautifulsoup4`, `selenium`, `fpdf`, `requests`.)

- Chrome browser and ChromeDriver installed for Selenium.

### Running the Scraper

#### Generate a PDF report from a URL

```bash
python Script.py <URL_TO_SCRAPE> -o <OUTPUT_FILENAME.pdf>
```

Example:
```bash
python Script.py https://thirdeyedata.ai -o thirdeye.pdf
```

- The script will scrape the provided webpage, extract relevant content (including tabbed sections), and generate a PDF report.

#### Extract structured data via script

The file `Second_Try.py` demonstrates scraping a webpage and printing structured data (metadata, headings, content, links, downloads, tabbed content) to the console.

### Customization

- You can modify or extend the main scraping logic in `Script.py` or `Second_Try.py` to suit other target sites or data needs.

## Project Structure

- `Script.py` — Main entry point for scraping and PDF generation.
- `Second_Try.py` — Alternative/experimental scraper focusing on structured extraction.
- Other utility/helper functions are defined within these scripts.

## License

Currently, no license is specified. Please contact the repository owner for usage terms.

## Author

- [taha-sadikot-m](https://github.com/taha-sadikot-m)

---

*Feel free to contribute or suggest improvements via issues or pull requests!*
