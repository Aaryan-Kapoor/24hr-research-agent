"""
Tools Module for Deep Research Agent
Handles web search, content extraction, and file operations
"""
import os
import re
import time
import random
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse
from functools import wraps

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import get_config, get_env_settings, Source, SearchProvider
from .logger import get_logger

logger = get_logger(__name__)

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Academic domains for quality scoring
ACADEMIC_DOMAINS = {
    'edu', 'ac.uk', 'ac.jp', 'edu.au', 'edu.cn',
    'arxiv.org', 'pubmed.gov', 'ncbi.nlm.nih.gov',
    'scholar.google.com', 'semanticscholar.org',
    'researchgate.net', 'academia.edu', 'jstor.org',
    'springer.com', 'nature.com', 'sciencedirect.com',
    'ieee.org', 'acm.org', 'nih.gov', 'gov'
}

# High-quality domains
HIGH_QUALITY_DOMAINS = {
    'wikipedia.org', 'britannica.com', 'bbc.com', 'bbc.co.uk',
    'nytimes.com', 'washingtonpost.com', 'theguardian.com',
    'reuters.com', 'apnews.com', 'bloomberg.com',
    'techcrunch.com', 'wired.com', 'arstechnica.com',
    'medium.com', 'github.com', 'stackoverflow.com'
}


# =============================================================================
# RATE LIMITING
# =============================================================================

class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.interval = 60.0 / calls_per_minute
        self.last_call = 0.0
    
    def wait(self):
        """Wait if necessary to respect rate limit"""
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last_call = time.time()


# Rate limiters
_search_limiter: Optional[RateLimiter] = None
_scrape_limiter: Optional[RateLimiter] = None


def get_search_limiter() -> RateLimiter:
    global _search_limiter
    if _search_limiter is None:
        config = get_config()
        _search_limiter = RateLimiter(config.rate_limits.search_calls_per_minute)
    return _search_limiter


def get_scrape_limiter() -> RateLimiter:
    global _scrape_limiter
    if _scrape_limiter is None:
        config = get_config()
        _scrape_limiter = RateLimiter(config.rate_limits.scrape_requests_per_minute)
    return _scrape_limiter


# =============================================================================
# SEARCH FUNCTIONS
# =============================================================================

