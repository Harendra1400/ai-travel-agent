"""Import all models so SQLAlchemy registers complete metadata."""

from app.db.models.agent_run import AgentRun
from app.db.models.approval import Approval
from app.db.models.booking import Booking
from app.db.models.conversation import Conversation
from app.db.models.memory import Memory
from app.db.models.message import Message
from app.db.models.operations import AuditEvent, OutboxEvent, ProviderConnection
from app.db.models.payment import Payment
from app.db.models.planning import Itinerary, ItineraryItem, Traveler
from app.db.models.preference import Preference
from app.db.models.tool_call import ToolCall
from app.db.models.trip import Trip
from app.db.models.user import User

__all__ = [
    "AgentRun",
    "Approval",
    "AuditEvent",
    "Booking",
    "Conversation",
    "Itinerary",
    "ItineraryItem",
    "Memory",
    "Message",
    "OutboxEvent",
    "Payment",
    "Preference",
    "ProviderConnection",
    "ToolCall",
    "Trip",
    "Traveler",
    "User",
]
