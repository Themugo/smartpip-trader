"""
AI Collaboration Bus - Agent Communication Layer

Event-driven communication between agents.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of agent messages"""
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    COMMAND = "command"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class Priority(Enum):
    """Message priority"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentCapability:
    """Capability of an agent"""
    name: str
    description: str
    version: str = "1.0.0"
    input_types: List[str] = field(default_factory=list)
    output_types: List[str] = field(default_factory=list)


@dataclass
class AgentMessage:
    """Message exchanged between agents"""
    id: str
    message_type: MessageType
    sender_id: str
    receiver_id: Optional[str]  # None for broadcast
    
    # Content
    action: str
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # Routing
    topic: str = ""  # For pub/sub
    correlation_id: Optional[str] = None  # For request/response
    reply_to: Optional[str] = None  # Channel to reply to
    
    # Priority
    priority: Priority = Priority.NORMAL
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Metadata
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "action": self.action,
            "payload": self.payload,
            "topic": self.topic,
            "correlation_id": self.correlation_id,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "trace_id": self.trace_id,
        }


@dataclass
class AgentRegistration:
    """Registration info for an agent"""
    agent_id: str
    agent_name: str
    agent_type: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    subscriptions: Set[str] = field(default_factory=set)  # Topics to subscribe
    
    # Status
    is_active: bool = True
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    
    # Resources
    max_concurrent_tasks: int = 5
    current_tasks: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "capabilities": [
                {"name": c.name, "description": c.description}
                for c in self.capabilities
            ],
            "is_active": self.is_active,
            "current_tasks": self.current_tasks,
        }


class AICollaborationBus:
    """
    AI Collaboration Bus for agent communication.
    
    Features:
    - Publish/Subscribe messaging
    - Request/Response pattern
    - Topic-based routing
    - Message persistence
    - Dead letter queue
    - Message tracing
    - Priority queuing
    - Agent discovery
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentRegistration] = {}
        self._handlers: Dict[str, List[Callable]] = {}  # topic -> handlers
        self._queues: Dict[str, asyncio.PriorityQueue] = {}  # agent_id -> queue
        self._pending_responses: Dict[str, asyncio.Future] = {}  # correlation_id -> future
        
        # Statistics
        self._messages_sent: int = 0
        self._messages_received: int = 0
        self._dead_letter_queue: List[AgentMessage] = []
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        # Message history
        self._message_history: List[AgentMessage] = []
        self._max_history = 10000
    
    async def register_agent(self, registration: AgentRegistration) -> None:
        """Register an agent"""
        async with self._lock:
            self._agents[registration.agent_id] = registration
            
            # Create message queue
            self._queues[registration.agent_id] = asyncio.PriorityQueue()
            
            # Subscribe to topics
            for topic in registration.subscriptions:
                if topic not in self._handlers:
                    self._handlers[topic] = []
        
        logger.info(f"Registered agent: {registration.agent_name} ({registration.agent_id})")
    
    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent"""
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
            
            if agent_id in self._queues:
                del self._queues[agent_id]
        
        logger.info(f"Unregistered agent: {agent_id}")
    
    async def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find agents that have a specific capability"""
        agents = []
        
        for agent_id, registration in self._agents.items():
            if not registration.is_active:
                continue
            
            for cap in registration.capabilities:
                if cap.name == capability:
                    agents.append(agent_id)
                    break
        
        return agents
    
    async def send_message(
        self,
        message: AgentMessage,
    ) -> None:
        """Send a message to an agent or topic"""
        message.id = message.id or str(uuid.uuid4())
        message.created_at = datetime.utcnow()
        
        async with self._lock:
            self._messages_sent += 1
            
            # Add to history
            self._message_history.append(message)
            if len(self._message_history) > self._max_history:
                self._message_history.pop(0)
        
        if message.receiver_id:
            # Direct message
            await self._deliver_to_agent(message)
        elif message.topic:
            # Topic-based publish
            await self._publish_to_topic(message)
        else:
            # Broadcast
            await self._broadcast(message)
    
    async def _deliver_to_agent(self, message: AgentMessage) -> None:
        """Deliver message to specific agent"""
        queue = self._queues.get(message.receiver_id)
        if queue:
            priority = message.priority.value
            await queue.put((priority, message))
        else:
            logger.warning(f"Agent not found: {message.receiver_id}")
            self._dead_letter_queue.append(message)
    
    async def _publish_to_topic(self, message: AgentMessage) -> None:
        """Publish message to topic subscribers"""
        handlers = self._handlers.get(message.topic, [])
        
        for handler in handlers:
            try:
                asyncio.create_task(self._safe_handle(handler, message))
            except Exception as e:
                logger.error(f"Handler error: {e}")
    
    async def _broadcast(self, message: AgentMessage) -> None:
        """Broadcast to all active agents"""
        for agent_id, queue in self._queues.items():
            if agent_id != message.sender_id:  # Don't send to self
                registration = self._agents.get(agent_id)
                if registration and registration.is_active:
                    priority = message.priority.value
                    await queue.put((priority, message))
    
    async def _safe_handle(self, handler: Callable, message: AgentMessage) -> None:
        """Safely execute a handler"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)
        except Exception as e:
            logger.error(f"Handler error for {message.topic}: {e}")
    
    async def request_response(
        self,
        sender_id: str,
        receiver_id: str,
        action: str,
        payload: Dict[str, Any],
        timeout: float = 30,
    ) -> Optional[Dict[str, Any]]:
        """Send request and wait for response"""
        correlation_id = str(uuid.uuid4())
        response_future = asyncio.Future()
        
        self._pending_responses[correlation_id] = response_future
        
        message = AgentMessage(
            id=str(uuid.uuid4()),
            message_type=MessageType.REQUEST,
            sender_id=sender_id,
            receiver_id=receiver_id,
            action=action,
            payload=payload,
            correlation_id=correlation_id,
            priority=Priority.NORMAL,
        )
        
        await self.send_message(message)
        
        try:
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout: {action}")
            return None
        finally:
            del self._pending_responses[correlation_id]
    
    async def receive_message(self, agent_id: str) -> Optional[AgentMessage]:
        """Receive a message for an agent"""
        queue = self._queues.get(agent_id)
        if not queue:
            return None
        
        try:
            priority, message = await asyncio.wait_for(queue.get(), timeout=1)
            async with self._lock:
                self._messages_received += 1
            return message
        except asyncio.TimeoutError:
            return None
    
    async def subscribe(self, agent_id: str, topic: str) -> None:
        """Subscribe an agent to a topic"""
        if topic not in self._handlers:
            self._handlers[topic] = []
        
        if agent_id not in self._handlers[topic]:
            self._handlers[topic].append(agent_id)
    
    async def unsubscribe(self, agent_id: str, topic: str) -> None:
        """Unsubscribe an agent from a topic"""
        if topic in self._handlers and agent_id in self._handlers[topic]:
            self._handlers[topic].remove(agent_id)
    
    async def publish_event(
        self,
        sender_id: str,
        topic: str,
        event_type: str,
        payload: Dict[str, Any],
        priority: Priority = Priority.NORMAL,
    ) -> None:
        """Publish an event to a topic"""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            message_type=MessageType.EVENT,
            sender_id=sender_id,
            receiver_id=None,
            action=event_type,
            payload=payload,
            topic=topic,
            priority=priority,
        )
        
        await self.send_message(message)
    
    async def send_command(
        self,
        sender_id: str,
        receiver_id: str,
        command: str,
        payload: Dict[str, Any],
    ) -> None:
        """Send a command to an agent"""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            message_type=MessageType.COMMAND,
            sender_id=sender_id,
            receiver_id=receiver_id,
            action=command,
            payload=payload,
            priority=Priority.HIGH,
        )
        
        await self.send_message(message)
    
    async def heartbeat(self, agent_id: str) -> None:
        """Send heartbeat from agent"""
        if agent_id in self._agents:
            self._agents[agent_id].last_heartbeat = datetime.utcnow()
    
    def get_active_agents(self) -> List[AgentRegistration]:
        """Get all active agents"""
        return [
            reg for reg in self._agents.values()
            if reg.is_active
        ]
    
    def get_agent(self, agent_id: str) -> Optional[AgentRegistration]:
        """Get agent registration"""
        return self._agents.get(agent_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get bus statistics"""
        return {
            "total_agents": len(self._agents),
            "active_agents": sum(1 for a in self._agents.values() if a.is_active),
            "topics": len(self._handlers),
            "messages_sent": self._messages_sent,
            "messages_received": self._messages_received,
            "dead_letter_count": len(self._dead_letter_queue),
            "pending_responses": len(self._pending_responses),
        }
