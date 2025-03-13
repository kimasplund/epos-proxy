"""
Email service module for the ePOS Proxy Server.
"""
import os
import logging
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import jinja2
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import EmailTemplate, EmailTheme, CompanyBranding

# Constants
EMAIL_TEMPLATES_DIR = Path("templates/email")
EMAIL_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Set up logger
logger = logging.getLogger(__name__)


async def get_default_template(db: AsyncSession) -> Optional[EmailTemplate]:
    """Get the default email template."""
    query = select(EmailTemplate).where(EmailTemplate.is_default == True)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_default_theme(db: AsyncSession) -> Optional[EmailTheme]:
    """Get the default email theme."""
    query = select(EmailTheme).where(EmailTheme.is_default == True)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_default_branding(db: AsyncSession) -> Optional[CompanyBranding]:
    """Get the default company branding."""
    query = select(CompanyBranding).where(CompanyBranding.is_default == True)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def render_email_template(
    db: AsyncSession,
    template_id: Optional[int] = None,
    theme_id: Optional[int] = None,
    branding_id: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Render an email template with a theme and branding."""
    # Get template, theme, and branding
    if template_id:
        template_query = select(EmailTemplate).where(EmailTemplate.id == template_id)
        template_result = await db.execute(template_query)
        template = template_result.scalar_one_or_none()
    else:
        template = await get_default_template(db)
    
    if theme_id:
        theme_query = select(EmailTheme).where(EmailTheme.id == theme_id)
        theme_result = await db.execute(theme_query)
        theme = theme_result.scalar_one_or_none()
    else:
        theme = await get_default_theme(db)
    
    if branding_id:
        branding_query = select(CompanyBranding).where(
            CompanyBranding.id == branding_id
        )
        branding_result = await db.execute(branding_query)
        branding = branding_result.scalar_one_or_none()
    else:
        branding = await get_default_branding(db)
    
    if not template:
        raise ValueError("No template found")
    
    # Default theme and branding values if not found
    if not theme:
        theme_data = {
            "primary_color": "#0066cc",
            "secondary_color": "#4d94ff",
            "accent_color": "#ff6600",
            "text_color": "#333333",
            "background_color": "#ffffff",
            "font_family": "Arial, sans-serif",
        }
    else:
        theme_data = {
            "primary_color": theme.primary_color,
            "secondary_color": theme.secondary_color,
            "accent_color": theme.accent_color,
            "text_color": theme.text_color,
            "background_color": theme.background_color,
            "font_family": theme.font_family,
        }
    
    if not branding:
        branding_data = {
            "company_name": "ePOS Proxy",
            "company_logo_path": "",
            "company_website": "",
            "company_email": "",
            "company_phone": "",
            "company_address": "",
            "social_facebook": "",
            "social_twitter": "",
            "social_instagram": "",
        }
    else:
        branding_data = {
            "company_name": branding.company_name,
            "company_logo_path": branding.company_logo_path,
            "company_website": branding.company_website,
            "company_email": branding.company_email,
            "company_phone": branding.company_phone,
            "company_address": branding.company_address,
            "social_facebook": branding.social_facebook,
            "social_twitter": branding.social_twitter,
            "social_instagram": branding.social_instagram,
        }
    
    # Combine context with theme and branding data
    full_context = {
        "theme": theme_data,
        "branding": branding_data,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
    }
    
    if context:
        full_context.update(context)
    
    # Render the template
    try:
        # Render subject
        subject_template = jinja2.Template(template.subject_template)
        subject = subject_template.render(**full_context)
        
        # Render HTML content
        html_template = jinja2.Template(template.html_template)
        html_content = html_template.render(**full_context)
        
        # Combine with CSS
        full_html = f"""
        <html>
        <head>
            <style>
                {template.css_styles}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        return {
            "subject": subject,
            "html_content": full_html,
        }
    except Exception as e:
        logger.error(f"Error rendering email template: {e}")
        raise ValueError(f"Error rendering email template: {e}")


async def send_email(
    recipients: List[str],
    subject: str,
    html_content: str,
    sender: Optional[str] = None,
    sender_name: Optional[str] = None,
) -> bool:
    """Send an email."""
    # Get SMTP settings from environment
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "True").lower() == "true"
    smtp_use_ssl = os.getenv("SMTP_USE_SSL", "False").lower() == "true"
    
    # Use default sender if not provided
    if not sender:
        sender = os.getenv("EMAIL_FROM", "noreply@epoxy-proxy.local")
    
    if not sender_name:
        sender_name = os.getenv("EMAIL_FROM_NAME", "ePOS Proxy")
    
    # Check if SMTP is configured
    if not smtp_server or not smtp_username or not smtp_password:
        logger.error("SMTP not configured. Email not sent.")
        return False
    
    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{sender_name} <{sender}>"
    message["To"] = ", ".join(recipients)
    
    # Attach HTML content
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    try:
        # Connect to SMTP server
        if smtp_use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
        
        if smtp_use_tls and not smtp_use_ssl:
            server.starttls()
        
        # Login
        server.login(smtp_username, smtp_password)
        
        # Send email
        server.sendmail(sender, recipients, message.as_string())
        
        # Close connection
        server.quit()
        
        logger.info(f"Email sent successfully to {', '.join(recipients)}")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False


