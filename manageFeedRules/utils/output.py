import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from models import CoverageResult


class ReportGenerator:
    """Output formatting for JSON and CSV reports"""
    
    def __init__(self, output_prefix: str):
        self.output_prefix = output_prefix
        self.timestamp = datetime.now().strftime('%Y-%m-%d')
        
        # Create output directory
        self.output_dir = Path('output')
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_json_report(self, results: List[CoverageResult], 
                           summary_stats: Dict[str, Any]) -> str:
        """Generate comprehensive JSON report"""
        filename = f"{self.output_prefix}_{self.timestamp}.json"
        filepath = self.output_dir / filename
        
        # Prepare data for JSON output
        json_data = {
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'report_type': 'rule_coverage_analysis',
                'version': '1.0'
            },
            'summary': summary_stats,
            'results': [result.to_dict() for result in results]
        }
        
        # Write JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def generate_csv_report(self, results: List[CoverageResult]) -> str:
        """Generate CSV report optimized for Excel/Google Sheets"""
        filename = f"{self.output_prefix}_{self.timestamp}.csv"
        filepath = self.output_dir / filename
        
        # Define CSV columns for easy analysis
        fieldnames = [
            'rule_id',
            'rule_name', 
            'rule_actions',
            'automation_actions',
            'total_messages',
            'covered_messages',
            'uncovered_messages',
            'percent_covered',
            'has_messages',
            'error'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                row_data = result.to_dict()
                # Ensure all required fields are present
                for field in fieldnames:
                    if field not in row_data:
                        row_data[field] = ''
                writer.writerow(row_data)
        
        return str(filepath)
    
    def print_summary(self, summary_stats: Dict[str, Any], 
                     json_filename: str, csv_filename: str):
        """Print summary statistics to console"""
        print("\n" + "="*60)
        print("📊 COVERAGE ANALYSIS SUMMARY")
        print("="*60)
        print(f"📋 Total rules analyzed: {summary_stats['total_rules_analyzed']}")
        print(f"📧 Rules with messages: {summary_stats['rules_with_messages']}")
        print(f"⚠️  Rules with errors: {summary_stats['rules_with_errors']}")
        print(f"📅 Date range: {summary_stats['date_range_days']} days")
        print(f"📈 Average coverage: {summary_stats['average_coverage_percent']}%")
        print(f"🔢 Total messages analyzed: {summary_stats['total_messages_analyzed']}")
        print(f"✅ Messages covered by automations: {summary_stats['total_messages_covered']}")
        print()
        print(f"📄 JSON report: {json_filename}")
        print(f"📊 CSV report: {csv_filename}")
        print(f"📁 Output directory: {Path(json_filename).parent}")
        print("="*60)
    
    def print_rules_for_modification(self, rules: List[CoverageResult], threshold: float):
        """Print rules that would be modified with pagination"""
        if not rules:
            print(f"\n🔍 No rules found with ≥{threshold}% coverage.")
            return
        
        print(f"\n📋 Rules with ≥{threshold}% coverage that would be modified:")
        print("-" * 80)
        print(f"{'Rule Name':<40} {'Coverage':<10} {'Messages':<10} {'Actions'}")
        print("-" * 80)
        
        for i, rule in enumerate(rules):
            actions_str = ','.join(rule.rule_actions)
            coverage_str = f"{rule.percent_covered:>7.1f}%" if isinstance(rule.percent_covered, (int, float)) else f"{rule.percent_covered:>9}"
            print(f"{rule.rule_name[:39]:<40} {coverage_str} {rule.total_messages:>8} {actions_str}")
            
            # Pause every 20 rules for large lists
            if (i + 1) % 20 == 0 and i < len(rules) - 1:
                print(f"\n--- Press SPACE to continue ({i+1}/{len(rules)} shown) ---")
                while True:
                    key = input().strip()
                    if key == ' ' or key == '':
                        break
                    elif key.lower() in ['q', 'quit']:
                        print("Cancelled.")
                        return
                print()
        
        print("-" * 80)
        print(f"Total: {len(rules)} rules would be modified")


def show_paged_output(lines: List[str], title: str = "Output"):
    """Display content with pagination support"""
    print(f"\n{title}")
    print("-" * len(title))
    
    page_size = 20
    for i in range(0, len(lines), page_size):
        page_lines = lines[i:i + page_size]
        for line in page_lines:
            print(line)
        
        if i + page_size < len(lines):
            print(f"\n--- Press SPACE to continue ({i + page_size}/{len(lines)} shown) ---")
            while True:
                key = input().strip()
                if key == ' ' or key == '':
                    break
                elif key.lower() in ['q', 'quit']:
                    return
            print()