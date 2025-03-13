"""
Web API module for the ePOS Proxy Server.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from pydantic import BaseModel, EmailStr, validator

from database import (
    User, EmailTemplate, EmailTheme, CompanyBranding, PrintJob,
    get_db
)
from auth import (
    get_current_active_user, get_current_admin_user,
    authenticate_user, create_access_token, get_password_hash,
    Token, UserBase, UserCreate, UserUpdate
)
from email_service import (
    render_email_template, send_email
)

# Constants
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Setup router
router = APIRouter()

# Setup logging
logger = logging.getLogger(__name__)


# Pydantic models for API
class EmailTemplateBase(BaseModel):
    """Base model for email templates."""
    name: str
    description: Optional[str] = None
    subject_template: str
    html_template: str
    css_styles: str
    is_default: bool = False


class EmailTemplateCreate(EmailTemplateBase):
    """Model for creating email templates."""
    pass


class EmailTemplateUpdate(BaseModel):
    """Model for updating email templates."""
    name: Optional[str] = None
    description: Optional[str] = None
    subject_template: Optional[str] = None
    html_template: Optional[str] = None
    css_styles: Optional[str] = None
    is_default: Optional[bool] = None


class EmailTemplateResponse(EmailTemplateBase):
    """Model for email template responses."""
    id: int
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None

    class Config:
        """Pydantic model configuration."""
        orm_mode = True


class EmailThemeBase(BaseModel):
    """Base model for email themes."""
    name: str
    description: Optional[str] = None
    primary_color: str
    secondary_color: str
    accent_color: str
    text_color: str
    background_color: str
    font_family: str
    is_default: bool = False


class EmailThemeCreate(EmailThemeBase):
    """Model for creating email themes."""
    pass


class EmailThemeUpdate(BaseModel):
    """Model for updating email themes."""
    name: Optional[str] = None
    description: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    text_color: Optional[str] = None
    background_color: Optional[str] = None
    font_family: Optional[str] = None
    is_default: Optional[bool] = None


class EmailThemeResponse(EmailThemeBase):
    """Model for email theme responses."""
    id: int
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None

    class Config:
        """Pydantic model configuration."""
        orm_mode = True


class CompanyBrandingBase(BaseModel):
    """Base model for company branding."""
    name: str
    company_name: str
    company_logo_path: Optional[str] = None
    company_website: Optional[str] = None
    company_email: Optional[EmailStr] = None
    company_phone: Optional[str] = None
    company_address: Optional[str] = None
    social_facebook: Optional[str] = None
    social_twitter: Optional[str] = None
    social_instagram: Optional[str] = None
    is_default: bool = False


class CompanyBrandingCreate(CompanyBrandingBase):
    """Model for creating company branding."""
    pass


class CompanyBrandingUpdate(BaseModel):
    """Model for updating company branding."""
    name: Optional[str] = None
    company_name: Optional[str] = None
    company_logo_path: Optional[str] = None
    company_website: Optional[str] = None
    company_email: Optional[EmailStr] = None
    company_phone: Optional[str] = None
    company_address: Optional[str] = None
    social_facebook: Optional[str] = None
    social_twitter: Optional[str] = None
    social_instagram: Optional[str] = None
    is_default: Optional[bool] = None


class CompanyBrandingResponse(CompanyBrandingBase):
    """Model for company branding responses."""
    id: int
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None

    class Config:
        """Pydantic model configuration."""
        orm_mode = True


class PrintJobResponse(BaseModel):
    """Model for print job responses."""
    id: int
    job_id: str
    printer_name: str
    status: str
    created_at: datetime
    email_sent: bool
    email_recipients: Optional[str] = None
    email_sent_at: Optional[datetime] = None

    class Config:
        """Pydantic model configuration."""
        orm_mode = True


class EmailSendRequest(BaseModel):
    """Model for sending emails."""
    recipients: List[EmailStr]
    template_id: Optional[int] = None
    theme_id: Optional[int] = None
    branding_id: Optional[int] = None
    context: Dict[str, Any] = {}
    print_job_id: Optional[str] = None


class EmailPreviewRequest(BaseModel):
    """Model for previewing emails."""
    template_id: Optional[int] = None
    theme_id: Optional[int] = None
    branding_id: Optional[int] = None
    context: Dict[str, Any] = {}


class EmailPreviewResponse(BaseModel):
    """Model for email preview responses."""
    subject: str
    html_content: str


# Authentication endpoints
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Get an access token."""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


