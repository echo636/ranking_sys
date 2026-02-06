import logging
import aiohttp
from typing import Optional, List
from bs4 import BeautifulSoup
from readability import Document

logger = logging.getLogger("ranking_sys")

class WebScraperService:
    """
    Web scraping service to fetch and extract content from URLs
    """
    
    def __init__(self, timeout: int = 10):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    async def scrape_url(self, url: str) -> Optional[dict]:
        """
        Fetch and parse a single URL
        
        Returns:
            dict with keys: url, title, description, content, author, status
            None if scraping fails
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout, headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                        return {
                            "url": url,
                            "title": f"Error: HTTP {response.status}",
                            "content": f"无法访问此网页 (HTTP {response.status})",
                            "status": "error"
                        }
                    
                    html = await response.text()
                    return self._extract_content(url, html)
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {url}: {e}")
            return {
                "url": url,
                "title": "网络错误",
                "content": f"无法连接到此网页: {str(e)}",
                "status": "error"
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return {
                "url": url,
                "title": "爬取失败",
                "content": f"爬取时发生错误: {str(e)}",
                "status": "error"
            }
    
    async def scrape_urls(self, urls: List[str]) -> List[dict]:
        """
        Fetch and parse multiple URLs concurrently
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of scraped page data dictionaries
        """
        import asyncio
        
        # Limit concurrency to avoid overwhelming servers
        semaphore = asyncio.Semaphore(5)
        
        async def fetch_with_semaphore(url):
            async with semaphore:
                return await self.scrape_url(url)
        
        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        # Filter out None results
        return [r for r in results if r is not None]
    
    def _extract_content(self, url: str, html: str) -> dict:
        """
        Extract main content, title, and metadata from HTML
        
        Args:
            url: Source URL
            html: Raw HTML content
            
        Returns:
            Dictionary with extracted data
        """
        try:
            # Use readability to extract main content
            doc = Document(html)
            
            # Parse with BeautifulSoup for metadata
            soup = BeautifulSoup(html, 'lxml')
            
            # Extract title (prefer readability, fallback to <title> tag)
            title = doc.title() or self._get_meta_tag(soup, 'title')
            
            # Extract description
            description = self._get_meta_tag(soup, 'description') or \
                         self._get_meta_tag(soup, 'og:description')
            
            # Extract author
            author = self._get_meta_tag(soup, 'author') or \
                    self._get_meta_tag(soup, 'article:author')
            
            # Get main content (already cleaned by readability)
            content_html = doc.summary()
            
            # Convert HTML to plain text and truncate
            content_text = self._html_to_text(content_html, max_length=2000)
            
            return {
                "url": url,
                "title": title or "无标题",
                "description": description,
                "content": content_text,
                "author": author,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            # Fallback: simple text extraction
            soup = BeautifulSoup(html, 'lxml')
            text = soup.get_text()[:2000]
            
            return {
                "url": url,
                "title": soup.title.string if soup.title else "无标题",
                "content": text,
                "status": "partial"
            }
    
    def _get_meta_tag(self, soup: BeautifulSoup, name: str) -> Optional[str]:
        """Extract content from meta tags"""
        # Try name attribute
        tag = soup.find('meta', attrs={'name': name})
        if tag and tag.get('content'):
            return tag.get('content')
        
        # Try property attribute (for Open Graph tags)
        tag = soup.find('meta', attrs={'property': name})
        if tag and tag.get('content'):
            return tag.get('content')
        
        return None
    
    def _html_to_text(self, html: str, max_length: int = 2000) -> str:
        """
        Convert HTML to clean plain text
        
        Args:
            html: HTML content
            max_length: Maximum length of output text
            
        Returns:
            Plain text string
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script and style tags
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        # Get text and clean up whitespace
        text = soup.get_text(separator='\n', strip=True)
        
        # Remove excessive newlines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length] + "...(内容已截断)"
        
        return text
