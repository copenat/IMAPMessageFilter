"""Filter engine for IMAP Message Filter."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

import yaml
from pydantic import BaseModel, Field, field_validator


class FilterOperator(str, Enum):
    """Supported filter operators."""
    CONTAINS = "contains"
    IS = "is"
    STARTS_WITH = "starts with"
    ENDS_WITH = "ends with"
    DOESNT_CONTAIN = "doesn't contain"
    GREATER_THAN = "greater than"
    LESS_THAN = "less than"
    EQUALS = "equals"
    NOT_EQUALS = "not equals"


class FilterAction(str, Enum):
    """Supported filter actions."""
    MOVE = "move"
    DELETE = "delete"
    MARK = "mark"
    COPY = "copy"


class FilterField(str, Enum):
    """Supported filter fields."""
    FROM = "from"
    TO = "to"
    SUBJECT = "subject"
    BODY = "body"
    DATE = "date"
    SIZE = "size"
    CC = "cc"
    BCC = "bcc"
    HAS_ATTACHMENT = "has_attachment"


class FilterCondition(BaseModel):
    """A single filter condition."""
    
    field: FilterField = Field(..., description="Field to match against")
    operator: FilterOperator = Field(..., description="Comparison operator")
    value: str = Field(..., description="Value to compare against")
    
    @field_validator('field')
    @classmethod
    def validate_field(cls, v: str) -> FilterField:
        """Validate filter field."""
        try:
            return FilterField(v.lower())
        except ValueError:
            raise ValueError(f'Invalid field: {v}. Valid fields: {[f.value for f in FilterField]}')
    
    @field_validator('operator')
    @classmethod
    def validate_operator(cls, v: str) -> FilterOperator:
        """Validate filter operator."""
        try:
            return FilterOperator(v.lower())
        except ValueError:
            raise ValueError(f'Invalid operator: {v}. Valid operators: {[op.value for op in FilterOperator]}')


class FilterActionConfig(BaseModel):
    """Configuration for a filter action."""
    
    type: FilterAction = Field(..., description="Action type")
    folder: Optional[str] = Field(None, description="Target folder for move/copy actions")
    flag: Optional[str] = Field(None, description="Flag for mark actions")
    
    @field_validator('type')
    @classmethod
    def validate_action_type(cls, v: str) -> FilterAction:
        """Validate action type."""
        try:
            return FilterAction(v.lower())
        except ValueError:
            raise ValueError(f'Invalid action type: {v}. Valid actions: {[a.value for a in FilterAction]}')
    
    @field_validator('folder')
    @classmethod
    def validate_folder(cls, v: Optional[str], info) -> Optional[str]:
        """Validate folder is provided for move/copy actions."""
        if info.data.get('type') in [FilterAction.MOVE, FilterAction.COPY] and not v:
            raise ValueError(f'Folder is required for {info.data.get("type")} actions')
        return v
    
    @field_validator('flag')
    @classmethod
    def validate_flag(cls, v: Optional[str], info) -> Optional[str]:
        """Validate flag is provided for mark actions."""
        if info.data.get('type') == FilterAction.MARK and not v:
            raise ValueError('Flag is required for mark actions')
        return v


class FilterRule(BaseModel):
    """A complete filter rule."""
    
    name: str = Field(..., description="Filter rule name")
    enabled: bool = Field(True, description="Whether the filter is enabled")
    priority: int = Field(1, description="Filter priority (lower numbers = higher priority)")
    conditions: List[FilterCondition] = Field(..., description="Filter conditions")
    actions: List[FilterActionConfig] = Field(..., description="Filter actions")
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: int) -> int:
        """Validate priority value."""
        if v < 1:
            raise ValueError('Priority must be 1 or greater')
        return v
    
    @field_validator('conditions')
    @classmethod
    def validate_conditions(cls, v: List[FilterCondition]) -> List[FilterCondition]:
        """Validate conditions list."""
        if not v:
            raise ValueError('At least one condition is required')
        return v
    
    @field_validator('actions')
    @classmethod
    def validate_actions(cls, v: List[FilterActionConfig]) -> List[FilterActionConfig]:
        """Validate actions list."""
        if not v:
            raise ValueError('At least one action is required')
        return v


class FilterConfig(BaseModel):
    """Complete filter configuration."""
    
    filters: List[FilterRule] = Field(default_factory=list, description="List of filter rules")


class MessageData:
    """Container for message data used in filtering."""
    
    def __init__(self, **kwargs):
        self.from_: Optional[str] = kwargs.get('from_', kwargs.get('from'))
        self.to: Optional[str] = kwargs.get('to')
        self.subject: Optional[str] = kwargs.get('subject')
        self.body: Optional[str] = kwargs.get('body')
        self.date: Optional[str] = kwargs.get('date')
        self.size: Optional[int] = kwargs.get('size')
        self.cc: Optional[str] = kwargs.get('cc')
        self.bcc: Optional[str] = kwargs.get('bcc')
        self.has_attachment: Optional[bool] = kwargs.get('has_attachment')
    
    def get_field_value(self, field: FilterField) -> Optional[Union[str, int, bool]]:
        """Get the value of a specific field."""
        field_map = {
            FilterField.FROM: self.from_,
            FilterField.TO: self.to,
            FilterField.SUBJECT: self.subject,
            FilterField.BODY: self.body,
            FilterField.DATE: self.date,
            FilterField.SIZE: self.size,
            FilterField.CC: self.cc,
            FilterField.BCC: self.bcc,
            FilterField.HAS_ATTACHMENT: self.has_attachment,
        }
        return field_map.get(field)


class FilterEngine:
    """Main filter engine for processing email messages."""
    
    def __init__(self, filters_path: Optional[str] = None):
        """Initialize the filter engine."""
        self.logger = logging.getLogger(__name__)
        if filters_path:
            # Expand ~ to home directory if present
            if filters_path.startswith('~'):
                filters_path = str(Path.home()) + filters_path[1:]
            self.filters_path = filters_path
        else:
            self.filters_path = str(Path.home() / ".config" / "IMAPMessageFilter" / "filters.yaml")
        self.filters: Optional[FilterConfig] = None
        self._load_filters()
    
    def _load_filters(self) -> None:
        """Load filters from the configuration file."""
        try:
            filters_file = Path(self.filters_path)
            if not filters_file.exists():
                self.logger.warning(f"Filters file not found: {self.filters_path}")
                self.filters = FilterConfig()
                return
            
            with open(filters_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self.filters = FilterConfig(**data)
            self.logger.info(f"Loaded {len(self.filters.filters)} filter(s) from {self.filters_path}")
            
        except Exception as e:
            self.logger.error(f"Error loading filters from {self.filters_path}: {e}")
            self.filters = FilterConfig()
    
    def _evaluate_condition(self, condition: FilterCondition, message: MessageData) -> bool:
        """Evaluate a single condition against a message."""
        field_value = message.get_field_value(condition.field)
        
        if field_value is None:
            return False
        
        # Convert to string for comparison (except for size and has_attachment)
        if condition.field in [FilterField.SIZE, FilterField.HAS_ATTACHMENT]:
            # Handle numeric/boolean comparisons
            if condition.operator in [FilterOperator.GREATER_THAN, FilterOperator.LESS_THAN, FilterOperator.EQUALS, FilterOperator.NOT_EQUALS]:
                try:
                    if condition.field == FilterField.SIZE:
                        target_value = int(condition.value)
                        current_value = int(field_value) if field_value is not None else 0
                    else:  # HAS_ATTACHMENT
                        target_value = condition.value.lower() in ['true', '1', 'yes']
                        current_value = bool(field_value)
                    
                    if condition.operator == FilterOperator.GREATER_THAN:
                        return current_value > target_value
                    elif condition.operator == FilterOperator.LESS_THAN:
                        return current_value < target_value
                    elif condition.operator == FilterOperator.EQUALS:
                        return current_value == target_value
                    elif condition.operator == FilterOperator.NOT_EQUALS:
                        return current_value != target_value
                except (ValueError, TypeError):
                    return False
        else:
            # Handle string comparisons
            field_str = str(field_value).lower()
            condition_str = condition.value.lower()
            
            if condition.operator == FilterOperator.CONTAINS:
                return condition_str in field_str
            elif condition.operator == FilterOperator.IS:
                return field_str == condition_str
            elif condition.operator == FilterOperator.STARTS_WITH:
                return field_str.startswith(condition_str)
            elif condition.operator == FilterOperator.ENDS_WITH:
                return field_str.endswith(condition_str)
            elif condition.operator == FilterOperator.DOESNT_CONTAIN:
                return condition_str not in field_str
        
        return False
    
    def _evaluate_conditions(self, conditions: List[FilterCondition], message: MessageData) -> bool:
        """Evaluate all conditions for a filter (AND logic)."""
        for condition in conditions:
            if not self._evaluate_condition(condition, message):
                return False
        return True
    
    def match_message(self, message: MessageData) -> List[FilterRule]:
        """Find all filters that match a message."""
        if not self.filters or not self.filters.filters:
            return []
        
        matching_filters = []
        
        # Sort filters by priority (lower numbers = higher priority)
        sorted_filters = sorted(self.filters.filters, key=lambda f: f.priority)
        
        for filter_rule in sorted_filters:
            if not filter_rule.enabled:
                continue
            
            if self._evaluate_conditions(filter_rule.conditions, message):
                matching_filters.append(filter_rule)
                self.logger.debug(f"Message matches filter: {filter_rule.name}")
        
        return matching_filters
    
    def get_filter_summary(self) -> Dict[str, Any]:
        """Get a summary of loaded filters."""
        if not self.filters:
            return {"total_filters": 0, "enabled_filters": 0, "filters": []}
        
        enabled_count = sum(1 for f in self.filters.filters if f.enabled)
        
        return {
            "total_filters": len(self.filters.filters),
            "enabled_filters": enabled_count,
            "filters": [
                {
                    "name": f.name,
                    "enabled": f.enabled,
                    "priority": f.priority,
                    "conditions_count": len(f.conditions),
                    "actions_count": len(f.actions)
                }
                for f in self.filters.filters
            ]
        }
    
    def validate_filters(self) -> List[str]:
        """Validate all filters and return any errors."""
        errors = []
        
        if not self.filters:
            errors.append("No filters loaded")
            return errors
        
        for i, filter_rule in enumerate(self.filters.filters):
            try:
                # Validate the filter rule (Pydantic will catch most issues)
                filter_rule.model_validate(filter_rule.model_dump())
            except Exception as e:
                errors.append(f"Filter {i+1} ({filter_rule.name}): {e}")
        
        return errors
