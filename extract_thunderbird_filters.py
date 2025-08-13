#!/usr/bin/env python3
"""Extract message filter rules from Thunderbird configuration files."""

import os
import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


def get_thunderbird_profiles_path() -> Path:
    """Get Thunderbird profiles directory path based on operating system."""
    import platform
    
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        return Path.home() / "Library" / "Thunderbird" / "Profiles"
    elif system == "linux":
        return Path.home() / ".thunderbird"
    elif system == "windows":
        return Path.home() / "AppData" / "Roaming" / "Thunderbird" / "Profiles"
    else:
        # Fallback to Linux path for unknown systems
        return Path.home() / ".thunderbird"


def find_thunderbird_profiles() -> list:
    """Find Thunderbird profile directories."""
    profiles_dir = get_thunderbird_profiles_path()
    
    if not profiles_dir.exists():
        print(f"Thunderbird profiles directory not found: {profiles_dir}")
        return []
    
    profiles = []
    for profile_dir in profiles_dir.iterdir():
        if profile_dir.is_dir() and profile_dir.name.endswith(('.default', '.default-release')):
            profiles.append(profile_dir)
    
    return profiles


def find_filter_files_comprehensive(profile_dir: Path) -> List[Path]:
    """Find filter files in Thunderbird profile using comprehensive search."""
    filter_files = []
    
    print(f"    Searching in: {profile_dir}")
    
    # Search for filter files in various locations
    search_patterns = [
        "**/msgFilterRules.dat",
        "**/*.sbd/msgFilterRules.dat",
        "**/ImapMail/**/msgFilterRules.dat",
        "**/Mail/**/msgFilterRules.dat",
        "**/Local Folders/**/msgFilterRules.dat",
        "**/msgFilterRules.dat",
        "**/filters.dat",
        "**/filterRules.dat"
    ]
    
    for pattern in search_patterns:
        try:
            found_files = list(profile_dir.glob(pattern))
            for file_path in found_files:
                if file_path.is_file() and file_path not in filter_files:
                    filter_files.append(file_path)
                    print(f"      Found: {file_path.relative_to(profile_dir)}")
        except Exception as e:
            print(f"      Error searching pattern {pattern}: {e}")
    
    return filter_files


def parse_thunderbird_filter_format(content: str, file_path: Path) -> List[Dict]:
    """Parse Thunderbird's specific filter format."""
    filters = []
    
    lines = content.split('\n')
    current_filter = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip version and logging lines
        if line.startswith('version=') or line.startswith('logging='):
            continue
        
        # Check if this is a new filter (starts with name=)
        if line.startswith('name='):
            # Save previous filter if exists
            if current_filter and 'name' in current_filter:
                filters.append(current_filter)
            
            # Start new filter
            current_filter = {}
            name_match = re.search(r'name="([^"]+)"', line)
            if name_match:
                current_filter['name'] = name_match.group(1)
        
        # Parse enabled status
        elif line.startswith('enabled='):
            enabled_match = re.search(r'enabled="([^"]+)"', line)
            if enabled_match:
                current_filter['enabled'] = enabled_match.group(1) == 'yes'
        
        # Parse filter type
        elif line.startswith('type='):
            type_match = re.search(r'type="([^"]+)"', line)
            if type_match:
                current_filter['type'] = type_match.group(1)
        
        # Parse action
        elif line.startswith('action='):
            action_match = re.search(r'action="([^"]+)"', line)
            if action_match:
                current_filter['action'] = action_match.group(1)
        
        # Parse action value
        elif line.startswith('actionValue='):
            action_value_match = re.search(r'actionValue="([^"]+)"', line)
            if action_value_match:
                current_filter['actionValue'] = action_value_match.group(1)
        
        # Parse condition (this is the complex part)
        elif line.startswith('condition='):
            condition_match = re.search(r'condition="([^"]+)"', line)
            if condition_match:
                condition_str = condition_match.group(1)
                current_filter['condition'] = condition_str
                
                # Parse the condition string to extract individual conditions
                conditions = parse_condition_string(condition_str)
                current_filter['parsed_conditions'] = conditions
    
    # Add the last filter
    if current_filter and 'name' in current_filter:
        filters.append(current_filter)
    
    return filters


