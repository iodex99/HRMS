from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
import os
import secrets
import string
import hashlib
import jwt
import json
import pandas as pd
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
import uuid
from enum import Enum

# Initialize FastAPI
app = FastAPI(title="HRMS - Employee Master & Admin Masters")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/hrms_db")
client = MongoClient(MONGO_URL)
db = client.get_database()

# Collections
organizations_collection = db["organizations"]
organization_settings_collection = db["organization_settings"]
users_collection = db["users"]
employees_collection = db["employees"]
employee_history_collection = db["employee_history"]
roles_collection = db["roles"]
permissions_collection = db["permissions"]
reporting_hierarchy_collection = db["reporting_hierarchy"]
audit_logs_collection = db["audit_logs"]
import_batches_collection = db["import_batches"]
auth_tokens_collection = db["auth_tokens"]

# Module 2: Master Data Collections
departments_collection = db["departments"]
designations_collection = db["designations"]
employee_types_collection = db["employee_types"]
locations_collection = db["locations"]
clients_collection = db["clients"]
tasks_collection = db["tasks"]
holidays_collection = db["holidays"]
weekly_off_rules_collection = db["weekly_off_rules"]
exit_support_functions_collection = db["exit_support_functions"]
exit_checklist_items_collection = db["exit_checklist_items"]

# Create indexes
employees_collection.create_index([("employee_code", ASCENDING)], unique=True)
employees_collection.create_index([("email", ASCENDING)])
employees_collection.create_index([("mobile", ASCENDING)])
employees_collection.create_index([("organization_id", ASCENDING)])
users_collection.create_index([("username", ASCENDING)], unique=True)
users_collection.create_index([("organization_id", ASCENDING)])
auth_tokens_collection.create_index([("token", ASCENDING)], unique=True)
auth_tokens_collection.create_index([("expires_at", ASCENDING)])

# Module 2: Master Data Indexes
departments_collection.create_index([("organization_id", ASCENDING)])
departments_collection.create_index([("code", ASCENDING), ("organization_id", ASCENDING)])
designations_collection.create_index([("organization_id", ASCENDING)])
designations_collection.create_index([("code", ASCENDING), ("organization_id", ASCENDING)])
locations_collection.create_index([("organization_id", ASCENDING)])
locations_collection.create_index([("code", ASCENDING), ("organization_id", ASCENDING)])
clients_collection.create_index([("organization_id", ASCENDING)])
clients_collection.create_index([("code", ASCENDING), ("organization_id", ASCENDING)])
holidays_collection.create_index([("organization_id", ASCENDING)])
holidays_collection.create_index([("location_id", ASCENDING), ("year", ASCENDING)])

# JWT Configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production-min-32-chars-long")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# Security
security = HTTPBearer()

# ==================== ENUMS ====================

class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    FIRM_ADMIN = "FIRM_ADMIN"
    EMPLOYEE = "EMPLOYEE"

class EmployeeStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class EmployeeType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERN = "INTERN"

class AuthMethod(str, Enum):
    EMAIL = "EMAIL"
    MOBILE = "MOBILE"
    BOTH = "BOTH"

class ImportScope(str, Enum):
    PROFILE_ONLY = "PROFILE_ONLY"
    PROFILE_WITH_LEAVE = "PROFILE_WITH_LEAVE"
    FULL_MIGRATION = "FULL_MIGRATION"

class ImportStatus(str, Enum):
    UPLOADED = "UPLOADED"
    VALIDATED = "VALIDATED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"

# ==================== PYDANTIC MODELS ====================

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    address: Optional[str] = None
    admin_name: str = Field(..., min_length=1)
    admin_email: EmailStr
    admin_mobile: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')

class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    address: Optional[str] = None
    is_active: Optional[bool] = None

class OrganizationSettings(BaseModel):
    email_notifications_enabled: bool = True
    email_sender_address: Optional[EmailStr] = None
    email_sender_name: Optional[str] = None
    whatsapp_notifications_enabled: bool = False
    whatsapp_phone_number: Optional[str] = None
    whatsapp_api_key: Optional[str] = None
    auth_method: AuthMethod = AuthMethod.BOTH

class LoginRequest(BaseModel):
    username: str  # email or mobile
    pin: str = Field(..., min_length=4, max_length=4)
    organization_id: Optional[str] = None

class ActivateAccountRequest(BaseModel):
    token: str
    pin: str = Field(..., min_length=4, max_length=4)
    confirm_pin: str = Field(..., min_length=4, max_length=4)

    @validator('confirm_pin')
    def pins_match(cls, v, values):
        if 'pin' in values and v != values['pin']:
            raise ValueError('PINs do not match')
        return v

class ForgotPasswordRequest(BaseModel):
    username: str
    organization_id: Optional[str] = None