async def load_default_templates():
    """Load default email templates from disk."""
    templates_dir = EMAIL_TEMPLATES_DIR
    
    if not templates_dir.exists():
        templates_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we have default templates
    default_receipt_path = templates_dir / "default_receipt.json"
    
    if not default_receipt_path.exists():
        # Create default receipt template
        default_receipt = {
            "name": "Default Receipt",
            "description": "Default receipt email template",
            "subject_template": "Your Receipt from {{ branding.company_name }}",
            "html_template": """
            <div class="container">
                <div class="header">
                    <h1>{{ branding.company_name }}</h1>
                    {% if branding.company_logo_path %}
                    <img src="{{ branding.company_logo_path }}" alt="{{ branding.company_name }}" class="logo">
                    {% endif %}
                </div>
                
                <div class="receipt">
                    <h2>Receipt</h2>
                    <p class="date">Date: {{ date }}</p>
                    <p class="time">Time: {{ time }}</p>
                    
                    <div class="items">
                        <h3>Items:</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Item</th>
                                    <th>Quantity</th>
                                    <th>Price</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for item in items %}
                                <tr>
                                    <td>{{ item.name }}</td>
                                    <td>{{ item.quantity }}</td>
                                    <td>{{ item.price }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                            <tfoot>
                                <tr>
                                    <td colspan="2">Total</td>
                                    <td>{{ total }}</td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Thank you for your purchase!</p>
                    {% if branding.company_website %}
                    <p>Visit us at: <a href="{{ branding.company_website }}">{{ branding.company_website }}</a></p>
                    {% endif %}
                    
                    <div class="contact">
                        {% if branding.company_email %}
                        <p>Email: {{ branding.company_email }}</p>
                        {% endif %}
                        
                        {% if branding.company_phone %}
                        <p>Phone: {{ branding.company_phone }}</p>
                        {% endif %}
                        
                        {% if branding.company_address %}
                        <p>Address: {{ branding.company_address }}</p>
                        {% endif %}
                    </div>
                    
                    <div class="social">
                        {% if branding.social_facebook %}
                        <a href="{{ branding.social_facebook }}">Facebook</a>
                        {% endif %}
                        
                        {% if branding.social_twitter %}
                        <a href="{{ branding.social_twitter }}">Twitter</a>
                        {% endif %}
                        
                        {% if branding.social_instagram %}
                        <a href="{{ branding.social_instagram }}">Instagram</a>
                        {% endif %}
                    </div>
                </div>
            </div>
            """,
            "css_styles": """
            body {
                font-family: {{ theme.font_family }};
                color: {{ theme.text_color }};
                background-color: {{ theme.background_color }};
                margin: 0;
                padding: 0;
            }
            
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }
            
            .header {
                text-align: center;
                margin-bottom: 20px;
            }
            
            .header h1 {
                color: {{ theme.primary_color }};
                margin: 0;
            }
            
            .logo {
                max-width: 200px;
                margin-top: 10px;
            }
            
            .receipt {
                border: 1px solid {{ theme.secondary_color }};
                padding: 20px;
                margin-bottom: 20px;
                background-color: #f9f9f9;
            }
            
            .receipt h2 {
                color: {{ theme.primary_color }};
                margin-top: 0;
            }
            
            .items table {
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }
            
            .items th, .items td {
                border: 1px solid {{ theme.secondary_color }};
                padding: 8px;
                text-align: left;
            }
            
            .items th {
                background-color: {{ theme.secondary_color }};
                color: white;
            }
            
            .items tfoot {
                font-weight: bold;
            }
            
            .footer {
                margin-top: 20px;
                text-align: center;
                font-size: 14px;
                color: #666;
            }
            
            .footer a {
                color: {{ theme.accent_color }};
                text-decoration: none;
            }
            
            .contact {
                margin: 10px 0;
            }
            
            .social {
                margin-top: 10px;
            }
            
            .social a {
                margin: 0 10px;
            }
            """
        }
        
        # Save template
        with open(default_receipt_path, "w") as f:
            json.dump(default_receipt, f, indent=2)
    
    return True 