from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .api_client import APIClient, APIError
from models import Feed, Action, Rule, Message


class SublimeAPI:
    """Sublime-specific API operations"""
    
    def __init__(self, client: APIClient):
        self.client = client
    
    def get_feeds(self) -> List[Feed]:
        """Get all feeds"""
        try:
            response = self.client.get('/v1/feeds')
            feeds = []
            for feed_data in response.get('feeds', []):
                feeds.append(Feed.from_dict(feed_data))
            return feeds
        except APIError as e:
            raise APIError(f"Failed to get feeds: {str(e)}")
    
    def get_actions(self) -> List[Action]:
        """Get all actions"""
        try:
            response = self.client.get('/v1/actions')
            actions = []
            # We'll set remediative types later when we have the settings
            for action_data in response:
                actions.append(Action.from_dict(action_data, []))
            return actions
        except APIError as e:
            raise APIError(f"Failed to get actions: {str(e)}")
    
    def get_rules_with_actions(self, action_ids: List[str], rule_type: str, 
                              feed_id: Optional[str] = None) -> List[Rule]:
        """Get rules that have specific actions assigned"""
        rules = []
        
        for action_id in action_ids:
            try:
                params = {
                    'action': action_id,
                    'type': rule_type,
                    'limit': 500,
                    'offset': 0
                }
                
                if feed_id:
                    params['feed'] = feed_id
                
                # Paginate through all results
                while True:
                    response = self.client.get('/v1/rules', params=params)
                    rule_data_list = response.get('rules', [])
                    
                    if not rule_data_list:
                        break
                    
                    # We'll populate actions later when we have all_actions available
                    for rule_data in rule_data_list:
                        rule = Rule.from_dict(rule_data)
                        # Only add if not already in the list (deduplication)
                        if not any(r.id == rule.id for r in rules):
                            rules.append(rule)
                    
                    # Check if there are more pages
                    if len(rule_data_list) < params['limit']:
                        break
                    
                    params['offset'] += params['limit']
                    
            except APIError as e:
                print(f"⚠️  Warning: Failed to get rules for action {action_id}: {str(e)}")
                continue
        
        return rules
    
    def get_messages_by_rule(self, rule_id: str, date_from: datetime, 
                           progress_callback=None) -> List[Message]:
        """Get message groups flagged by a specific rule (with pagination)"""
        messages = []
        
        try:
            params = {
                'flagged': 'true',
                'flagged_rule_id__is': rule_id,
                'user_reported': 'false',
                'created_at__gte': date_from.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'limit': 100,  # Reasonable page size
                'offset': 0
            }
            
            # Paginate through all results
            while True:
                response = self.client.get('/v0/message-groups', params=params)
                message_groups = response.get('message_groups', [])
                
                if not message_groups:
                    break
                
                for group_data in message_groups:
                    message = Message.from_dict(group_data)
                    messages.append(message)
                
                if progress_callback:
                    progress_callback(len(message_groups))
                
                # Check if there are more pages
                total = response.get('total', 0)
                if params['offset'] + len(message_groups) >= total:
                    break
                
                params['offset'] += params['limit']
                
        except APIError as e:
            raise APIError(f"Failed to get messages for rule {rule_id}: {str(e)}")
        
        return messages
    
    def remove_actions_from_rule(self, rule_id: str, action_ids_to_remove: List[str], 
                            current_actions: List[Action], rule_data: dict) -> bool:
        """Remove specific actions from a rule while preserving auto-review settings"""
        try:
            # Get current action IDs and remove the ones we want to remove
            current_action_ids = [action.id for action in current_actions]
            remaining_action_ids = [aid for aid in current_action_ids if aid not in action_ids_to_remove]

            # Prepare patch data with auto-review fields from current rule
            patch_data = {
                "action_ids": remaining_action_ids,
                "overwrite_actions": True,
                "overwrite_auto_review_classification": True,
                "tags": rule_data.get("tags", [])
            }
            
            # Include auto-review classification if present
            # auto_review_classification = rule_data.get("auto_review_classification")
            # if auto_review_classification:
            #     patch_data["auto_review_classification"] = auto_review_classification
            #     patch_data["overwrite_auto_review_classification"] = False  # Don't clear existing classification
            # else:
            #     patch_data["auto_review_classification"] = None
            #     # patch_data["overwrite_auto_review_classification"] = True
                
            # # Include auto-review auto-share setting
            # patch_data["auto_review_auto_share"] = rule_data.get("auto_review_auto_share", False)

            print(patch_data)
            self.client.patch(f'/v1/rules/{rule_id}', patch_data)
            return True
                
        except APIError as e:
            raise APIError(f"Failed to remove actions from rule {rule_id}: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test API connection and permissions"""
        try:
            self.client.get('/v1/feeds')
            return True
        except APIError:
            return False