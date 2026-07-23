"""Stable enumerations persisted by the database models."""

from enum import StrEnum


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    """Persist enum values instead of Python member names."""
    return [member.value for member in enum_class]


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class TripStatus(StrEnum):
    DRAFT = "draft"
    PLANNING = "planning"
    BOOKED = "booked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class BookingType(StrEnum):
    FLIGHT = "flight"
    LODGING = "lodging"
    RAIL = "rail"
    VEHICLE = "vehicle"
    ACTIVITY = "activity"
    TRANSFER = "transfer"
    OTHER = "other"


class BookingStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class PaymentKind(StrEnum):
    AUTHORIZATION = "authorization"
    CAPTURE = "capture"
    REFUND = "refund"
    VOID = "void"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_USER = "waiting_for_user"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolCallStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"


class ToolRisk(StrEnum):
    READ = "read"
    WRITE = "write"
    FINANCIAL = "financial"


class CabinClass(StrEnum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class MemoryKind(StrEnum):
    PREFERENCE = "preference"
    FACT = "fact"
    EPISODIC = "episodic"
    SUMMARY = "summary"


class ItineraryStatus(StrEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class ItineraryItemKind(StrEnum):
    FLIGHT = "flight"
    LODGING = "lodging"
    RAIL = "rail"
    TRANSFER = "transfer"
    ACTIVITY = "activity"
    MEAL = "meal"
    NOTE = "note"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class ProviderConnectionStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    ERROR = "error"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
