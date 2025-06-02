import requests
import time
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class APIClient:
    """Generic HTTP client with retry logic and error handling"""
    
    def __init__(self, base_url: str, headers: Dict[str, str], timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.headers = headers
        self.timeout = timeout
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update(self.headers)
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise APIError("Authentication failed. Check your API key.")
            elif response.status_code == 403:
                raise APIError("Access forbidden. Check your permissions.")
            elif response.status_code == 404:
                raise APIError(f"Endpoint not found: {endpoint}")
            else:
                raise APIError(f"HTTP {response.status_code}: {response.text}")
        except requests.exceptions.ConnectionError:
            raise APIError(f"Failed to connect to {self.base_url}")
        except requests.exceptions.Timeout:
            raise APIError(f"Request timed out after {self.timeout} seconds")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")
    
    def patch(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make PATCH request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.patch(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            
            # Some endpoints might return empty response
            try:
                return response.json()
            except ValueError:
                return {"status": "success"}
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise APIError("Authentication failed. Check your API key.")
            elif response.status_code == 403:
                raise APIError("Access forbidden. Check your permissions.")
            elif response.status_code == 404:
                raise APIError(f"Resource not found: {endpoint}")
            else:
                raise APIError(f"HTTP {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")
    
    def close(self):
        """Close the session"""
        self.session.close()


class APIError(Exception):
    """Custom exception for API-related errors"""
    pass