# User endpoints
@router.get("/users/me", response_model=UserBase)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user."""
    return current_user


@router.get("/users", response_model=List[UserBase])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all users."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return users


@router.post("/users", response_model=UserBase, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a user."""
    # Check if user exists
    result = await db.execute(select(User).where(User.username == user.username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    
    # Create user
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=get_password_hash(user.password),
        is_admin=user.is_admin,
        is_active=user.is_active
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    logger.info(f"User created: {user.username}")
    return db_user


# Email template endpoints
@router.get("/email/templates", response_model=List[EmailTemplateResponse])
async def get_email_templates(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all email templates."""
    result = await db.execute(select(EmailTemplate).offset(skip).limit(limit))
    templates = result.scalars().all()
    return templates


@router.get("/email/templates/{template_id}", response_model=EmailTemplateResponse)
async def get_email_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get an email template by ID."""
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))
    template = result.scalars().first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    return template


@router.post("/email/templates", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_email_template(
    template: EmailTemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an email template."""
    # Check if name exists
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.name == template.name))
    existing_template = result.scalars().first()
    if existing_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template name already exists",
        )
    
    # Handle default template
    if template.is_default is True:
        # Reset other default templates
        await db.execute(
            "UPDATE email_templates SET is_default = 0 WHERE is_default = 1"
        )
    
    # Create template
    db_template = EmailTemplate(
        name=template.name,
        description=template.description,
        subject_template=template.subject_template,
        html_template=template.html_template,
        css_styles=template.css_styles,
        is_default=template.is_default,
        created_by_id=current_user.id
    )
    db.add(db_template)
    await db.commit()
    await db.refresh(db_template)
    
    logger.info(f"Email template created: {template.name}")
    return db_template


# Email theme endpoints
@router.get("/email/themes", response_model=List[EmailThemeResponse])
async def get_email_themes(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all email themes."""
    result = await db.execute(select(EmailTheme).offset(skip).limit(limit))
    themes = result.scalars().all()
    return themes


@router.post("/email/themes", response_model=EmailThemeResponse, status_code=status.HTTP_201_CREATED)
async def create_email_theme(
    theme: EmailThemeCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an email theme."""
    # Check if name exists
    result = await db.execute(select(EmailTheme).where(EmailTheme.name == theme.name))
    existing_theme = result.scalars().first()
    if existing_theme:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Theme name already exists",
        )
    
    # Handle default theme
    if theme.is_default is True:
        # Reset other default themes
        await db.execute(
            "UPDATE email_themes SET is_default = 0 WHERE is_default = 1"
        )
    
    # Create theme
    db_theme = EmailTheme(
        name=theme.name,
        description=theme.description,
        primary_color=theme.primary_color,
        secondary_color=theme.secondary_color,
        accent_color=theme.accent_color,
        text_color=theme.text_color,
        background_color=theme.background_color,
        font_family=theme.font_family,
        is_default=theme.is_default,
        created_by_id=current_user.id
    )
    db.add(db_theme)
    await db.commit()
    await db.refresh(db_theme)
    
    logger.info(f"Email theme created: {theme.name}")
    return db_theme


# Company branding endpoints
@router.get("/branding", response_model=List[CompanyBrandingResponse])
async def get_company_brandings(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all company brandings."""
    result = await db.execute(select(CompanyBranding).offset(skip).limit(limit))
    brandings = result.scalars().all()
    return brandings


@router.post("/branding", response_model=CompanyBrandingResponse, status_code=status.HTTP_201_CREATED)
async def create_company_branding(
    branding: CompanyBrandingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create company branding."""
    # Check if name exists
    result = await db.execute(select(CompanyBranding).where(CompanyBranding.name == branding.name))
    existing_branding = result.scalars().first()
    if existing_branding:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Branding name already exists",
        )
    
    # Handle default branding
    if branding.is_default is True:
        # Reset other default brandings
        await db.execute(
            "UPDATE company_branding SET is_default = 0 WHERE is_default = 1"
        )
    
    # Create branding
    db_branding = CompanyBranding(
        name=branding.name,
        company_name=branding.company_name,
        company_logo_path=branding.company_logo_path,
        company_website=branding.company_website,
        company_email=branding.company_email,
        company_phone=branding.company_phone,
        company_address=branding.company_address,
        social_facebook=branding.social_facebook,
        social_twitter=branding.social_twitter,
        social_instagram=branding.social_instagram,
        is_default=branding.is_default,
        created_by_id=current_user.id
    )
    db.add(db_branding)
    await db.commit()
    await db.refresh(db_branding)
    
    logger.info(f"Company branding created: {branding.name}")
    return db_branding


# Logo upload endpoint
@router.post("/branding/logo")
async def upload_company_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Upload a company logo."""
    from pathlib import Path
    import shutil
    import os
    
    # Check file
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Create directory if it doesn't exist
    upload_dir = Path("static/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    file_extension = os.path.splitext(file.filename)[1]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"logo_{timestamp}{file_extension}"
    file_path = upload_dir / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    logger.info(f"Logo uploaded: {filename}")
    
    return {
        "filename": filename,
        "path": f"/static/uploads/{filename}"
    }


# Email sending endpoint
@router.post("/email/send")
async def send_email_receipt(
    request: EmailSendRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send an email receipt."""
    # Check if print job exists if provided
    if request.print_job_id:
        result = await db.execute(select(PrintJob).where(PrintJob.job_id == request.print_job_id))
        print_job = result.scalars().first()
        if not print_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Print job not found",
            )
    
    try:
        # Render email template
        rendered = await render_email_template(
            db,
            template_id=request.template_id,
            theme_id=request.theme_id,
            branding_id=request.branding_id,
            context=request.context
        )
        
        # Send email
        sent = await send_email(
            recipients=request.recipients,
            subject=rendered["subject"],
            html_content=rendered["html_content"]
        )
        
        if not sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email",
            )
        
        # Update print job if provided
        if request.print_job_id and sent:
            print_job.email_sent = True
            print_job.email_recipients = ",".join(request.recipients)
            print_job.email_sent_at = datetime.now()
            await db.commit()
        
        logger.info(f"Email sent to {', '.join(request.recipients)}")
        
        return {"status": "success", "message": "Email sent successfully"}
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending email: {str(e)}",
        )


# Print job endpoints
@router.get("/print_jobs", response_model=List[PrintJobResponse])
async def get_print_jobs(
    skip: int = 0,
    limit: int = 50,
    printer: Optional[str] = None,
    days: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all print jobs."""
    query = select(PrintJob).order_by(desc(PrintJob.created_at))
    
    # Filter by printer
    if printer:
        query = query.where(PrintJob.printer_name == printer)
    
    # Filter by days
    if days:
        cutoff_date = datetime.now() - timedelta(days=days)
        query = query.where(PrintJob.created_at >= cutoff_date)
    
    # Add pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return jobs


@router.get("/print_jobs/{job_id}", response_model=PrintJobResponse)
async def get_print_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a print job by ID."""
    result = await db.execute(select(PrintJob).where(PrintJob.job_id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Print job not found",
        )
    return job


# Template preview endpoint
@router.post("/email/preview", response_model=EmailPreviewResponse)
async def preview_email_template(
    request: EmailPreviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Preview an email template."""
    try:
        # Render email template
        rendered = await render_email_template(
            db,
            template_id=request.template_id,
            theme_id=request.theme_id,
            branding_id=request.branding_id,
            context=request.context
        )
        
        return {
            "subject": rendered["subject"],
            "html_content": rendered["html_content"]
        }
    except Exception as e:
        logger.error(f"Error previewing email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error previewing email: {str(e)}",
        ) 