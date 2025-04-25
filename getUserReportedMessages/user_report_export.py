import asyncio
import aiohttp
import pandas as pd
import os
from datetime import datetime
from getpass import getpass
import time

# Region mapping
REGION_MAP = {
    'na-west': ('https://na-west.platform.sublime.security', 'North America West (Oregon)'),
    'na-east': ('https://platform.sublime.security', 'North America East (Virginia)'),
    'canada': ('https://ca.platform.sublime.security', 'Canada (Montréal)'),
    'europe': ('https://eu.platform.sublime.security', 'Europe (Dublin)'),
    'uk': ('https://uk.platform.sublime.security', 'Europe (London)'),
    'australia': ('https://au.platform.sublime.security', 'Australia (Sydney)')
}

# Constants
ENDPOINT_PATH = "/v0/message-groups"
QUERY_PARAMS = "first_message_reported_at__gte=2025-03-01T00%3A00%3A00Z&user_reported=true"
CHUNK_SIZE = 25  # Number of items to request per page


async def fetch_data(session, url, headers, offset=0, limit=CHUNK_SIZE):
    """Fetch data from API with pagination parameters"""
    paginated_url = f"{url}?{QUERY_PARAMS}&offset={offset}&limit={limit}"
    try:
        async with session.get(paginated_url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Error: HTTP {response.status}")
                return None
    except Exception as e:
        print(f"Exception during fetch: {e}")
        return None


def get_earliest_report_timestamp(user_reports):
    """Extract the earliest timestamp from user_reports array"""
    if not user_reports:
        return None
    
    # Extract all timestamps
    timestamps = [report.get('reported_at') for report in user_reports if report.get('reported_at')]
    
    # Return the earliest timestamp if any exist
    return min(timestamps) if timestamps else None


async def process_all_data(base_url, api_token):
    """Process all data from the API using pagination and async requests"""
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json"
    }
    
    all_data = []
    offset = 0
    total = None
    
    async with aiohttp.ClientSession() as session:
        while total is None or offset < total:
            # Create tasks for fetching multiple chunks in parallel
            tasks = []
            for chunk_offset in range(offset, offset + 5 * CHUNK_SIZE, CHUNK_SIZE):
                if total is not None and chunk_offset >= total:
                    break
                task = asyncio.create_task(fetch_data(session, f"{base_url}{ENDPOINT_PATH}", headers, chunk_offset, CHUNK_SIZE))
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks)
            
            # Process results
            for result in results:
                if result and 'message_groups' in result:
                    if total is None:
                        total = result.get('total', 0)
                        print(f"Total records to fetch: {total}")
                    
                    # Process each message group
                    for msg_group in result['message_groups']:
                        # Extract the earliest reported_at timestamp
                        earliest_reported_at = get_earliest_report_timestamp(msg_group.get('user_reports', []))
                        
                        # Extract the required fields
                        processed_data = {
                            'id': msg_group.get('id'),
                            'review_status': msg_group.get('review_status'),
                            'review_label': msg_group.get('review_label'),
                            'classification': msg_group.get('classification'),
                            'state': msg_group.get('state'),
                            'message_count': len(msg_group.get('messages', [])),
                            'reporters': ', '.join([report.get('reporter', '') for report in msg_group.get('user_reports') or []]),
                            'first_reported_at': earliest_reported_at  # Add the new field
                        }
                        all_data.append(processed_data)
            
            # Update offset for next batch
            offset += len(tasks) * CHUNK_SIZE
            print(f"Processed {min(offset, total if total else 0)} of {total if total else 'unknown'} records")
            
            # Small delay to avoid hammering the API
            await asyncio.sleep(0.5)
    
    return all_data


def select_region():
    """Prompt user to select a region"""
    print("Available regions:")
    for i, (key, (_, desc)) in enumerate(REGION_MAP.items(), 1):
        print(f"{i}. {desc} ({key})")
    
    while True:
        try:
            choice = int(input("\nSelect region (1-6): "))
            if 1 <= choice <= len(REGION_MAP):
                region_key = list(REGION_MAP.keys())[choice - 1]
                base_url, region_name = REGION_MAP[region_key]
                print(f"Selected: {region_name} ({base_url})")
                return base_url
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a number.")


async def main():
    print("=== Sublime Security API Data Exporter ===")
    
    # Get region and API token
    base_url = select_region()
    api_token = getpass("\nEnter your API token: ")
    
    print("\nFetching data...")
    start_time = time.time()
    
    # Process all data
    data = await process_all_data(base_url, api_token)
    
    if not data:
        print("No data returned or an error occurred.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Create output directory if it doesn't exist
    os.makedirs('output', exist_ok=True)
    
    # Save to Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_file = f"output/message_groups_{timestamp}.xlsx"
    df.to_excel(excel_file, index=False)
    
    elapsed_time = time.time() - start_time
    print(f"\nExport complete!")
    print(f"Records exported: {len(data)}")
    print(f"File saved: {os.path.abspath(excel_file)}")
    print(f"Time elapsed: {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())