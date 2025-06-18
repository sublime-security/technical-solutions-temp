"""Model for Sublime Security Action."""
from dataclasses import dataclass
from typing import Dict, Optional, Any


@dataclass
class Action:
    """Represents an action in the Sublime Security Platform."""

    id: str
    name: str
    type: str
    active: bool
    config: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Action":
        """Create an Action instance from a dictionary.
        
        Args:
            data: Dictionary containing action data
            
        Returns:
            Action: New Action instance
        """
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type", ""),
            active=data.get("active", False),
            config=data.get("config"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
    
    def to_dict(self, include_sensitive: bool = False) -> Dict:
        """Convert the action to a dictionary.
        
        Args:
            include_sensitive: Whether to include sensitive information
            
        Returns:
            Dict: Dictionary representation of the action
        """
        result = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "active": self.active
        }
        
        # Include timestamps if available
        if self.created_at:
            result["created_at"] = self.created_at
        if self.updated_at:
            result["updated_at"] = self.updated_at
            
        # Handle config with redaction if needed
        if self.config:
            if include_sensitive:
                result["config"] = self.config
            else:
                result["config"] = self._redact_config(self.config.copy() if isinstance(self.config, dict) else self.config)
        
        return result
    
    def _redact_config(self, config: Any) -> Any:
        """Redact sensitive information from the action configuration.
        
        Args:
            config: Action configuration (can be dict, list, or scalar)
            
        Returns:
            Redacted configuration
        """
        if not isinstance(config, dict):
            return config
            
        # Make a copy to avoid modifying the original
        redacted_config = config.copy()
        
        # Handle webhook actions specially
        if self.type == "webhook":
            # Redact the webhook secret
            if "secret" in redacted_config:
                redacted_config["secret"] = "[REDACTED]"
                
            # Redact auth info in the endpoint URL
            if "endpoint" in redacted_config and isinstance(redacted_config["endpoint"], str):
                if "@" in redacted_config["endpoint"]:
                    # URL contains auth info (e.g. https://username:password@example.com)
                    parts = redacted_config["endpoint"].split("@", 1)
                    if "://" in parts[0]:
                        protocol_auth = parts[0].split("://", 1)
                        redacted_config["endpoint"] = f"{protocol_auth[0]}://[REDACTED]@{parts[1]}"
            
            # Redact custom headers that might contain auth tokens
            if "custom_headers" in redacted_config and isinstance(redacted_config["custom_headers"], list):
                for i, header in enumerate(redacted_config["custom_headers"]):
                    if isinstance(header, dict):
                        # Headers that likely contain sensitive information
                        sensitive_headers = {
                            "authorization", "x-api-key", "api-key", "token", 
                            "x-auth", "auth", "secret", "password", "key"
                        }
                        if "name" in header and "value" in header:
                            header_name = header["name"].lower()
                            if any(sensitive in header_name for sensitive in sensitive_headers):
                                redacted_config["custom_headers"][i] = {
                                    **header,
                                    "value": "[REDACTED]"
                                }
        
        # Generic redaction for any config with sensitive keys
        sensitive_keys = {"secret", "password", "token", "api_key", "key", "auth"}
        for key in list(redacted_config.keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                redacted_config[key] = "[REDACTED]"
        
        return redacted_config