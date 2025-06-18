"""Export actions from Sublime Security instance."""
import os
from typing import Dict, List, Optional, Set
import click

from sublime_migration_cli.api.client import get_api_client_from_env_or_args
from sublime_migration_cli.models.action import Action
from sublime_migration_cli.presentation.base import CommandResult
from sublime_migration_cli.presentation.factory import create_formatter
from sublime_migration_cli.utils.api import PaginatedFetcher
from sublime_migration_cli.utils.filtering import filter_by_creator
from sublime_migration_cli.utils.errors import handle_api_error
from sublime_migration_cli.commands.export.utils import (
    sanitize_filename, resolve_filename_collision, write_resource_file
)


# Action types to exclude (system actions)
EXCLUDED_ACTION_TYPES = {
    "quarantine_message", 
    "auto_review", 
    "move_to_spam", 
    "delete_message"
}


def export_actions_impl(api_key=None, region=None, output_dir="./sublime-export/actions",
                       output_format="yaml", include_sensitive=False, formatter=None):
    """Implementation for exporting actions.
    
    Args:
        api_key: API key for the instance
        region: Region for the instance
        output_dir: Directory to export actions to
        output_format: Output format (yaml or json)
        include_sensitive: Whether to include sensitive information
        formatter: Output formatter
        
    Returns:
        Dict: Export results with counts
    """
    if formatter is None:
        formatter = create_formatter("table")
    
    try:
        # Create API client
        client = get_api_client_from_env_or_args(api_key, region)
        
        # Fetch all actions
        fetcher = PaginatedFetcher(client, formatter)
        
        with formatter.create_progress("Fetching actions...") as (progress, task):
            all_actions = fetcher.fetch_all("/v1/actions")
            progress.update(task, advance=1)
        
        if not all_actions:
            return {"exported": 0, "failed": 0, "redacted": 0}
        
        # Filter out system action types
        user_actions = [
            action for action in all_actions 
            if action.get("type") not in EXCLUDED_ACTION_TYPES
        ]
        
        if not user_actions:
            return {"exported": 0, "failed": 0, "redacted": 0}
        
        # Track exported files to avoid collisions
        existing_files = set()
        exported_count = 0
        failed_count = 0
        redacted_count = 0
        
        extension = ".yml" if output_format == "yaml" else ".json"
        
        with formatter.create_progress("Exporting actions...", total=len(user_actions)) as (progress, task):
            for i, action_data in enumerate(user_actions):
                try:
                    # Check if the action has potentially sensitive information
                    has_sensitive = False
                    if action_data.get("type") == "webhook" and isinstance(action_data.get("config"), dict):
                        config = action_data.get("config")
                        sensitive_fields = {"secret", "password", "token", "api_key", "key", "auth"}
                        if "secret" in config or "custom_headers" in config:
                            has_sensitive = True
                        elif any(sensitive in key.lower() for sensitive in sensitive_fields for key in config.keys()):
                            has_sensitive = True
                    
                    # Convert action to export format
                    export_data = convert_action_to_export_format(action_data, include_sensitive)
                    
                    # Track redacted actions
                    if not include_sensitive and has_sensitive:
                        redacted_count += 1
                    
                    # Generate filename
                    base_name = sanitize_filename(action_data.get("name", "unnamed-action"))
                    filename = resolve_filename_collision(
                        base_name, existing_files, action_data.get("id", ""), extension
                    )
                    existing_files.add(filename)
                    
                    # Write file
                    file_path = os.path.join(output_dir, filename)
                    write_resource_file(export_data, file_path, output_format)
                    
                    exported_count += 1
                    
                except Exception as e:
                    error = handle_api_error(e)
                    formatter.output_error(
                        f"Failed to export action '{action_data.get('name', 'unknown')}': {error.message}"
                    )
                    failed_count += 1
                
                progress.update(task, completed=i+1)
        
        return {
            "exported": exported_count, 
            "failed": failed_count,
            "redacted": redacted_count
        }
        
    except Exception as e:
        error = handle_api_error(e)
        formatter.output_error(f"Failed to export actions: {error.message}")
        return {"exported": 0, "failed": 0, "redacted": 0}


def convert_action_to_export_format(action: Dict, include_sensitive: bool = False) -> Dict:
    """Convert an action object to export format.
    
    Args:
        action: Action object from API
        include_sensitive: Whether to include sensitive information
        
    Returns:
        Dict: Action in export format
    """
    # Convert to Action model
    action_model = Action.from_dict(action)
    
    # Get dictionary with or without sensitive information
    action_dict = action_model.to_dict(include_sensitive=include_sensitive)
    
    # Create export data with required fields
    export_data = {
        "name": action_dict["name"],
        "type": action_dict["type"],
        "active": action_dict["active"]
    }
    
    # Add description if present
    if action.get("description"):
        export_data["description"] = action["description"]
    
    # Add config if present
    if "config" in action_dict:
        export_data["config"] = action_dict["config"]
    
    # Add any other relevant fields, excluding system-generated ones
    excluded_fields = {
        "id", "org_id", "created_at", "updated_at", "created_by_user_id",
        "created_by_user_name", "created_by_org_id", "created_by_org_name"
    }
    
    for key, value in action.items():
        if key not in excluded_fields and key not in export_data and value is not None:
            export_data[key] = value
    
    return export_data


@click.command()
@click.option("--api-key", help="API key for authentication")
@click.option("--region", help="Region to connect to")
@click.option("--output-dir", "-o", default="./sublime-export", 
              help="Output directory (default: ./sublime-export)")
@click.option("--format", "output_format", type=click.Choice(["yaml", "json"]), 
              default="yaml", help="Output format (default: yaml)")
@click.option("--include-sensitive", is_flag=True, 
              help="Include sensitive information like secrets and passwords")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def actions(api_key, region, output_dir, output_format, include_sensitive, verbose):
    """Export actions from a Sublime Security instance.
    
    This command exports all user-created actions to local files.
    System actions (quarantine, auto-review, etc.) are excluded by default.
    Sensitive information like webhook secrets is redacted by default.
    
    Examples:
        # Export actions with redacted secrets (default)
        sublime export actions
        
        # Export actions including sensitive information
        sublime export actions --include-sensitive
        
        # Export to specific directory in JSON format
        sublime export actions --output-dir ./my-export --format json
    """
    formatter = create_formatter("table")
    
    # Create the actions subdirectory within the export directory
    actions_dir = os.path.join(output_dir, "actions")
    os.makedirs(actions_dir, exist_ok=True)
    
    # Export actions
    result = export_actions_impl(api_key, region, actions_dir, output_format, include_sensitive, formatter)
    
    # Display results
    if result["exported"] > 0:
        success_message = f"Successfully exported {result['exported']} actions to {actions_dir}"
        if result.get("redacted", 0) > 0 and not include_sensitive:
            success_message += f" ({result['redacted']} with redacted secrets)"
        formatter.output_success(success_message)
    
    if result.get("failed", 0) > 0:
        formatter.output_error(f"{result['failed']} actions failed to export")
    
    if result["exported"] == 0 and result.get("failed", 0) == 0:
        formatter.output_success("No user-created actions found to export")