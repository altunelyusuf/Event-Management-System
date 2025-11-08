"""
Guest Management Schemas

Pydantic schemas for guest management system including validation
and serialization for guests, RSVPs, invitations, and seating.
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.models.guest import (
    GuestStatus, RSVPStatus, InvitationStatus,
    GuestCategory, MealPreference
)


# ============================================================================
# Guest Schemas
# ============================================================================

class GuestBase(BaseModel):
    """Base guest schema"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    category: GuestCategory = Field(GuestCategory.OTHER)
    is_vip: bool = Field(False)


class GuestCreate(GuestBase):
    """Schema for creating a new guest"""
    event_id: UUID

    # Plus-One
    allows_plus_one: bool = Field(False)
    plus_one_name: Optional[str] = Field(None, max_length=200)

    # Dietary
    dietary_restrictions: List[str] = Field(default_factory=list)
    meal_preference: Optional[str] = None
    special_requirements: Optional[str] = None
    accessibility_needs: Optional[str] = None

    # Seating
    table_number: Optional[int] = None
    seat_number: Optional[int] = None
    seating_preference: Optional[str] = None

    # Additional
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    age_group: Optional[str] = Field(None, pattern="^(child|adult|senior)$")
    group_id: Optional[UUID] = None

    @validator('email', 'phone')
    def at_least_one_contact(cls, v, values):
        """Ensure at least email or phone is provided"""
        if not v and 'email' in values and not values.get('email'):
            raise ValueError('Either email or phone must be provided')
        return v


class GuestUpdate(BaseModel):
    """Schema for updating a guest"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    category: Optional[GuestCategory] = None
    is_vip: Optional[bool] = None
    status: Optional[GuestStatus] = None

    # Plus-One
    allows_plus_one: Optional[bool] = None
    plus_one_name: Optional[str] = Field(None, max_length=200)

    # Dietary
    dietary_restrictions: Optional[List[str]] = None
    meal_preference: Optional[str] = None
    special_requirements: Optional[str] = None
    accessibility_needs: Optional[str] = None

    # Seating
    table_number: Optional[int] = None
    seat_number: Optional[int] = None
    seating_preference: Optional[str] = None

    # Gift
    gift_given: Optional[bool] = None
    gift_description: Optional[str] = None

    # Additional
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    age_group: Optional[str] = Field(None, pattern="^(child|adult|senior)$")
    group_id: Optional[UUID] = None


class GuestResponse(GuestBase):
    """Schema for guest response"""
    id: UUID
    event_id: UUID
    status: GuestStatus
    rsvp_status: RSVPStatus
    rsvp_responded_at: Optional[datetime]
    attending_count: int

    # Plus-One
    allows_plus_one: bool
    plus_one_name: Optional[str]

    # Dietary
    dietary_restrictions: List[str]
    meal_preference: Optional[str]
    special_requirements: Optional[str]
    accessibility_needs: Optional[str]

    # Seating
    table_number: Optional[int]
    seat_number: Optional[int]
    seating_preference: Optional[str]

    # Check-In
    checked_in: bool
    checked_in_at: Optional[datetime]

    # Invitation
    invitation_sent_at: Optional[datetime]
    invitation_opened_at: Optional[datetime]
    reminder_sent_count: int

    # Gift
    gift_given: bool
    gift_description: Optional[str]

    # Additional
    notes: Optional[str]
    tags: List[str]
    age_group: Optional[str]
    group_id: Optional[UUID]

    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True


class GuestBulkImport(BaseModel):
    """Schema for bulk importing guests"""
    guests: List[GuestCreate] = Field(..., min_items=1, max_items=1000)


class GuestBulkUpdate(BaseModel):
    """Schema for bulk updating guests"""
    guest_ids: List[UUID] = Field(..., min_items=1, max_items=500)
    update_data: GuestUpdate


# ============================================================================
# Guest Group Schemas
# ============================================================================

class GuestGroupBase(BaseModel):
    """Base guest group schema"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: GuestCategory = Field(GuestCategory.OTHER)
    color_code: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class GuestGroupCreate(GuestGroupBase):
    """Schema for creating a guest group"""
    event_id: UUID
    preferred_tables: List[int] = Field(default_factory=list)