def parse_condition_string(condition_str: str) -> List[Dict]:
    """Parse Thunderbird condition string into structured format."""
    conditions = []
    
    # Remove the outer AND/OR wrapper
    condition_str = condition_str.strip()
    if condition_str.startswith('AND (') and condition_str.endswith(')'):
        condition_str = condition_str[5:-1]  # Remove "AND (" and ")"
    elif condition_str.startswith('OR (') and condition_str.endswith(')'):
        condition_str = condition_str[4:-1]  # Remove "OR (" and ")"
    
    # Split by "AND (" or "OR ("
    parts = re.split(r'\s+(?:AND|OR)\s+\(', condition_str)
    
    for part in parts:
        if not part.strip():
            continue
        
        # Remove trailing ")" if present
        if part.endswith(')'):
            part = part[:-1]
        
        # Parse individual condition: field,operator,value
        if ',' in part:
            # Handle quoted values
            matches = re.findall(r'([^,]+),([^,]+),([^,]+)', part)
            if matches:
                field, operator, value = matches[0]
                conditions.append({
                    'field': field.strip(),
                    'operator': operator.strip(),
                    'value': value.strip()
                })
    
    return conditions


def extract_filter_rules_advanced(filter_file: Path) -> List[Dict]:
    """Extract filter rules from Thunderbird filter file with advanced parsing."""
    filters = []
    
    try:
        with open(filter_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print(f"      Reading: {filter_file.name} ({len(content)} bytes)")
        
        # Use the Thunderbird-specific parser
        filters = parse_thunderbird_filter_format(content, filter_file)
        
        if not filters:
            print(f"      No filters found in {filter_file.name}")
        else:
            print(f"      Found {len(filters)} filters")
        
    except Exception as e:
        print(f"      Error reading {filter_file}: {e}")
    
    return filters


def find_account_filters_comprehensive(profile_dir: Path, account_identifier: str) -> List[Dict]:
    """Find filters for a specific account using comprehensive search."""
    all_filters = []
    
    # Search for filter files
    filter_files = find_filter_files_comprehensive(profile_dir)
    
    for filter_file in filter_files:
        filters = extract_filter_rules_advanced(filter_file)
        for filter_rule in filters:
            filter_rule['source_file'] = str(filter_file)
            all_filters.append(filter_rule)
    
    return all_filters


def convert_to_yaml_format(filters: List[Dict]) -> Dict:
    """Convert Thunderbird filters to YAML format for our application."""
    yaml_filters = {
        'filters': []
    }
    
    for filter_rule in filters:
        yaml_filter = {
            'name': filter_rule.get('name', 'Unnamed Filter'),
            'enabled': filter_rule.get('enabled', True),
            'priority': 1,  # Default priority
            'conditions': [],
            'actions': []
        }
        
        # Convert parsed conditions
        parsed_conditions = filter_rule.get('parsed_conditions', [])
        for condition in parsed_conditions:
            yaml_filter['conditions'].append({
                'field': condition.get('field', 'subject'),
                'operator': condition.get('operator', 'contains'),
                'value': condition.get('value', '')
            })
        
        # Convert actions
        action = filter_rule.get('action', '')
        action_value = filter_rule.get('actionValue', '')
        
        if action == 'Move to folder':
            # Extract folder name from actionValue
            folder_name = extract_folder_name_from_action_value(action_value)
            yaml_filter['actions'].append({
                'type': 'move',
                'folder': folder_name
            })
        elif action == 'Delete':
            yaml_filter['actions'].append({
                'type': 'delete'
            })
        elif action == 'Mark':
            yaml_filter['actions'].append({
                'type': 'mark',
                'flag': action_value
            })
        
        yaml_filters['filters'].append(yaml_filter)
    
    return yaml_filters


def extract_folder_name_from_action_value(action_value: str) -> str:
    """Extract folder name from Thunderbird action value."""
    # Example: "imap://nathan%40yearaway.com@imap.positive-internet.com/INBOX/India/MF"
    if '/' in action_value:
        # Split by '/' and take the last part
        parts = action_value.split('/')
        if len(parts) > 1:
            # Remove the protocol and server parts, keep the folder path
            folder_parts = parts[3:]  # Skip protocol, username, server
            return '/'.join(folder_parts)
    
    return action_value


def main():
    """Main function to extract Thunderbird filters."""
    import platform
    
    system = platform.system()
    print(f"🔍 Extracting message filters from Thunderbird on {system}...")
    print()
    
    # Find Thunderbird profiles
    profiles = find_thunderbird_profiles()
    if not profiles:
        print("❌ No Thunderbird profiles found.")
        return
    
    print(f"📁 Found {len(profiles)} Thunderbird profile(s):")
    for i, profile in enumerate(profiles, 1):
        print(f"  {i}. {profile.name}")
    print()
    
    # Look for filters in all profiles
    all_filters = []
    for profile in profiles:
        print(f"🔍 Searching for filters in profile: {profile.name}")
        
        # Look for filters for your specific account
        account_identifier = "nathan@yearaway.com"
        filters = find_account_filters_comprehensive(profile, account_identifier)
        
        if filters:
            print(f"  ✅ Found {len(filters)} filter(s)")
            all_filters.extend(filters)
        else:
            print(f"  ❌ No filters found for {account_identifier}")
    
    if not all_filters:
        print("\n❌ No message filters found in Thunderbird.")
        print("This could mean:")
        print("  • No filters are configured")
        print("  • Filters are stored in a different location")
        print("  • Filters use a different format")
        print()
        print("💡 Creating sample filter template...")
        
        # Create a sample filter template
        sample_filters = {
            'filters': [
                {
                    'name': 'Sample Filter - Move Spam',
                    'enabled': True,
                    'priority': 1,
                    'conditions': [
                        {
                            'field': 'subject',
                            'operator': 'contains',
                            'value': 'spam'
                        }
                    ],
                    'actions': [
                        {
                            'type': 'move',
                            'folder': 'Trash'
                        }
                    ]
                },
                {
                    'name': 'Sample Filter - Move Work Emails',
                    'enabled': True,
                    'priority': 2,
                    'conditions': [
                        {
                            'field': 'from',
                            'operator': 'contains',
                            'value': 'work@company.com'
                        }
                    ],
                    'actions': [
                        {
                            'type': 'move',
                            'folder': 'INBOX.Work'
                        }
                    ]
                }
            ]
        }
        
        all_filters = [{'name': 'Sample Filter', 'enabled': True}]
        yaml_filters = sample_filters
    else:
        print(f"\n📧 Found {len(all_filters)} total filter(s):")
        for i, filter_rule in enumerate(all_filters, 1):
            name = filter_rule.get('name', 'Unnamed Filter')
            enabled = filter_rule.get('enabled', True)
            status = "✅ Enabled" if enabled else "❌ Disabled"
            action = filter_rule.get('action', 'Unknown')
            print(f"  {i}. {name} ({status}) - {action}")
        
        print("\n📝 Converting filters to YAML format...")
        yaml_filters = convert_to_yaml_format(all_filters)
    
    # Save to file
    filters_path = Path.home() / ".config" / "IMAPMessageFilter" / "filters.yaml"
    filters_path.parent.mkdir(parents=True, exist_ok=True)
    
    import yaml
    with open(filters_path, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_filters, f, default_flow_style=False, indent=2)
    
    print(f"✅ Filters saved to: {filters_path}")
    print()
    print("📋 Next steps:")
    print("1. Review the extracted filters:")
    print(f"   nano {filters_path}")
    print()
    print("2. Edit filters as needed for your IMAP Message Filter")
    print("3. The filters will be used in Phase 2 implementation")
    print()
    print("🔍 Filter details:")
    for filter_rule in yaml_filters['filters']:
        print(f"  • {filter_rule['name']}: {len(filter_rule['conditions'])} conditions, {len(filter_rule['actions'])} actions")


if __name__ == "__main__":
    main()
