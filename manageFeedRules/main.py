#!/usr/bin/env python3
"""
Email Security Platform: Rule-Level to Automation-Level Action Migration

This script analyzes coverage of detection rules by automation rules and
provides options to migrate rule-level actions to automation-level.
"""

import click
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import Settings
from services import APIClient, SublimeAPI, DataProcessor, APIError
from utils import ReportGenerator, validate_threshold, confirm_action, validate_output_prefix
from models import Action


@click.command()
@click.option('--api-key', help='Sublime API key (or set SUBLIME_API_KEY env var)')
@click.option('--region', default='default', help='Region: default, uk, na-west (or set SUBLIME_REGION env var)')
@click.option('--date-range-days', type=int, default=30, help='Number of days to analyze (default: 30)')
@click.option('--output-prefix', default='rule_coverage_analysis', help='Output file prefix')
@click.option('--all-feeds', is_flag=True, help='Analyze all feeds (not just Sublime Core)')
@click.option('--dry-run', is_flag=True, help='Show what would be modified without making changes')
@click.option('--action-types', default='delete_message,move_to_spam,quarantine_message', 
              help='Comma-separated list of remediative action types')
def main(api_key, region, date_range_days, output_prefix, all_feeds, dry_run, action_types):
    """
    Analyze email security rule coverage and migrate rule-level actions to automation-level.
    
    This tool helps identify detection rules that can have their actions removed because
    automation rules provide equivalent coverage with better accuracy.
    """
    
    try:
        # Validate and setup configuration
        output_prefix = validate_output_prefix(output_prefix)
        remediative_types = [t.strip() for t in action_types.split(',')]
        
        settings = Settings(
            api_key=api_key,
            region=region,
            date_range_days=date_range_days,
            output_prefix=output_prefix,
            all_feeds=all_feeds,
            dry_run=dry_run
        )
        
        # Override default remediative types if provided
        settings.remediative_action_types = remediative_types
        
        # Show configuration
        print("🚀 Starting Rule Coverage Analysis")
        settings.show_config_info()
        
        # Initialize API client
        client = APIClient(settings.base_url, settings.headers)
        api = SublimeAPI(client)
        
        # Test connection
        print("\n🔗 Testing API connection...")
        if not api.test_connection():
            print("❌ Failed to connect to API. Check your API key and region.")
            return 1
        print("✅ API connection successful")
        
        # Step 1: Get feeds and identify target feed
        print("\n📦 Step 1: Identifying feeds...")
        feeds = api.get_feeds()
        sublime_feed = next((f for f in feeds if f.is_sublime_core), None)
        
        if not sublime_feed and not all_feeds:
            print("❌ Sublime Core Feed not found")
            return 1
        
        target_feed_id = None if all_feeds else sublime_feed.id
        target_description = "all feeds" if all_feeds else "Sublime Core Feed"
        print(f"✅ Analyzing {target_description}")
        
        # Step 2: Get actions and identify remediative ones
        print("\n⚙️  Step 2: Identifying remediative actions...")
        all_actions = api.get_actions()
        
        # Update actions with remediative status
        for action in all_actions:
            action.is_remediative = action.type in settings.remediative_action_types
        
        remediative_actions = [a for a in all_actions if a.is_remediative]
        remediative_action_ids = [a.id for a in remediative_actions]
        
        print(f"✅ Found {len(remediative_actions)} remediative actions: {', '.join(a.type for a in remediative_actions)}")
        
        # Step 3: Get automation rules with remediative actions
        print("\n🤖 Step 3: Finding automation rules with remediative actions...")
        automation_rules = api.get_rules_with_actions(
            remediative_action_ids, 'triage', target_feed_id
        )
        
        # Update automation rules with proper action objects
        for rule in automation_rules:
            rule.populate_actions(all_actions)
        
        print(f"✅ Found {len(automation_rules)} automation rules with remediative actions")
        
        # Step 4: Get detection rules with remediative actions
        print("\n🔍 Step 4: Finding detection rules with remediative actions...")
        detection_rules = api.get_rules_with_actions(
            remediative_action_ids, 'detection', target_feed_id
        )
        
        # Update detection rules with proper action objects
        for rule in detection_rules:
            rule.populate_actions(all_actions)
        
        print(f"✅ Found {len(detection_rules)} detection rules with remediative actions")
        
        if not detection_rules:
            print("ℹ️  No detection rules found with remediative actions. Nothing to analyze.")
            return 0
        
        # Step 5-6: Analyze coverage
        print(f"\n📊 Step 5-6: Analyzing coverage for {len(detection_rules)} rules...")
        processor = DataProcessor(api, settings)
        results = processor.analyze_coverage(detection_rules, automation_rules)
        
        # Step 7: Generate reports
        print("\n📄 Step 7: Generating reports...")
        report_gen = ReportGenerator(settings.output_prefix)
        summary_stats = processor.get_summary_stats(results)
        
        json_file = report_gen.generate_json_report(results, summary_stats)
        csv_file = report_gen.generate_csv_report(results)
        
        report_gen.print_summary(summary_stats, json_file, csv_file)
        
        # Step 8: Offer to modify rules
        print("\n🔧 Step 8: Rule modification options")
        
        if not confirm_action("Do you want to remove actions from rules based on coverage threshold?"):
            print("Analysis complete. Check the generated reports.")
            return 0
        
        # Get threshold from user
        while True:
            try:
                threshold_input = input("Enter coverage threshold percentage (50-100): ").strip()
                threshold = validate_threshold(threshold_input)
                break
            except ValueError as e:
                print(f"❌ {e}")
                if not confirm_action("Try again?"):
                    return 0
        
        # Find rules above threshold
        rules_above_threshold = processor.get_rules_above_threshold(results, threshold)
        
        # Ask about rules with no message groups
        include_no_messages = confirm_action("Also remove actions from rules that didn't flag any message groups in this time period?")
        rules_no_messages = []
        if include_no_messages:
            rules_no_messages = processor.get_rules_with_no_message_groups(results)
        
        # Combine the lists
        all_rules_to_modify = rules_above_threshold + rules_no_messages
        
        if not all_rules_to_modify:
            message = f"No rules found with ≥{threshold}% coverage"
            if include_no_messages:
                message += " or with no message groups"
            print(f"{message}.")
            return 0
        
        # Show rules that would be modified
        if rules_above_threshold:
            report_gen.print_rules_for_modification(rules_above_threshold, threshold, "coverage")
        
        if rules_no_messages:
            report_gen.print_rules_for_modification(rules_no_messages, rule_type="no_messages")
        
        # Show combined summary
        print(f"\n📊 SUMMARY:")
        print(f"  - Rules with ≥{threshold}% coverage: {len(rules_above_threshold)}")
        if include_no_messages:
            print(f"  - Rules with no message groups: {len(rules_no_messages)}")
        print(f"  - Total rules to modify: {len(all_rules_to_modify)}")
        
        # Confirm modification
        action_word = "simulate removing" if settings.dry_run else "remove"
        if not confirm_action(f"\nProceed to {action_word} actions from {len(all_rules_to_modify)} rules?"):
            print("Operation cancelled.")
            return 0
        
        # Perform modifications
        print(f"\n{'🧪 Simulating' if settings.dry_run else '🔧 Performing'} rule modifications...")
        
        success_count = 0
        failed_rules = []
        
        for result in all_rules_to_modify:
            rule_name = result.rule_name[:50]
            
            if settings.dry_run:
                print(f"✅ [DRY RUN] Would remove actions from: {rule_name}")
                success_count += 1
            else:
                try:
                    # Find the original rule to get current actions
                    original_rule = next(r for r in detection_rules if r.id == result.rule_id)
                    remediative_action_ids_to_remove = [a.id for a in original_rule.remediative_actions]
                    
                    api.remove_actions_from_rule(
                        result.rule_id, 
                        remediative_action_ids_to_remove,
                        original_rule.actions
                    )
                    print(f"✅ Removed actions from: {rule_name}")
                    success_count += 1
                    
                except Exception as e:
                    print(f"❌ Failed to modify {rule_name}: {str(e)}")
                    failed_rules.append((result.rule_id, result.rule_name, str(e)))
        
        # Summary
        print(f"\n{'Simulation' if settings.dry_run else 'Modification'} complete!")
        print(f"✅ Successfully {'simulated' if settings.dry_run else 'modified'}: {success_count} rules")
        
        if failed_rules:
            print(f"❌ Failed: {len(failed_rules)} rules")
            print("\nFailed rules (manual intervention required):")
            for rule_id, rule_name, error in failed_rules:
                print(f"  - {rule_name} ({rule_id}): {error}")
        
        print(f"\n📊 Reports saved:")
        print(f"  - {json_file}")
        print(f"  - {csv_file}")
        print(f"📁 All outputs in: {Path(json_file).parent}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return 1
    finally:
        # Cleanup
        try:
            client.close()
        except:
            pass
    
    return 0


if __name__ == '__main__':
    sys.exit(main())