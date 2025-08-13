"""Tests for the filter engine."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from imapmessagefilter.filter_engine import (
    FilterEngine, FilterRule, FilterCondition, FilterActionConfig,
    FilterOperator, FilterAction, FilterField, MessageData
)


class TestFilterEngine:
    """Test cases for the FilterEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.filters_path = Path(self.temp_dir) / "test_filters.yaml"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_filters(self, filters_data: dict) -> None:
        """Create a test filters file."""
        with open(self.filters_path, 'w', encoding='utf-8') as f:
            yaml.dump(filters_data, f, default_flow_style=False, indent=2)
    
    def test_load_filters_success(self):
        """Test successful loading of filters."""
        filters_data = {
            'filters': [
                {
                    'name': 'Test Filter',
                    'enabled': True,
                    'priority': 1,
                    'conditions': [
                        {
                            'field': 'subject',
                            'operator': 'contains',
                            'value': 'test'
                        }
                    ],
                    'actions': [
                        {
                            'type': 'move',
                            'folder': 'INBOX.Test'
                        }
                    ]
                }
            ]
        }
        
        self.create_test_filters(filters_data)
        engine = FilterEngine(str(self.filters_path))
        
        assert engine.filters is not None
        assert len(engine.filters.filters) == 1
        assert engine.filters.filters[0].name == 'Test Filter'
    
    def test_load_filters_file_not_found(self):
        """Test handling of missing filters file."""
        engine = FilterEngine(str(self.filters_path))
        
        assert engine.filters is not None
        assert len(engine.filters.filters) == 0
    
    def test_load_filters_invalid_yaml(self):
        """Test handling of invalid YAML."""
        with open(self.filters_path, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        engine = FilterEngine(str(self.filters_path))
        
        assert engine.filters is not None
        assert len(engine.filters.filters) == 0
    
    def test_match_message_simple_condition(self):
        """Test matching a message with a simple condition."""
        filters_data = {
            'filters': [
                {
                    'name': 'Subject Filter',
                    'enabled': True,
                    'priority': 1,
                    'conditions': [
                        {
                            'field': 'subject',
                            'operator': 'contains',
                            'value': 'important'
                        }
                    ],
                    'actions': [
                        {
                            'type': 'move',
                            'folder': 'INBOX.Important'
                        }
                    ]
                }
            ]
        }
        
        self.create_test_filters(filters_data)
        engine = FilterEngine(str(self.filters_path))
        
        # Test matching message
        message = MessageData(subject='This is an important message')
        matches = engine.match_message(message)
        
        assert len(matches) == 1
        assert matches[0].name == 'Subject Filter'
        
        # Test non-matching message
        message = MessageData(subject='This is a regular message')
        matches = engine.match_message(message)
        
        assert len(matches) == 0
    
    def test_match_message_multiple_conditions(self):
        """Test matching a message with multiple conditions (AND logic)."""
        filters_data = {
            'filters': [
                {
                    'name': 'Complex Filter',
                    'enabled': True,
                    'priority': 1,
                    'conditions': [
                        {
                            'field': 'from',
                            'operator': 'contains',
                            'value': 'example.com'
                        },
                        {
                            'field': 'subject',
                            'operator': 'starts with',
                            'value': 'urgent'
                        }
                    ],
                    'actions': [
                        {
                            'type': 'move',
                            'folder': 'INBOX.Urgent'
                        }
                    ]
                }
            ]
        }
        
        self.create_test_filters(filters_data)
        engine = FilterEngine(str(self.filters_path))
        
        # Test matching message (both conditions met)
        message = MessageData(
            from_='sender@example.com',
            subject='urgent meeting tomorrow'
        )
        matches = engine.match_message(message)
        
        assert len(matches) == 1
        assert matches[0].name == 'Complex Filter'
        
        # Test non-matching message (only one condition met)
        message = MessageData(
            from_='sender@example.com',
            subject='regular meeting tomorrow'
        )
        matches = engine.match_message(message)
        
        assert len(matches) == 0
    
    def test_match_message_priority_ordering(self):
        """Test that filters are processed in priority order."""
        filters_data = {
            'filters': [
                {
                    'name': 'Low Priority Filter',
                    'enabled': True,
                    'priority': 10,
                    'conditions': [
                        {
                            'field': 'subject',
                            'operator': 'contains',
                            'value': 'test'
                        }
                    ],
                    'actions': [
                        {
                            'type': 'move',
                            'folder': 'INBOX.Low'
                        }
                    ]
                },
                {
                    'name': 'High Priority Filter',
                    'enabled': True,
                    'priority': 1,
                    'conditions': [
                        {
                            'field': 'subject',
                            'operator': 'contains',
                            'value': 'test'
                        }
                    ],
                    'actions': [
                        {
                            'type': 'move',
                            'folder': 'INBOX.High'
                        }
                    ]
                }
            ]
        }
        
        self.create_test_filters(filters_data)
        engine = FilterEngine(str(self.filters_path))
        
        message = MessageData(subject='This is a test message')
        matches = engine.match_message(message)
        
        assert len(matches) == 2
        # Higher priority (lower number) should come first
        assert matches[0].name == 'High Priority Filter'
        assert matches[1].name == 'Low Priority Filter'
    
    def test_match_message_disabled_filter(self):
        """Test that disabled filters are not processed."""
        filters_data = {
            'filters': [
                {
                    'name': 'Disabled Filter',
                    'enabled': False,
                    'priority': 1,
                    'conditions': [
                        {
                            'field': 'subject',
                            'operator': 'contains',
                            'value': 'test'
                        }
                    ],
                    'actions': [
                        {
                            'type': 'move',
                            'folder': 'INBOX.Test'
                        }
                    ]
                }
            ]
        }
        
        self.create_test_filters(filters_data)
        engine = FilterEngine(str(self.filters_path))
        
        message = MessageData(subject='This is a test message')
        matches = engine.match_message(message)
        
        assert len(matches) == 0
    
    def test_get_filter_summary(self):
        """Test getting filter summary."""
        filters_data = {
            'filters': [
                {
                    'name': 'Filter 1',
                    'enabled': True,
                    'priority': 1,
                    'conditions': [
                        {
                            'field': 'subject',
                            'operator': 'contains',
                            'value': 'test'
                        }
                    ],
                    'actions': [
                        {
                            'type': 'move',
                            'folder': 'INBOX.Test'
                        }
                    ]
                },
                {
                    'name': 'Filter 2',
                    'enabled': False,
                    'priority': 2,
                    'conditions': [
                        {
                            'field': 'from',
                            'operator': 'contains',
                            'value': 'example'
                        }
                    ],
                    'actions': [
                        {
                            'type': 'delete'
                        }
                    ]
                }
            ]
        }
        
        self.create_test_filters(filters_data)
        engine = FilterEngine(str(self.filters_path))
        
        summary = engine.get_filter_summary()
        
        assert summary['total_filters'] == 2
        assert summary['enabled_filters'] == 1
        assert len(summary['filters']) == 2
        
        # Check first filter details
        filter1 = summary['filters'][0]
        assert filter1['name'] == 'Filter 1'
        assert filter1['enabled'] is True
        assert filter1['priority'] == 1
        assert filter1['conditions_count'] == 1
        assert filter1['actions_count'] == 1
    
    def test_validate_filters_success(self):
        """Test filter validation with valid filters."""
        filters_data = {
            'filters': [
                {
                    'name': 'Valid Filter',
                    'enabled': True,
                    'priority': 1,
                    'conditions': [
                        {
                            'field': 'subject',
                            'operator': 'contains',
                            'value': 'test'
                        }
                    ],
                    'actions': [
                        {
                            'type': 'move',
                            'folder': 'INBOX.Test'
                        }
                    ]
                }
            ]
        }
        
        self.create_test_filters(filters_data)
        engine = FilterEngine(str(self.filters_path))
        
        errors = engine.validate_filters()
        assert len(errors) == 0
    
    def test_validate_filters_invalid(self):
        """Test filter validation with invalid filters."""
        # Test that validation catches invalid field values
        try:
            invalid_condition = FilterCondition(
                field='invalid_field',  # Invalid field
                operator='invalid_operator',  # Invalid operator
                value='test'
            )
            assert False, "Should have raised validation error"
        except Exception as e:
            error_str = str(e)
            assert "validation error" in error_str
            assert "invalid_field" in error_str or "invalid_operator" in error_str
        
        # Test that validation catches invalid action types
        try:
            invalid_action = FilterActionConfig(
                type='invalid_action',  # Invalid action type
                folder='INBOX.Test'
            )
            assert False, "Should have raised validation error"
        except Exception as e:
            error_str = str(e)
            assert "validation error" in error_str
            assert "invalid_action" in error_str
        
        # Test that validation works for valid configurations
        try:
            valid_action = FilterActionConfig(
                type=FilterAction.MOVE,
                folder='INBOX.Test'
            )
            # Should not raise an error
            assert valid_action.type == FilterAction.MOVE
            assert valid_action.folder == 'INBOX.Test'
        except Exception as e:
            assert False, f"Valid configuration should not raise error: {e}"


class TestMessageData:
    """Test cases for the MessageData class."""
    
    def test_message_data_initialization(self):
        """Test MessageData initialization."""
        message = MessageData(
            from_='sender@example.com',
            to='recipient@example.com',
            subject='Test Subject',
            body='Test body content'
        )
        
        assert message.from_ == 'sender@example.com'
        assert message.to == 'recipient@example.com'
        assert message.subject == 'Test Subject'
        assert message.body == 'Test body content'
    
    def test_message_data_field_access(self):
        """Test accessing message fields."""
        message = MessageData(
            from_='sender@example.com',
            subject='Test Subject',
            size=1024,
            has_attachment=True
        )
        
        assert message.get_field_value(FilterField.FROM) == 'sender@example.com'
        assert message.get_field_value(FilterField.SUBJECT) == 'Test Subject'
        assert message.get_field_value(FilterField.SIZE) == 1024
        assert message.get_field_value(FilterField.HAS_ATTACHMENT) is True
        assert message.get_field_value(FilterField.TO) is None
    
    def test_message_data_from_alias(self):
        """Test that 'from' and 'from_' both work."""
        message1 = MessageData(from_='sender@example.com')
        message2 = MessageData(**{'from': 'sender@example.com'})
        
        assert message1.from_ == 'sender@example.com'
        assert message2.from_ == 'sender@example.com'


class TestFilterConditionEvaluation:
    """Test cases for filter condition evaluation."""
    
    def test_string_contains_operator(self):
        """Test 'contains' operator with strings."""
        condition = FilterCondition(
            field=FilterField.SUBJECT,
            operator=FilterOperator.CONTAINS,
            value='important'
        )
        
        message = MessageData(subject='This is an important message')
        engine = FilterEngine()
        
        assert engine._evaluate_condition(condition, message) is True
        
        message = MessageData(subject='This is a regular message')
        assert engine._evaluate_condition(condition, message) is False
    
    def test_string_is_operator(self):
        """Test 'is' operator with strings."""
        condition = FilterCondition(
            field=FilterField.SUBJECT,
            operator=FilterOperator.IS,
            value='test subject'
        )
        
        message = MessageData(subject='test subject')
        engine = FilterEngine()
        
        assert engine._evaluate_condition(condition, message) is True
        
        message = MessageData(subject='different subject')
        assert engine._evaluate_condition(condition, message) is False
    
    def test_string_starts_with_operator(self):
        """Test 'starts with' operator."""
        condition = FilterCondition(
            field=FilterField.SUBJECT,
            operator=FilterOperator.STARTS_WITH,
            value='urgent'
        )
        
        message = MessageData(subject='urgent meeting tomorrow')
        engine = FilterEngine()
        
        assert engine._evaluate_condition(condition, message) is True
        
        message = MessageData(subject='regular meeting tomorrow')
        assert engine._evaluate_condition(condition, message) is False
    
    def test_string_ends_with_operator(self):
        """Test 'ends with' operator."""
        condition = FilterCondition(
            field=FilterField.SUBJECT,
            operator=FilterOperator.ENDS_WITH,
            value='urgent'
        )
        
        message = MessageData(subject='meeting urgent')
        engine = FilterEngine()
        
        assert engine._evaluate_condition(condition, message) is True
        
        message = MessageData(subject='urgent meeting')
        assert engine._evaluate_condition(condition, message) is False
    
    def test_string_doesnt_contain_operator(self):
        """Test 'doesn't contain' operator."""
        condition = FilterCondition(
            field=FilterField.SUBJECT,
            operator=FilterOperator.DOESNT_CONTAIN,
            value='spam'
        )
        
        message = MessageData(subject='important message')
        engine = FilterEngine()
        
        assert engine._evaluate_condition(condition, message) is True
        
        message = MessageData(subject='spam message')
        assert engine._evaluate_condition(condition, message) is False
    
    def test_numeric_comparison_operators(self):
        """Test numeric comparison operators with size field."""
        message = MessageData(size=1024)
        engine = FilterEngine()
        
        # Greater than
        condition = FilterCondition(
            field=FilterField.SIZE,
            operator=FilterOperator.GREATER_THAN,
            value='512'
        )
        assert engine._evaluate_condition(condition, message) is True
        
        # Less than
        condition = FilterCondition(
            field=FilterField.SIZE,
            operator=FilterOperator.LESS_THAN,
            value='2048'
        )
        assert engine._evaluate_condition(condition, message) is True
        
        # Equals
        condition = FilterCondition(
            field=FilterField.SIZE,
            operator=FilterOperator.EQUALS,
            value='1024'
        )
        assert engine._evaluate_condition(condition, message) is True
    
    def test_boolean_comparison_operators(self):
        """Test boolean comparison operators with has_attachment field."""
        message = MessageData(has_attachment=True)
        engine = FilterEngine()
        
        # Equals true
        condition = FilterCondition(
            field=FilterField.HAS_ATTACHMENT,
            operator=FilterOperator.EQUALS,
            value='true'
        )
        assert engine._evaluate_condition(condition, message) is True
        
        # Equals false
        condition = FilterCondition(
            field=FilterField.HAS_ATTACHMENT,
            operator=FilterOperator.EQUALS,
            value='false'
        )
        assert engine._evaluate_condition(condition, message) is False
    
    def test_case_insensitive_comparison(self):
        """Test that string comparisons are case insensitive."""
        condition = FilterCondition(
            field=FilterField.SUBJECT,
            operator=FilterOperator.CONTAINS,
            value='IMPORTANT'
        )
        
        message = MessageData(subject='This is an important message')
        engine = FilterEngine()
        
        assert engine._evaluate_condition(condition, message) is True
    
    def test_missing_field_value(self):
        """Test handling of missing field values."""
        condition = FilterCondition(
            field=FilterField.SUBJECT,
            operator=FilterOperator.CONTAINS,
            value='test'
        )
        
        message = MessageData()  # No subject field
        engine = FilterEngine()
        
        assert engine._evaluate_condition(condition, message) is False