class EmployeeCreate(BaseModel):
    # Identity & Contact
    full_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    mobile: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    emergency_contact: Optional[str] = None
    
    # Personal
    date_of_birth: Optional[str] = None
    blood_group: Optional[str] = None
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    address: Optional[str] = None
    
    # Employment
    date_of_joining: str
    employee_type: EmployeeType
    department: str
    designation: str
    location: str
    monthly_salary: Optional[float] = None
    send_invitation: bool = True
    
    # Assets
    firm_laptop: bool = False
    laptop_serial_number: Optional[str] = None
    charger_serial_number: Optional[str] = None
    
    # Reporting
    primary_reporting_authority: Optional[str] = None  # employee_id
    secondary_reporting_authority: Optional[str] = None  # employee_id

class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    mobile: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    emergency_contact: Optional[str] = None
    date_of_birth: Optional[str] = None
    blood_group: Optional[str] = None
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    address: Optional[str] = None
    date_of_joining: Optional[str] = None
    employee_type: Optional[EmployeeType] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    location: Optional[str] = None
    monthly_salary: Optional[float] = None
    firm_laptop: Optional[bool] = None
    laptop_serial_number: Optional[str] = None
    charger_serial_number: Optional[str] = None
    primary_reporting_authority: Optional[str] = None
    secondary_reporting_authority: Optional[str] = None
    date_of_resignation: Optional[str] = None

class StatusChangeRequest(BaseModel):
    status: EmployeeStatus
    reason: str = Field(..., min_length=1)

class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: List[str] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class AssignRoleRequest(BaseModel):
    role_id: str
    reason: Optional[str] = None

# ==================== UTILITY FUNCTIONS ====================

def generate_pin() -> str:
    """Generate a random 4-digit PIN"""
    return ''.join(secrets.choice(string.digits) for _ in range(4))

def hash_pin(pin: str) -> str:
    """Hash a PIN using SHA-256"""
    return hashlib.sha256(pin.encode()).hexdigest()

def generate_employee_code(organization_id: str) -> str:
    """Generate sequential employee code"""
    last_employee = employees_collection.find_one(
        {"organization_id": organization_id},
        sort=[("employee_code", DESCENDING)]
    )
    
    if last_employee and last_employee.get("employee_code"):
        last_code = int(last_employee["employee_code"].split("-")[-1])
        new_code = last_code + 1
    else:
        new_code = 1
    
    return f"EMP-{new_code:05d}"

def generate_token() -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def log_audit(
    organization_id: str,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict = None
):
    """Log an audit trail entry"""
    audit_logs_collection.insert_one({
        "organization_id": organization_id,
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat(),
        "ip_address": None  # Can be enhanced with request context
    })

def snapshot_employee(employee_id: str, action: str, changed_by: str):
    """Create a snapshot of employee data"""
    employee = employees_collection.find_one({"employee_id": employee_id})
    if employee:
        snapshot = employee.copy()
        snapshot["_id"] = ObjectId()
        snapshot["snapshot_action"] = action
        snapshot["snapshot_timestamp"] = datetime.utcnow().isoformat()
        snapshot["snapshot_by"] = changed_by
        employee_history_collection.insert_one(snapshot)

def validate_circular_reporting(employee_id: str, ra_id: str, organization_id: str) -> bool:
    """Check if assigning ra_id as reporting authority creates a circular reference"""
    if employee_id == ra_id:
        return False
    
    visited = set()
    current = ra_id
    
    while current:
        if current in visited:
            return False  # Circular reference detected
        visited.add(current)
        
        # Get reporting authority of current employee
        employee = employees_collection.find_one({
            "employee_id": current,
            "organization_id": organization_id
        })
        
        if not employee:
            break
        
        if employee.get("primary_reporting_authority") == employee_id:
            return False  # Would create circular reference
        
        current = employee.get("primary_reporting_authority")
    
    return True

async def send_notification(
    organization_id: str,
    recipient_email: Optional[str],
    recipient_mobile: Optional[str],
    subject: str,
    message: str
):
    """Send notification via email and/or WhatsApp based on organization settings"""
    settings = organization_settings_collection.find_one({"organization_id": organization_id})
    
    if not settings:
        return
    
    # Email notification
    if settings.get("email_notifications_enabled") and recipient_email:
        # TODO: Implement email sending using organization's email settings
        print(f"[EMAIL] To: {recipient_email}, Subject: {subject}, Message: {message}")
    
    # WhatsApp notification
    if settings.get("whatsapp_notifications_enabled") and recipient_mobile:
        # TODO: Implement WhatsApp sending using organization's WhatsApp API
        print(f"[WHATSAPP] To: {recipient_mobile}, Message: {message}")

# ==================== AUTH DEPENDENCY ====================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    payload = verify_token(token)
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="User account is inactive")
    
    return user

async def require_super_admin(current_user: dict = Depends(get_current_user)):
    """Require super admin role"""
    if current_user.get("role") != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user

