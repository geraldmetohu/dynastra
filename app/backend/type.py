from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime


# ---------- USER ----------
class UserBase(BaseModel):
    email: EmailStr
    role: str  # e.g. admin, client, potential, guest, other


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# ---------- CLIENT ----------
class ClientBase(BaseModel):
    name: str
    surname: str
    phone: str
    email: EmailStr
    address: Optional[str]
    dob: Optional[date]
    place_of_birth: Optional[str]
    sex: Optional[str]  # Male, Female, Other
    client_type: Optional[str]  # Individual / Company
    tasks: List[str] = []  # e.g. ["Consult", "Design"]
    status: Optional[str]  # Negotiating, Paid, etc.
    description: Optional[str]


class ClientCreate(ClientBase):
    pass


class Client(ClientBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# ---------- INVOICE ----------
class InvoiceBase(BaseModel):
    client_id: int
    service_description: str
    price: float
    invoice_type: str  # monthly, annual, one_time
    date_issued: Optional[date]
    status: str  # sent, paid, unpaid, overdue


class InvoiceCreate(InvoiceBase):
    pass


class Invoice(InvoiceBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# ---------- MESSAGE ----------
class MessageBase(BaseModel):
    sender: EmailStr
    recipient: EmailStr
    subject: str
    content: str


class MessageCreate(MessageBase):
    repeat_interval: Optional[str] = None  # e.g. weekly, monthly


class Message(MessageBase):
    id: int
    sent_at: Optional[datetime]
    repeat_interval: Optional[str]

    class Config:
        orm_mode = True


# ---------- REPEAT RULE ----------
class RepeatRuleBase(BaseModel):
    message_id: int
    interval: str  # weekly, monthly, etc.


class RepeatRuleCreate(RepeatRuleBase):
    pass


class RepeatRule(RepeatRuleBase):
    id: int

    class Config:
        orm_mode = True
