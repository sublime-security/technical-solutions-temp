# Sublime Rule Analysis Tool

A Python tool for analyzing email security rule coverage to aid in the removal of rule-level actions in favor of automation-level actions, for better accuracy and reduced false positives.

## Overview

This tool helps email security platform customers migrate from legacy rule-level actions to automation-level actions by:

1. Analyzing coverage of detection rules by automation rules
2. Generating detailed reports (JSON/CSV) 
3. Safely removing rule-level actions where automation coverage is sufficient

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

### Environment Variables (Recommended)

```bash
export SUBLIME_API_KEY="your-api-key-here"
export SUBLIME_REGION="uk"  # or "default", "na-west"
export SUBLIME_DATE_RANGE_DAYS="30"
export SUBLIME_OUTPUT_PREFIX="my_analysis"
```

### Command Line Options

All configuration can be provided via command line:

```bash
python main.py --api-key "your-key" --region "uk" --date-range-days 30
```

## Usage

### Basic Analysis (Sublime Core Feed Only)

```bash
python main.py
```

### Analyze All Feeds

```bash
python main.py --all-feeds
```

### Dry Run (Preview Changes)

```bash
python main.py --dry-run
```

### Custom Date Range and Output

```bash
python main.py --date-range-days 60 --output-prefix "quarterly_analysis"
```

## Regions

The tool supports multiple regions. Add new regions in `config/regions.yaml`:

```yaml
regions:
  default: platform.sublime.security
  uk: uk.platform.sublime.security
  na-west: na-west.platform.sublime.security
  custom: my-custom-domain.sublime.security  # Add new regions here
```

## Reports

All output files are automatically saved to the `output/` directory, which is created if it doesn't exist.

**Example output structure:**
```
output/
├── rule_coverage_analysis_2025-06-02.json
├── rule_coverage_analysis_2025-06-02.csv
├── quarterly_analysis_2025-06-02.json
└── quarterly_analysis_2025-06-02.csv
```

## Examples

### Environment Variable Configuration
```bash
# Set environment variables
export SUBLIME_API_KEY="sk-abc123..."
export SUBLIME_REGION="uk"

# Run analysis with environment configuration
python main.py
# Output: "ℹ️ Using configured environment variables: SUBLIME_API_KEY, SUBLIME_REGION"
```

### Command Line Override
```bash
# Environment has SUBLIME_REGION="uk", but override to na-west
python main.py --region na-west --all-feeds --dry-run
```

### Typical Session
```bash
$ python main.py

🚀 Starting Rule Coverage Analysis
ℹ️  Using configured environment variables: SUBLIME_API_KEY, SUBLIME_REGION
🌍 Region: uk (https://uk.platform.sublime.security)
📅 Date range: 30 days
📦 Analyzing: Sublime Core Feed only

🔗 Testing API connection...
✅ API connection successful

📦 Step 1: Identifying feeds...
✅ Analyzing Sublime Core Feed

⚙️  Step 2: Identifying remediative actions...
✅ Found 3 remediative actions: quarantine_message, move_to_spam, delete_message

🤖 Step 3: Finding automation rules with remediative actions...
✅ Found 12 automation rules with remediative actions

🔍 Step 4: Finding detection rules with remediative actions...
✅ Found 45 detection rules with remediative actions

📊 Step 5-6: Analyzing coverage for 45 rules...
Analyzing rule coverage: 100%|██████████| 45/45 [02:15<00:00]

📄 Step 7: Generating reports...

============================================================
📊 COVERAGE ANALYSIS SUMMARY
============================================================
📋 Total rules analyzed: 45
📧 Rules with messages: 38
⚠️  Rules with errors: 2
📅 Date range: 30 days
📈 Average coverage: 87.3%
🔢 Total messages analyzed: 1,247
✅ Messages covered by automations: 1,089
```

## Extending the Tool

### Adding New Regions
Edit `config/regions.yaml` to add new regions.

### Custom Analysis Logic
Extend the `DataProcessor` class in `services/data_processor.py`.

### New Output Formats
Add methods to the `ReportGenerator` class in `utils/output.py`.

## Troubleshooting

### Authentication Errors
```bash
❌ Failed to connect to API. Check your API key and region.
```
- Verify `SUBLIME_API_KEY` environment variable or `--api-key` parameter
- Ensure API key has necessary permissions

### No Rules Found
```bash
ℹ️  No detection rules found with remediative actions. Nothing to analyze.
```
- Try `--all-feeds` to analyze beyond Sublime Core Feed
- Verify the target feed has rules with the specified action types

### Region Issues
```bash
❌ Unknown region: xyz. Available: ['default', 'uk', 'na-west']
```
- Check available regions in `config/regions.yaml`
- Use `--region` parameter with a valid region name
