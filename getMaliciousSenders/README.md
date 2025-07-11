# Extract Malicious Sender Emails

This script extracts sender email addresses from malicious messages using the Sublime Security API. It fetches messages with malicious attack score verdict and extracts unique sender emails from the specified time period.

## Installation

1. Clone or download the script files
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

```bash
python main.py --base-url https://platform.sublime.security --api-token YOUR_API_TOKEN
```

### Interactive Mode (No Arguments)

If you don't provide credentials, the script will prompt you:

```bash
python main.py
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--base-url` | Base URL for the Sublime Security API | Interactive prompt |
| `--api-token` | API token for authentication | Interactive prompt (masked) |
| `--days-back` | Number of days to look back | 7 |
| `--output-format` | Output format: `file` or `json` | `file` |
| `--output-file` | Custom output filename (file format only) | `malicious-senders-TIMESTAMP.txt` |

### Examples

**Basic file output with custom lookback period:**
```bash
python main.py --base-url https://platform.sublime.security --api-token YOUR_TOKEN --days-back 14
```

**JSON output to console:**
```bash
python main.py --base-url https://platform.sublime.security --api-token YOUR_TOKEN --output-format json
```

**Custom output filename:**
```bash
python main.py --base-url https://platform.sublime.security --api-token YOUR_TOKEN --output-file my-malicious-senders.txt
```

**Different region (example):**
```bash
python main.py --base-url https://eu.platform.sublime.security --api-token YOUR_TOKEN
```

## Output Formats

### File Output (Default)
Creates a text file with one email address per line:
```
malicious-sender@example.com
another-sender@suspicious.com
phishing@fake-domain.com
```

### JSON Output
Outputs structured JSON to console:
```json
{
  "malicious_sender_emails": [
    "malicious-sender@example.com",
    "another-sender@suspicious.com",
    "phishing@fake-domain.com"
  ]
}
```

## API Requirements

The script queries the Sublime Security API with the following parameters:
- `attack_score_verdict__is=malicious`
- `attack_surface_reduction__is=include`
- `created_at__gte=<calculated-date>`
- `flagged__eq=true`
- `limit=500`

## Sublime Security API Endpoints

- **North America East (Virginia)**: `https://platform.sublime.security`
- **North America West (Oregon)**: `https://na-west.platform.sublime.security`
- **Europe (Dublin)**: `https://eu.platform.sublime.security`
- **Europe (UK)**: `https://uk.platform.sublime.security`
- **Canada (Montréal)**: `https://ca.platform.sublime.security`
- **Australia (Sydney)**: `https://au.platform.sublime.security`

## Troubleshooting

**Authentication Issues:**
- Verify your API token is valid and has the necessary permissions
- Check that you're using the correct base URL for your region

**No Results:**
- Adjust the `--days-back` parameter to look further back
- Verify that there are malicious messages in your environment for the specified period

**Network Errors:**
- Check your internet connection
- Verify the base URL is accessible

## Dependencies

- `requests>=2.31.0`: HTTP library for API calls
- `urllib3>=2.0.0`: HTTP client library (used by requests)
