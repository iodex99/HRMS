"""
Module 4: Timesheet
Calendar-First, Policy-Driven Time Tracking System
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from enum import Enum
import uuid
import calendar

# ==================== ENUMS ====================

class TimesheetCycleState(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FROZEN = "FROZEN"

class TimesheetStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class DayStatus(str, Enum):
    NOT_FILLED = "NOT_FILLED"
    VALID = "VALID"
    UNDER_HOURS = "UNDER_HOURS"
    OVER_HOURS = "OVER_HOURS"
    HALF_DAY_LEAVE = "HALF_DAY_LEAVE"
    FULL_DAY_LEAVE = "FULL_DAY_LEAVE"
    HOLIDAY = "HOLIDAY"
    WEEKLY_OFF = "WEEKLY_OFF"
    WORKED_ON_HOLIDAY = "WORKED_ON_HOLIDAY"

# ==================== POLICY ENGINE (SIMULATED) ====================

class TimesheetPolicy:
    """
    Simulated Policy Engine for Timesheet Rules
    In production, this would read from a policy management system
    """
    
    @staticmethod
    def get_policy(organization_id: str, version: str = "v1") -> Dict[str, Any]:
        """Get timesheet policy configuration"""
        return {
            "policy_version": version,
            "cycle_type": "CALENDAR_MONTH",  # or CUSTOM_RANGE
            "standard_hours_per_day": 8.0,
            "min_hours_per_day": 0.0,
            "max_hours_per_day": 12.0,
            "tolerance_hours": 0.5,
            "allow_holiday_work": True,
            "require_approval": True,
            "auto_approve": False,
            "week_view_enabled": True,
            "allow_half_day_entry": True,
            "submission_window_days": 5,  # Days after month end
            "comp_off_on_holiday_work": True
        }
    
    @staticmethod
    def get_current_cycle(organization_id: str, target_date: date = None) -> Dict[str, Any]:
        """Get current timesheet cycle"""
        if target_date is None:
            target_date = date.today()
        
        # Calendar month cycle
        first_day = date(target_date.year, target_date.month, 1)
        last_day = date(target_date.year, target_date.month, 
                       calendar.monthrange(target_date.year, target_date.month)[1])
        
        # Determine state based on date
        today = date.today()
        submission_deadline = last_day + timedelta(days=5)
        
        if target_date.month < today.month or target_date.year < today.year:
            state = TimesheetCycleState.FROZEN
        elif today > submission_deadline:
            state = TimesheetCycleState.CLOSED
        else:
            state = TimesheetCycleState.OPEN
        
        return {
            "cycle_id": f"{target_date.year}-{target_date.month:02d}",
            "start_date": first_day.isoformat(),
            "end_date": last_day.isoformat(),
            "state": state,
            "submission_deadline": submission_deadline.isoformat()
        }

# ==================== PYDANTIC MODELS ====================

class TimesheetEntryCreate(BaseModel):
    date: str
    client_id: str
    task_id: str
    hours: float = Field(..., ge=0, le=24)
    description: Optional[str] = None

class TimesheetEntryUpdate(BaseModel):
    client_id: Optional[str] = None
    task_id: Optional[str] = None
    hours: Optional[float] = Field(None, ge=0, le=24)
    description: Optional[str] = None

class TimesheetSubmitRequest(BaseModel):
    cycle_id: str
    comment: Optional[str] = None

class TimesheetApprovalRequest(BaseModel):
    action: str = Field(..., pattern="^(APPROVE|REJECT)$")
    comment: Optional[str] = None

class BulkTimesheetEntry(BaseModel):
    employee_id: str
    date: str
    client_id: str
    task_id: str
    hours: float
    description: Optional[str] = None

# ==================== TIMESHEET ENGINE ====================

class TimesheetEngine:
    """Core timesheet business logic"""
    
    def __init__(self, db, calendar_engine):
        self.db = db
        self.calendar_engine = calendar_engine
    
    def validate_entry(
        self,
        organization_id: str,
        employee_id: str,
        entry_date: date,
        hours: float,
        policy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate timesheet entry
        Returns: {valid: bool, errors: [], warnings: []}
        """
        errors = []
        warnings = []
        
        # Get employee details
        employee = self.db["employees"].find_one({
            "employee_id": employee_id,
            "organization_id": organization_id
        })
        
        if not employee:
            errors.append("Employee not found")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        location_id = self._get_employee_location_id(employee)
        
        # Check calendar classification
        resolution = self.calendar_engine.resolve_date(
            organization_id,
            location_id,
            entry_date
        )
        
        # Rule 1: Check if it's a working day
        if resolution["classification"] == "HOLIDAY":
            if not policy.get("allow_holiday_work", False):
                errors.append(f"Cannot enter hours on holiday: {resolution.get('holiday_name', 'Holiday')}")
            else:
                warnings.append(f"Working on holiday: {resolution.get('holiday_name', 'Holiday')}")
        
        elif resolution["classification"] == "WEEKLY_OFF":
            if not policy.get("allow_holiday_work", False):
                errors.append(f"Cannot enter hours on weekly off: {resolution.get('rule_name', 'Weekly Off')}")
            else:
                warnings.append(f"Working on weekly off: {resolution.get('rule_name', 'Weekly Off')}")
        
        # Rule 2: Check leave conflict
        leave_entry = self.db["leave_entries"].find_one({
            "employee_id": employee_id,
            "date": entry_date.isoformat(),
            "status": {"$in": ["APPROVED", "PENDING"]}
        })
        
        if leave_entry:
            if leave_entry.get("leave_type") == "FULL_DAY":
                errors.append("Cannot enter hours on full-day leave")
            elif leave_entry.get("leave_type") == "HALF_DAY":
                max_allowed = policy.get("standard_hours_per_day", 8.0) / 2
                if hours > max_allowed:
                    errors.append(f"Half-day leave: Maximum {max_allowed} hours allowed")
        
        # Rule 3: Check hours limits
        min_hours = policy.get("min_hours_per_day", 0)
        max_hours = policy.get("max_hours_per_day", 12)
        standard_hours = policy.get("standard_hours_per_day", 8)
        tolerance = policy.get("tolerance_hours", 0.5)
        
        if hours < min_hours:
            errors.append(f"Minimum {min_hours} hours required")
        
        if hours > max_hours:
            errors.append(f"Maximum {max_hours} hours allowed")
        
        if abs(hours - standard_hours) > tolerance and resolution["classification"] == "WORKING_DAY":
            if hours < standard_hours:
                warnings.append(f"Under standard hours ({standard_hours}h)")
            else:
                warnings.append(f"Over standard hours ({standard_hours}h)")
        
        # Rule 4: Check for existing entries
        existing_total = self._get_day_total_hours(employee_id, entry_date)
        if existing_total + hours > max_hours:
            errors.append(f"Total hours for day would exceed maximum ({max_hours}h)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_day_status(
        self,
        organization_id: str,
        employee_id: str,
        entry_date: date,
        policy: Dict[str, Any]
    ) -> DayStatus:
        """Determine visual status of a day"""
        
        employee = self.db["employees"].find_one({
            "employee_id": employee_id,
            "organization_id": organization_id
        })
        
        location_id = self._get_employee_location_id(employee)
        
        # Check calendar
        resolution = self.calendar_engine.resolve_date(
            organization_id,
            location_id,
            entry_date
        )
        
        # Check leave
        leave_entry = self.db["leave_entries"].find_one({
            "employee_id": employee_id,
            "date": entry_date.isoformat(),
            "status": "APPROVED"
        })
        
        if leave_entry:
            if leave_entry.get("leave_type") == "FULL_DAY":
                return DayStatus.FULL_DAY_LEAVE
            elif leave_entry.get("leave_type") == "HALF_DAY":
                return DayStatus.HALF_DAY_LEAVE
        
        # Check if non-working day
        if resolution["classification"] == "HOLIDAY":
            # Check if hours entered
            total_hours = self._get_day_total_hours(employee_id, entry_date)
            if total_hours > 0:
                return DayStatus.WORKED_ON_HOLIDAY
            return DayStatus.HOLIDAY
        
        elif resolution["classification"] == "WEEKLY_OFF":
            total_hours = self._get_day_total_hours(employee_id, entry_date)
            if total_hours > 0:
                return DayStatus.WORKED_ON_HOLIDAY
            return DayStatus.WEEKLY_OFF
        
        # Working day - check hours
        total_hours = self._get_day_total_hours(employee_id, entry_date)
        
        if total_hours == 0:
            return DayStatus.NOT_FILLED
        
        standard_hours = policy.get("standard_hours_per_day", 8.0)
        tolerance = policy.get("tolerance_hours", 0.5)
        
        if total_hours < standard_hours - tolerance:
            return DayStatus.UNDER_HOURS
        elif total_hours > standard_hours + tolerance:
            return DayStatus.OVER_HOURS
        else:
            return DayStatus.VALID
    
    def _get_employee_location_id(self, employee: Dict) -> str:
        """Get employee's location master_id"""
        location = self.db["locations"].find_one({
            "organization_id": employee["organization_id"],
            "name": employee.get("location", "")
        })
        return location["master_id"] if location else None
    
    def _get_day_total_hours(self, employee_id: str, entry_date: date) -> float:
        """Get total hours entered for a day"""
        entries = list(self.db["timesheet_entries"].find({
            "employee_id": employee_id,
            "date": entry_date.isoformat()
        }))
        return sum([e.get("hours", 0) for e in entries])

