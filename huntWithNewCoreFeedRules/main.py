#!/usr/bin/env python3
"""
Sublime Rule Hunter

This script identifies newly added rules in the Sublime Core feed, hunts with them
in the customer environment, and reports on the number of messages flagged by each new rule.
"""

import argparse
import json
import requests
import time
import csv
import datetime
import os
import re
from typing import Dict, List, Optional, NamedTuple, Tuple
from dataclasses import dataclass, field
import asyncio
import sys
import getpass


class Region(NamedTuple):
    """Represents a Sublime Security region"""
    code: str
    api_url: str
    description: str


@dataclass
class Rule:
    """Represents a Sublime Security detection rule"""
    id: str
    name: str
    severity: str
    source: str
    type: str
    retrieved_at: datetime.datetime


@dataclass
class HuntJob:
    """Represents a Sublime Security hunt job"""
    id: str
    rule_id: str
    rule_name: str
    rule_severity: str
    status: str = "PENDING"
    message_groups_count: int = 0
    message_group_ids: List[str] = field(default_factory=list) 

# Available regions for Sublime Security
REGIONS: Dict[str, Region] = {
    "NA_WEST": Region(
        code="NA_WEST",
        api_url="https://na-west.platform.sublime.security",
        description="North America West (Oregon)",
    ),
    "NA_EAST": Region(
        code="NA_EAST",
        api_url="https://platform.sublime.security",
        description="North America East (Virginia)",
    ),
    "CANADA": Region(
        code="CANADA",
        api_url="https://ca.platform.sublime.security",
        description="Canada (Montréal)",
    ),
    "EU_DUBLIN": Region(
        code="EU_DUBLIN",
        api_url="https://eu.platform.sublime.security",
        description="Europe (Dublin)",
    ),
    "EU_UK": Region(
        code="EU_UK",
        api_url="https://uk.platform.sublime.security",
        description="Europe (UK)",
    ),
    "AUSTRALIA": Region(
        code="AUSTRALIA",
        api_url="https://au.platform.sublime.security",
        description="Australia (Sydney)",
    ),
}


