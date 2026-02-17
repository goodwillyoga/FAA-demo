#!/usr/bin/env python3
"""Generate the actual LangGraph state diagram from the orchestrator implementation."""

import subprocess
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from altitude_warning.orchestrator import Orchestrator


def render_mermaid_to_png(mmd_path: str, output_path: str) -> bool:
    """Render a Mermaid .mmd file to PNG using mermaid-cli (mmdc).
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            ["mmdc", "-i", mmd_path, "-o", output_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except FileNotFoundError:
        print("⚠ mermaid-cli (mmdc) not found. Install with: npm install -g @mermaid-js/mermaid-cli")
        return False
    except subprocess.CalledProcessError as e:
        print(f"⚠ Error rendering mermaid diagram: {e.stderr}")
        return False


def main() -> None:
    """Generate and save the LangGraph state diagrams."""
    # Generate actual implementation diagram from LangGraph
    orchestrator = Orchestrator(trace_enabled=False)
    
    actual_output = "diagrams/langgraph-state-actual.png"
    saved_path = orchestrator.save_graph_diagram(actual_output)
    print(f"✓ LangGraph actual state diagram saved to: {saved_path}")
    
    # Render spec diagram from mermaid file
    spec_mmd = "diagrams/langgraph-state-flow.mmd"
    spec_output = "diagrams/langgraph-state-spec.png"
    
    if Path(spec_mmd).exists():
        if render_mermaid_to_png(spec_mmd, spec_output):
            print(f"✓ Spec state diagram rendered to: {Path(spec_output).absolute()}")
        else:
            print(f"⚠ Could not render spec diagram from {spec_mmd}")
    else:
        print(f"⚠ Spec diagram not found at {spec_mmd}")
    
    print("\nCompare diagrams:")
    print(f"  Actual: {actual_output}")
    print(f"  Spec:   {spec_output}")


if __name__ == "__main__":
    main()
