from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Feed:
    id: str
    name: str
    git_url: str
    is_sublime_core: bool = False
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Feed':
        is_sublime_core = data.get('git_url') == 'https://github.com/sublime-security/sublime-rules.git'
        return cls(
            id=data['id'],
            name=data['name'],
            git_url=data['git_url'],
            is_sublime_core=is_sublime_core
        )


@dataclass
class Action:
    id: str
    name: str
    type: str
    is_remediative: bool = False
    
    @classmethod
    def from_dict(cls, data: dict, remediative_types: List[str]) -> 'Action':
        is_remediative = data.get('type') in remediative_types
        return cls(
            id=data['id'],
            name=data['name'],
            type=data['type'],
            is_remediative=is_remediative
        )


@dataclass
class Rule:
    id: str
    name: str
    type: str  # 'detection' or 'triage'
    actions: List[Action]
    feed_id: Optional[str] = None
    active: bool = True
    action_data: List[dict] = None
    auto_review_classification: Optional[str] = None
    auto_review_auto_share: bool = False
    tags: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict, all_actions: List[Action] = None) -> 'Rule':
        # Store raw action data for later processing
        action_data = data.get('actions', [])
        
        # Map action IDs to Action objects if all_actions is provided
        rule_actions = []
        if all_actions:
            for action_info in action_data:
                action = next((a for a in all_actions if a.id == action_info['id']), None)
                if action:
                    rule_actions.append(action)
        
        return cls(
            id=data['id'],
            name=data['name'],
            type=data.get('full_type', '').replace('_rule', ''),
            actions=rule_actions,
            feed_id=data.get('feed_id'),
            active=data.get('active', True),
            action_data=action_data,
            auto_review_classification=data.get('auto_review_classification'),
            auto_review_auto_share=data.get('auto_review_auto_share', False),
            tags=data.get('tags', [])
        )
    
    def populate_actions(self, all_actions: List[Action]):
        """Populate action objects from raw action data"""
        if self.action_data:
            self.actions = []
            for action_info in self.action_data:
                action = next((a for a in all_actions if a.id == action_info['id']), None)
                if action:
                    self.actions.append(action)
    
    @property
    def remediative_actions(self) -> List[Action]:
        return [action for action in self.actions if action.is_remediative]
    
    @property
    def remediative_action_types(self) -> List[str]:
        return [action.type for action in self.remediative_actions]


@dataclass
class Message:
    id: str
    group_id: str
    flagged_rule_ids: List[str]
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        # Extract flagged rule IDs from the message group data
        flagged_rule_ids = []
        for rule in data.get('flagged_rules', []):
            flagged_rule_ids.append(rule['id'])
        
        # Get the first message for basic info
        messages = data.get('messages', [])
        message_id = messages[0]['id'] if messages else data.get('id', '')
        
        return cls(
            id=message_id,
            group_id=data.get('id', ''),
            flagged_rule_ids=flagged_rule_ids,
            created_at=None  # We'll parse this if needed
        )


@dataclass
class CoverageResult:
    rule_id: str
    rule_name: str
    rule_actions: List[str]
    total_message_groups: int
    covered_message_groups: int
    uncovered_message_groups: int
    percent_covered: float | str  # Can be float or "unknown"
    automation_actions: List[str]
    error: Optional[str] = None
    has_message_groups: bool = True  # New field to track if rule had message groups
    
    def to_dict(self) -> dict:
        return {
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'rule_actions': ','.join(self.rule_actions),
            'automation_actions': ','.join(self.automation_actions),
            'total_message_groups': self.total_message_groups,
            'covered_message_groups': self.covered_message_groups,
            'uncovered_message_groups': self.uncovered_message_groups,
            'percent_covered': self.percent_covered if isinstance(self.percent_covered, str) else round(self.percent_covered, 2),
            'has_message_groups': self.has_message_groups,
            'error': self.error
        }