class GuestGroupUpdate(BaseModel):
    """Schema for updating a guest group"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[GuestCategory] = None
    color_code: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    preferred_tables: Optional[List[int]] = None


class GuestGroupResponse(GuestGroupBase):
    """Schema for guest group response"""
    id: UUID
    event_id: UUID
    total_guests: int
    confirmed_guests: int
    declined_guests: int
    pending_guests: int
    preferred_tables: List[int]
    created_at: datetime
    updated_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True


# ============================================================================
# Invitation Schemas
# ============================================================================

class GuestInvitationBase(BaseModel):
    """Base invitation schema"""
    invitation_type: str = Field("email", pattern="^(email|sms|physical)$")
    subject: Optional[str] = Field(None, max_length=200)
    message: Optional[str] = None


class GuestInvitationCreate(GuestInvitationBase):
    """Schema for creating an invitation"""
    guest_id: UUID
    event_id: UUID
    is_reminder: bool = Field(False)


class GuestInvitationBulkCreate(BaseModel):
    """Schema for sending bulk invitations"""
    guest_ids: List[UUID] = Field(..., min_items=1, max_items=500)
    event_id: UUID
    invitation_type: str = Field("email", pattern="^(email|sms|physical)$")
    subject: str = Field(..., max_length=200)
    message: str


class GuestInvitationUpdate(BaseModel):
    """Schema for updating an invitation"""
    status: Optional[InvitationStatus] = None
    subject: Optional[str] = Field(None, max_length=200)
    message: Optional[str] = None


class GuestInvitationResponse(GuestInvitationBase):
    """Schema for invitation response"""
    id: UUID
    guest_id: UUID
    event_id: UUID
    status: InvitationStatus

    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    opened_at: Optional[datetime]
    responded_at: Optional[datetime]
    failed_at: Optional[datetime]
    failure_reason: Optional[str]

    open_count: int
    click_count: int
    last_opened_at: Optional[datetime]

    sent_to_email: Optional[str]
    sent_to_phone: Optional[str]

    is_reminder: bool
    reminder_number: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# RSVP Schemas
# ============================================================================

class RSVPResponseBase(BaseModel):
    """Base RSVP response schema"""
    status: RSVPStatus
    attending_count: int = Field(1, ge=0, le=20)


class RSVPResponseCreate(RSVPResponseBase):
    """Schema for creating an RSVP response"""
    guest_id: UUID
    event_id: UUID

    # Plus-One
    plus_one_attending: bool = Field(False)
    plus_one_name: Optional[str] = Field(None, max_length=200)
    plus_one_dietary_restrictions: List[str] = Field(default_factory=list)

    # Dietary
    dietary_restrictions: List[str] = Field(default_factory=list)
    meal_preference: Optional[str] = None

    # Messages
    message: Optional[str] = None
    special_requests: Optional[str] = None

    # Song Requests
    song_requests: List[str] = Field(default_factory=list, max_items=5)

    # Needs
    needs_accommodation: bool = Field(False)
    accommodation_details: Optional[str] = None
    needs_transportation: bool = Field(False)
    transportation_details: Optional[str] = None

    # Tracking
    response_method: Optional[str] = Field(None, pattern="^(web|email|phone|sms)$")
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    @validator('attending_count')
    def validate_attending_count(cls, v, values):
        """Validate attending count based on status"""
        if values.get('status') == RSVPStatus.NOT_ATTENDING and v > 0:
            raise ValueError('Attending count must be 0 for not attending status')
        return v


class RSVPResponseUpdate(BaseModel):
    """Schema for updating an RSVP response"""
    status: Optional[RSVPStatus] = None
    attending_count: Optional[int] = Field(None, ge=0, le=20)

    plus_one_attending: Optional[bool] = None
    plus_one_name: Optional[str] = Field(None, max_length=200)
    plus_one_dietary_restrictions: Optional[List[str]] = None

    dietary_restrictions: Optional[List[str]] = None
    meal_preference: Optional[str] = None

    message: Optional[str] = None
    special_requests: Optional[str] = None

    song_requests: Optional[List[str]] = Field(None, max_items=5)

    needs_accommodation: Optional[bool] = None
    accommodation_details: Optional[str] = None
    needs_transportation: Optional[bool] = None
    transportation_details: Optional[str] = None


class RSVPResponseResponse(RSVPResponseBase):
    """Schema for RSVP response"""
    id: UUID
    guest_id: UUID
    event_id: UUID

    plus_one_attending: bool
    plus_one_name: Optional[str]
    plus_one_dietary_restrictions: List[str]

    dietary_restrictions: List[str]
    meal_preference: Optional[str]

    message: Optional[str]
    special_requests: Optional[str]

    song_requests: List[str]

    needs_accommodation: bool
    accommodation_details: Optional[str]
    needs_transportation: bool
    transportation_details: Optional[str]

    responded_at: datetime
    response_method: Optional[str]

    is_latest: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Seating Arrangement Schemas
# ============================================================================

class SeatingArrangementBase(BaseModel):
    """Base seating arrangement schema"""
    table_number: int = Field(..., ge=1)
    table_name: Optional[str] = Field(None, max_length=100)
    table_capacity: int = Field(8, ge=1, le=50)
    table_shape: Optional[str] = Field(None, pattern="^(round|rectangle|square)$")


class SeatingArrangementCreate(SeatingArrangementBase):
    """Schema for creating a seating arrangement"""
    event_id: UUID

    # Location
    section: Optional[str] = Field(None, max_length=50)
    position_x: Optional[int] = None
    position_y: Optional[int] = None

    # Details
    is_vip_table: bool = Field(False)
    is_kids_table: bool = Field(False)
    table_type: Optional[str] = Field(None, pattern="^(head_table|guest_table|vendor_table)$")

    # Features
    special_features: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class SeatingArrangementUpdate(BaseModel):
    """Schema for updating a seating arrangement"""
    table_number: Optional[int] = Field(None, ge=1)
    table_name: Optional[str] = Field(None, max_length=100)
    table_capacity: Optional[int] = Field(None, ge=1, le=50)
    table_shape: Optional[str] = Field(None, pattern="^(round|rectangle|square)$")

    section: Optional[str] = Field(None, max_length=50)
    position_x: Optional[int] = None
    position_y: Optional[int] = None

    is_vip_table: Optional[bool] = None
    is_kids_table: Optional[bool] = None
    table_type: Optional[str] = Field(None, pattern="^(head_table|guest_table|vendor_table)$")

    special_features: Optional[List[str]] = None
    notes: Optional[str] = None


class SeatingArrangementResponse(SeatingArrangementBase):
    """Schema for seating arrangement response"""
    id: UUID
    event_id: UUID

    section: Optional[str]
    position_x: Optional[int]
    position_y: Optional[int]

    is_vip_table: bool
    is_kids_table: bool
    table_type: Optional[str]

    assigned_seats: int
    reserved_seats: int

    special_features: List[str]
    notes: Optional[str]

    created_at: datetime
    updated_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True


# ============================================================================
# Check-In Schemas
# ============================================================================

class GuestCheckInBase(BaseModel):
    """Base check-in schema"""
    actual_attending_count: int = Field(1, ge=1, le=20)
    plus_one_checked_in: bool = Field(False)
    plus_one_name: Optional[str] = Field(None, max_length=200)


class GuestCheckInCreate(GuestCheckInBase):
    """Schema for creating a check-in"""
    guest_id: UUID
    event_id: UUID

    check_in_method: str = Field("manual", pattern="^(manual|qr_code|nfc)$")
    check_in_location: Optional[str] = Field(None, max_length=100)

    gift_bag_given: bool = Field(False)
    name_tag_given: bool = Field(False)
    table_card_given: bool = Field(False)

    notes: Optional[str] = None
    special_assistance_provided: Optional[str] = None


class GuestCheckInUpdate(BaseModel):
    """Schema for updating a check-in"""
    actual_attending_count: Optional[int] = Field(None, ge=1, le=20)
    plus_one_checked_in: Optional[bool] = None
    plus_one_name: Optional[str] = Field(None, max_length=200)

    gift_bag_given: Optional[bool] = None
    name_tag_given: Optional[bool] = None
    table_card_given: Optional[bool] = None

    notes: Optional[str] = None
    special_assistance_provided: Optional[str] = None


class GuestCheckInResponse(GuestCheckInBase):
    """Schema for check-in response"""
    id: UUID
    guest_id: UUID
    event_id: UUID

    checked_in_at: datetime
    checked_in_by: UUID

    check_in_method: str
    qr_code_scanned: bool
    check_in_location: Optional[str]
    check_in_device: Optional[str]

    gift_bag_given: bool
    name_tag_given: bool
    table_card_given: bool

    notes: Optional[str]
    special_assistance_provided: Optional[str]

    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Dietary Restriction Schemas
# ============================================================================

class DietaryRestrictionBase(BaseModel):
    """Base dietary restriction schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = Field(None, pattern="^(allergy|preference|religious)$")
    severity: Optional[str] = Field(None, pattern="^(mild|moderate|severe)$")


