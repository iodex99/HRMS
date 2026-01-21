"""
Module 2: Admin Masters & Reference Data Management
This module provides all master data management APIs
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pymongo import ASCENDING, DESCENDING
from enum import Enum
import uuid
import pandas as pd
import io

# Master Status Enum
class MasterStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

# ==================== PYDANTIC MODELS ====================

# Department Master
class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    effective_from: str  # ISO date format

class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    effective_from: Optional[str] = None

# Designation Master
class DesignationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    level: Optional[int] = Field(None, ge=1)  # Hierarchy level
    effective_from: str

class DesignationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    level: Optional[int] = Field(None, ge=1)
    effective_from: Optional[str] = None

# Employee Type Master
class EmployeeTypeMasterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    effective_from: str

class EmployeeTypeMasterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    effective_from: Optional[str] = None

# Location Master
class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    effective_from: str

class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    effective_from: Optional[str] = None

# Client Master
class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    effective_from: str

class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    effective_from: Optional[str] = None

# Task Master
class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    client_id: Optional[str] = None  # Reference to client
    effective_from: str

class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    client_id: Optional[str] = None
    effective_from: Optional[str] = None

# Holiday Master
class HolidayCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    date: str  # ISO date format
    location_id: str  # Must reference a location
    year: int = Field(..., ge=2000, le=2100)
    is_mandatory: bool = True
    description: Optional[str] = None

class HolidayUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    date: Optional[str] = None
    is_mandatory: Optional[bool] = None
    description: Optional[str] = None

# Weekly Off Rule Master
class WeeklyOffRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    location_id: str
    rule_type: str = Field(..., pattern="^(FIXED|NTH_WEEKDAY)$")  # FIXED or NTH_WEEKDAY
    fixed_weekdays: Optional[List[str]] = None  # ["SATURDAY", "SUNDAY"]
    nth_weekday_config: Optional[Dict[str, Any]] = None  # {"weekday": "SATURDAY", "occurrences": [2, 4]}
    effective_from: str
    effective_to: Optional[str] = None

class WeeklyOffRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    rule_type: Optional[str] = Field(None, pattern="^(FIXED|NTH_WEEKDAY)$")
    fixed_weekdays: Optional[List[str]] = None
    nth_weekday_config: Optional[Dict[str, Any]] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None

# Exit Support Function Master
class ExitSupportFunctionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    responsible_email: Optional[str] = None
    effective_from: str

class ExitSupportFunctionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    responsible_email: Optional[str] = None
    effective_from: Optional[str] = None

# Exit Checklist Item Master
class ExitChecklistItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    support_function_id: str  # Reference to support function
    description: Optional[str] = None
    is_mandatory: bool = True
    sequence: Optional[int] = Field(None, ge=1)
    effective_from: str

class ExitChecklistItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_mandatory: Optional[bool] = None
    sequence: Optional[int] = Field(None, ge=1)
    effective_from: Optional[str] = None

# Status Change Request
class StatusChangeRequest(BaseModel):
    status: MasterStatus
    reason: str = Field(..., min_length=1)

# Bulk Import Request
class BulkImportRequest(BaseModel):
    master_type: str
    field_mapping: Optional[Dict[str, str]] = None

# ==================== HELPER FUNCTIONS ====================

def create_master_record(
    collection,
    data: dict,
    organization_id: str,
    user_id: str,
    master_type: str
) -> dict:
    """Create a new master record"""
    master_id = str(uuid.uuid4())
    
    record = {
        **data,
        "master_id": master_id,
        "organization_id": organization_id,
        "status": MasterStatus.ACTIVE,
        "created_by": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_by": user_id,
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    collection.insert_one(record)
    return master_id

def check_master_dependencies(
    db,
    master_type: str,
    master_id: str,
    organization_id: str
) -> Dict[str, int]:
    """Check dependencies for a master record"""
    dependencies = {}
    
    if master_type == "department":
        # Check employees
        count = db["employees"].count_documents({
            "organization_id": organization_id,
            "department": db["departments"].find_one({"master_id": master_id})["name"]
        })
        if count > 0:
            dependencies["employees"] = count
    
    elif master_type == "designation":
        count = db["employees"].count_documents({
            "organization_id": organization_id,
            "designation": db["designations"].find_one({"master_id": master_id})["name"]
        })
        if count > 0:
            dependencies["employees"] = count
    
    elif master_type == "location":
        count = db["employees"].count_documents({
            "organization_id": organization_id,
            "location": db["locations"].find_one({"master_id": master_id})["name"]
        })
        if count > 0:
            dependencies["employees"] = count
        
        # Check holidays
        count = db["holidays"].count_documents({
            "organization_id": organization_id,
            "location_id": master_id
        })
        if count > 0:
            dependencies["holidays"] = count
    
    elif master_type == "client":
        count = db["tasks"].count_documents({
            "organization_id": organization_id,
            "client_id": master_id,
            "status": MasterStatus.ACTIVE
        })
        if count > 0:
            dependencies["tasks"] = count
    
    elif master_type == "exit_support_function":
        count = db["exit_checklist_items"].count_documents({
            "organization_id": organization_id,
            "support_function_id": master_id,
            "status": MasterStatus.ACTIVE
        })
        if count > 0:
            dependencies["checklist_items"] = count
    
    return dependencies

def log_master_audit(
    db,
    organization_id: str,
    user_id: str,
    action: str,
    master_type: str,
    master_id: str,
    details: dict = None
):
    """Log audit trail for master data changes"""
    db["audit_logs"].insert_one({
        "organization_id": organization_id,
        "user_id": user_id,
        "action": action,
        "resource_type": f"master_{master_type}",
        "resource_id": master_id,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat(),
        "ip_address": None
    })

# ==================== ROUTER SETUP ====================

# This function will be called from main server.py to register all routes
def register_master_routes(app, db, get_current_user, require_firm_admin):
    """Register all master data routes"""
    
    # Helper to get collections
    def get_collection(master_type: str):
        collection_map = {
            "department": "departments",
            "designation": "designations",
            "employee_type": "employee_types",
            "location": "locations",
            "client": "clients",
            "task": "tasks",
            "holiday": "holidays",
            "weekly_off_rule": "weekly_off_rules",
            "exit_support_function": "exit_support_functions",
            "exit_checklist_item": "exit_checklist_items"
        }
        return db[collection_map[master_type]]
    
    # ==================== DEPARTMENT MASTER ====================
    
    @app.post("/api/masters/departments")
    async def create_department(
        data: DepartmentCreate,
        current_user: dict = Depends(require_firm_admin)
    ):
        """Create a new department"""
        collection = db["departments"]
        
        # Check for duplicate code
        existing = collection.find_one({
            "organization_id": current_user["organization_id"],
            "code": data.code,
            "status": MasterStatus.ACTIVE
        })
        if existing:
            raise HTTPException(status_code=400, detail="Department code already exists")
        
        master_id = create_master_record(
            collection,
            data.dict(),
            current_user["organization_id"],
            current_user["user_id"],
            "department"
        )
        
        log_master_audit(
            db,
            current_user["organization_id"],
            current_user["user_id"],
            "CREATE_DEPARTMENT",
            "department",
            master_id,
            {"name": data.name, "code": data.code}
        )
        
        return {"master_id": master_id, "message": "Department created successfully"}
    
    @app.get("/api/masters/departments")
    async def list_departments(
        current_user: dict = Depends(get_current_user),
        status: Optional[MasterStatus] = None,
        skip: int = 0,
        limit: int = 100
    ):
        """List all departments"""
        query = {"organization_id": current_user["organization_id"]}
        if status:
            query["status"] = status
        
        total = db["departments"].count_documents(query)
        departments = list(db["departments"].find(query).skip(skip).limit(limit).sort("name", ASCENDING))
        
        for dept in departments:
            dept.pop("_id", None)
        
        return {"total": total, "departments": departments}
    
    @app.get("/api/masters/departments/{master_id}")
    async def get_department(
        master_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Get department details"""
        dept = db["departments"].find_one({
            "master_id": master_id,
            "organization_id": current_user["organization_id"]
        })
        
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        
        dept.pop("_id", None)
        return dept
    
    @app.put("/api/masters/departments/{master_id}")
    async def update_department(
        master_id: str,
        data: DepartmentUpdate,
        current_user: dict = Depends(require_firm_admin)
    ):
        """Update department"""
        dept = db["departments"].find_one({
            "master_id": master_id,
            "organization_id": current_user["organization_id"]
        })
        
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        
        # Check for duplicate code if code is being changed
        if data.code and data.code != dept["code"]:
            existing = db["departments"].find_one({
                "organization_id": current_user["organization_id"],
                "code": data.code,
                "status": MasterStatus.ACTIVE,
                "master_id": {"$ne": master_id}
            })
            if existing:
                raise HTTPException(status_code=400, detail="Department code already exists")
        
        update_data = {k: v for k, v in data.dict(exclude_unset=True).items() if v is not None}
        update_data["updated_by"] = current_user["user_id"]
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        db["departments"].update_one(
            {"master_id": master_id},
            {"$set": update_data}
        )
        
        log_master_audit(
            db,
            current_user["organization_id"],
            current_user["user_id"],
            "UPDATE_DEPARTMENT",
            "department",
            master_id,
            update_data
        )
        
        return {"message": "Department updated successfully"}
    
    @app.patch("/api/masters/departments/{master_id}/status")
    async def change_department_status(
        master_id: str,
        request: StatusChangeRequest,
        current_user: dict = Depends(require_firm_admin)
    ):
        """Change department status"""
        dept = db["departments"].find_one({
            "master_id": master_id,
            "organization_id": current_user["organization_id"]
        })
        
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        
        # Check dependencies if deactivating
        if request.status == MasterStatus.INACTIVE:
            deps = check_master_dependencies(db, "department", master_id, current_user["organization_id"])
            if deps:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot deactivate: Used by {deps.get('employees', 0)} employees"
                )
        
        db["departments"].update_one(
            {"master_id": master_id},
            {"$set": {
                "status": request.status,
                "updated_by": current_user["user_id"],
                "updated_at": datetime.utcnow().isoformat()
            }}
        )
        
        log_master_audit(
            db,
            current_user["organization_id"],
            current_user["user_id"],
            "CHANGE_DEPARTMENT_STATUS",
            "department",
            master_id,
            {"status": request.status, "reason": request.reason}
        )
        
        return {"message": "Department status updated successfully"}
    
    @app.get("/api/masters/departments/{master_id}/dependencies")
    async def get_department_dependencies(
        master_id: str,
        current_user: dict = Depends(require_firm_admin)
    ):
        """Get department dependencies"""
        dept = db["departments"].find_one({
            "master_id": master_id,
            "organization_id": current_user["organization_id"]
        })
        
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        
        deps = check_master_dependencies(db, "department", master_id, current_user["organization_id"])
        return {"dependencies": deps, "can_deactivate": len(deps) == 0}
    
    # Similar endpoints for other masters...
    # (I'll create a generic approach for the remaining masters)
    
    # ==================== GENERIC MASTER ENDPOINTS ====================
    
    def create_generic_master_endpoints(master_type: str, create_model, update_model):
        """Create CRUD endpoints for a master type"""
        
        collection_name = f"{master_type}s"
        
        @app.post(f"/api/masters/{collection_name}")
        async def create_master(
            data: create_model,
            current_user: dict = Depends(require_firm_admin)
        ):
            collection = db[collection_name]
            
            # Check for duplicate code
            existing = collection.find_one({
                "organization_id": current_user["organization_id"],
                "code": data.code,
                "status": MasterStatus.ACTIVE
            })
            if existing:
                raise HTTPException(status_code=400, detail=f"{master_type.title()} code already exists")
            
            master_id = create_master_record(
                collection,
                data.dict(),
                current_user["organization_id"],
                current_user["user_id"],
                master_type
            )
            
            log_master_audit(
                db,
                current_user["organization_id"],
                current_user["user_id"],
                f"CREATE_{master_type.upper()}",
                master_type,
                master_id,
                {"name": data.name, "code": data.code}
            )
            
            return {"master_id": master_id, "message": f"{master_type.title()} created successfully"}
        
        @app.get(f"/api/masters/{collection_name}")
        async def list_masters(
            current_user: dict = Depends(get_current_user),
            status: Optional[MasterStatus] = None,
            skip: int = 0,
            limit: int = 100
        ):
            query = {"organization_id": current_user["organization_id"]}
            if status:
                query["status"] = status
            
            collection = db[collection_name]
            total = collection.count_documents(query)
            records = list(collection.find(query).skip(skip).limit(limit).sort("name", ASCENDING))
            
            for record in records:
                record.pop("_id", None)
            
            return {"total": total, collection_name: records}
        
        @app.get(f"/api/masters/{collection_name}/{{master_id}}")
        async def get_master(
            master_id: str,
            current_user: dict = Depends(get_current_user)
        ):
            record = db[collection_name].find_one({
                "master_id": master_id,
                "organization_id": current_user["organization_id"]
            })
            
            if not record:
                raise HTTPException(status_code=404, detail=f"{master_type.title()} not found")
            
            record.pop("_id", None)
            return record
        
        @app.patch(f"/api/masters/{collection_name}/{{master_id}}/status")
        async def change_master_status(
            master_id: str,
            request: StatusChangeRequest,
            current_user: dict = Depends(require_firm_admin)
        ):
            record = db[collection_name].find_one({
                "master_id": master_id,
                "organization_id": current_user["organization_id"]
            })
            
            if not record:
                raise HTTPException(status_code=404, detail=f"{master_type.title()} not found")
            
            # Check dependencies if deactivating
            if request.status == MasterStatus.INACTIVE:
                deps = check_master_dependencies(db, master_type, master_id, current_user["organization_id"])
                if deps:
                    dep_str = ", ".join([f"{count} {name}" for name, count in deps.items()])
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot deactivate: Used by {dep_str}"
                    )
            
            db[collection_name].update_one(
                {"master_id": master_id},
                {"$set": {
                    "status": request.status,
                    "updated_by": current_user["user_id"],
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )
            
            log_master_audit(
                db,
                current_user["organization_id"],
                current_user["user_id"],
                f"CHANGE_{master_type.upper()}_STATUS",
                master_type,
                master_id,
                {"status": request.status, "reason": request.reason}
            )
            
            return {"message": f"{master_type.title()} status updated successfully"}
    
    # Create endpoints for remaining masters
    create_generic_master_endpoints("designation", DesignationCreate, DesignationUpdate)
    create_generic_master_endpoints("location", LocationCreate, LocationUpdate)
    create_generic_master_endpoints("client", ClientCreate, ClientUpdate)
    
    # ==================== BULK IMPORT ====================
    
    @app.post("/api/masters/import/template")
    async def get_import_template(
        master_type: str,
        current_user: dict = Depends(require_firm_admin)
    ):
        """Get CSV template for master import"""
        templates = {
            "department": ["code", "name", "description", "effective_from"],
            "designation": ["code", "name", "description", "level", "effective_from"],
            "location": ["code", "name", "address", "city", "state", "country", "timezone", "effective_from"],
            "client": ["code", "name", "description", "contact_person", "contact_email", "contact_phone", "effective_from"],
        }
        
        if master_type not in templates:
            raise HTTPException(status_code=400, detail="Invalid master type")
        
        df = pd.DataFrame(columns=templates[master_type])
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={master_type}_import_template.csv"}
        )
    
    @app.post("/api/masters/import/upload")
    async def upload_master_import(
        master_type: str,
        file: UploadFile = File(...),
        current_user: dict = Depends(require_firm_admin)
    ):
        """Upload and validate master import file"""
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
        
        content = await file.read()
        
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
        
        # Basic validation
        required_fields = {"code", "name"}
        if not required_fields.issubset(set(df.columns)):
            raise HTTPException(status_code=400, detail=f"Missing required fields: {required_fields}")
        
        # Check for duplicates
        errors = []
        collection = db[f"{master_type}s"]
        
        for idx, row in df.iterrows():
            if pd.isna(row.get('code')) or pd.isna(row.get('name')):
                errors.append({"row": idx + 2, "error": "Code and name are required"})
                continue
            
            existing = collection.find_one({
                "organization_id": current_user["organization_id"],
                "code": row['code'],
                "status": MasterStatus.ACTIVE
            })
            if existing:
                errors.append({"row": idx + 2, "error": f"Code '{row['code']}' already exists"})
        
        batch_id = str(uuid.uuid4())
        db["import_batches"].insert_one({
            "batch_id": batch_id,
            "organization_id": current_user["organization_id"],
            "master_type": master_type,
            "filename": file.filename,
            "total_rows": len(df),
            "valid_rows": len(df) - len(errors),
            "error_rows": len(errors),
            "errors": errors[:100],
            "status": "VALIDATED" if len(errors) == 0 else "VALIDATION_FAILED",
            "created_at": datetime.utcnow().isoformat(),
            "created_by": current_user["user_id"]
        })
        
        return {
            "batch_id": batch_id,
            "total_rows": len(df),
            "valid_rows": len(df) - len(errors),
            "error_rows": len(errors),
            "errors": errors[:100],
            "can_proceed": len(errors) == 0
        }
    
    # ==================== REPORTS ====================
    
    @app.get("/api/masters/reports/{master_type}")
    async def get_master_report(
        master_type: str,
        current_user: dict = Depends(require_firm_admin),
        format: str = "json"
    ):
        """Get master data report"""
        collection = db[f"{master_type}s"]
        records = list(collection.find({
            "organization_id": current_user["organization_id"]
        }).sort("name", ASCENDING))
        
        for record in records:
            record.pop("_id", None)
        
        if format == "excel":
            df = pd.DataFrame(records)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name=master_type.title())
            output.seek(0)
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                output,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={"Content-Disposition": f"attachment; filename={master_type}_report.xlsx"}
            )
        
        return {master_type: records, "total": len(records)}
