"""
Base API Client
Provides common functionality for all API clients including retry logic, error handling, and logging
"""
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

@dataclass
class APIClientConfig:
    """Configuration for API clients"""
    url: str
    headers: Dict[str, str]
    timeout: int = 30  # Total timeout for API requests
    connection_timeout: int = 10  # Timeout for initial connection
    max_retries: int = 3
    backoff_factor: float = 1.0
    model: Optional[str] = None

class APIError(Exception):
    """Base exception for API errors"""
    pass

class APITimeoutError(APIError):
    """Exception raised when API request times out"""
    pass

class APIRateLimitError(APIError):
    """Exception raised when API rate limit is exceeded"""
    pass

class BaseAPIClient:
    """Base class for API clients with common functionality"""
    
    def __init__(self, config: APIClientConfig):
        self.config = config
        self.session = self._create_session()
        logger.debug(f"Initialized {self.__class__.__name__} with URL: {config.url}")
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request with error handling and retries"""
        logger.debug(f"Making request to {self.config.url}")
        logger.debug(f"Request payload keys: {list(payload.keys())}")
        
        try:
            # Use tuple for (connection_timeout, read_timeout)
            timeout_tuple = (self.config.connection_timeout, self.config.timeout)
            response = self.session.post(
                self.config.url,
                headers=self.config.headers,
                json=payload,
                timeout=timeout_tuple
            )
            
            logger.debug(f"Response status: {response.status_code}")
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', '60')
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(float(retry_after))
                raise APIRateLimitError(f"Rate limited. Retry after {retry_after} seconds")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout (connection: {self.config.connection_timeout}s, read: {self.config.timeout}s)")
            raise APITimeoutError(f"Request timeout (connection: {self.config.connection_timeout}s, read: {self.config.timeout}s)")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise APIError(f"Request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise APIError(f"Unexpected error: {e}")
    
    def _extract_content(self, response_data: Dict[str, Any]) -> str:
        """Extract content from API response (to be overridden by subclasses)"""
        # Try OpenAI format first
        if "choices" in response_data and response_data["choices"]:
            return response_data["choices"][0]["message"]["content"]
        
        # Try direct message format
        if "message" in response_data:
            return response_data["message"]
        
        logger.error(f"Unexpected response format: {response_data}")
        raise APIError("Response missing 'message' or 'choices[0][\"message\"][\"content\"]' key")
    
    def send_message(self, payload: Dict[str, Any]) -> str:
        """Send message and return extracted content"""
        response_data = self._make_request(payload)
        content = self._extract_content(response_data)
        logger.debug(f"Extracted content length: {len(content)}")
        return content
