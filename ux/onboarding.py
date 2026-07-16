"""
Interactive Onboarding
====================

Tutorial and onboarding system.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class OnboardingStep:
    """A step in the onboarding process"""
    step_id: str
    title: str
    content: str
    
    # Element targeting
    target_selector: Optional[str] = None  # CSS selector
    target_position: str = "bottom"  # top, bottom, left, right, center
    
    # Actions
    action_type: str = "click"  # click, type, wait, none
    action_target: Optional[str] = None
    action_value: Optional[str] = None
    
    # Navigation
    next_button_text: str = "Next"
    back_button_text: str = "Back"
    skip_button_text: str = "Skip"
    
    # Validation
    validation_fn: Optional[str] = None  # Function name to call
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "content": self.content,
            "target_selector": self.target_selector,
            "position": self.target_position,
            "action_type": self.action_type,
        }


@dataclass
class Tutorial:
    """A complete tutorial"""
    tutorial_id: str
    name: str
    description: str
    steps: List[OnboardingStep] = field(default_factory=list)
    
    # State
    is_completed: bool = False
    completed_at: Optional[float] = None
    
    # Tracking
    current_step_index: int = 0
    completion_count: int = 0
    
    # Conditions
    trigger_condition: Optional[str] = None  # When to show
    required_features: List[str] = field(default_factory=list)  # Features this covers
    
    def get_current_step(self) -> Optional[OnboardingStep]:
        """Get the current step"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def next_step(self) -> bool:
        """Move to next step"""
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            return True
        return False
    
    def previous_step(self) -> bool:
        """Move to previous step"""
        if self.current_step_index > 0:
            self.current_step_index -= 1
            return True
        return False
    
    def complete(self) -> None:
        """Complete the tutorial"""
        self.is_completed = True
        self.completed_at = time.time()
        self.completion_count += 1
    
    def reset(self) -> None:
        """Reset tutorial progress"""
        self.current_step_index = 0
        self.is_completed = False
        self.completed_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tutorial_id": self.tutorial_id,
            "name": self.name,
            "description": self.description,
            "is_completed": self.is_completed,
            "current_step": self.current_step_index,
            "total_steps": len(self.steps),
            "completion_count": self.completion_count,
        }


