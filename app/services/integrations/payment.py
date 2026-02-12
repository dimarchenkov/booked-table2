"""Payment provider interfaces and implementations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Payment


@dataclass(slots=True)
class PaymentInitResult:
    """Result payload for payment initialization."""

    payment_url: str
    provider_payment_id: str | None = None


class PaymentProvider(Protocol):
    """Interface for payment providers."""

    def init_payment(self, payment: Payment) -> PaymentInitResult:
        """Initialize a payment and return provider details."""

    def verify_webhook(self, payload: dict) -> bool:
        """Verify webhook authenticity."""


class StubPaymentProvider:
    """Stub payment provider used when integrations are disabled."""

    def init_payment(self, payment: Payment) -> PaymentInitResult:
        """Return a dummy payment URL for stub payments."""

        return PaymentInitResult(payment_url=f"http://localhost:8000/payments/{payment.id}/stub")

    def verify_webhook(self, payload: dict) -> bool:
        """Always approve stub webhooks."""

        return True


class TBankPaymentProvider:
    """Placeholder for TBank payment provider."""

    def __init__(self, terminal_key: str, token: str) -> None:
        self.terminal_key = terminal_key
        self.token = token

    def init_payment(self, payment: Payment) -> PaymentInitResult:
        """Initialize a payment in TBank (stub implementation)."""

        return PaymentInitResult(payment_url=f"http://localhost:8000/payments/{payment.id}/tbank")

    def verify_webhook(self, payload: dict) -> bool:
        """Verify webhook signature (stub implementation)."""

        return True
