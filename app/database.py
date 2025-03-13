"""
Database module for the ePOS Proxy Server web interface.
"""
import logging
from typing import AsyncGenerator
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship

logger = logging.getLogger(__name__)

# SQLite database URL
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./epos_proxy.db"

# Create async engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Create session
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Create base model
Base = declarative_base()


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmailTemplate(Base):
    """Email template model for skinnable emails."""
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    subject_template = Column(String)
    html_template = Column(Text)
    css_styles = Column(Text)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    
    created_by = relationship("User")


class EmailTheme(Base):
    """Email theme model for customizing colors and typography."""
    __tablename__ = "email_themes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    primary_color = Column(String, default="#0066cc")
    secondary_color = Column(String, default="#4d94ff")
    accent_color = Column(String, default="#ff6600")
    text_color = Column(String, default="#333333")
    background_color = Column(String, default="#ffffff")
    font_family = Column(String, default="Arial, sans-serif")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    
    created_by = relationship("User")


class CompanyBranding(Base):
    """Company branding model for logos and contact information."""
    __tablename__ = "company_branding"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    company_name = Column(String)
    company_logo_path = Column(String)
    company_website = Column(String)
    company_email = Column(String)
    company_phone = Column(String)
    company_address = Column(Text)
    social_facebook = Column(String)
    social_twitter = Column(String)
    social_instagram = Column(String)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    
    created_by = relationship("User")


class PrintJob(Base):
    """Print job model for tracking print history."""
    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, index=True)
    printer_name = Column(String, index=True)
    content = Column(Text)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    file_path = Column(String)
    email_sent = Column(Boolean, default=False)
    email_recipients = Column(String)
    email_sent_at = Column(DateTime)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize the database."""
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
        
    logger.info("Database initialized") 