class OnboardingManager:
    """
    Manages tutorials and onboarding.
    """
    
    def __init__(self):
        self._tutorials: Dict[str, Tutorial] = {}
        self._current_tutorial: Optional[Tutorial] = None
        self._listeners: List[Callable] = []
        self._completion_history: Dict[str, List[float]] = {}  # Tutorial completions
        
        # Initialize default tutorials
        self._initialize_default_tutorials()
    
    def _initialize_default_tutorials(self) -> None:
        """Initialize default onboarding tutorials"""
        # Welcome tutorial
        welcome_steps = [
            OnboardingStep(
                step_id="welcome",
                title="Welcome to SmartPip",
                content="This quick tour will help you get started with the trading platform.",
                action_type="none",
            ),
            OnboardingStep(
                step_id="dashboard",
                title="Dashboard",
                content="Your dashboard shows an overview of your portfolio, recent activity, and key metrics.",
                target_selector=".dashboard",
                target_position="bottom",
            ),
            OnboardingStep(
                step_id="charts",
                title="Trading Charts",
                content="Analyze market data with interactive charts. Use the toolbar to add indicators.",
                target_selector=".chart",
                target_position="right",
            ),
            OnboardingStep(
                step_id="orders",
                title="Order Entry",
                content="Place new orders here. Select the symbol, quantity, and order type.",
                target_selector=".order-entry",
                target_position="left",
            ),
            OnboardingStep(
                step_id="shortcuts",
                title="Keyboard Shortcuts",
                content="Press Ctrl+K to open the command palette for quick access to all features.",
                action_type="none",
            ),
        ]
        
        self.register_tutorial(Tutorial(
            tutorial_id="welcome",
            name="Welcome Tour",
            description="Quick introduction to the platform",
            steps=welcome_steps,
            required_features=["core"],
        ))
        
        # Strategy tutorial
        strategy_steps = [
            OnboardingStep(
                step_id="strategy_overview",
                title="Strategy Management",
                content="Create and manage your trading strategies here.",
                target_selector=".strategy-panel",
                target_position="bottom",
            ),
            OnboardingStep(
                step_id="strategy_create",
                title="Create Strategy",
                content="Click this button to create a new trading strategy.",
                target_selector=".btn-new-strategy",
                target_position="right",
                action_type="click",
            ),
        ]
        
        self.register_tutorial(Tutorial(
            tutorial_id="strategy_basics",
            name="Strategy Basics",
            description="Learn how to create and manage strategies",
            steps=strategy_steps,
            required_features=["strategies"],
        ))
    
    # ========== Tutorial Management ==========
    
    def register_tutorial(self, tutorial: Tutorial) -> None:
        """Register a tutorial"""
        self._tutorials[tutorial.tutorial_id] = tutorial
    
    def unregister_tutorial(self, tutorial_id: str) -> bool:
        """Unregister a tutorial"""
        return self._tutorials.pop(tutorial_id, None) is not None
    
    def get_tutorial(self, tutorial_id: str) -> Optional[Tutorial]:
        """Get a tutorial"""
        return self._tutorials.get(tutorial_id)
    
    def get_all_tutorials(self) -> List[Tutorial]:
        """Get all tutorials"""
        return list(self._tutorials.values())
    
    def get_incomplete_tutorials(self) -> List[Tutorial]:
        """Get tutorials that haven't been completed"""
        return [t for t in self._tutorials.values() if not t.is_completed]
    
    # ========== Progress ==========
    
    def start_tutorial(self, tutorial_id: str) -> Optional[Tutorial]:
        """Start a tutorial"""
        tutorial = self._tutorials.get(tutorial_id)
        if tutorial:
            tutorial.reset()
            self._current_tutorial = tutorial
            self._notify_change("started", tutorial)
        return tutorial
    
    def get_current_tutorial(self) -> Optional[Tutorial]:
        """Get the currently active tutorial"""
        return self._current_tutorial
    
    def get_current_step(self) -> Optional[OnboardingStep]:
        """Get the current step in the active tutorial"""
        if self._current_tutorial:
            return self._current_tutorial.get_current_step()
        return None
    
    def next_step(self) -> bool:
        """Move to next step"""
        if self._current_tutorial:
            if self._current_tutorial.next_step():
                self._notify_change("step", self._current_tutorial.get_current_step())
                return True
            else:
                # Tutorial complete
                self._current_tutorial.complete()
                self._record_completion(self._current_tutorial.tutorial_id)
                self._notify_change("completed", self._current_tutorial)
                self._current_tutorial = None
        return False
    
    def previous_step(self) -> bool:
        """Move to previous step"""
        if self._current_tutorial:
            if self._current_tutorial.previous_step():
                self._notify_change("step", self._current_tutorial.get_current_step())
                return True
        return False
    
    def skip_tutorial(self) -> None:
        """Skip the current tutorial"""
        if self._current_tutorial:
            tutorial_id = self._current_tutorial.tutorial_id
            self._current_tutorial = None
            self._notify_change("skipped", tutorial_id)
    
    def reset_tutorial(self, tutorial_id: str) -> Optional[Tutorial]:
        """Reset a tutorial to the beginning"""
        tutorial = self._tutorials.get(tutorial_id)
        if tutorial:
            tutorial.reset()
            self._notify_change("reset", tutorial)
        return tutorial
    
    # ========== Completion History ==========
    
    def get_completion_history(self, tutorial_id: str) -> List[float]:
        """Get completion timestamps for a tutorial"""
        return self._completion_history.get(tutorial_id, [])
    
    def _record_completion(self, tutorial_id: str) -> None:
        """Record tutorial completion"""
        if tutorial_id not in self._completion_history:
            self._completion_history[tutorial_id] = []
        self._completion_history[tutorial_id].append(time.time())
    
    # ========== Listeners ==========
    
    def on_change(self, callback: Callable) -> None:
        """Register change listener"""
        self._listeners.append(callback)
    
    def _notify_change(self, event: str, data: Any = None) -> None:
        """Notify listeners of changes"""
        for callback in self._listeners:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Onboarding listener error: {e}")
    
    # ========== Export ==========
    
    def export_progress(self) -> Dict[str, Any]:
        """Export onboarding progress"""
        return {
            tutorial_id: {
                "is_completed": t.is_completed,
                "current_step": t.current_step_index,
                "completion_count": t.completion_count,
                "completions": self._completion_history.get(tutorial_id, []),
            }
            for tutorial_id, t in self._tutorials.items()
        }
    
    def import_progress(self, progress: Dict[str, Any]) -> None:
        """Import onboarding progress"""
        for tutorial_id, data in progress.items():
            tutorial = self._tutorials.get(tutorial_id)
            if tutorial:
                if data.get("is_completed"):
                    tutorial.is_completed = True
                tutorial.current_step_index = data.get("current_step", 0)
                tutorial.completion_count = data.get("completion_count", 0)
        
        if "completion_history" in progress:
            self._completion_history = progress["completion_history"]
