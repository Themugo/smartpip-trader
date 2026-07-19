"""
Developer Console

Interactive developer console for:
- Command execution
- API testing
- System inspection
- Performance profiling
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import deque
from uuid import uuid4

logger = logging.getLogger(__name__)


class CommandCategory(Enum):
    """Categories for console commands"""
    SYSTEM = "system"
    PLUGIN = "plugin"
    TRADING = "trading"
    ACCOUNT = "account"
    RISK = "risk"
    DATA = "data"
    UTILITY = "utility"
    DEBUG = "debug"


@dataclass
class Command:
    """Console command definition"""
    name: str
    description: str
    category: CommandCategory
    usage: str
    handler: Callable
    aliases: List[str] = field(default_factory=list)
    parameters: List[Dict[str, str]] = field(default_factory=list)
    requires_admin: bool = False
    hidden: bool = False


@dataclass
class CommandResult:
    """Result of command execution"""
    command: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
        }


class CommandRegistry:
    """Registry for console commands"""
    
    def __init__(self):
        self._commands: Dict[str, Command] = {}
        self._aliases: Dict[str, str] = {}  # alias -> command name
    
    def register(self, command: Command) -> None:
        """Register a command"""
        self._commands[command.name] = command
        
        # Register aliases
        for alias in command.aliases:
            self._aliases[alias] = command.name
    
    def get(self, name: str) -> Optional[Command]:
        """Get a command by name or alias"""
        name = self._aliases.get(name, name)
        return self._commands.get(name)
    
    def get_by_category(self, category: CommandCategory) -> List[Command]:
        """Get all commands in a category"""
        return [c for c in self._commands.values() if c.category == category]
    
    def get_all(self) -> List[Command]:
        """Get all commands"""
        return list(self._commands.values())
    
    def search(self, query: str) -> List[Command]:
        """Search commands by name or description"""
        query_lower = query.lower()
        return [
            c for c in self._commands.values()
            if query_lower in c.name.lower() or query_lower in c.description.lower()
        ]


class DeveloperConsole:
    """
    Interactive developer console for system management.
    
    Features:
    - Command registration and execution
    - Command history
    - Auto-completion
    - Output formatting
    - Performance tracking
    """
    
    def __init__(self):
        self._registry = CommandRegistry()
        self._history: deque = deque(maxlen=1000)
        self._session_id = str(uuid4())
        self._variables: Dict[str, Any] = {}
        self._init_default_commands()
    
    @property
    def registry(self) -> CommandRegistry:
        return self._registry
    
    def _init_default_commands(self) -> None:
        """Initialize default system commands"""
        
        # Help command
        self._registry.register(Command(
            name="help",
            description="Show help for a command",
            category=CommandCategory.SYSTEM,
            usage="help [command]",
            handler=self._cmd_help,
        ))
        
        # Clear command
        self._registry.register(Command(
            name="clear",
            description="Clear the console",
            category=CommandCategory.SYSTEM,
            usage="clear",
            handler=lambda _: "",
        ))
        
        # History command
        self._registry.register(Command(
            name="history",
            description="Show command history",
            category=CommandCategory.SYSTEM,
            usage="history [limit]",
            handler=self._cmd_history,
        ))
        
        # Variables command
        self._registry.register(Command(
            name="vars",
            description="Show/set variables",
            category=CommandCategory.SYSTEM,
            usage="vars [name] [value]",
            handler=self._cmd_vars,
        ))
        
        # Status command
        self._registry.register(Command(
            name="status",
            description="Show system status",
            category=CommandCategory.SYSTEM,
            usage="status",
            handler=self._cmd_status,
        ))
        
        # Plugins command
        self._registry.register(Command(
            name="plugins",
            description="List plugins",
            category=CommandCategory.PLUGIN,
            usage="plugins [list|info <id>]",
            handler=self._cmd_plugins,
        ))
        
        # Risk command
        self._registry.register(Command(
            name="risk",
            description="Risk management commands",
            category=CommandCategory.RISK,
            usage="risk [status|limits|reset]",
            handler=self._cmd_risk,
        ))
    
    async def execute(self, command_line: str) -> CommandResult:
        """
        Execute a command.
        
        Args:
            command_line: The command string to execute
            
        Returns:
            CommandResult with execution details
        """
        start_time = time.perf_counter()
        
        # Add to history
        self._history.append(command_line)
        
        # Parse command
        parts = self._parse_command(command_line)
        if not parts:
            return CommandResult(
                command=command_line,
                success=False,
                output=None,
                error="Empty command",
                execution_time=time.perf_counter() - start_time,
            )
        
        command_name = parts[0]
        args = parts[1:]
        
        # Get command
        command = self._registry.get(command_name)
        if not command:
            return CommandResult(
                command=command_line,
                success=False,
                output=None,
                error=f"Unknown command: {command_name}",
                execution_time=time.perf_counter() - start_time,
            )
        
        # Execute command
        try:
            output = await command.handler(CommandContext(args, self))
            
            return CommandResult(
                command=command_line,
                success=True,
                output=output,
                execution_time=time.perf_counter() - start_time,
            )
            
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return CommandResult(
                command=command_line,
                success=False,
                output=None,
                error=str(e),
                execution_time=time.perf_counter() - start_time,
            )
    
    def _parse_command(self, command_line: str) -> List[str]:
        """Parse command line into parts"""
        parts = []
        current = ""
        in_quote = False
        quote_char = None
        
        for char in command_line:
            if char in ('"', "'") and not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char and in_quote:
                in_quote = False
                quote_char = None
            elif char.isspace() and not in_quote:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
        
        if current:
            parts.append(current)
        
        return parts
    
    # Default command handlers
    
    def _cmd_help(self, ctx: "CommandContext") -> str:
        """Help command handler"""
        if ctx.args:
            command = self._registry.get(ctx.args[0])
            if command:
                lines = [
                    f"Command: {command.name}",
                    f"Description: {command.description}",
                    f"Usage: {command.usage}",
                    f"Category: {command.category.value}",
                ]
                if command.aliases:
                    lines.append(f"Aliases: {', '.join(command.aliases)}")
                return "\n".join(lines)
            return f"Unknown command: {ctx.args[0]}"
        
        # List all commands
        lines = ["Available commands:"]
        current_category = None
        
        for command in sorted(self._registry.get_all(), key=lambda c: (c.category.value, c.name)):
            if command.hidden:
                continue
            if command.category != current_category:
                lines.append(f"\n[{command.category.value.upper()}]")
                current_category = command.category
            lines.append(f"  {command.name}: {command.description}")
        
        return "\n".join(lines)
    
    def _cmd_history(self, ctx: "CommandContext") -> str:
        """History command handler"""
        limit = int(ctx.args[0]) if ctx.args else 20
        history = list(self._history)[-limit:]
        
        return "\n".join(
            f"{i+1}: {cmd}" for i, cmd in enumerate(history)
        )
    
    def _cmd_vars(self, ctx: "CommandContext") -> str:
        """Variables command handler"""
        if not ctx.args:
            # List all variables
            if not self._variables:
                return "No variables defined"
            return "\n".join(
                f"{name}: {value}" for name, value in self._variables.items()
            )
        
        if len(ctx.args) == 1:
            # Get variable
            name = ctx.args[0]
            if name in self._variables:
                return f"{name}: {self._variables[name]}"
            return f"Variable not found: {name}"
        
        # Set variable
        name = ctx.args[0]
        value = " ".join(ctx.args[1:])
        
        # Try to parse as JSON
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
        
        self._variables[name] = value
        return f"Set {name} = {value}"
    
    def _cmd_status(self, ctx: "CommandContext") -> str:
        """Status command handler"""
        from utils import system_logger
        return f"System Status: OK\nSession: {self._session_id}"
    
    def _cmd_plugins(self, ctx: "CommandContext") -> str:
        """Plugins command handler"""
        if not ctx.args:
            # List plugins
            return "Plugin management commands available"
        
        subcmd = ctx.args[0]
        if subcmd == "list":
            return "No plugins loaded"
        
        return f"Unknown subcommand: {subcmd}"
    
    def _cmd_risk(self, ctx: "CommandContext") -> str:
        """Risk command handler"""
        if not ctx.args:
            return "Risk commands: status, limits, reset"
        
        subcmd = ctx.args[0]
        if subcmd == "status":
            return "Risk status: NORMAL"
        elif subcmd == "limits":
            return "Risk limits: Default configuration"
        
        return f"Unknown subcommand: {subcmd}"
    
    def get_history(self, limit: int = 50) -> List[str]:
        """Get command history"""
        return list(self._history)[-limit:]
    
    def clear_history(self) -> None:
        """Clear command history"""
        self._history.clear()
    
    def set_variable(self, name: str, value: Any) -> None:
        """Set a console variable"""
        self._variables[name] = value
    
    def get_variable(self, name: str) -> Optional[Any]:
        """Get a console variable"""
        return self._variables.get(name)


@dataclass
class CommandContext:
    """Context passed to command handlers"""
    args: List[str]
    console: DeveloperConsole
    
    @property
    def arg_string(self) -> str:
        """Get arguments as a single string"""
        return " ".join(self.args)


# Global console instance
_console: Optional[DeveloperConsole] = None


def get_console() -> DeveloperConsole:
    """Get the global console instance"""
    global _console
    if _console is None:
        _console = DeveloperConsole()
    return _console


def register_command(
    name: str,
    description: str,
    category: CommandCategory,
    usage: str,
    handler: Callable,
    aliases: Optional[List[str]] = None,
) -> None:
    """Register a new command with the global console"""
    console = get_console()
    command = Command(
        name=name,
        description=description,
        category=category,
        usage=usage,
        handler=handler,
        aliases=aliases or [],
    )
    console.registry.register(command)
