from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ContactCreate(BaseModel):
    """Schema for creating a new Contact."""
    first_name: str = Field(..., description="First name of the contact")
    last_name: str = Field(..., description="Last name of the contact")
    email: str = Field(..., description="Email address of the contact")
    phone: str | None = Field(default=None, description="Phone number of the contact")
    company: str | None = Field(default=None, description="Company/organization name")


class Contact(BaseModel):
    """Canonical domain model for a Contact."""
    id: str = Field(..., description="Unique contact identifier")
    first_name: str = Field(..., description="First name of the contact")
    last_name: str = Field(..., description="Last name of the contact")
    email: str = Field(..., description="Email address of the contact")
    phone: str | None = Field(default=None, description="Phone number of the contact")
    company: str | None = Field(default=None, description="Company/organization name")
    created_at: datetime | None = Field(default=None, description="Timestamp when the contact was created")


class OrderItem(BaseModel):
    """Individual line item within an Order."""
    item_id: str | None = Field(default=None, description="Product or item identifier")
    name: str = Field(..., description="Display name of the item")
    quantity: int = Field(default=1, description="Quantity ordered")
    unit_price: float = Field(default=0.0, description="Unit price per item")


class Order(BaseModel):
    """Canonical domain model for an Order."""
    id: str = Field(..., description="Unique order identifier")
    contact_id: str = Field(..., description="Identifier of the contact who placed the order")
    items: list[OrderItem] = Field(default_factory=list, description="List of items ordered")
    total_amount: float = Field(..., description="Total monetary amount of the order")
    currency: str = Field(default="USD", description="Currency code (e.g. USD, EUR)")
    status: str = Field(default="pending", description="Order status (e.g. pending, shipped, delivered, cancelled)")
    shipping_address: str | dict[str, Any] | None = Field(default=None, description="Shipping destination address")


class AppointmentSlot(BaseModel):
    """Canonical domain model for an Appointment Slot on a calendar."""
    id: str = Field(..., description="Unique appointment slot identifier")
    start_time: datetime = Field(..., description="Slot start time (ISO 8601 / datetime)")
    end_time: datetime = Field(..., description="Slot end time (ISO 8601 / datetime)")
    title: str = Field(default="Meeting", description="Title or subject of the appointment")
    attendee_email: str | None = Field(default=None, description="Email address of attendee")
    status: str = Field(default="available", description="Slot status (e.g. available, booked, cancelled)")


class Payment(BaseModel):
    """Canonical domain model for a Payment transaction."""
    id: str = Field(..., description="Unique payment identifier")
    order_id: str = Field(..., description="Identifier of the order being paid")
    amount: float = Field(..., description="Payment amount charged")
    currency: str = Field(default="USD", description="Currency code (e.g. USD, EUR)")
    payment_method: str = Field(default="credit_card", description="Payment method used")
    status: str = Field(default="completed", description="Payment status (e.g. pending, completed, failed, refunded)")
    transaction_timestamp: datetime | None = Field(default=None, description="Timestamp of the transaction")
