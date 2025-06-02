import os
import yaml
from pathlib import Path
from typing import List, Dict


class Settings:
    def __init__(self, 
                 api_key: str = None,
                 region: str = None,
                 date_range_days: int = 30,
                 output_prefix: str = None,
                 all_feeds: bool = False,
                 dry_run: bool = False):
        
        # Load regions from config file
        self.regions = self._load_regions()
        
        # API Configuration with precedence: env vars > cli args
        self.api_key = os.getenv('SUBLIME_API_KEY') or api_key
        provided_region = os.getenv('SUBLIME_REGION') or region or 'default'
        
        if provided_region not in self.regions:
            raise ValueError(f"Unknown region: {provided_region}. Available: {list(self.regions.keys())}")
        
        self.region = provided_region
        self.base_url = f"https://{self.regions[self.region]}"
        
        # Other settings
        self.date_range_days = int(os.getenv('SUBLIME_DATE_RANGE_DAYS', date_range_days))
        self.output_prefix = os.getenv('SUBLIME_OUTPUT_PREFIX') or output_prefix or 'rule_coverage_analysis'
        self.all_feeds = all_feeds
        self.dry_run = dry_run
        
        # Default remediative action types
        self.remediative_action_types = [
            'delete_message',
            'move_to_spam', 
            'quarantine_message'
        ]
        
        # Validate required settings
        if not self.api_key:
            raise ValueError("API key is required. Set SUBLIME_API_KEY env var or use --api-key")
    
    def _load_regions(self) -> Dict[str, str]:
        """Load region configuration from YAML file"""
        config_path = Path(__file__).parent / 'regions.yaml'
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('regions', {})
        except FileNotFoundError:
            # Fallback to hardcoded regions if file not found
            return {
                'default': 'platform.sublime.security',
                'uk': 'uk.platform.sublime.security',
                'na-west': 'na-west.platform.sublime.security'
            }
    
    def show_config_info(self):
        """Display configuration information to user"""
        env_vars_used = []
        if os.getenv('SUBLIME_API_KEY'):
            env_vars_used.append('SUBLIME_API_KEY')
        if os.getenv('SUBLIME_REGION'):
            env_vars_used.append('SUBLIME_REGION')
        if os.getenv('SUBLIME_DATE_RANGE_DAYS'):
            env_vars_used.append('SUBLIME_DATE_RANGE_DAYS')
        if os.getenv('SUBLIME_OUTPUT_PREFIX'):
            env_vars_used.append('SUBLIME_OUTPUT_PREFIX')
        
        if env_vars_used:
            print(f"ℹ️  Using configured environment variables: {', '.join(env_vars_used)}")
        
        print(f"🌍 Region: {self.region} ({self.base_url})")
        print(f"📅 Date range: {self.date_range_days} days")
        if self.all_feeds:
            print("📦 Analyzing: All feeds")
        else:
            print("📦 Analyzing: Sublime Core Feed only")
        if self.dry_run:
            print("🧪 Mode: Dry run (no changes will be made)")
    
    @property
    def headers(self) -> Dict[str, str]:
        """Generate HTTP headers for API requests"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }