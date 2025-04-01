# Sublime Migration CLI

A command-line utility for migrating configuration between Sublime Security Platform instances.

## Overview

The Sublime Migration CLI enables you to migrate configuration objects between different Sublime Security Platform instances.

## Features

- **Command Categories**:
  - `migrate`: Copy configuration between instances
  
- **Supported Object Types**:
  - Actions
  - Lists
  - Exclusions
  - Feeds
  - Rules (detection and automations)
  - Rule-Action Associations
  - Rule Exclusions

- **Cross-Region Support**: Migrate between any of Sublime's global regions

- **Interactive and JSON Modes**: Human-readable tables or machine-parsable JSON

- **Comprehensive Filtering**: Select specific objects to migrate

- **Dry Run Mode**: Preview migrations before applying changes

## Installation

### Requirements

- Python 3.8 or higher
- Required packages: click, requests, rich, tabulate

### Install from Source

```bash
git clone https://github.com/yourusername/sublime-migration-cli.git
cd sublime-migration-cli
pip install -e .
```

### Install from PyPI

Package not published to PyPI, but if there is interest, let us know!

## Authentication

The CLI supports authentication via:

1. Command-line parameters
2. Environment variables

### Using Environment Variables

```bash
# For source instance
export SUBLIME_API_KEY="your-api-key"
export SUBLIME_REGION="NA_EAST"

# For destination instance (when migrating)
export SUBLIME_DEST_API_KEY="dest-api-key" 
export SUBLIME_DEST_REGION="EU_DUBLIN"
```

### Available Regions

- `NA_EAST`: North America East (Virginia)
- `NA_WEST`: North America West (Oregon)
- `CANADA`: Canada (Montréal)
- `EU_DUBLIN`: Europe (Dublin)
- `EU_UK`: Europe (UK)
- `AUSTRALIA`: Australia (Sydney)

#### Need support for a custom region?

To support a custom region, simply add it with the proper Base URL to the Regions object in `/api/regions.py` -
```
REGIONS: Dict[str, Region] = {
    "CUSTOM": Region(
        code="CUSTOM",
        api_url="https://BASE_URL",
        description="My custom region",
    ),

...
```

## Usage Examples

### Migrating Configuration

```bash
# Migrate all actions between instances
sublime migrate actions --source-api-key KEY1 --source-region NA_EAST \
                        --dest-api-key KEY2 --dest-region EU_DUBLIN

# Migrate only webhook actions
sublime migrate actions --include-types webhook

# Preview a migration without making changes
sublime migrate lists --dry-run

# Migrate specific rules by ID
sublime migrate rules --include-rule-ids id1,id2,id3

# Migrate everything
sublime migrate all

# Migrate everything except feeds
sublime migrate all --skip feeds
```

### Output Formats

```bash
# Default tabular output
sublime migrate rules

# JSON output
sublime migrate rules --format json

# JSON output to a file
sublime migrate rules --format json > rules.json
```

## Project Structure

```
sublime-migration-cli/
├── src/
│   └── sublime_migration_cli/
│       ├── api/               # API communication layer
│       ├── commands/          # CLI command implementations
│       │   └── migrate/       # Commands for migrations
│       ├── presentation/      # Output formatting
│       └── utils/             # Utility functions
└── pyproject.toml             # Project configuration
```

## Development

### Setting Up a Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/sublime-migration-cli.git
cd sublime-migration-cli

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

## Support

For issues or questions, please create an Issue on this repo, or contact support@sublimesecurity.com
