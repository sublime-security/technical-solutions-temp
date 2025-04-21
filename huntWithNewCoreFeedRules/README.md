# Sublime Rule Hunter

A Python script that identifies newly added rules in the Sublime Security Core Feed, hunts with them in your environment, and reports on the number of messages flagged by each new rule.

## Features

- Automatically identifies newly added rules in the Sublime Core Feed
- Performs hunts with the MQL source code of each new rule
- Allows configurable hunt time ranges using simple lookback periods
- Polls for hunt job completion
- Generates reports in JSON or CSV format
- Provides direct links to flagged messages in the Sublime console

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
- `--rule-lookback`: Days to look back for new rules (default: 14d)
- `--output`: Output file name (default: prints to stdout for JSON; sublime_rule_hunt_report.csv for CSV)
- `--format`: Output format (json or csv, default: json)

### Interactive Mode

If you don't provide the API key or region via command line arguments, the script will prompt you to enter them interactively.

## Output

### JSON Output (Default)

The script generates a JSON report with the following structure:

```json
[
  {
    "ruleName": "Detect suspicious domain",
    "ruleSeverity": "critical",
    "messageGroupsCount": 2,
    "huntStatus": "COMPLETED",
    "ruleURL": "https://platform.sublime.security/feeds/e532a7dc-cf2d-4c2b-b4a3-936f5567e757/rules/7cf5585e-8be9-5286-8977-763ec7ceaf33",
    "samples": [
      "https://platform.sublime.security/messages/f97f223a6fe54d7b95373feb38aab5efc7cf842805111df75c6035fa28da3d3c",
      "https://platform.sublime.security/messages/74573c6bd3a30f2e23ae301579fe51955cefdb79b456491c106c74d79ebb839e"
    ]
  },
  {
    "ruleName": "Detect suspicious senders",
    "ruleSeverity": "high",
    "messageGroupsCount": 2,
    "huntStatus": "COMPLETED",
    "ruleURL": "https://platform.sublime.security/feeds/e532a7dc-cf2d-4c2b-b4a3-936f5567e757/rules/97830ff8-f63e-53ea-bf63-982ed8639915",
    "samples": [
      "https://platform.sublime.security/messages/f97f223a6fe54d7b95373feb38aab5efc7cf842805111df75c6035fa28da3d3c",
      "https://platform.sublime.security/messages/74573c6bd3a30f2e23ae301579fe51955cefdb79b456491c106c74d79ebb839e"
    ]
  }
]
```

The JSON output includes:
- **ruleName**: The name of the rule
- **ruleSeverity**: The severity level of the rule (high, medium, low, critical, or unknown)
- **messageGroupsCount**: The number of message groups flagged by the rule
- **huntStatus**: The status of the hunt job (COMPLETED or ERROR)
- **ruleURL**: URL to view the rule in the Sublime console
- **samples**: Links to up to 5 sample message groups flagged by the rule

### CSV Output

When using the CSV format, the script generates a CSV file with the following columns:
- **ruleName**: The name of the rule
- **ruleSeverity**: The severity level of the rule
- **messageGroupsCount**: The number of message groups flagged by the rule
- **huntStatus**: The status of the hunt job
- **ruleURL**: URL to view the rule in the Sublime console
- **samples**: Comma-separated list of sample message group URLs

## Example Commands

### Generate JSON output to stdout
```bash
python main.py --region NA_WEST --hunt-lookback 7d
```

### Save JSON output to a file
```bash
python main.py --region NA_WEST --hunt-lookback 7d --output recent_rules_report.json
```

### Generate a CSV report
```bash
python main.py --region NA_WEST --hunt-lookback 7d --format csv --output recent_rules_report.csv
```

This will:
1. Prompt for your API key if not provided
2. Look for rules added in the last 14 days (default)
3. Run hunts for the past 7 days with those rules
4. Generate a report in the specified format

## Troubleshooting

If you encounter issues:

1. Verify your API key has the necessary permissions
2. Check your network connectivity to the Sublime Security API
3. For hunt jobs with ERROR status, check the console output for error messages

## License

This script is provided as-is with no warranty. Use at your own risk.