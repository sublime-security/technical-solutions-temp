# Sublime Security API Data Exporter

This script pulls data from the Sublime Security API and exports it to an Excel file.

## Features

- Region selection for different API endpoints
- Secure API token input
- Asynchronous data fetching with pagination
- Parallel processing of data chunks
- Excel export with formatted data

## Installation

1. Make sure you have Python 3.7+ installed
2. Clone or download this repository
3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the script with:

```bash
python user_report_export.py
```

The script will:
1. Prompt you to select a region
2. Ask for your API token (input is hidden for security)
3. Export the data to an Excel file in the `output` directory

## Data Fields

The exported Excel file includes the following fields:
- `id`: Message group ID
- `review_status`: Review status
- `review_label`: Review label
- `classification`: Classification
- `state`: State
- `message_count`: Number of messages in the group
- `reporters`: Comma-separated list of all reporters

## Requirements

See `requirements.txt` for the complete list of dependencies.

## Notes

- The script creates an `output` directory if it doesn't exist
- Each export has a timestamp in the filename
- Progress is displayed during the data fetch process