class SublimeAPI:
    """Class for handling API interactions with Sublime Security"""
    
    def __init__(self, api_key: str, region: Region):
        """Initialize the API client"""
        self.api_key = api_key
        self.region = region
        self.api_url = region.api_url
        self.headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json"
        }
    
    def get_feeds(self) -> Dict:
        """Get all feeds"""
        url = f"{self.api_url}/v1/feeds"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_feed_rules(self, feed_id: str) -> Dict:
        """Get rules for a specific feed"""
        url = f"{self.api_url}/v1/feeds/{feed_id}/rules"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def start_hunt_job(self, source: str, start_time: str, end_time: str) -> str:
        """Start a hunt job and return the job ID"""
        url = f"{self.api_url}/v0/hunt-jobs"
        payload = {
            "source": source,
            "range_start_time": start_time,
            "range_end_time": end_time
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json().get("hunt_job_id")
    
    def get_hunt_job_status(self, job_id: str) -> Dict:
        """Get the status of a hunt job"""
        url = f"{self.api_url}/v0/hunt-jobs/{job_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_hunt_job_results(self, job_id: str) -> Dict:
        """Get the results of a hunt job"""
        url = f"{self.api_url}/v0/hunt-jobs/{job_id}/results"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()


class SublimeRuleHunter:
    """Main class for hunting with new Sublime Security rules"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        region: Optional[str] = None,
        hunt_lookback: Optional[str] = None,
        rule_lookback: Optional[str] = "14d",
        output_file: Optional[str] = None,
        output_format: str = "json"
    ):
        self.api_key = api_key or self._prompt_for_api_key()
        self.region = self._get_region(region)
        self.rule_lookback = rule_lookback
        self.output_file = output_file
        self.output_format = output_format
        
        # Initialize API client
        self.api = SublimeAPI(self.api_key, self.region)
        
        # Set hunt time range
        self.hunt_time_range = self._set_time_range(hunt_lookback)
        self.hunt_jobs: List[HuntJob] = []

    def _prompt_for_api_key(self) -> str:
        """Prompt the user for their API key"""
        api_key = getpass.getpass("Please enter your Sublime Security API key: ")
        if not api_key:
            print("API key is required.")
            sys.exit(1)
        return api_key

    def _get_region(self, region_code: Optional[str]) -> Region:
        """Get the region based on the provided code or prompt the user to select one"""
        if region_code and region_code in REGIONS:
            return REGIONS[region_code]
        
        print("Please select your Sublime Security region:")
        for i, (code, region) in enumerate(REGIONS.items(), 1):
            print(f"{i}. {region.description} ({code})")
        
        while True:
            try:
                selection = int(input("Enter the number of your region: "))
                if 1 <= selection <= len(REGIONS):
                    return list(REGIONS.values())[selection - 1]
                print(f"Please enter a number between 1 and {len(REGIONS)}")
            except ValueError:
                print("Please enter a valid number")

    def _parse_lookback(self, lookback: str) -> Tuple[int, str]:
        """Parse the lookback parameter (e.g., '4d', '12h')"""
        if not lookback:
            return None, None
            
        match = re.match(r'^(\d+)([dh])$', lookback)
        if not match:
            raise ValueError(f"Invalid lookback format: {lookback}. Expected format: Nd or Nh (e.g., 4d for 4 days, 12h for 12 hours)")
        
        value = int(match.group(1))
        unit = match.group(2)
        
        return value, unit

    def _set_time_range(self, hunt_lookback: Optional[str]) -> Dict[str, str]:
        """Set the time range for hunting based on hunt_lookback parameter or user input"""
        now = datetime.datetime.now(datetime.timezone.utc)
        
        if hunt_lookback:
            try:
                value, unit = self._parse_lookback(hunt_lookback)
                if unit == 'd':
                    start = now - datetime.timedelta(days=value)
                elif unit == 'h':
                    start = now - datetime.timedelta(hours=value)
                else:
                    raise ValueError(f"Invalid unit: {unit}")
                end = now
            except ValueError as e:
                print(f"Error: {e}")
                print("Using default of 7 days lookback.")
                start = now - datetime.timedelta(days=7)
                end = now
        else:
            # Interactive mode only for CSV output
            if self.output_format.lower() == "csv":
                print("\nPlease specify a lookback period for the hunt:")
                print("1. Last 24 hours")
                print("2. Last 7 days")
                print("3. Last 30 days")
                print("4. Custom period")
                
                choice = input("Enter your choice (1-4): ")
                
                if choice == "1":
                    start = now - datetime.timedelta(days=1)
                    end = now
                elif choice == "2":
                    start = now - datetime.timedelta(days=7)
                    end = now
                elif choice == "3":
                    start = now - datetime.timedelta(days=30)
                    end = now
                elif choice == "4":
                    while True:
                        custom_input = input("Enter lookback period (e.g., 4d for 4 days, 12h for 12 hours): ")
                        try:
                            value, unit = self._parse_lookback(custom_input)
                            if unit == 'd':
                                start = now - datetime.timedelta(days=value)
                            elif unit == 'h':
                                start = now - datetime.timedelta(hours=value)
                            else:
                                print("Invalid unit. Please use 'd' for days or 'h' for hours.")
                                continue
                            end = now
                            break
                        except (ValueError, TypeError) as e:
                            print(f"Invalid format: {e}")
                            print("Please try again with the format Nd or Nh (e.g., 4d for 4 days, 12h for 12 hours)")
                else:
                    print("Invalid choice. Using default of 7 days.")
                    start = now - datetime.timedelta(days=7)
                    end = now
            else:
                # Default to 7 days for JSON output (non-interactive)
                start = now - datetime.timedelta(days=7)
                end = now
        
        # Format for API
        start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Only print time range for CSV format
        if self.output_format.lower() == "csv":
            print(f"Hunt time range: {start_str} to {end_str}")
        
        return {"start": start_str, "end": end_str}

    def get_core_feed_id(self) -> str:
        """Get the ID of the Sublime Core Feed"""
        try:
            feeds = self.api.get_feeds().get("feeds", [])
            for feed in feeds:
                if (feed.get("name") == "Sublime Core Feed" and 
                    feed.get("git_url") == "https://github.com/sublime-security/sublime-rules.git"):
                    return feed.get("id")
            
            raise ValueError("Sublime Core Feed not found")
        except Exception as e:
            print(f"Error getting core feed ID: {e}")
            sys.exit(1)

    def get_new_rules(self, feed_id: str) -> List[Rule]:
        """Get newly added rules from the specified feed"""
        try:
            rules_data = self.api.get_feed_rules(feed_id).get("rules", [])
            
            # Parse rule_lookback to get time delta
            if isinstance(self.rule_lookback, str):
                try:
                    value, unit = self._parse_lookback(self.rule_lookback)
                    if unit == 'd':
                        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=value)
                    elif unit == 'h':
                        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=value)
                    else:
                        # Default to 14 days if invalid format
                        if self.output_format.lower() == "csv":
                            print(f"Invalid rule_lookback format: {self.rule_lookback}. Using default of 14 days.")
                        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)
                except (ValueError, TypeError):
                    # Default to 14 days if parsing fails
                    if self.output_format.lower() == "csv":
                        print(f"Invalid rule_lookback format: {self.rule_lookback}. Using default of 14 days.")
                    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)
            else:
                # If rule_lookback is not a string (shouldn't happen with updated parameter), default to 14 days
                cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)
            
            new_rules = []
            for rule_data in rules_data:
                # Skip triage rules
                if rule_data.get("rule", {}).get("type") == "triage_rule":
                    continue
                
                # Check if the rule is new (not active and recently retrieved)
                if rule_data.get("sync_status") == "new":
                    retrieved_at_str = rule_data.get("retrieved_at")
                    if retrieved_at_str:
                        # Parse the timestamp with timezone awareness
                        retrieved_at = datetime.datetime.fromisoformat(
                            retrieved_at_str.replace('Z', '+00:00')
                        )
                        if retrieved_at > cutoff_date:
                            rule_obj = rule_data.get("rule", {})
                            
                            # Create Rule object
                            rule = Rule(
                                id=rule_obj.get("id"),
                                name=rule_obj.get("name"),
                                severity=rule_obj.get("severity", "unknown"),
                                source=rule_obj.get("source"),
                                type=rule_obj.get("type"),
                                retrieved_at=retrieved_at
                            )
                            new_rules.append(rule)
            
            return new_rules
        except Exception as e:
            print(f"Error getting new rules: {e}")
            sys.exit(1)

    async def start_hunt_jobs(self, rules: List[Rule]) -> List[HuntJob]:
        """Start hunt jobs for each new rule"""
        async def start_hunt(rule: Rule) -> Optional[HuntJob]:
            try:
                hunt_job_id = self.api.start_hunt_job(
                    rule.source, 
                    self.hunt_time_range["start"], 
                    self.hunt_time_range["end"]
                )
                
                return HuntJob(
                    id=hunt_job_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    rule_severity=rule.severity
                )
            except Exception as e:
                print(f"Error starting hunt for rule '{rule.name}': {e}")
                return None
        
        # Start all hunt jobs concurrently
        tasks = [start_hunt(rule) for rule in rules]
        hunt_jobs = await asyncio.gather(*tasks)
        
        # Filter out None values (failed hunt jobs)
        return [job for job in hunt_jobs if job]

    async def poll_hunt_job_status(self, hunt_jobs: List[HuntJob]) -> List[HuntJob]:
        """Poll for the status of each hunt job"""
        async def poll_job(job: HuntJob) -> HuntJob:
            while True:
                try:
                    job_status = self.api.get_hunt_job_status(job.id)
                    status = job_status.get("status")
                    job.status = status
                    
                    if status == "COMPLETED" or status == "ERROR":
                        if status == "ERROR":
                            print(f"Hunt job for rule '{job.rule_name}' failed with error: {job_status.get('error')}")
                        break
                    
                    # Wait before polling again
                    await asyncio.sleep(5)
                except Exception as e:
                    print(f"Error polling status for hunt job '{job.id}': {e}")
                    job.status = "ERROR"
                    break
            
            return job
        
        # Poll all hunt jobs concurrently
        tasks = [poll_job(job) for job in hunt_jobs]
        return await asyncio.gather(*tasks)

    async def get_hunt_results(self, hunt_jobs: List[HuntJob]) -> List[HuntJob]:
        """Get results for each completed hunt job"""
        async def get_result(job: HuntJob) -> HuntJob:
            if job.status != "COMPLETED":
                return job
            
            try:
                results = self.api.get_hunt_job_results(job.id)
                
                # Count the number of message groups
                message_groups = results.get("message_groups", [])
                job.message_groups_count = len(message_groups)

                # Include canonicalIds
                job.message_group_ids = [msg.get("id") for msg in message_groups]
                
                return job
            except Exception as e:
                print(f"Error getting results for hunt job '{job.id}': {e}")
                return job
        
        # Get results for all completed hunt jobs concurrently
        tasks = [get_result(job) for job in hunt_jobs]
        return await asyncio.gather(*tasks)
    
    def get_message_url(self, message_group_id: str) -> str:
        """Generate a URL to view a message group in the Sublime console"""
        return f"{self.api.region.api_url}/messages/{message_group_id}"

    def prepare_report_data(self, core_feed_id: str, hunt_jobs: List[HuntJob]) -> List[Dict]:
        """Prepare the report data in a structured format"""
        report_data = []
        for job in hunt_jobs:
            rule_url = f"{self.api.region.api_url}/feeds/{core_feed_id}/rules/{job.rule_id}"
            
            message_links = []
            for msg_id in job.message_group_ids[:5]:
                message_links.append(self.get_message_url(msg_id))
            
            report_item = {
                'ruleName': job.rule_name,
                'ruleSeverity': job.rule_severity,
                'messageGroupsCount': job.message_groups_count,
                'huntStatus': job.status,
                'ruleURL': rule_url,
                'samples': message_links
            }
            report_data.append(report_item)
            
        return report_data

    def write_csv_report(self, report_data: List[Dict], output_file: str) -> None:
        """Write the report data to a CSV file"""
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['ruleName', 'ruleSeverity', 'messageGroupsCount', 'huntStatus', 'ruleURL', 'samples']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for item in report_data:
                # Create a copy to avoid modifying the original data
                row = item.copy()
                # For CSV, convert the list of samples to a comma-separated string
                if isinstance(row['samples'], list):
                    row['samples'] = ','.join(row['samples'])
                writer.writerow(row)
        
        print(f"\nCSV report written to: {os.path.abspath(output_file)}")

    def generate_report(self, core_feed_id: str, hunt_jobs: List[HuntJob]) -> None:
        """Generate a report with the hunt results based on the specified format"""
        try:
            # Prepare the structured report data
            report_data = self.prepare_report_data(core_feed_id, hunt_jobs)
            
            # Handle output based on format
            if self.output_format.lower() == "csv":
                # For CSV format, write to file
                output_file = self.output_file or "sublime_rule_hunt_report.csv"
                self.write_csv_report(report_data, output_file)
            else:
                # For JSON format
                if self.output_file:
                    # Write to file if specified
                    with open(self.output_file, 'w') as jsonfile:
                        json.dump(report_data, jsonfile, indent=2)
                    print(f"\nJSON report written to: {os.path.abspath(self.output_file)}")
                else:
                    # Print raw JSON to stdout (default behavior)
                    print(json.dumps(report_data))
                
        except Exception as e:
            if self.output_format.lower() == "json" and not self.output_file:
                # Return error as JSON when outputting to stdout
                error_data = {"error": str(e)}
                print(json.dumps(error_data))
            else:
                print(f"Error generating report: {e}")

    async def run(self) -> None:
        """Run the main process"""
        # Determine if we should operate in verbose mode (CSV) or quiet mode (JSON)
        verbose_mode = self.output_format.lower() == "csv"
        
        # Get the core feed ID
        if verbose_mode:
            print("Starting Sublime Rule Hunter...")
            print("\nFetching Sublime Core Feed...")
        
        core_feed_id = self.get_core_feed_id()
        
        if verbose_mode:
            print(f"Found Sublime Core Feed with ID: {core_feed_id}")
            print(f"\nLooking for new rules added in the last {self.rule_lookback}...")
        
        # Get new rules
        rules = self.get_new_rules(core_feed_id)
        
        if not rules:
            if verbose_mode:
                print("No new rules found.")
            else:
                # For JSON, return empty array
                print("[]")
            return
        
        if verbose_mode:
            print(f"Found {len(rules)} new rules:")
            for rule in rules:
                print(f"- {rule.name} (Severity: {rule.severity})")
        
        # Start hunt jobs for each rule
        if verbose_mode:
            print("\nStarting hunt jobs...")
        
        hunt_jobs = await self.start_hunt_jobs(rules)
        
        if not hunt_jobs:
            if verbose_mode:
                print("No hunt jobs were started successfully.")
            else:
                # For JSON, return empty array
                print("[]")
            return
        
        # Poll for hunt job status
        if verbose_mode:
            print("\nPolling for hunt job status...")
            print("This may take a while depending on the size of your data and the time range...")
        
        hunt_jobs = await self.poll_hunt_job_status(hunt_jobs)
        
        # Get hunt results
        if verbose_mode:
            print("\nGetting hunt results...")
        
        hunt_jobs = await self.get_hunt_results(hunt_jobs)
        
        # Generate report
        if verbose_mode:
            print("\nGenerating report...")
        
        self.generate_report(core_feed_id, hunt_jobs)
        
        # Print summary only for CSV format
        if verbose_mode:
            print("\nSummary:")
            for job in hunt_jobs:
                status = "✅ Completed" if job.status == "COMPLETED" else "❌ Failed"
                print(f"- {job.rule_name}: {job.message_groups_count} message groups found ({status})")


async def main():
    parser = argparse.ArgumentParser(description='Sublime Rule Hunter - Find and hunt with new rules')
    parser.add_argument('--api-key', help='Your Sublime Security API key')
    parser.add_argument('--region', choices=REGIONS.keys(), help='Your Sublime Security region')
    parser.add_argument('--hunt-lookback', help='Hunt time range (e.g., 7d for 7 days, 12h for 12 hours)')
    parser.add_argument('--rule-lookback', default='14d', help='Time to look back for new rules (e.g., 14d for 14 days, 48h for 48 hours, default: 14d)')
    parser.add_argument('--output', help='Output file name (if not specified, prints to stdout)')
    parser.add_argument('--format', choices=['csv', 'json'], default='json', 
                        help='Output format (json or csv, default: json). CSV format requires a filename or defaults to sublime_rule_hunt_report.csv')
    
    args = parser.parse_args()
    
    hunter = SublimeRuleHunter(
        api_key=args.api_key,
        region=args.region,
        hunt_lookback=args.hunt_lookback,
        rule_lookback=args.rule_lookback,
        output_file=args.output,
        output_format=args.format
    )
    
    await hunter.run()


if __name__ == "__main__":
    asyncio.run(main())