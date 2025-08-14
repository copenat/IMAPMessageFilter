#!/usr/bin/env python3
"""Extract IMAP settings from Thunderbird configuration files."""

import os
import re
import sys
import yaml
from pathlib import Path
from typing import Dict, Optional


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


def extract_imap_settings_from_prefs(prefs_file: Path) -> list:
    """Extract IMAP settings from Thunderbird prefs.js file."""
    accounts = []
    
    if not prefs_file.exists():
        return accounts
    
    try:
        with open(prefs_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Find all server IDs
        server_ids = re.findall(r'mail\.server\.server(\d+)\.hostname', content)
        
        for server_id in server_ids:
            account = {}
            
            # Extract hostname
            host_match = re.search(fr'user_pref\("mail\.server\.server{server_id}\.hostname",\s*"([^"]+)"\);', content)
            if host_match:
                account['host'] = host_match.group(1)
            
            # Extract port
            port_match = re.search(fr'user_pref\("mail\.server\.server{server_id}\.port",\s*(\d+)\);', content)
            if port_match:
                account['port'] = int(port_match.group(1))
            
            # Extract username
            username_match = re.search(fr'user_pref\("mail\.server\.server{server_id}\.userName",\s*"([^"]+)"\);', content)
            if username_match:
                account['username'] = username_match.group(1)
            
            # Extract socket type (SSL settings)
            socket_match = re.search(fr'user_pref\("mail\.server\.server{server_id}\.socketType",\s*(\d+)\);', content)
            if socket_match:
                socket_type = int(socket_match.group(1))
                # 0=No encryption, 1=STARTTLS, 2=STARTTLS, 3=SSL/TLS
                account['use_ssl'] = socket_type == 3  # Only true SSL/TLS
                account['use_starttls'] = socket_type in [1, 2]  # STARTTLS
                account['socket_type'] = socket_type
            
            # Extract auth method
            auth_match = re.search(fr'user_pref\("mail\.server\.server{server_id}\.authMethod",\s*(\d+)\);', content)
            if auth_match:
                account['auth_method'] = int(auth_match.group(1))
            
            # Only add if we have at least host and username
            if account.get('host') and account.get('username'):
                accounts.append(account)
                
    except Exception as e:
        print(f"Error reading {prefs_file}: {e}")
    
    return accounts


def get_common_imap_servers() -> Dict[str, Dict[str, any]]:
    """Common IMAP server configurations."""
    return {
        'gmail.com': {
            'host': 'imap.gmail.com',
            'port': 993,
            'use_ssl': True,
            'notes': 'Requires App Password if 2FA is enabled'
        },
        'outlook.com': {
            'host': 'outlook.office365.com',
            'port': 993,
            'use_ssl': True,
            'notes': 'Use your Microsoft account password'
        },
        'hotmail.com': {
            'host': 'outlook.office365.com',
            'port': 993,
            'use_ssl': True,
            'notes': 'Use your Microsoft account password'
        },
        'yahoo.com': {
            'host': 'imap.mail.yahoo.com',
            'port': 993,
            'use_ssl': True,
            'notes': 'Requires App Password'
        },
        'icloud.com': {
            'host': 'imap.mail.me.com',
            'port': 993,
            'use_ssl': True,
            'notes': 'Requires App-Specific Password'
        },
        'aol.com': {
            'host': 'imap.aol.com',
            'port': 993,
            'use_ssl': True,
            'notes': 'Requires App Password'
        }
    }


def main():
    """Main function to extract Thunderbird settings."""
    import platform
    
    system = platform.system()
    print(f"🔍 Extracting IMAP settings from Thunderbird on {system}...")
    print()
    
    # Find Thunderbird profiles
    profiles = find_thunderbird_profiles()
    if not profiles:
        print("❌ No Thunderbird profiles found.")
        print("Make sure Thunderbird is installed and you have at least one email account configured.")
        return
    
    print(f"📁 Found {len(profiles)} Thunderbird profile(s):")
    for i, profile in enumerate(profiles, 1):
        print(f"  {i}. {profile.name}")
    print()
    
    # Extract settings from each profile
    all_accounts = []
    for profile in profiles:
        prefs_file = profile / "prefs.js"
        accounts = extract_imap_settings_from_prefs(prefs_file)
        for account in accounts:
            account['profile'] = profile.name
            all_accounts.append(account)
    
    if not all_accounts:
        print("❌ No IMAP accounts found in Thunderbird profiles.")
        print("Make sure you have configured at least one IMAP email account.")
        print()
        print("💡 If you have email accounts configured but they're not showing up,")
        print("   they might be using POP3 instead of IMAP, or stored in a different location.")
        print()
        print("📋 Manual configuration options:")
        
        # Show common server configurations
        common_servers = get_common_imap_servers()
        print("🌐 Common IMAP server configurations:")
        for domain, config in common_servers.items():
            print(f"  • {domain}: {config['host']}:{config['port']} ({'SSL' if config['use_ssl'] else 'No SSL'})")
        print()
        
        # Ask user to choose a common provider
        print("Would you like to configure a common email provider?")
        print("Enter the number of your choice, or 'n' to create a generic template:")
        
        provider_choices = list(common_servers.keys())
        for i, domain in enumerate(provider_choices, 1):
            config = common_servers[domain]
            print(f"  {i}. {domain} ({config['host']})")
        print(f"  {len(provider_choices) + 1}. Generic template")
        
        try:
            choice = input("\nEnter your choice: ").strip()
            if choice.lower() == 'n':
                choice = str(len(provider_choices) + 1)
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(provider_choices):
                selected_domain = provider_choices[choice_num - 1]
                selected_config = common_servers[selected_domain]
                
                # Ask for email address
                email = input(f"Enter your {selected_domain} email address: ").strip()
                if not email:
                    email = f"your-email@{selected_domain}"
                
                config_template = {
                    'imap': {
                        'host': selected_config['host'],
                        'port': selected_config['port'],
                        'username': email,
                        'password': 'your-password-here',  # User needs to fill this
                        'use_ssl': selected_config['use_ssl'],
                        'use_starttls': False,  # Most providers use SSL/TLS
                        'timeout': 30
                    },
                    'logging': {
                        'level': 'INFO',
                        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        'file': None
                    },
                    'filters': {
                        'filters_path': str(Path.home() / ".config" / "IMAPMessageFilter" / "filters.yaml")
                    }
                }
                
                print(f"\n📝 Creating configuration for {selected_domain}...")
                
            else:
                # Generic template
                config_template = {
                    'imap': {
                        'host': 'imap.gmail.com',  # Most common
                        'port': 993,
                        'username': 'your-email@gmail.com',
                        'password': 'your-app-password',
                        'use_ssl': True,
                        'timeout': 30
                    },
                    'logging': {
                        'level': 'INFO',
                        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        'file': None
                    },
                    'filters': {
                        'filters_path': str(Path.home() / ".config" / "IMAPMessageFilter" / "filters.yaml")
                    }
                }
                print("\n📝 Creating generic configuration template...")
                
        except (ValueError, IndexError):
            print("\n📝 Creating generic configuration template...")
            config_template = {
                'imap': {
                    'host': 'imap.gmail.com',  # Most common
                    'port': 993,
                    'username': 'your-email@gmail.com',
                    'password': 'your-app-password',
                    'use_ssl': True,
                    'timeout': 30
                },
                'logging': {
                    'level': 'INFO',
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    'file': None
                },
                'filters': {
                    'filters_path': str(Path.home() / ".config" / "IMAPMessageFilter" / "filters.yaml")
                }
            }
        
        # Save to default config location
        config_path = Path.home() / ".local" / "IMAPMessageFilter" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_template, f, default_flow_style=False, indent=2)
        
        print(f"✅ Configuration template created at: {config_path}")
        print()
        print("📋 Next steps:")
        print("1. Edit the configuration file:")
        print(f"   nano {config_path}")
        print()
        print("2. Update with your actual email provider settings:")
        print("   - username: Your email address")
        print("   - password: Your password or app password")
        print()
        print("3. Test the connection:")
        print("   uv run python main.py test-connection")
        return
    
    print("📧 Found IMAP account(s):")
    for i, account in enumerate(all_accounts, 1):
        username = account.get('username', 'Unknown')
        host = account.get('host', 'Unknown host')
        port = account.get('port', 'Unknown port')
        ssl = "SSL" if account.get('use_ssl') else "No SSL"
        print(f"  {i}. {username} @ {host}:{port} ({ssl})")
    print()
    
    # Ask user to choose which account to configure
    print("Which IMAP account would you like to configure?")
    try:
        choice = input(f"Enter the number (1-{len(all_accounts)}): ").strip()
        choice_num = int(choice)
        
        if choice_num < 1 or choice_num > len(all_accounts):
            print("Invalid choice. Using the first account.")
            choice_num = 1
            
    except (ValueError, IndexError):
        print("Invalid input. Using the first account.")
        choice_num = 1
    
    selected_account = all_accounts[choice_num - 1]
    username = selected_account.get('username', 'your-email@example.com')
    host = selected_account.get('host', 'imap.example.com')
    port = selected_account.get('port', 993)
    use_ssl = selected_account.get('use_ssl', True)
    use_starttls = selected_account.get('use_starttls', False)
    
    print(f"\n📝 Configuring account: {username} @ {host}:{port}")
    if use_starttls:
        print(f"   Connection type: STARTTLS (encrypted)")
    elif use_ssl:
        print(f"   Connection type: SSL/TLS (encrypted)")
    else:
        print(f"   Connection type: Unencrypted")
    
    # Create config template from selected account
    config_template = {
        'imap': {
            'host': host,
            'port': port,
            'username': username,
            'password': 'your-password-here',  # User needs to fill this
            'use_ssl': use_ssl,
            'use_starttls': use_starttls,
            'timeout': 30
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': None
        },
        'filters': {
            'filters_path': str(Path.home() / ".local" / "IMAPMessageFilter" / "filters.yaml")
        }
    }
    
    # Save to default config location
    config_path = Path.home() / ".local" / "IMAPMessageFilter" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_template, f, default_flow_style=False, indent=2)
    
    print(f"✅ Configuration created at: {config_path}")
    print()
    print("📋 Next steps:")
    print("1. Edit the configuration file:")
    print(f"   nano {config_path}")
    print()
    print("2. Update the password field with your actual password")
    print("3. Test the connection:")
    print("   uv run python main.py test-connection")
    print()
    print("🔐 Security notes:")
    print("• For Gmail, Yahoo, and other providers, you may need to generate an App Password")
    print("• Never commit the config.yaml file to version control")
    print("• The config file is stored in ~/.config/IMAPMessageFilter/ for security")


if __name__ == "__main__":
    main()
