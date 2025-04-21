# Sublime Rule Hunter

A Python script that identifies newly added rules in the Sublime Security Core Feed, hunts with them in your environment, and reports on the number of messages flagged by each new rule.

## Features

- Automatically identifies newly added rules in the Sublime Core Feed
- Performs hunts with the MQL source code of each new rule
- Allows configurable hunt time ranges using simple lookback periods
- Polls for hunt job completion
- Generates a CSV report

## Prerequisites

- Python 3.7 or higher
- Sublime Security API access
- Valid API key with permissions to:
  - Access feeds and rules
  - Start and monitor hunt jobs

## Installation

1. Clone this repository or download the script file.

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the script with the following command:

```bash
python main.py [OPTIONS]
```

### Command Line Options

- `--api-key`: Your Sublime Security API key
- `--region`: Your Sublime Security region (NA_WEST, NA_EAST, CANADA, EU_DUBLIN, EU_UK, AUSTRALIA)
- `--hunt-lookback`: Hunt time range (e.g., 7d for 7 days, 12h for 12 hours)
- `--rule-lookback`: Days to look back for new rules (default: 14)
- `--output`: Output file name (default: sublime_rule_hunt_report.csv)

### Interactive Mode

If you don't provide the API key or region via command line arguments, the script will prompt you to enter them interactively.

Similarly, if you don't provide a lookback period, you'll be prompted to choose one of the following options:
1. Last 24 hours
2. Last 7 days
3. Last 30 days
4. Custom period

## Output

The script generates a CSV report with the following columns:

- **Rule Name**: The name of the rule
- **Rule Severity**: The severity level of the rule (high, medium, low, or unknown)
- **MessageGroupsCount**: The number of message groups flagged by the rule
- **Hunt Status**: The status of the hunt job (COMPLETED or ERROR)

## Example

```bash
python sublime_rule_hunter.py --region NA_WEST --hunt-lookback 7d --output recent_rules_report.csv
```

This will:
1. Prompt for your API key if not stored
2. Look for rules added in the last 14 days (default)
3. Run hunts for the past 7 days with those rules
4. Generate a report named "recent_rules_report.csv"

## Troubleshooting

If you encounter issues:

1. Verify your API key has the necessary permissions
2. Check your network connectivity to the Sublime Security API
3. For hunt jobs with ERROR status, check the console output for error messages

## License

This script is provided as-is with no warranty. Use at your own risk.