#!/bin/bash

# IMAP Message Filter Installation Script
# This script handles complete installation from cloning to executable setup

set -e  # Exit on any error

echo "🚀 IMAP Message Filter - Complete Installation"
echo "=============================================="

# Configuration
REPO_URL="https://github.com/copenat/IMAPMessageFilter.git"
REPO_NAME="imapmessagefilter"
BIN_DIR="$HOME/bin"
WRAPPER_SCRIPT="$BIN_DIR/$REPO_NAME"

# Check if we're running from within the repository or need to clone it
if [ -f "main.py" ] && [ -f "pyproject.toml" ]; then
    echo "✅ Running from existing repository"
    TOOL_DIR="$(pwd)"
else
    echo "📥 Cloning repository..."
    
    # Create a temporary directory for cloning
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    # Clone the repository
    git clone "$REPO_URL" "$REPO_NAME"
    cd "$REPO_NAME"
    TOOL_DIR="$(pwd)"
    
    echo "✅ Repository cloned to: $TOOL_DIR"
fi

echo "📁 Tool directory: $TOOL_DIR"
echo "📁 Target bin directory: $BIN_DIR"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: 'uv' command not found"
    echo "   Please install uv first: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Install dependencies if they haven't been installed yet
if [ ! -d ".venv" ]; then
    echo "📦 Installing dependencies with uv sync..."
    uv sync
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

# Create ~/bin directory if it doesn't exist
if [ ! -d "$BIN_DIR" ]; then
    echo "📂 Creating ~/bin directory..."
    mkdir -p "$BIN_DIR"
    echo "✅ Created $BIN_DIR"
else
    echo "✅ ~/bin directory already exists"
fi

# Create the wrapper script
echo "📝 Creating wrapper script: $WRAPPER_SCRIPT"
cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash

# IMAP Message Filter Wrapper Script
# This script is a wrapper around the main.py command

# The tool is installed at: $TOOL_DIR
TOOL_DIR="$TOOL_DIR"

# Check if the tool exists
if [ ! -f "\$TOOL_DIR/main.py" ]; then
    echo "❌ Error: Could not find IMAP Message Filter installation"
    echo "   Expected location: \$TOOL_DIR"
    echo "   Please re-run the installation script."
    exit 1
fi

# Change to the tool directory
cd "\$TOOL_DIR"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: 'uv' command not found"
    echo "   Please install uv first: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Execute the command with uv
exec uv run python main.py "\$@"
EOF

# Make the wrapper script executable
chmod +x "$WRAPPER_SCRIPT"
echo "✅ Created executable wrapper script"

# Check if ~/bin is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "🔧 Adding ~/bin to PATH..."
    
    # Determine which shell configuration file to use
    SHELL_CONFIG=""
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
        # Also check for .bash_profile on macOS
        if [[ "$OSTYPE" == "darwin"* ]] && [ -f "$HOME/.bash_profile" ]; then
            SHELL_CONFIG="$HOME/.bash_profile"
        fi
    fi
    
    if [ -n "$SHELL_CONFIG" ] && [ -f "$SHELL_CONFIG" ]; then
        # Add to PATH if not already there
        if ! grep -q "export PATH.*$BIN_DIR" "$SHELL_CONFIG"; then
            echo "" >> "$SHELL_CONFIG"
            echo "# Add ~/bin to PATH for IMAP Message Filter" >> "$SHELL_CONFIG"
            echo 'export PATH="$HOME/bin:$PATH"' >> "$SHELL_CONFIG"
            echo "✅ Added ~/bin to PATH in $SHELL_CONFIG"
        else
            echo "✅ ~/bin already in PATH in $SHELL_CONFIG"
        fi
    else
        echo "⚠️  Could not automatically add ~/bin to PATH"
        echo "   Please manually add the following line to your shell configuration file:"
        echo "   export PATH=\"\$HOME/bin:\$PATH\""
    fi
else
    echo "✅ ~/bin already in PATH"
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "📋 Usage:"
echo "   $REPO_NAME --help                    # Show help"
echo "   $REPO_NAME test-connection          # Test IMAP connection"
echo "   $REPO_NAME filter-status            # Show filter status"
echo "   $REPO_NAME apply-filters --dry-run  # Test filters"
echo ""
echo "🔧 If you can't run the command immediately, please:"
echo "   1. Restart your terminal, or"
echo "   2. Run: source ~/.zshrc (or ~/.bashrc)"
echo ""
echo "📁 Tool location: $TOOL_DIR"
echo "🔗 Wrapper script: $WRAPPER_SCRIPT"
echo ""
echo "💡 Next steps:"
echo "   1. Configure your IMAP settings: $REPO_NAME setup-config"
echo "   2. Extract filters from Thunderbird: $REPO_NAME extract-config"
echo "   3. Test your connection: $REPO_NAME test-connection"