# ==================== ROUTER REGISTRATION ====================

def register_timesheet_routes(app, db, get_current_user, require_firm_admin, calendar_engine):
    """Register all timesheet module routes"""
    
    timesheet_engine = TimesheetEngine(db, calendar_engine)
    
    # ==================== TIMESHEET ENTRY ====================
    
    @app.post("/api/timesheet/entries")
    async def create_timesheet_entry(
        entry: TimesheetEntryCreate,
        current_user: dict = Depends(get_current_user)
    ):
        """Create a timesheet entry for a specific date"""
        organization_id = current_user["organization_id"]
        employee_id = current_user.get("employee_id")
        
        if not employee_id:
            raise HTTPException(status_code=400, detail="Only employees can create timesheet entries")
        
        entry_date = datetime.fromisoformat(entry.date).date()
        
        # Get policy
        policy = TimesheetPolicy.get_policy(organization_id)
        
        # Check cycle state
        cycle = TimesheetPolicy.get_current_cycle(organization_id, entry_date)
        if cycle["state"] == TimesheetCycleState.FROZEN:
            raise HTTPException(status_code=400, detail="Timesheet cycle is frozen. Cannot add entries.")
        
        # Validate entry
        validation = timesheet_engine.validate_entry(
            organization_id,
            employee_id,
            entry_date,
            entry.hours,
            policy
        )
        
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Validation failed",
                    "errors": validation["errors"],
                    "warnings": validation["warnings"]
                }
            )
        
        # Validate client and task exist
        client = db["clients"].find_one({
            "master_id": entry.client_id,
            "organization_id": organization_id,
            "status": "ACTIVE"
        })
        
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        task = db["tasks"].find_one({
            "master_id": entry.task_id,
            "organization_id": organization_id,
            "status": "ACTIVE"
        })
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Create entry
        entry_id = str(uuid.uuid4())
        
        timesheet_entry = {
            "entry_id": entry_id,
            "organization_id": organization_id,
            "employee_id": employee_id,
            "date": entry.date,
            "cycle_id": cycle["cycle_id"],
            "client_id": entry.client_id,
            "client_name": client["name"],
            "task_id": entry.task_id,
            "task_name": task["name"],
            "hours": entry.hours,
            "description": entry.description,
            "policy_version_used": policy["policy_version"],
            "status": TimesheetStatus.DRAFT,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "created_by": current_user["user_id"]
        }
        
        db["timesheet_entries"].insert_one(timesheet_entry)
        
        # Log audit
        db["audit_logs"].insert_one({
            "organization_id": organization_id,
            "user_id": current_user["user_id"],
            "action": "CREATE_TIMESHEET_ENTRY",
            "resource_type": "timesheet_entry",
            "resource_id": entry_id,
            "details": {"date": entry.date, "hours": entry.hours},
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "entry_id": entry_id,
            "message": "Timesheet entry created successfully",
            "warnings": validation.get("warnings", [])
        }
    
    @app.get("/api/timesheet/calendar")
    async def get_timesheet_calendar(
        year: int,
        month: int,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Get complete timesheet calendar for a month
        This is the PRIMARY view
        """
        organization_id = current_user["organization_id"]
        employee_id = current_user.get("employee_id")
        
        if not employee_id:
            raise HTTPException(status_code=400, detail="Only employees can view timesheets")
        
        # Get policy
        policy = TimesheetPolicy.get_policy(organization_id)
        
        # Get cycle info
        first_day = date(year, month, 1)
        cycle = TimesheetPolicy.get_current_cycle(organization_id, first_day)
        
        # Get all entries for the month
        start_date = datetime.fromisoformat(cycle["start_date"]).date()
        end_date = datetime.fromisoformat(cycle["end_date"]).date()
        
        entries = list(db["timesheet_entries"].find({
            "employee_id": employee_id,
            "date": {
                "$gte": start_date.isoformat(),
                "$lte": end_date.isoformat()
            }
        }))
        
        # Build calendar data
        calendar_days = []
        current_date = start_date
        
        while current_date <= end_date:
            # Get day entries
            day_entries = [e for e in entries if e["date"] == current_date.isoformat()]
            total_hours = sum([e.get("hours", 0) for e in day_entries])
            
            # Get day status
            day_status = timesheet_engine.get_day_status(
                organization_id,
                employee_id,
                current_date,
                policy
            )
            
            # Remove _id from entries
            for e in day_entries:
                e.pop("_id", None)
            
            calendar_days.append({
                "date": current_date.isoformat(),
                "day_of_week": calendar.day_name[current_date.weekday()],
                "status": day_status,
                "total_hours": total_hours,
                "entries": day_entries,
                "is_editable": cycle["state"] == TimesheetCycleState.OPEN
            })
            
            current_date += timedelta(days=1)
        
        # Get submission status
        submission = db["timesheet_submissions"].find_one({
            "employee_id": employee_id,
            "cycle_id": cycle["cycle_id"]
        })
        
        return {
            "cycle": cycle,
            "policy": policy,
            "calendar": calendar_days,
            "submission": {
                "status": submission.get("status") if submission else None,
                "submitted_at": submission.get("submitted_at") if submission else None,
                "approved_at": submission.get("approved_at") if submission else None,
                "approved_by": submission.get("approved_by") if submission else None
            },
            "summary": {
                "total_working_days": len([d for d in calendar_days if d["status"] in [DayStatus.NOT_FILLED, DayStatus.VALID, DayStatus.UNDER_HOURS, DayStatus.OVER_HOURS]]),
                "days_filled": len([d for d in calendar_days if d["total_hours"] > 0]),
                "total_hours": sum([d["total_hours"] for d in calendar_days])
            }
        }
    
    @app.get("/api/timesheet/entries/{date}")
    async def get_day_entries(
        date: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Get all entries for a specific date"""
        employee_id = current_user.get("employee_id")
        
        if not employee_id:
            raise HTTPException(status_code=400, detail="Only employees can view timesheet entries")
        
        entries = list(db["timesheet_entries"].find({
            "employee_id": employee_id,
            "date": date
        }))
        
        for e in entries:
            e.pop("_id", None)
        
        return {"entries": entries}
    
    @app.put("/api/timesheet/entries/{entry_id}")
    async def update_timesheet_entry(
        entry_id: str,
        entry_update: TimesheetEntryUpdate,
        current_user: dict = Depends(get_current_user)
    ):
        """Update a timesheet entry"""
        organization_id = current_user["organization_id"]
        employee_id = current_user.get("employee_id")
        
        # Get existing entry
        entry = db["timesheet_entries"].find_one({
            "entry_id": entry_id,
            "employee_id": employee_id,
            "organization_id": organization_id
        })
        
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        # Check if entry is editable
        entry_date = datetime.fromisoformat(entry["date"]).date()
        cycle = TimesheetPolicy.get_current_cycle(organization_id, entry_date)
        
        if cycle["state"] == TimesheetCycleState.FROZEN:
            raise HTTPException(status_code=400, detail="Cannot edit frozen timesheet")
        
        if entry["status"] == TimesheetStatus.APPROVED:
            raise HTTPException(status_code=400, detail="Cannot edit approved entry")
        
        # Update entry
        update_data = {k: v for k, v in entry_update.dict(exclude_unset=True).items() if v is not None}
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        db["timesheet_entries"].update_one(
            {"entry_id": entry_id},
            {"$set": update_data}
        )
        
        return {"message": "Entry updated successfully"}
    
    @app.delete("/api/timesheet/entries/{entry_id}")
    async def delete_timesheet_entry(
        entry_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Delete a timesheet entry"""
        employee_id = current_user.get("employee_id")
        
        entry = db["timesheet_entries"].find_one({
            "entry_id": entry_id,
            "employee_id": employee_id
        })
        
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        if entry["status"] == TimesheetStatus.APPROVED:
            raise HTTPException(status_code=400, detail="Cannot delete approved entry")
        
        db["timesheet_entries"].delete_one({"entry_id": entry_id})
        
        return {"message": "Entry deleted successfully"}
    
    # ==================== SUBMISSION & APPROVAL ====================
    
    @app.post("/api/timesheet/submit")
    async def submit_timesheet(
        request: TimesheetSubmitRequest,
        current_user: dict = Depends(get_current_user)
    ):
        """Submit timesheet for approval"""
        organization_id = current_user["organization_id"]
        employee_id = current_user.get("employee_id")
        
        if not employee_id:
            raise HTTPException(status_code=400, detail="Only employees can submit timesheets")
        
        # Check if already submitted
        existing = db["timesheet_submissions"].find_one({
            "employee_id": employee_id,
            "cycle_id": request.cycle_id
        })
        
        if existing and existing["status"] in [TimesheetStatus.SUBMITTED, TimesheetStatus.APPROVED]:
            raise HTTPException(status_code=400, detail="Timesheet already submitted")
        
        # Create submission
        submission_id = str(uuid.uuid4())
        
        submission = {
            "submission_id": submission_id,
            "organization_id": organization_id,
            "employee_id": employee_id,
            "cycle_id": request.cycle_id,
            "status": TimesheetStatus.SUBMITTED,
            "comment": request.comment,
            "submitted_at": datetime.utcnow().isoformat(),
            "created_by": current_user["user_id"]
        }
        
        db["timesheet_submissions"].insert_one(submission)
        
        # Update all entries status
        db["timesheet_entries"].update_many(
            {"employee_id": employee_id, "cycle_id": request.cycle_id},
            {"$set": {"status": TimesheetStatus.SUBMITTED}}
        )
        
        return {"submission_id": submission_id, "message": "Timesheet submitted successfully"}
    
    @app.post("/api/timesheet/submissions/{submission_id}/approve")
    async def approve_timesheet(
        submission_id: str,
        request: TimesheetApprovalRequest,
        current_user: dict = Depends(require_firm_admin)
    ):
        """Approve or reject timesheet submission"""
        organization_id = current_user["organization_id"]
        
        submission = db["timesheet_submissions"].find_one({
            "submission_id": submission_id,
            "organization_id": organization_id
        })
        
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        if submission["status"] != TimesheetStatus.SUBMITTED:
            raise HTTPException(status_code=400, detail="Can only approve submitted timesheets")
        
        # Update submission
        new_status = TimesheetStatus.APPROVED if request.action == "APPROVE" else TimesheetStatus.REJECTED
        
        db["timesheet_submissions"].update_one(
            {"submission_id": submission_id},
            {"$set": {
                "status": new_status,
                "approval_comment": request.comment,
                "approved_by": current_user["user_id"],
                "approved_at": datetime.utcnow().isoformat()
            }}
        )
        
        # Update entries
        db["timesheet_entries"].update_many(
            {"employee_id": submission["employee_id"], "cycle_id": submission["cycle_id"]},
            {"$set": {"status": new_status}}
        )
        
        return {"message": f"Timesheet {request.action.lower()}d successfully"}
    
    # ==================== REPORTS ====================
    
    @app.get("/api/timesheet/reports/compliance")
    async def get_compliance_report(
        cycle_id: str,
        current_user: dict = Depends(require_firm_admin)
    ):
        """Get timesheet compliance report"""
        organization_id = current_user["organization_id"]
        
        # Get all employees
        employees = list(db["employees"].find({
            "organization_id": organization_id,
            "status": "ACTIVE"
        }))
        
        compliance_data = []
        
        for emp in employees:
            submission = db["timesheet_submissions"].find_one({
                "employee_id": emp["employee_id"],
                "cycle_id": cycle_id
            })
            
            compliance_data.append({
                "employee_id": emp["employee_id"],
                "employee_code": emp["employee_code"],
                "full_name": emp["full_name"],
                "department": emp.get("department"),
                "status": submission.get("status") if submission else "NOT_SUBMITTED",
                "submitted_at": submission.get("submitted_at") if submission else None
            })
        
        return {"compliance": compliance_data}
