from typing import List, Dict, Set
from datetime import datetime, timedelta
from models import Rule, Message, CoverageResult, Action
from .sublime_api import SublimeAPI
from utils.progress import ProgressTracker


class DataProcessor:
    """Core business logic for coverage analysis"""
    
    def __init__(self, api: SublimeAPI, settings):
        self.api = api
        self.settings = settings
    
    def analyze_coverage(self, detection_rules: List[Rule], 
                        automation_rules: List[Rule]) -> List[CoverageResult]:
        """Analyze coverage for all detection rules"""
        results = []
        date_from = datetime.utcnow() - timedelta(days=self.settings.date_range_days)
        
        with ProgressTracker() as progress:
            progress.start(len(detection_rules), "Analyzing rule coverage")
            
            for i, rule in enumerate(detection_rules):
                progress.update(1, f"Processing {rule.name[:30]}...")
                
                try:
                    # Get messages flagged by this rule
                    messages = self.api.get_messages_by_rule(rule.id, date_from)
                    
                    if not messages:
                        # No messages found - this is not an error, just no data
                        result = CoverageResult(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            rule_actions=rule.remediative_action_types,
                            total_messages=0,
                            covered_messages=0,
                            uncovered_messages=0,
                            percent_covered="unknown",
                            automation_actions=self._get_automation_actions(automation_rules),
                            has_messages=False
                        )
                    else:
                        # Calculate coverage
                        result = self._calculate_rule_coverage(rule, messages, automation_rules)
                    
                    results.append(result)
                    
                except Exception as e:
                    # Handle errors gracefully
                    error_result = CoverageResult(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        rule_actions=rule.remediative_action_types,
                        total_messages=0,
                        covered_messages=0,
                        uncovered_messages=0,
                        percent_covered="unknown",
                        automation_actions=self._get_automation_actions(automation_rules),
                        error=str(e),
                        has_messages=False
                    )
                    results.append(error_result)
                    print(f"⚠️  Error processing rule {rule.name}: {str(e)}")
            
            progress.finish("Coverage analysis complete")
        
        return results
    
    def _calculate_rule_coverage(self, rule: Rule, messages: List[Message], 
                               automation_rules: List[Rule]) -> CoverageResult:
        """Calculate coverage for a single rule"""
        total_messages = len(messages)
        covered_messages = 0
        
        # Get all automation rule IDs for quick lookup
        automation_rule_ids = {ar.id for ar in automation_rules}
        automation_rules_dict = {ar.id: ar for ar in automation_rules}
        
        # Track which automation actions actually flagged messages for this rule
        actual_automation_actions = set()
        
        # Check each message to see if it's also flagged by an automation
        for message in messages:
            message_rule_ids = set(message.flagged_rule_ids)
            
            # Check if any of the rules that flagged this message are automations
            flagged_automation_ids = message_rule_ids.intersection(automation_rule_ids)
            if flagged_automation_ids:
                covered_messages += 1
                
                # Collect the actions from the automations that flagged this message
                for automation_id in flagged_automation_ids:
                    automation_rule = automation_rules_dict[automation_id]
                    actual_automation_actions.update(automation_rule.remediative_action_types)
        
        uncovered_messages = total_messages - covered_messages
        percent_covered = (covered_messages / total_messages * 100) if total_messages > 0 else 0.0
        
        return CoverageResult(
            rule_id=rule.id,
            rule_name=rule.name,
            rule_actions=rule.remediative_action_types,
            total_messages=total_messages,
            covered_messages=covered_messages,
            uncovered_messages=uncovered_messages,
            percent_covered=percent_covered,
            automation_actions=list(actual_automation_actions),
            has_messages=True
        )
    
    def _get_automation_actions(self, automation_rules: List[Rule]) -> List[str]:
        """Get all unique automation actions for reporting"""
        automation_actions_set = set()
        for automation_rule in automation_rules:
            automation_actions_set.update(automation_rule.remediative_action_types)
        return list(automation_actions_set)
    
    def get_rules_above_threshold(self, results: List[CoverageResult], 
                                 threshold: float) -> List[CoverageResult]:
        """Filter results to only include rules above coverage threshold"""
        return [
            result for result in results 
            if (isinstance(result.percent_covered, (int, float)) and 
                result.percent_covered >= threshold and 
                result.has_messages and 
                not result.error)
        ]
    
    def get_summary_stats(self, results: List[CoverageResult]) -> Dict[str, any]:
        """Generate summary statistics"""
        total_rules = len(results)
        rules_with_messages = len([r for r in results if r.has_messages and not r.error])
        rules_with_no_messages = len([r for r in results if not r.has_messages and not r.error])
        rules_with_errors = len([r for r in results if r.error])
        
        if rules_with_messages > 0:
            # Only calculate average for rules that actually have messages and numeric coverage
            numeric_results = [r for r in results if r.has_messages and not r.error and isinstance(r.percent_covered, (int, float))]
            avg_coverage = sum(r.percent_covered for r in numeric_results) / len(numeric_results) if numeric_results else 0.0
            total_messages = sum(r.total_messages for r in results if not r.error)
            total_covered = sum(r.covered_messages for r in results if not r.error)
        else:
            avg_coverage = 0.0
            total_messages = 0
            total_covered = 0
        
        return {
            'total_rules_analyzed': total_rules,
            'rules_with_messages': rules_with_messages,
            'rules_with_no_messages': rules_with_no_messages,
            'rules_with_errors': rules_with_errors,
            'average_coverage_percent': round(avg_coverage, 2),
            'total_messages_analyzed': total_messages,
            'total_messages_covered': total_covered,
            'date_range_days': self.settings.date_range_days
        }