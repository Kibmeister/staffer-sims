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
    # Connection pooling settings
    pool_connections: int = 10  # Number of connection pools to cache
    pool_maxsize: int = 20  # Maximum number of connections to save in the pool
    pool_block: bool = False  # Whether to block when no free connections available

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
        """Create a requests session with optimized connection pooling and retry strategy"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        
        # Create HTTPAdapter with connection pooling optimization
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.config.pool_connections,
            pool_maxsize=self.config.pool_maxsize,
            pool_block=self.config.pool_block
        )
        
        # Mount adapters for both HTTP and HTTPS
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        logger.debug(f"Created session with connection pool (connections: {self.config.pool_connections}, maxsize: {self.config.pool_maxsize})")
        
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
    
    def _extract_usage(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage data from API response"""
        usage = response_data.get("usage", {})
        
        # Standardize usage format
        extracted_usage = {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
        
        # Calculate total if not provided
        if extracted_usage["total_tokens"] == 0:
            extracted_usage["total_tokens"] = extracted_usage["input_tokens"] + extracted_usage["output_tokens"]
        
        logger.debug(f"Extracted usage: {extracted_usage}")
        return extracted_usage
    
    def send_message(self, payload: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Send message and return extracted content and usage data"""
        response_data = self._make_request(payload)
        content = self._extract_content(response_data)
        usage = self._extract_usage(response_data)
        logger.debug(f"Extracted content length: {len(content)}, tokens: {usage['total_tokens']}")
        return content, usage
    
    def close(self):
        """Close the session and cleanup connections"""
        if hasattr(self, 'session') and self.session:
            logger.debug(f"Closing session for {self.__class__.__name__}")
            self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup connections"""
        self.close()
