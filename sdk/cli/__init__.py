"""
SDK CLI
=======

Command line interface for SmartPip SDK.
"""

import sys
import os
import json
import argparse
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def cmd_init(args):
    """Initialize a new SmartPip project"""
    project_name = args.name
    
    # Create project structure
    dirs = [
        f"{project_name}/strategies",
        f"{project_name}/plugins",
        f"{project_name}/models",
        f"{project_name}/data",
        f"{project_name}/config",
        f"{project_name}/tests",
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    
    # Create __init__.py files
    for d in dirs:
        init_file = os.path.join(d, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write(f'"""{os.path.basename(d)} package"""\n')
    
    # Create config file
    config = {
        "project_name": project_name,
        "version": "0.1.0",
        "smartpip_version": ">=1.0.0",
        "strategies": [],
        "plugins": [],
    }
    
    config_file = os.path.join(project_name, "smartpip.json")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    # Create requirements.txt
    requirements = [
        "smartpip-sdk>=1.0.0",
    ]
    
    req_file = os.path.join(project_name, "requirements.txt")
    with open(req_file, "w") as f:
        f.write("\n".join(requirements))
    
    print(f"✓ Project '{project_name}' initialized")
    print(f"  cd {project_name}")
    print(f"  pip install -r requirements.txt")


def cmd_new_strategy(args):
    """Create a new strategy"""
    strategy_name = args.name
    strategy_file = f"strategies/{strategy_name}.py"
    
    template = f'''"""Trading Strategy: {strategy_name}"""

from sdk.strategy import Strategy, Signal, OrderSide


class {strategy_name.title().replace("_", "")}Strategy(Strategy):
    """My trading strategy"""
    
    strategy_id = "{strategy_name}"
    strategy_name = "{strategy_name}"
    version = "0.1.0"
    
    def __init__(self):
        super().__init__()
        # Configure strategy parameters
        self.configure({{
            "lookback_period": 20,
            "threshold": 0.01,
        }})
    
    def on_init(self):
        """Initialize strategy"""
        pass
    
    def on_tick(self, tick, context):
        """Process market tick"""
        signals = []
        
        # Your trading logic here
        # signal = Signal(
        #     symbol=tick["symbol"],
        #     side=OrderSide.BUY,
        #     strength=0.8,
        #     confidence=0.9
        # )
        # signals.append(signal)
        
        return signals


# Register strategy
strategy = {strategy_name.title().replace("_", "")}Strategy()
'''

    os.makedirs("strategies", exist_ok=True)
    with open(strategy_file, "w") as f:
        f.write(template)
    
    print(f"✓ Strategy '{strategy_name}' created at {strategy_file}")


def cmd_new_plugin(args):
    """Create a new plugin"""
    plugin_name = args.name
    plugin_file = f"plugins/{plugin_name}.py"
    
    template = f'''"""SmartPip Plugin: {plugin_name}"""

from sdk.plugin import Plugin, PluginMetadata, PluginHook, create_plugin


@create_plugin(
    name="{plugin_name}",
    version="0.1.0",
    hooks=[PluginHook.ON_TICK, PluginHook.ON_SIGNAL],
    description="My custom plugin"
)
class {plugin_name.title().replace("-", "")}Plugin(Plugin):
    """My trading plugin"""
    
    def on_init(self):
        """Initialize plugin"""
        pass
    
    def on_tick(self, tick):
        """Handle market tick"""
        pass
    
    def on_signal(self, signal):
        """Handle trading signal"""
        pass


# Register plugin
plugin = {plugin_name.title().replace("-", "")}Plugin()
'''

    os.makedirs("plugins", exist_ok=True)
    with open(plugin_file, "w") as f:
        f.write(template)
    
    print(f"✓ Plugin '{plugin_name}' created at {plugin_file}")


def cmd_validate(args):
    """Validate plugins and strategies"""
    import importlib.util
    
    errors = []
    warnings = []
    
    # Validate plugins
    if args.path:
        plugin_dir = args.path
    else:
        plugin_dir = "plugins"
    
    if os.path.exists(plugin_dir):
        for filename in os.listdir(plugin_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                filepath = os.path.join(plugin_dir, filename)
                
                try:
                    spec = importlib.util.spec_from_file_location("plugin", filepath)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Check for Plugin class
                    has_plugin = False
                    for name, obj in module.__dict__.items():
                        if isinstance(obj, type) and issubclass(obj, Plugin) and obj != Plugin:
                            has_plugin = True
                            if not obj.metadata:
                                warnings.append(f"{filename}: Plugin without metadata")
                    
                    if not has_plugin:
                        errors.append(f"{filename}: No Plugin class found")
                
                except Exception as e:
                    errors.append(f"{filename}: {str(e)}")
    
    # Print results
    if errors:
        print("❌ Errors:")
        for e in errors:
            print(f"  - {e}")
    
    if warnings:
        print("⚠ Warnings:")
        for w in warnings:
            print(f"  - {w}")
    
    if not errors and not warnings:
        print("✓ All validations passed")
    
    return len(errors) == 0


def cmd_check_deps(args):
    """Check dependencies"""
    print("Checking dependencies...")
    
    # Check Python version
    py_version = sys.version_info
    print(f"  Python: {py_version.major}.{py_version.minor}.{py_version.micro}")
    
    # Check required packages
    required = ["requests", "pandas", "numpy"]
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
            print(f"  ✓ {pkg}")
        except ImportError:
            print(f"  ✗ {pkg} (not installed)")
            missing.append(pkg)
    
    if missing:
        print(f"\nInstall missing packages: pip install {' '.join(missing)}")
        return False
    
    print("\n✓ All dependencies satisfied")
    return True


def cmd_profile(args):
    """Profile strategy performance"""
    print("Strategy Profiling")
    print("=" * 40)
    print("Note: Run strategies with profiling enabled")
    print("Usage: python -m cProfile -o output.prof script.py")


def cmd_doc(args):
    """Generate documentation"""
    print("Documentation Generator")
    print("=" * 40)
    
    docs_dir = "docs"
    os.makedirs(docs_dir, exist_ok=True)
    
    # Generate API docs
    readme_content = """# SmartPip Project

## Project Structure

```
.
├── strategies/     # Trading strategies
├── plugins/         # Custom plugins
├── models/          # AI models
├── data/            # Market data
├── config/          # Configuration
└── tests/           # Test cases
```

## Getting Started

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run backtest:
   ```
   smartpip run --strategy your_strategy
   ```

3. Deploy:
   ```
   smartpip deploy
   ```
"""
    
    readme_file = os.path.join(docs_dir, "README.md")
    with open(readme_file, "w") as f:
        f.write(readme_content)
    
    print(f"✓ Documentation generated in {docs_dir}/")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="SmartPip SDK CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # init
    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument("name", help="Project name")
    init_parser.set_defaults(func=cmd_init)
    
    # new strategy
    strategy_parser = subparsers.add_parser("new:strategy", help="Create a new strategy")
    strategy_parser.add_argument("name", help="Strategy name")
    strategy_parser.set_defaults(func=cmd_new_strategy)
    
    # new plugin
    plugin_parser = subparsers.add_parser("new:plugin", help="Create a new plugin")
    plugin_parser.add_argument("name", help="Plugin name")
    plugin_parser.set_defaults(func=cmd_new_plugin)
    
    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate plugins and strategies")
    validate_parser.add_argument("--path", help="Path to validate")
    validate_parser.set_defaults(func=cmd_validate)
    
    # check-deps
    deps_parser = subparsers.add_parser("check-deps", help="Check dependencies")
    deps_parser.set_defaults(func=cmd_check_deps)
    
    # profile
    profile_parser = subparsers.add_parser("profile", help="Profile strategy")
    profile_parser.set_defaults(func=cmd_profile)
    
    # doc
    doc_parser = subparsers.add_parser("doc", help="Generate documentation")
    doc_parser.set_defaults(func=cmd_doc)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 1
    
    try:
        result = args.func(args)
        return 0 if result is None or result else 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
