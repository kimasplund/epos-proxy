"""
Web setup module for the ePOS Proxy Server.
"""
import os
import logging
import asyncio
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import (
    User, EmailTemplate, EmailTheme, CompanyBranding,
    async_session, init_db
)
from auth import get_password_hash
from email_service import EMAIL_TEMPLATES_DIR, load_default_templates

# Setup logging
logger = logging.getLogger(__name__)


async def setup_default_assets():
    """Setup default assets for the web interface."""
    logger.info("Setting up default assets...")
    
    # Create directories if they don't exist
    static_dir = Path("static")
    templates_dir = Path("templates")
    uploads_dir = static_dir / "uploads"
    
    static_dir.mkdir(exist_ok=True)
    templates_dir.mkdir(exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy default logo if it doesn't exist
    default_logo_path = static_dir / "default-logo.png"
    if not default_logo_path.exists():
        # Try to find the logo in the package
        package_logo = Path(__file__).parent / "static" / "default-logo.png"
        if package_logo.exists():
            shutil.copy(package_logo, default_logo_path)
        else:
            # Create a simple text file as placeholder
            with open(default_logo_path, "w") as f:
                f.write("This is a placeholder for the default logo.")
            logger.warning("Default logo not found, using placeholder.")
    
    # Create index.html template if it doesn't exist
    index_path = templates_dir / "index.html"
    if not index_path.exists():
        with open(index_path, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f8f9fa;
        }
        .navbar {
            background-color: #0066cc;
        }
        .navbar-brand {
            font-weight: bold;
            color: white !important;
        }
        .main-container {
            margin-top: 2rem;
        }
        .card {
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 1.5rem;
            border-radius: 0.5rem;
            border: none;
        }
        .card-header {
            background-color: #007bff;
            color: white;
            border-radius: 0.5rem 0.5rem 0 0 !important;
            font-weight: bold;
        }
        .btn-primary {
            background-color: #0066cc;
            border-color: #0066cc;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="/">{{ app_name }}</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link active" href="/">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/web/print-jobs">Print Jobs</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/web/templates">Email Templates</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/web/settings">Settings</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container main-container">
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        Welcome to {{ app_name }}
                    </div>
                    <div class="card-body">
                        <h5 class="card-title">Manage your printer and email settings</h5>
                        <p class="card-text">
                            Use this interface to manage your printers, view print jobs, and configure email templates
                            for receipt delivery.
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        Print Jobs
                    </div>
                    <div class="card-body">
                        <h5 class="card-title">View Recent Print Jobs</h5>
                        <p class="card-text">View and manage printer activity, send email receipts.</p>
                        <a href="/web/print-jobs" class="btn btn-primary">Manage Print Jobs</a>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        Email Templates
                    </div>
                    <div class="card-body">
                        <h5 class="card-title">Design Email Receipts</h5>
                        <p class="card-text">Customize the appearance of email receipts sent to customers.</p>
                        <a href="/web/templates" class="btn btn-primary">Manage Templates</a>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        Settings
                    </div>
                    <div class="card-body">
                        <h5 class="card-title">Configure System</h5>
                        <p class="card-text">Configure system settings, users, and branding.</p>
                        <a href="/web/settings" class="btn btn-primary">Manage Settings</a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <footer class="bg-light mt-5 py-3">
        <div class="container text-center">
            <p class="text-muted mb-0">© 2023 {{ app_name }}. All rights reserved.</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
""")
    
    logger.info("Default assets setup complete")
    return True


async def setup_database():
    """Setup the database with default data."""
    logger.info("Setting up database with default data...")
    
    # Load environment variables for admin user
    load_dotenv()
    
    admin_username = os.getenv("ADMIN_USER", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    
    # Create admin user
    async with async_session() as session:
        # Check if any users exist
        query = text("SELECT count(*) FROM users")
        result = await session.execute(query)
        user_count = result.scalar()
        
        if user_count == 0:
            # Create admin user
            hashed_password = get_password_hash(admin_password)
            admin_user = User(
                username=admin_username,
                email=admin_email,
                full_name="Administrator",
                hashed_password=hashed_password,
                is_admin=True,
                is_active=True
            )
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            logger.info(f"Created admin user: {admin_username}")
        else:
            logger.info("Users already exist, skipping admin user creation")
        
        # Create default email theme if none exists
        query = text("SELECT count(*) FROM email_themes")
        result = await session.execute(query)
        theme_count = result.scalar()
        
        if theme_count == 0:
            # Create default theme
            default_theme = EmailTheme(
                name="Default Theme",
                description="Default blue theme with accents",
                primary_color="#0066cc",
                secondary_color="#4d94ff",
                accent_color="#ff6600",
                text_color="#333333",
                background_color="#ffffff",
                font_family="Arial, sans-serif",
                is_default=True
            )
            session.add(default_theme)
            
            # Create a second theme
            minimal_theme = EmailTheme(
                name="Minimal Theme",
                description="Minimalist black and white theme",
                primary_color="#000000",
                secondary_color="#666666",
                accent_color="#999999",
                text_color="#333333",
                background_color="#ffffff",
                font_family="Arial, sans-serif",
                is_default=False
            )
            session.add(minimal_theme)
            await session.commit()
            logger.info("Created default email themes")
        else:
            logger.info("Email themes already exist, skipping creation")
        
        # Create default company branding if none exists
        query = text("SELECT count(*) FROM company_branding")
        result = await session.execute(query)
        branding_count = result.scalar()
        
        if branding_count == 0:
            # Get company info from environment
            company_name = os.getenv("COMPANY_NAME", "ePOS Proxy")
            company_website = os.getenv("COMPANY_WEBSITE", "")
            company_email = os.getenv("COMPANY_EMAIL", "")
            company_phone = os.getenv("COMPANY_PHONE", "")
            
            # Create default branding
            default_branding = CompanyBranding(
                name="Default Branding",
                company_name=company_name,
                company_logo_path="/static/default-logo.png",
                company_website=company_website,
                company_email=company_email,
                company_phone=company_phone,
                company_address="",
                is_default=True
            )
            session.add(default_branding)
            await session.commit()
            logger.info("Created default company branding")
        else:
            logger.info("Company branding already exists, skipping creation")
    
    # Load default templates
    await load_default_templates()
    
    # Create email templates if needed
    async with async_session() as session:
        query = text("SELECT count(*) FROM email_templates")
        result = await session.execute(query)
        template_count = result.scalar()
        
        if template_count == 0:
            # Load templates from disk
            templates_dir = Path(EMAIL_TEMPLATES_DIR)
            for template_file in templates_dir.glob("*.json"):
                import json
                with open(template_file, "r") as f:
                    template_data = json.load(f)
                
                template = EmailTemplate(
                    name=template_data["name"],
                    description=template_data["description"],
                    subject_template=template_data["subject_template"],
                    html_template=template_data["html_template"],
                    css_styles=template_data["css_styles"],
                    is_default=True  # First one will be default
                )
                session.add(template)
                await session.commit()
                logger.info(f"Created email template: {template_data['name']}")
        else:
            logger.info("Email templates already exist, skipping creation")
    
    logger.info("Database setup complete")
    return True


async def main():
    """Run the setup process."""
    try:
        # Initialize the database
        await init_db()
        logger.info("Database initialized")
        
        # Setup default assets
        await setup_default_assets()
        
        # Setup database with default data
        await setup_database()
        
        logger.info("Setup complete")
    except Exception as e:
        logger.error(f"Error during setup: {e}")
        raise


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run setup
    asyncio.run(main()) 