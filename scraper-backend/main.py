# main.py
from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel
from typing import List
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urljoin, urlparse
from tldextract import extract

app = FastAPI(title="Web Scraper API")

class ScrapedItem(BaseModel):
    title: str
    content: str
    content_type: str
    source_url: str

class ScrapeResponse(BaseModel):
    site: str
    items: List[ScrapedItem]

@app.post("/scrape", response_model=ScrapeResponse)
def scrape(url: str = Form(...)):
    domain = extract(url).registered_domain
    if not domain:
        raise HTTPException(status_code=400, detail="Invalid URL")

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Page not reachable")
        soup = BeautifulSoup(resp.text, 'html.parser')

        article = soup.find('article')
        if article and article.get_text(strip=True):
            content_block = article
        else:
            paragraphs = soup.find_all(['p', 'div'])
            max_text = ''
            max_block = None
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > len(max_text):
                    max_text = text
                    max_block = p
            content_block = max_block

        if not content_block or not content_block.get_text(strip=True):
            raise HTTPException(status_code=404, detail="No readable content found")

        title = soup.title.string.strip() if soup.title else "No title"
        content_md = md(str(content_block))

        item = ScrapedItem(
            title=title,
            content=content_md,
            content_type="blog",
            source_url=url
        )

        return ScrapeResponse(site=url, items=[item])

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