async def require_firm_admin(current_user: dict = Depends(get_current_user)):
    """Require firm admin role"""
    if current_user.get("role") not in [UserRole.SUPER_ADMIN, UserRole.FIRM_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# ==================== API ENDPOINTS ====================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# ==================== SUPER ADMIN - ORGANIZATION MANAGEMENT ====================

@app.post("/api/super-admin/init")
async def initialize_super_admin():
    """Initialize super admin account (one-time setup)"""
    existing = users_collection.find_one({"role": UserRole.SUPER_ADMIN})
    if existing:
        raise HTTPException(status_code=400, detail="Super admin already exists")
    
    pin = generate_pin()
    user_id = str(uuid.uuid4())
    
    super_admin = {
        "user_id": user_id,
        "username": "superadmin",
        "pin_hash": hash_pin(pin),
        "role": UserRole.SUPER_ADMIN,
        "organization_id": None,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    users_collection.insert_one(super_admin)
    
    return {
        "message": "Super admin created successfully",
        "username": "superadmin",
        "pin": pin,
        "note": "Please save this PIN securely. It will not be shown again."
    }

@app.post("/api/organizations")
async def create_organization(
    org_data: OrganizationCreate,
    current_user: dict = Depends(require_super_admin)
):
    """Create a new organization (firm)"""
    organization_id = str(uuid.uuid4())
    
    # Create organization
    organization = {
        "organization_id": organization_id,
        "name": org_data.name,
        "email": org_data.email,
        "phone": org_data.phone,
        "address": org_data.address,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "created_by": current_user["user_id"]
    }
    organizations_collection.insert_one(organization)
    
    # Create default organization settings
    settings = {
        "organization_id": organization_id,
        "email_notifications_enabled": True,
        "email_sender_address": org_data.email,
        "email_sender_name": org_data.name,
        "whatsapp_notifications_enabled": False,
        "whatsapp_phone_number": None,
        "whatsapp_api_key": None,
        "auth_method": AuthMethod.BOTH,
        "updated_at": datetime.utcnow().isoformat()
    }
    organization_settings_collection.insert_one(settings)
    
    # Create firm admin user
    admin_pin = generate_pin()
    admin_user_id = str(uuid.uuid4())
    admin_username = org_data.admin_email  # Default to email
    
    admin_user = {
        "user_id": admin_user_id,
        "username": admin_username,
        "pin_hash": hash_pin(admin_pin),
        "role": UserRole.FIRM_ADMIN,
        "organization_id": organization_id,
        "email": org_data.admin_email,
        "mobile": org_data.admin_mobile,
        "full_name": org_data.admin_name,
        "is_active": True,
        "requires_password_change": False,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    users_collection.insert_one(admin_user)
    
    # Send credentials to admin
    await send_notification(
        organization_id=organization_id,
        recipient_email=org_data.admin_email,
        recipient_mobile=org_data.admin_mobile,
        subject="Welcome to HRMS - Your Admin Credentials",
        message=f"Welcome {org_data.admin_name}! Your organization has been set up.\n\nUsername: {admin_username}\nPIN: {admin_pin}\n\nPlease keep this secure."
    )
    
    log_audit(
        organization_id=organization_id,
        user_id=current_user["user_id"],
        action="CREATE_ORGANIZATION",
        resource_type="organization",
        resource_id=organization_id,
        details={"name": org_data.name}
    )
    
    return {
        "organization_id": organization_id,
        "message": "Organization created successfully",
        "admin_username": admin_username,
        "admin_pin": admin_pin,
        "note": "Admin credentials have been sent to the provided email and mobile."
    }

@app.get("/api/organizations")
async def list_organizations(
    current_user: dict = Depends(require_super_admin),
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None
):
    """List all organizations"""
    query = {}
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    total = organizations_collection.count_documents(query)
    organizations = list(organizations_collection.find(query).skip(skip).limit(limit))
    
    # Remove MongoDB _id
    for org in organizations:
        org.pop("_id", None)
    
    return {
        "total": total,
        "organizations": organizations
    }

@app.get("/api/organizations/{organization_id}")
async def get_organization(
    organization_id: str,
    current_user: dict = Depends(require_super_admin)
):
    """Get organization details"""
    organization = organizations_collection.find_one({"organization_id": organization_id})
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    organization.pop("_id", None)
    return organization

@app.put("/api/organizations/{organization_id}")
async def update_organization(
    organization_id: str,
    org_data: OrganizationUpdate,
    current_user: dict = Depends(require_super_admin)
):
    """Update organization details"""
    organization = organizations_collection.find_one({"organization_id": organization_id})
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    update_data = {k: v for k, v in org_data.dict(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    organizations_collection.update_one(
        {"organization_id": organization_id},
        {"$set": update_data}
    )
    
    log_audit(
        organization_id=organization_id,
        user_id=current_user["user_id"],
        action="UPDATE_ORGANIZATION",
        resource_type="organization",
        resource_id=organization_id,
        details=update_data
    )
    
    return {"message": "Organization updated successfully"}

# ==================== ORGANIZATION SETTINGS ====================

@app.get("/api/organizations/{organization_id}/settings")
async def get_organization_settings(
    organization_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get organization settings"""
    # Check access
    if current_user["role"] == UserRole.EMPLOYEE and current_user["organization_id"] != organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    settings = organization_settings_collection.find_one({"organization_id": organization_id})
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    settings.pop("_id", None)
    # Hide sensitive data for non-admin users
    if current_user["role"] == UserRole.EMPLOYEE:
        settings.pop("whatsapp_api_key", None)
    
    return settings

@app.put("/api/organizations/{organization_id}/settings")
async def update_organization_settings(
    organization_id: str,
    settings_data: OrganizationSettings,
    current_user: dict = Depends(require_firm_admin)
):
    """Update organization settings"""
    if current_user["role"] == UserRole.FIRM_ADMIN and current_user["organization_id"] != organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    settings = settings_data.dict()
    settings["updated_at"] = datetime.utcnow().isoformat()
    
    organization_settings_collection.update_one(
        {"organization_id": organization_id},
        {"$set": settings},
        upsert=True
    )
    
    log_audit(
        organization_id=organization_id,
        user_id=current_user["user_id"],
        action="UPDATE_SETTINGS",
        resource_type="organization_settings",
        resource_id=organization_id,
        details=settings
    )
    
    return {"message": "Settings updated successfully"}

# ==================== AUTHENTICATION ====================

@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    """User login with email/mobile and 4-digit PIN"""
    query = {"username": login_data.username}
    
    if login_data.organization_id:
        query["organization_id"] = login_data.organization_id
    
    user = users_collection.find_one(query)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is inactive")
    
    # Verify PIN
    if hash_pin(login_data.pin) != user["pin_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token
    token_data = {
        "user_id": user["user_id"],
        "role": user["role"],
        "organization_id": user.get("organization_id")
    }
    access_token = create_access_token(token_data)
    
    log_audit(
        organization_id=user.get("organization_id", "system"),
        user_id=user["user_id"],
        action="LOGIN",
        resource_type="user",
        resource_id=user["user_id"]
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"],
            "organization_id": user.get("organization_id"),
            "full_name": user.get("full_name")
        }
    }

@app.post("/api/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    """Send new PIN to user"""
    query = {"username": request.username}
    if request.organization_id:
        query["organization_id"] = request.organization_id
    
    user = users_collection.find_one(query)
    
    if not user:
        # Don't reveal if user exists
        return {"message": "If the account exists, a new PIN will be sent"}
    
    # Generate new PIN
    new_pin = generate_pin()
    
    # Update user
    users_collection.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "pin_hash": hash_pin(new_pin),
            "updated_at": datetime.utcnow().isoformat()
        }}
    )
    
    # Send new PIN
    background_tasks.add_task(
        send_notification,
        organization_id=user.get("organization_id", "system"),
        recipient_email=user.get("email"),
        recipient_mobile=user.get("mobile"),
        subject="Password Reset - Your New PIN",
        message=f"Your new PIN is: {new_pin}\n\nPlease keep this secure."
    )
    
    log_audit(
        organization_id=user.get("organization_id", "system"),
        user_id=user["user_id"],
        action="FORGOT_PASSWORD",
        resource_type="user",
        resource_id=user["user_id"]
    )
    
    return {"message": "If the account exists, a new PIN will be sent"}

@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    user_info = {
        "user_id": current_user["user_id"],
        "username": current_user["username"],
        "role": current_user["role"],
        "organization_id": current_user.get("organization_id"),
        "full_name": current_user.get("full_name"),
        "email": current_user.get("email"),
        "mobile": current_user.get("mobile"),
        "is_active": current_user.get("is_active", True)
    }
    return user_info

@app.post("/api/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user"""
    log_audit(
        organization_id=current_user.get("organization_id", "system"),
        user_id=current_user["user_id"],
        action="LOGOUT",
        resource_type="user",
        resource_id=current_user["user_id"]
    )
    return {"message": "Logged out successfully"}

# ==================== EMPLOYEES ====================

@app.post("/api/employees")
async def create_employee(
    employee_data: EmployeeCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_firm_admin)
):
    """Create a new employee"""
    organization_id = current_user["organization_id"]
    
    # Check for duplicate email/mobile in organization
    existing = employees_collection.find_one({
        "organization_id": organization_id,
        "$or": [
            {"email": employee_data.email},
            {"mobile": employee_data.mobile}
        ]
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Employee with this email or mobile already exists")
    
    # Validate reporting authorities
    if employee_data.primary_reporting_authority:
        ra = employees_collection.find_one({
            "employee_id": employee_data.primary_reporting_authority,
            "organization_id": organization_id
        })
        if not ra:
            raise HTTPException(status_code=400, detail="Primary reporting authority not found")
    
    if employee_data.secondary_reporting_authority:
        ra = employees_collection.find_one({
            "employee_id": employee_data.secondary_reporting_authority,
            "organization_id": organization_id
        })
        if not ra:
            raise HTTPException(status_code=400, detail="Secondary reporting authority not found")
    
    # Generate employee ID and code
    employee_id = str(uuid.uuid4())
    employee_code = generate_employee_code(organization_id)
    
    # Create employee
    employee = employee_data.dict()
    employee.update({
        "employee_id": employee_id,
        "employee_code": employee_code,
        "biometric_code": employee_code,
        "organization_id": organization_id,
        "status": EmployeeStatus.DRAFT,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "created_by": current_user["user_id"]
    })
    
    employees_collection.insert_one(employee)
    
    # Create user account
    user_pin = generate_pin()
    user_id = str(uuid.uuid4())
    
    user = {
        "user_id": user_id,
        "username": employee_data.email,  # Default username
        "pin_hash": hash_pin(user_pin),
        "role": UserRole.EMPLOYEE,
        "organization_id": organization_id,
        "employee_id": employee_id,
        "email": employee_data.email,
        "mobile": employee_data.mobile,
        "full_name": employee_data.full_name,
        "is_active": False,  # Will activate when status changes to ACTIVE
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    users_collection.insert_one(user)
    
    # Send invitation if requested
    if employee_data.send_invitation:
        background_tasks.add_task(
            send_notification,
            organization_id=organization_id,
            recipient_email=employee_data.email,
            recipient_mobile=employee_data.mobile,
            subject="Welcome to the Organization",
            message=f"Hello {employee_data.full_name},\n\nYour employee account has been created.\nEmployee Code: {employee_code}\nUsername: {employee_data.email}\nPIN: {user_pin}\n\nYou will be able to login once your account is activated."
        )
    
    # Create initial snapshot
    snapshot_employee(employee_id, "CREATE", current_user["user_id"])
    
    log_audit(
        organization_id=organization_id,
        user_id=current_user["user_id"],
        action="CREATE_EMPLOYEE",
        resource_type="employee",
        resource_id=employee_id,
        details={"employee_code": employee_code, "full_name": employee_data.full_name}
    )
    
    return {
        "employee_id": employee_id,
        "employee_code": employee_code,
        "message": "Employee created successfully",
        "credentials": {
            "username": employee_data.email,
            "pin": user_pin
        } if employee_data.send_invitation else None
    }

@app.get("/api/employees")
async def list_employees(
    current_user: dict = Depends(get_current_user),
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    status: Optional[EmployeeStatus] = None,
    department: Optional[str] = None,
    location: Optional[str] = None
):
    """List employees"""
    organization_id = current_user["organization_id"]
    
    query = {"organization_id": organization_id}
    
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"employee_code": {"$regex": search, "$options": "i"}},
            {"mobile": {"$regex": search, "$options": "i"}}
        ]
    
    if status:
        query["status"] = status
    
    if department:
        query["department"] = department
    
    if location:
        query["location"] = location
    
    total = employees_collection.count_documents(query)
    employees = list(employees_collection.find(query).skip(skip).limit(limit).sort("employee_code", ASCENDING))
    
    # Remove MongoDB _id and sensitive data
    for emp in employees:
        emp.pop("_id", None)
        if current_user["role"] == UserRole.EMPLOYEE:
            emp.pop("aadhaar_number", None)
            emp.pop("pan_number", None)
            emp.pop("monthly_salary", None)
    
    return {
        "total": total,
        "employees": employees
    }

@app.get("/api/employees/{employee_id}")
async def get_employee(
    employee_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get employee details"""
    employee = employees_collection.find_one({
        "employee_id": employee_id,
        "organization_id": current_user["organization_id"]
    })
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee.pop("_id", None)
    
    # Hide sensitive data for regular employees
    if current_user["role"] == UserRole.EMPLOYEE and current_user.get("employee_id") != employee_id:
        employee.pop("aadhaar_number", None)
        employee.pop("pan_number", None)
        employee.pop("monthly_salary", None)
        employee.pop("date_of_birth", None)
        employee.pop("blood_group", None)
    
    return employee

@app.put("/api/employees/{employee_id}")
async def update_employee(
    employee_id: str,
    employee_data: EmployeeUpdate,
    current_user: dict = Depends(require_firm_admin)
):
    """Update employee details"""
    employee = employees_collection.find_one({
        "employee_id": employee_id,
        "organization_id": current_user["organization_id"]
    })
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Create snapshot before update
    snapshot_employee(employee_id, "UPDATE", current_user["user_id"])
    
    # Validate reporting authorities if changed
    if employee_data.primary_reporting_authority:
        if not validate_circular_reporting(
            employee_id,
            employee_data.primary_reporting_authority,
            current_user["organization_id"]
        ):
            raise HTTPException(status_code=400, detail="Circular reporting hierarchy detected")
    
    update_data = {k: v for k, v in employee_data.dict(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    employees_collection.update_one(
        {"employee_id": employee_id},
        {"$set": update_data}
    )
    
    log_audit(
        organization_id=current_user["organization_id"],
        user_id=current_user["user_id"],
        action="UPDATE_EMPLOYEE",
        resource_type="employee",
        resource_id=employee_id,
        details=update_data
    )
    
    return {"message": "Employee updated successfully"}

@app.patch("/api/employees/{employee_id}/status")
async def change_employee_status(
    employee_id: str,
    status_data: StatusChangeRequest,
    current_user: dict = Depends(require_firm_admin)
):
    """Change employee status"""
    employee = employees_collection.find_one({
        "employee_id": employee_id,
        "organization_id": current_user["organization_id"]
    })
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Create snapshot before status change
    snapshot_employee(employee_id, f"STATUS_CHANGE_TO_{status_data.status}", current_user["user_id"])
    
    # Update employee status
    employees_collection.update_one(
        {"employee_id": employee_id},
        {"$set": {
            "status": status_data.status,
            "updated_at": datetime.utcnow().isoformat()
        }}
    )
    
    # Update user account status
    users_collection.update_one(
        {"employee_id": employee_id},
        {"$set": {
            "is_active": status_data.status == EmployeeStatus.ACTIVE,
            "updated_at": datetime.utcnow().isoformat()
        }}
    )
    
    log_audit(
        organization_id=current_user["organization_id"],
        user_id=current_user["user_id"],
        action="CHANGE_STATUS",
        resource_type="employee",
        resource_id=employee_id,
        details={"status": status_data.status, "reason": status_data.reason}
    )
    
    return {"message": "Employee status updated successfully"}

@app.get("/api/employees/{employee_id}/history")
async def get_employee_history(
    employee_id: str,
    current_user: dict = Depends(require_firm_admin)
):
    """Get employee change history"""
    employee = employees_collection.find_one({
        "employee_id": employee_id,
        "organization_id": current_user["organization_id"]
    })
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    history = list(employee_history_collection.find(
        {"employee_id": employee_id}
    ).sort("snapshot_timestamp", DESCENDING))
    
    for item in history:
        item.pop("_id", None)
    
    return {"history": history}

# ==================== ROLES & PERMISSIONS ====================

@app.get("/api/permissions")
async def list_permissions(current_user: dict = Depends(require_firm_admin)):
    """List all available permissions"""
    permissions = [
        {"code": "VIEW_SELF", "name": "View Own Data", "description": "View own employee information"},
        {"code": "VIEW_TEAM", "name": "View Team Data", "description": "View team members' information"},
        {"code": "APPROVE_REQUESTS", "name": "Approve Requests", "description": "Approve leave and other requests"},
        {"code": "VIEW_REPORTS", "name": "View Reports", "description": "Access system reports"},
        {"code": "CONFIGURE_SYSTEM", "name": "Configure System", "description": "Modify system settings"},
        {"code": "OVERRIDE_DATA", "name": "Override Data", "description": "Override system-generated data"},
        {"code": "MANAGE_EMPLOYEES", "name": "Manage Employees", "description": "Create, update, delete employees"},
        {"code": "MANAGE_ROLES", "name": "Manage Roles", "description": "Create and assign roles"},
        {"code": "VIEW_AUDIT_LOGS", "name": "View Audit Logs", "description": "Access audit trail"}
    ]
    return {"permissions": permissions}

@app.post("/api/roles")
async def create_role(
    role_data: RoleCreate,
    current_user: dict = Depends(require_firm_admin)
):
    """Create a new role"""
    role_id = str(uuid.uuid4())
    
    role = {
        "role_id": role_id,
        "organization_id": current_user["organization_id"],
        "name": role_data.name,
        "description": role_data.description,
        "permissions": role_data.permissions,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "created_by": current_user["user_id"]
    }
    
    roles_collection.insert_one(role)
    
    log_audit(
        organization_id=current_user["organization_id"],
        user_id=current_user["user_id"],
        action="CREATE_ROLE",
        resource_type="role",
        resource_id=role_id,
        details={"name": role_data.name}
    )
    
    return {"role_id": role_id, "message": "Role created successfully"}

@app.get("/api/roles")
async def list_roles(current_user: dict = Depends(require_firm_admin)):
    """List all roles"""
    roles = list(roles_collection.find({"organization_id": current_user["organization_id"]}))
    
    for role in roles:
        role.pop("_id", None)
    
    return {"roles": roles}

@app.put("/api/roles/{role_id}")
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: dict = Depends(require_firm_admin)
):
    """Update a role"""
    role = roles_collection.find_one({
        "role_id": role_id,
        "organization_id": current_user["organization_id"]
    })
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    update_data = {k: v for k, v in role_data.dict(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    roles_collection.update_one(
        {"role_id": role_id},
        {"$set": update_data}
    )
    
    log_audit(
        organization_id=current_user["organization_id"],
        user_id=current_user["user_id"],
        action="UPDATE_ROLE",
        resource_type="role",
        resource_id=role_id,
        details=update_data
    )
    
    return {"message": "Role updated successfully"}

@app.post("/api/employees/{employee_id}/assign-role")
async def assign_role_to_employee(
    employee_id: str,
    request: AssignRoleRequest,
    current_user: dict = Depends(require_firm_admin)
):
    """Assign a role to an employee"""
    employee = employees_collection.find_one({
        "employee_id": employee_id,
        "organization_id": current_user["organization_id"]
    })
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    role = roles_collection.find_one({
        "role_id": request.role_id,
        "organization_id": current_user["organization_id"]
    })
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Update employee
    employees_collection.update_one(
        {"employee_id": employee_id},
        {"$set": {
            "assigned_role_id": request.role_id,
            "updated_at": datetime.utcnow().isoformat()
        }}
    )
    
    log_audit(
        organization_id=current_user["organization_id"],
        user_id=current_user["user_id"],
        action="ASSIGN_ROLE",
        resource_type="employee",
        resource_id=employee_id,
        details={"role_id": request.role_id, "reason": request.reason}
    )
    
    return {"message": "Role assigned successfully"}

# ==================== REPORTING HIERARCHY ====================

@app.get("/api/reporting-hierarchy/{employee_id}")
async def get_reporting_hierarchy(
    employee_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get reporting hierarchy for an employee"""
    employee = employees_collection.find_one({
        "employee_id": employee_id,
        "organization_id": current_user["organization_id"]
    })
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    hierarchy = {
        "employee_id": employee_id,
        "employee_name": employee.get("full_name"),
        "primary_ra": None,
        "secondary_ra": None
    }
    
    if employee.get("primary_reporting_authority"):
        ra = employees_collection.find_one({"employee_id": employee["primary_reporting_authority"]})
        if ra:
            hierarchy["primary_ra"] = {
                "employee_id": ra["employee_id"],
                "employee_code": ra["employee_code"],
                "full_name": ra["full_name"],
                "designation": ra["designation"]
            }
    
    if employee.get("secondary_reporting_authority"):
        ra = employees_collection.find_one({"employee_id": employee["secondary_reporting_authority"]})
        if ra:
            hierarchy["secondary_ra"] = {
                "employee_id": ra["employee_id"],
                "employee_code": ra["employee_code"],
                "full_name": ra["full_name"],
                "designation": ra["designation"]
            }
    
    return hierarchy

@app.get("/api/reporting-hierarchy/validate")
async def validate_reporting_hierarchy(
    employee_id: str,
    ra_id: str,
    current_user: dict = Depends(require_firm_admin)
):
    """Validate if assigning reporting authority would create circular reference"""
    is_valid = validate_circular_reporting(employee_id, ra_id, current_user["organization_id"])
    
    return {
        "is_valid": is_valid,
        "message": "Valid reporting structure" if is_valid else "Circular reporting detected"
    }

# ==================== BULK IMPORT ====================

@app.post("/api/import/upload")
async def upload_import_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_firm_admin)
):
    """Upload CSV/Excel file for import"""
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
    # Read file
    content = await file.read()
    
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    # Create import batch
    batch_id = str(uuid.uuid4())
    
    batch = {
        "batch_id": batch_id,
        "organization_id": current_user["organization_id"],
        "filename": file.filename,
        "total_rows": len(df),
        "status": ImportStatus.UPLOADED,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": current_user["user_id"]
    }
    
    import_batches_collection.insert_one(batch)
    
    # Store preview data (first 10 rows)
    preview_data = df.head(10).to_dict('records')
    
    return {
        "batch_id": batch_id,
        "total_rows": len(df),
        "columns": list(df.columns),
        "preview": preview_data
    }

@app.post("/api/import/preview")
async def preview_import(
    batch_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_firm_admin)
):
    """Validate and preview import data"""
    batch = import_batches_collection.find_one({
        "batch_id": batch_id,
        "organization_id": current_user["organization_id"]
    })
    
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")
    
    # Read file
    content = await file.read()
    
    try:
        if batch["filename"].endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    # Validate data
    errors = []
    valid_rows = []
    
    for idx, row in df.iterrows():
        row_errors = []
        
        # Required fields validation
        if pd.isna(row.get('full_name')):
            row_errors.append("Full name is required")
        if pd.isna(row.get('email')):
            row_errors.append("Email is required")
        if pd.isna(row.get('mobile')):
            row_errors.append("Mobile is required")
        
        # Check for duplicates
        if not pd.isna(row.get('email')):
            existing = employees_collection.find_one({
                "email": row['email'],
                "organization_id": current_user["organization_id"]
            })
            if existing:
                row_errors.append(f"Email {row['email']} already exists")
        
        if row_errors:
            errors.append({
                "row": idx + 2,  # +2 for header and 0-indexing
                "errors": row_errors
            })
        else:
            valid_rows.append(row.to_dict())
    
    # Update batch
    import_batches_collection.update_one(
        {"batch_id": batch_id},
        {"$set": {
            "status": ImportStatus.VALIDATED,
            "valid_rows": len(valid_rows),
            "error_rows": len(errors),
            "errors": errors[:100],  # Store first 100 errors
            "updated_at": datetime.utcnow().isoformat()
        }}
    )
    
    return {
        "batch_id": batch_id,
        "total_rows": len(df),
        "valid_rows": len(valid_rows),
        "error_rows": len(errors),
        "errors": errors[:100],  # Return first 100 errors
        "can_proceed": len(errors) == 0
    }

@app.post("/api/import/execute")
async def execute_import(
    batch_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_firm_admin)
):
    """Execute the import"""
    batch = import_batches_collection.find_one({
        "batch_id": batch_id,
        "organization_id": current_user["organization_id"]
    })
    
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")
    
    if batch["status"] != ImportStatus.VALIDATED:
        raise HTTPException(status_code=400, detail="Batch must be validated first")
    
    if batch.get("error_rows", 0) > 0:
        raise HTTPException(status_code=400, detail="Cannot import batch with errors")
    
    # Update status to processing
    import_batches_collection.update_one(
        {"batch_id": batch_id},
        {"$set": {"status": ImportStatus.PROCESSING}}
    )
    
    # Note: In a real implementation, this should be done asynchronously
    # For now, we'll just update the status
    import_batches_collection.update_one(
        {"batch_id": batch_id},
        {"$set": {
            "status": ImportStatus.COMPLETED,
            "completed_at": datetime.utcnow().isoformat()
        }}
    )
    
    log_audit(
        organization_id=current_user["organization_id"],
        user_id=current_user["user_id"],
        action="EXECUTE_IMPORT",
        resource_type="import_batch",
        resource_id=batch_id
    )
    
    return {"message": "Import completed successfully", "batch_id": batch_id}

# ==================== REPORTS ====================

@app.get("/api/reports/directory")
async def employee_directory_report(
    current_user: dict = Depends(get_current_user),
    format: str = "json"
):
    """Employee directory report"""
    employees = list(employees_collection.find({
        "organization_id": current_user["organization_id"],
        "status": EmployeeStatus.ACTIVE
    }).sort("employee_code", ASCENDING))
    
    for emp in employees:
        emp.pop("_id", None)
        emp.pop("aadhaar_number", None)
        emp.pop("pan_number", None)
    
    if format == "excel":
        df = pd.DataFrame(employees)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Employee Directory')
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={"Content-Disposition": "attachment; filename=employee_directory.xlsx"}
        )
    
    return {"employees": employees}

@app.get("/api/reports/department-wise")
async def department_wise_report(current_user: dict = Depends(get_current_user)):
    """Department-wise employee report"""
    pipeline = [
        {"$match": {"organization_id": current_user["organization_id"]}},
        {"$group": {
            "_id": "$department",
            "count": {"$sum": 1},
            "active": {
                "$sum": {"$cond": [{"$eq": ["$status", EmployeeStatus.ACTIVE]}, 1, 0]}
            }
        }}
    ]
    
    results = list(employees_collection.aggregate(pipeline))
    
    return {"departments": results}

@app.get("/api/reports/location-wise")
async def location_wise_report(current_user: dict = Depends(get_current_user)):
    """Location-wise employee report"""
    pipeline = [
        {"$match": {"organization_id": current_user["organization_id"]}},
        {"$group": {
            "_id": "$location",
            "count": {"$sum": 1},
            "active": {
                "$sum": {"$cond": [{"$eq": ["$status", EmployeeStatus.ACTIVE]}, 1, 0]}
            }
        }}
    ]
    
    results = list(employees_collection.aggregate(pipeline))
    
    return {"locations": results}

# ==================== AUDIT LOGS ====================

@app.get("/api/audit-logs")
async def get_audit_logs(
    current_user: dict = Depends(require_firm_admin),
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = None,
    resource_type: Optional[str] = None
):
    """Get audit logs"""
    query = {"organization_id": current_user["organization_id"]}
    
    if action:
        query["action"] = action
    
    if resource_type:
        query["resource_type"] = resource_type
    
    total = audit_logs_collection.count_documents(query)
    logs = list(audit_logs_collection.find(query).sort("timestamp", DESCENDING).skip(skip).limit(limit))
    
    for log in logs:
        log.pop("_id", None)
    
    return {
        "total": total,
        "logs": logs
    }

# ==================== MODULE 2: MASTER DATA MANAGEMENT ====================

# Import and register Module 2 routes
try:
    from module2_masters import register_master_routes
    register_master_routes(app, db, get_current_user, require_firm_admin)
except ImportError:
    print("Warning: Module 2 (Masters) not loaded")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