class DietaryRestrictionCreate(DietaryRestrictionBase):
    """Schema for creating a dietary restriction"""
    alternative_options: Optional[str] = None
    kitchen_notes: Optional[str] = None
    is_common: bool = Field(False)


class DietaryRestrictionUpdate(BaseModel):
    """Schema for updating a dietary restriction"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = Field(None, pattern="^(allergy|preference|religious)$")
    severity: Optional[str] = Field(None, pattern="^(mild|moderate|severe)$")
    alternative_options: Optional[str] = None
    kitchen_notes: Optional[str] = None
    is_active: Optional[bool] = None
    is_common: Optional[bool] = None


class DietaryRestrictionResponse(DietaryRestrictionBase):
    """Schema for dietary restriction response"""
    id: UUID
    alternative_options: Optional[str]
    kitchen_notes: Optional[str]
    usage_count: int
    is_active: bool
    is_common: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Statistics Schemas
# ============================================================================

class GuestStatistics(BaseModel):
    """Guest statistics for an event"""
    total_guests: int
    invited_guests: int
    confirmed_guests: int
    declined_guests: int
    tentative_guests: int
    pending_guests: int
    checked_in_guests: int

    total_attending: int  # Including plus-ones
    plus_ones_count: int

    # By category
    by_category: dict

    # Dietary
    dietary_restrictions_summary: dict

    # Seating
    total_tables: int
    assigned_seats: int
    available_seats: int

    # RSVP
    rsvp_response_rate: float

    # Check-in
    check_in_rate: float


class SeatingStatistics(BaseModel):
    """Seating statistics for an event"""
    total_tables: int
    total_capacity: int
    assigned_seats: int
    available_seats: int
    occupancy_rate: float

    vip_tables: int
    kids_tables: int

    tables_by_section: dict
    tables_by_type: dict
