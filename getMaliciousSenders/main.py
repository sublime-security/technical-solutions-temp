#!/usr/bin/env python3
"""
Malicious Sender Email Extractor

This script extracts sender email addresses from malicious messages using the Sublime Security API.
It fetches messages with malicious attack score verdict and extracts unique sender emails.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from getpass import getpass
from typing import Dict, List, Optional, Set
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class MaliciousSenderExtractor:
    """Extracts sender emails from malicious messages via Sublime Security API."""
    
    def __init__(self, base_url: str, api_token: str):
        """
        Initialize the extractor with API credentials.
        
        Args:
            base_url: Base URL for the Sublime Security API
            api_token: API token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=1,  # Only retry once as per requirements
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_token}'
        })
        
        return session
    
    def _get_date_filter(self, days_back: int) -> str:
        """
        Generate the date filter for the API query.
        
        Args:
            days_back: Number of days to look back from today
            
        Returns:
            ISO formatted date string in UTC
        """
        target_date = datetime.utcnow() - timedelta(days=days_back)
        return target_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    
    def _make_api_request(self, offset: int = 0, days_back: int = 7) -> Dict:
        """
        Make API request to fetch message groups.
        
        Args:
            offset: Pagination offset
            days_back: Number of days to look back
            
        Returns:
            API response as dictionary
            
        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self.base_url}/v1/messages/groups"
        
        params = {
            'attack_score_verdict__is': 'malicious',
            'attack_surface_reduction__is': 'include',
            'created_at__gte': self._get_date_filter(days_back),
            'fetch_all_ids': 'false',
            'flagged__eq': 'true',
            'limit': '500',
            'offset': str(offset)
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API Error: {e}")
            print("Try again")
            sys.exit(1)
    
    def extract_sender_emails(self, days_back: int = 7) -> Set[str]:
        """
        Extract unique sender email addresses from malicious messages.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Set of unique sender email addresses
        """
        sender_emails = set()
        offset = 0
        
        while True:
            try:
                response_data = self._make_api_request(offset, days_back)
                
                # Check if we have message groups (for pagination purposes only)
                message_groups = response_data.get('message_groups', [])
                
                if not message_groups:
                    break
                
                # Extract sender emails from top-level sender_email__info
                sender_info = response_data.get('sender_email__info')
                if sender_info and isinstance(sender_info, dict):
                    # Add all keys (email addresses) from sender_email__info
                    sender_emails.update(sender_info.keys())
                
                # Check if we need to continue pagination
                if len(message_groups) < 500:
                    break
                
                offset += 500
                
            except Exception as e:
                print(f"Error processing data: {e}")
                print("Try again")
                sys.exit(1)
        
        return sender_emails
    
    def save_to_file(self, sender_emails: Set[str], filename: Optional[str] = None) -> str:
        """
        Save sender emails to a text file.
        
        Args:
            sender_emails: Set of sender email addresses
            filename: Optional custom filename
            
        Returns:
            The filename that was used
        """
        if filename is None:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"malicious-senders-{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            for email in sorted(sender_emails):
                f.write(f"{email}\n")
        
        return filename
    
    def get_json_output(self, sender_emails: Set[str]) -> Dict[str, List[str]]:
        """
        Format sender emails as JSON output.
        
        Args:
            sender_emails: Set of sender email addresses
            
        Returns:
            Dictionary with malicious_sender_emails key
        """
        return {
            "malicious_sender_emails": sorted(list(sender_emails))
        }


def get_user_input() -> tuple[str, str]:
    """
    Prompt user for BASE_URL and API_TOKEN if not provided.
    
    Returns:
        Tuple of (base_url, api_token)
    """
    print("API credentials not provided. Please enter them below:")
    
    base_url = input("Base URL (e.g., https://platform.sublime.security): ").strip()
    if not base_url:
        print("Base URL is required")
        sys.exit(1)
    
    api_token = getpass("API Token: ").strip()
    if not api_token:
        print("API Token is required")
        sys.exit(1)
    
    return base_url, api_token


def main():
    """Main function to handle command line arguments and execute the script."""
    parser = argparse.ArgumentParser(
        description="Extract sender email addresses from malicious messages"
    )
    parser.add_argument(
        '--base-url',
        help='Base URL for the Sublime Security API (e.g., https://platform.sublime.security)'
    )
    parser.add_argument(
        '--api-token',
        help='API token for authentication'
    )
    parser.add_argument(
        '--days-back',
        type=int,
        default=7,
        help='Number of days to look back (default: 7)'
    )
    parser.add_argument(
        '--output-format',
        choices=['file', 'json'],
        default='file',
        help='Output format: file (default) or json'
    )
    parser.add_argument(
        '--output-file',
        help='Custom output filename (only used with --output-format=file)'
    )
    
    args = parser.parse_args()
    
    # Get API credentials
    base_url = args.base_url
    api_token = args.api_token
    
    if not base_url or not api_token:
        base_url, api_token = get_user_input()
    
    # Validate days_back
    if args.days_back < 1:
        print("Error: --days-back must be at least 1")
        sys.exit(1)
    
    # Initialize extractor
    extractor = MaliciousSenderExtractor(base_url, api_token)
    
    # Extract sender emails
    try:
        sender_emails = extractor.extract_sender_emails(args.days_back)
        
        if not sender_emails:
            print("None found")
            return
        
        # Output results
        if args.output_format == 'json':
            json_output = extractor.get_json_output(sender_emails)
            print(json.dumps(json_output, indent=2))
        else:
            filename = extractor.save_to_file(sender_emails, args.output_file)
            print(f"Saved {len(sender_emails)} unique sender emails to: {filename}")
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Try again")
        sys.exit(1)


if __name__ == "__main__":
    main()