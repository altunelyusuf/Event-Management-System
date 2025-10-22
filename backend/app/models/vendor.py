"""
CelebraTech Event Management System - Vendor Models
Sprint 3: Vendor Profile Foundation
FR-003: Vendor Marketplace & Discovery
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Numeric, Enum as SQLEnum, Date, Time
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class VendorCategory(str, enum.Enum):
    """Vendor category enumeration"""
    VENUE = "VENUE"
    CATERING = "CATERING"
    PHOTOGRAPHY = "PHOTOGRAPHY"
    MUSIC_ENTERTAINMENT = "MUSIC_ENTERTAINMENT"
    DECORATION = "DECORATION"
    BEAUTY = "BEAUTY"
    INVITATION = "INVITATION"
    TRANSPORTATION = "TRANSPORTATION"
    ACCOMMODATION = "ACCOMMODATION"


class VendorStatus(str, enum.Enum):
    """Vendor status enumeration"""
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"
    DELETED = "DELETED"


class BusinessType(str, enum.Enum):
    """Business type enumeration"""
    INDIVIDUAL = "INDIVIDUAL"
    COMPANY = "COMPANY"


class SubscriptionTier(str, enum.Enum):
    """Subscription tier enumeration"""
    BASIC = "BASIC"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"


class Vendor(Base):
    """
    Vendor model - Service providers in the marketplace
    """
    __tablename__ = "vendors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Business Information
    business_name = Column(String(255), nullable=False)
    business_type = Column(SQLEnum(BusinessType), nullable=True)
    category = Column(SQLEnum(VendorCategory), nullable=False, index=True)
    description = Column(Text, nullable=False)
    short_description = Column(String(500), nullable=True)

    # Branding
    logo_url = Column(String(500), nullable=True)
    cover_image_url = Column(String(500), nullable=True)

    # Contact Information
    website_url = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False)

    # Location
    location_city = Column(String(100), nullable=False, index=True)
    location_district = Column(String(100), nullable=True)
    location_address = Column(Text, nullable=True)
    location_lat = Column(Numeric(10, 8), nullable=True)
    location_lng = Column(Numeric(11, 8), nullable=True)
    service_radius_km = Column(Integer, default=50)

    # Verification
    verified = Column(Boolean, default=False, index=True)
    verification_date = Column(DateTime(timezone=True), nullable=True)
    verification_notes = Column(Text, nullable=True)

    # Sustainability
    eco_certified = Column(Boolean, default=False)
    eco_score = Column(Numeric(5, 2), nullable=True)

    # Ratings and Performance
    avg_rating = Column(Numeric(3, 2), default=0, index=True)
    review_count = Column(Integer, default=0)
    booking_count = Column(Integer, default=0)
    completion_rate = Column(Numeric(5, 2), nullable=True)
    response_time_hours = Column(Numeric(6, 2), nullable=True)

    # Subscription
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.BASIC, nullable=False)
    subscription_started_at = Column(DateTime(timezone=True), nullable=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    zero_commission_until = Column(DateTime(timezone=True), nullable=True)
    commission_rate = Column(Numeric(5, 4), default=0.10)

    # Status
    status = Column(SQLEnum(VendorStatus), default=VendorStatus.PENDING_VERIFICATION, nullable=False, index=True)
    featured = Column(Boolean, default=False, index=True)
    featured_until = Column(DateTime(timezone=True), nullable=True)

    # Business Registration
    business_registration_number = Column(String(100), nullable=True)
    tax_id = Column(String(100), nullable=True)

    # Metadata
    bank_account_info = Column(Text, nullable=True)  # Encrypted
    metadata = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    services = relationship("VendorService", back_populates="vendor", cascade="all, delete-orphan")
    portfolio = relationship("VendorPortfolio", back_populates="vendor", cascade="all, delete-orphan")
    availability = relationship("VendorAvailability", back_populates="vendor", cascade="all, delete-orphan")
    team_members = relationship("VendorTeamMember", back_populates="vendor", cascade="all, delete-orphan")
    certifications = relationship("VendorCertification", back_populates="vendor", cascade="all, delete-orphan")
    working_hours = relationship("VendorWorkingHours", back_populates="vendor", cascade="all, delete-orphan")
    subcategories = relationship("VendorSubcategory", back_populates="vendor", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Vendor {self.business_name} ({self.category})>"


class VendorSubcategory(Base):
    """
    Vendor subcategory model - Additional service categories
    """
    __tablename__ = "vendor_subcategories"

    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), primary_key=True)
    subcategory = Column(String(100), nullable=False, primary_key=True)

    # Relationships
    vendor = relationship("Vendor", back_populates="subcategories")

    def __repr__(self):
        return f"<VendorSubcategory {self.subcategory} for vendor {self.vendor_id}>"


class PriceUnit(str, enum.Enum):
    """Price unit enumeration"""
    PER_PERSON = "PER_PERSON"
    PER_HOUR = "PER_HOUR"
    PER_DAY = "PER_DAY"
    PER_EVENT = "PER_EVENT"
    FLAT_RATE = "FLAT_RATE"
    CUSTOM = "CUSTOM"


class VendorService(Base):
    """
    Vendor service model - Services offered by vendors
    """
    __tablename__ = "vendor_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    # Service Details
    service_name = Column(String(255), nullable=False)
    service_category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Pricing
    base_price = Column(Numeric(12, 2), nullable=True)
    max_price = Column(Numeric(12, 2), nullable=True)
    price_unit = Column(SQLEnum(PriceUnit), nullable=True)

    # Capacity
    min_capacity = Column(Integer, nullable=True)
    max_capacity = Column(Integer, nullable=True)
    duration_hours = Column(Numeric(5, 2), nullable=True)

    # Options
    is_customizable = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    vendor = relationship("Vendor", back_populates="services")

    def __repr__(self):
        return f"<VendorService {self.service_name} for vendor {self.vendor_id}>"


class MediaType(str, enum.Enum):
    """Media type enumeration"""
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class VendorPortfolio(Base):
    """
    Vendor portfolio model - Portfolio items (photos/videos)
    """
    __tablename__ = "vendor_portfolio"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    # Portfolio Item
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Media
    media_type = Column(SQLEnum(MediaType), nullable=False)
    media_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)

    # Organization
    order_index = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False, index=True)
    event_type = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    vendor = relationship("Vendor", back_populates="portfolio")

    def __repr__(self):
        return f"<VendorPortfolio {self.title} for vendor {self.vendor_id}>"


class AvailabilityStatus(str, enum.Enum):
    """Availability status enumeration"""
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    BLOCKED = "BLOCKED"
    TENTATIVE = "TENTATIVE"


class VendorAvailability(Base):
    """
    Vendor availability model - Availability calendar
    """
    __tablename__ = "vendor_availability"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    # Availability
    date = Column(Date, nullable=False, index=True)
    status = Column(SQLEnum(AvailabilityStatus), nullable=False, index=True)

    # Booking Reference
    booking_id = Column(UUID(as_uuid=True), nullable=True)  # Will link to bookings later

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    vendor = relationship("Vendor", back_populates="availability")

    def __repr__(self):
        return f"<VendorAvailability {self.date} for vendor {self.vendor_id} - {self.status}>"


class VendorTeamMember(Base):
    """
    Vendor team member model - Team members of vendor
    """
    __tablename__ = "vendor_team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    # Team Member
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)

    # Contact
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)

    # Organization
    order_index = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    vendor = relationship("Vendor", back_populates="team_members")
    user = relationship("User")

    def __repr__(self):
        return f"<VendorTeamMember {self.name} for vendor {self.vendor_id}>"


class VendorCertification(Base):
    """
    Vendor certification model - Certifications and licenses
    """
    __tablename__ = "vendor_certifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    # Certification
    certification_name = Column(String(255), nullable=False)
    issuing_organization = Column(String(255), nullable=False)
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    certificate_url = Column(String(500), nullable=True)

    # Verification
    verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    vendor = relationship("Vendor", back_populates="certifications")

    def __repr__(self):
        return f"<VendorCertification {self.certification_name} for vendor {self.vendor_id}>"


class VendorWorkingHours(Base):
    """
    Vendor working hours model - Weekly working hours
    """
    __tablename__ = "vendor_working_hours"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)

    # Day of week (0 = Monday, 6 = Sunday)
    day_of_week = Column(Integer, nullable=False)

    # Hours
    open_time = Column(Time, nullable=False)
    close_time = Column(Time, nullable=False)
    is_closed = Column(Boolean, default=False)

    # Relationships
    vendor = relationship("Vendor", back_populates="working_hours")

    def __repr__(self):
        return f"<VendorWorkingHours day {self.day_of_week} for vendor {self.vendor_id}>"
