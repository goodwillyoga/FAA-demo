#!/usr/bin/env bash
# Launch the Streamlit demo UI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🚁 Launching FAA Altitude Warning Demo UI..."
echo "📂 Project root: $PROJECT_ROOT"
echo ""

# Check if streamlit is installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "⚠️  Streamlit not found. Installing..."
    pip install streamlit>=1.30
fi

# Run the demo
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
streamlit run src/altitude_warning/demo_ui.py --server.port 8501 --server.headless false