def search_tavily(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search using Tavily API with full content extraction"""
    settings = get_env_settings()
    config = get_config()
    
    if not settings.tavily_api_key:
        raise ValueError("TAVILY_API_KEY not set in environment")
    
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        
        # Apply rate limiting
        get_search_limiter().wait()
        
        logger.debug(f"Searching Tavily: {query}")
        
        response = client.search(
            query,
            search_depth=config.search.depth,
            max_results=max_results,
            include_domains=config.search.include_domains or None,
            exclude_domains=config.search.exclude_domains or None,
            include_raw_content=True  # Get full page content
        )
        
        results = []
        for r in response.get('results', []):
            results.append({
                'url': r.get('url', ''),
                'title': r.get('title', ''),
                'snippet': r.get('content', ''),
                'raw_content': r.get('raw_content', ''),  # Full page content
                'score': r.get('score', 0.5)
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return []


def search_serper(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search using Serper API"""
    settings = get_env_settings()
    
    if not settings.serper_api_key:
        raise ValueError("SERPER_API_KEY not set in environment")
    
    try:
        # Apply rate limiting
        get_search_limiter().wait()
        
        logger.debug(f"Searching Serper: {query}")
        
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": settings.serper_api_key,
                "Content-Type": "application/json"
            },
            json={"q": query, "num": max_results},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        for r in data.get('organic', [])[:max_results]:
            results.append({
                'url': r.get('link', ''),
                'title': r.get('title', ''),
                'snippet': r.get('snippet', ''),
                'score': 0.5
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Serper search error: {e}")
        return []


def search_brave(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search using Brave Search API"""
    settings = get_env_settings()
    
    if not settings.brave_api_key:
        raise ValueError("BRAVE_API_KEY not set in environment")
    
    try:
        # Apply rate limiting
        get_search_limiter().wait()
        
        logger.debug(f"Searching Brave: {query}")
        
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "X-Subscription-Token": settings.brave_api_key,
                "Accept": "application/json"
            },
            params={"q": query, "count": max_results},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        for r in data.get('web', {}).get('results', [])[:max_results]:
            results.append({
                'url': r.get('url', ''),
                'title': r.get('title', ''),
                'snippet': r.get('description', ''),
                'score': 0.5
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Brave search error: {e}")
        return []


def web_search(query: str, max_results: int = None) -> List[Dict[str, Any]]:
    """
    Unified search function that uses the configured provider
    """
    config = get_config()
    max_results = max_results or config.search.max_results
    
    provider = config.search.provider
    
    if provider == SearchProvider.TAVILY:
        return search_tavily(query, max_results)
    elif provider == SearchProvider.SERPER:
        return search_serper(query, max_results)
    elif provider == SearchProvider.BRAVE:
        return search_brave(query, max_results)
    else:
        raise ValueError(f"Unknown search provider: {provider}")


# =============================================================================
# CONTENT EXTRACTION
# =============================================================================

def get_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return ""


def is_academic_source(url: str) -> bool:
    """Check if URL is from an academic source"""
    domain = get_domain(url)
    
    # Check exact domain
    if domain in ACADEMIC_DOMAINS:
        return True
    
    # Check domain endings
    for academic in ACADEMIC_DOMAINS:
        if domain.endswith('.' + academic) or domain == academic:
            return True
    
    return False


def calculate_quality_score(url: str, title: str, content: str) -> float:
    """Calculate a quality score for a source (0-1)"""
    score = 0.5  # Base score
    domain = get_domain(url)
    
    # Academic bonus
    if is_academic_source(url):
        score += 0.3
    
    # High-quality domain bonus
    if domain in HIGH_QUALITY_DOMAINS:
        score += 0.2
    
    # Content length factor (longer = potentially more comprehensive)
    content_len = len(content) if content else 0
    if content_len > 5000:
        score += 0.1
    elif content_len > 2000:
        score += 0.05
    
    # Penalize very short content
    if content_len < 500:
        score -= 0.1
    
    # Title quality
    if title and len(title) > 20:
        score += 0.05
    
    # Cap score at 1.0
    return min(max(score, 0.0), 1.0)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.RequestException, ConnectionError))
)
def scrape_url(url: str) -> Tuple[str, str]:
    """
    Scrape content from a URL
    Returns: (title, content)
    """
    config = get_config()
    
    # Apply rate limiting
    get_scrape_limiter().wait()
    
    logger.debug(f"Scraping: {url}")
    
    # Get random user agent
    user_agent = random.choice(USER_AGENTS) if config.scraping.rotate_user_agents else USER_AGENTS[0]
    
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=config.scraping.timeout,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Try trafilatura first (better extraction)
        try:
            import trafilatura
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                content = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=True,
                    no_fallback=False
                )
                if content and len(content) > 200:
                    # Get title separately
                    soup = BeautifulSoup(response.content, 'html.parser')
                    title = soup.title.string if soup.title else ""
                    return title.strip() if title else "", content[:config.scraping.max_content_length]
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Trafilatura extraction failed: {e}")
        
        # Fallback to BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get title
        title = ""
        if soup.title:
            title = soup.title.string or ""
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 
                           'aside', 'form', 'button', 'iframe', 'noscript']):
            element.decompose()
        
        # Try to find main content
        main_content = None
        for selector in ['article', 'main', '[role="main"]', '.content', '#content', '.post', '.article']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            # Get body text
            body = soup.find('body')
            text = body.get_text(separator='\n', strip=True) if body else soup.get_text(separator='\n', strip=True)
        
        # Clean up text
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = '\n'.join(lines)
        
        # Truncate if needed
        text = text[:config.scraping.max_content_length]
        
        return title.strip(), text
        
    except requests.RequestException as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error scraping {url}: {e}")
        return "", ""


def extract_source_info(url: str, search_result: Dict[str, Any] = None) -> Source:
    """
    Extract full source information from a URL
    Uses raw_content from Tavily if available, falls back to scraping
    """
    title = search_result.get('title', '') if search_result else ''
    snippet = search_result.get('snippet', '') if search_result else ''
    
    # First, try to use raw_content from Tavily search results (already fetched)
    full_content = ""
    if search_result and search_result.get('raw_content'):
        full_content = search_result['raw_content']
        logger.debug(f"Using Tavily raw_content for {url[:50]}...")
    else:
        # Fall back to scraping if no raw_content (e.g., Serper/Brave results)
        try:
            scraped_title, scraped_content = scrape_url(url)
            if scraped_title and not title:
                title = scraped_title
            full_content = scraped_content
        except Exception as e:
            logger.warning(f"Could not scrape {url}: {e}")
    
    domain = get_domain(url)
    is_academic = is_academic_source(url)
    quality_score = calculate_quality_score(url, title, full_content or snippet)
    
    return Source(
        url=url,
        title=title or domain,
        domain=domain,
        snippet=snippet,
        full_content=full_content,
        quality_score=quality_score,
        is_academic=is_academic,
        accessed_at=datetime.utcnow()
    )


# =============================================================================
# FILE OPERATIONS
# =============================================================================

def ensure_directory(path: str) -> Path:
    """Ensure a directory exists"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_markdown(filepath: str, content: str, append: bool = True) -> bool:
    """
    Save content to a markdown file
    """
    try:
        path = Path(filepath)
        ensure_directory(path.parent)
        
        mode = 'a' if append and path.exists() else 'w'
        with open(path, mode, encoding='utf-8') as f:
            f.write(content)
            if not content.endswith('\n'):
                f.write('\n')
        
        logger.debug(f"Saved content to {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save to {filepath}: {e}")
        return False


def read_file(filepath: str) -> Optional[str]:
    """Read content from a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.error(f"Failed to read {filepath}: {e}")
        return None


def count_words(text: str) -> int:
    """Count words in text"""
    if not text:
        return 0
    return len(text.split())


def count_citations(text: str) -> int:
    """Count citations in text (looks for [Source: ...] or URLs)"""
    if not text:
        return 0
    
    # Count [Source: ...] patterns
    citation_pattern = r'\[Source:.*?\]'
    citations = len(re.findall(citation_pattern, text, re.IGNORECASE))
    
    # Count inline URLs
    url_pattern = r'https?://[^\s\]\)>]+'
    urls = len(re.findall(url_pattern, text))
    
    # Count markdown footnotes
    footnote_pattern = r'\[\^\d+\]'
    footnotes = len(re.findall(footnote_pattern, text))
    
    return max(citations, urls // 2, footnotes)


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be used as a filename"""
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    # Remove invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Limit length
    name = name[:100]
    return name


def generate_file_path(topic: str, output_dir: str = "report", index: int = None) -> str:
    """Generate a file path for a topic"""
    safe_name = sanitize_filename(topic)
    
    if index is not None:
        filename = f"{index:02d}_{safe_name}.md"
    else:
        filename = f"{safe_name}.md"
    
    return str(Path(output_dir) / filename)


# =============================================================================
# TOKEN COUNTING
# =============================================================================

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Estimate token count for text
    Uses tiktoken if available, otherwise rough estimate
    """
    try:
        import tiktoken
        
        # Map model names to encoding
        if "claude" in model.lower():
            # Claude uses similar tokenization to GPT-4
            encoding = tiktoken.get_encoding("cl100k_base")
        else:
            encoding = tiktoken.encoding_for_model(model)
        
        return len(encoding.encode(text))
        
    except Exception:
        # Rough estimate: ~4 characters per token
        return len(text) // 4


def truncate_to_tokens(text: str, max_tokens: int, model: str = "gpt-4") -> str:
    """Truncate text to fit within token limit"""
    try:
        import tiktoken
        
        if "claude" in model.lower():
            encoding = tiktoken.get_encoding("cl100k_base")
        else:
            encoding = tiktoken.encoding_for_model(model)
        
        tokens = encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        truncated_tokens = tokens[:max_tokens]
        return encoding.decode(truncated_tokens)
        
    except Exception:
        # Rough estimate
        chars_per_token = 4
        max_chars = max_tokens * chars_per_token
        return text[:max_chars]