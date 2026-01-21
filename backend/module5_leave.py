"""
Module 5: Leave Management
Policy-Driven, Calendar-Aware, Timesheet-Integrated Leave System
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from enum import Enum
import uuid
import pandas as pd
import io

# ==================== ENUMS ====================

class LeaveStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class LeaveDuration(str, Enum):
    FULL_DAY = "FULL_DAY"
    HALF_DAY = "HALF_DAY"
    HOURLY = "HOURLY"

class AccrualMethod(str, Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"
    DOJ_BASED = "DOJ_BASED"
    PRORATA = "PRORATA"

class BalanceTransactionType(str, Enum):
    OPENING = "OPENING"
    ACCRUAL = "ACCRUAL"
    AVAILED = "AVAILED"
    LAPSED = "LAPSED"
    CARRYFORWARD = "CARRYFORWARD"
    ADJUSTMENT = "ADJUSTMENT"
    COMPOFF_EARNED = "COMPOFF_EARNED"
    COMPOFF_AVAILED = "COMPOFF_AVAILED"

# ==================== LEAVE POLICY ENGINE ====================

class LeavePolicy:
    """
    Policy Engine for Leave Rules
    In production, this would read from policy management system
    """
    
    @staticmethod
    def get_policy(organization_id: str, version: str = "v1") -> Dict[str, Any]:
        """Get leave policy configuration"""
        return {
            "policy_version": version,
            "leave_types": {
                "CL": {
                    "name": "Casual Leave",
                    "accrual_method": AccrualMethod.MONTHLY,
                    "monthly_accrual": 1.0,
                    "max_balance": 12.0,
                    "carryforward_allowed": False,
                    "allow_half_day": True,
                    "min_advance_notice_days": 0,
                    "require_approval": True,
                    "eligible_for_all": True
                },
                "SL": {
                    "name": "Sick Leave",
                    "accrual_method": AccrualMethod.MONTHLY,
                    "monthly_accrual": 0.5,
                    "max_balance": 6.0,
                    "carryforward_allowed": False,
                    "allow_half_day": True,
                    "min_advance_notice_days": 0,
                    "require_approval": False,  # Auto-approve
                    "eligible_for_all": True
                },
                "EL": {
                    "name": "Earned Leave",
                    "accrual_method": AccrualMethod.MONTHLY,
                    "monthly_accrual": 1.5,
                    "max_balance": 30.0,
                    "carryforward_allowed": True,
                    "carryforward_max": 15.0,
                    "allow_half_day": False,
                    "min_advance_notice_days": 7,
                    "require_approval": True,
                    "eligible_for_all": True
                },
                "COMPOFF": {
                    "name": "Compensatory Off",
                    "accrual_method": None,  # Earned via holiday work
                    "max_balance": 10.0,
                    "validity_days": 90,  # Expires in 90 days
                    "allow_half_day": True,
                    "min_advance_notice_days": 1,
                    "require_approval": True,
                    "eligible_for_all": True
                }
            },
            "allow_negative_balance": False,
            "sandwich_leave_rule": False  # If true, leaves between holidays count
        }
    
    @staticmethod
    def get_leave_type_config(organization_id: str, leave_type: str) -> Optional[Dict[str, Any]]:
        """Get configuration for specific leave type"""
        policy = LeavePolicy.get_policy(organization_id)
        return policy["leave_types"].get(leave_type)

# ==================== PYDANTIC MODELS ====================

class LeaveApplicationCreate(BaseModel):
    leave_type: str
    from_date: str
    to_date: str
    duration: LeaveDuration = LeaveDuration.FULL_DAY
    reason: str = Field(..., min_length=1)

class LeaveApprovalRequest(BaseModel):
    action: str = Field(..., pattern="^(APPROVE|REJECT)$")
    comment: Optional[str] = None

class BalanceAdjustmentRequest(BaseModel):
    leave_type: str
    adjustment: float
    reason: str = Field(..., min_length=1)

class CompOffEarnRequest(BaseModel):
    date: str
    reason: str

# ==================== LEAVE ENGINE ====================

class LeaveEngine:
    """Core leave management business logic"""
    
    def __init__(self, db, calendar_engine):
        self.db = db
        self.calendar_engine = calendar_engine
    
    def get_leave_balance(
        self,
        organization_id: str,
        employee_id: str,
        leave_type: str
    ) -> Dict[str, float]:
        """
        Calculate current leave balance
        Returns: {opening, accrued, availed, lapsed, carried_forward, closing}
        """
        # Get all balance transactions
        transactions = list(self.db["leave_balance_transactions"].find({
            "organization_id": organization_id,
            "employee_id": employee_id,
            "leave_type": leave_type
        }).sort("transaction_date", 1))
        
        balance = {
            "opening": 0.0,
            "accrued": 0.0,
            "availed": 0.0,
            "lapsed": 0.0,
            "carried_forward": 0.0,
            "closing": 0.0
        }
        
        for txn in transactions:
            txn_type = txn["transaction_type"]
            amount = txn["amount"]
            
            if txn_type == BalanceTransactionType.OPENING:
                balance["opening"] += amount
            elif txn_type == BalanceTransactionType.ACCRUAL:
                balance["accrued"] += amount
            elif txn_type == BalanceTransactionType.AVAILED:
                balance["availed"] += amount
            elif txn_type == BalanceTransactionType.LAPSED:
                balance["lapsed"] += amount
            elif txn_type == BalanceTransactionType.CARRYFORWARD:
                balance["carried_forward"] += amount
            elif txn_type in [BalanceTransactionType.COMPOFF_EARNED, BalanceTransactionType.ADJUSTMENT]:
                balance["accrued"] += amount
            elif txn_type == BalanceTransactionType.COMPOFF_AVAILED:
                balance["availed"] += amount
        
        balance["closing"] = (
            balance["opening"] + 
            balance["accrued"] + 
            balance["carried_forward"] - 
            balance["availed"] - 
            balance["lapsed"]
        )
        
        return balance
    
    def validate_leave_application(
        self,
        organization_id: str,
        employee_id: str,
        leave_type: str,
        from_date: date,
        to_date: date,
        duration: LeaveDuration,
        policy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate leave application
        Returns: {valid: bool, errors: [], warnings: []}
        """
        errors = []
        warnings = []
        
        leave_config = policy["leave_types"].get(leave_type)
        if not leave_config:
            errors.append(f"Leave type '{leave_type}' not found")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Get employee
        employee = self.db["employees"].find_one({
            "employee_id": employee_id,
            "organization_id": organization_id
        })
        
        if not employee:
            errors.append("Employee not found")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # Rule 1: Check date order
        if from_date > to_date:
            errors.append("From date must be before or equal to to date")
        
        # Rule 2: Check advance notice
        min_notice = leave_config.get("min_advance_notice_days", 0)
        if min_notice > 0:
            days_advance = (from_date - date.today()).days
            if days_advance < min_notice:
                errors.append(f"Minimum {min_notice} days advance notice required")
        
        # Rule 3: Check half-day eligibility
        if duration == LeaveDuration.HALF_DAY and not leave_config.get("allow_half_day", False):
            errors.append(f"{leave_type} does not allow half-day leaves")
        
        # Rule 4: Calculate working days in range
        location_id = self._get_employee_location_id(employee)
        working_days = self._count_working_days_in_range(
            organization_id,
            location_id,
            from_date,
            to_date
        )
        
        if working_days == 0:
            errors.append("No working days in selected range (all holidays/weekly-offs)")
        
        # Rule 5: Check balance
        balance = self.get_leave_balance(organization_id, employee_id, leave_type)
        leave_days = working_days if duration == LeaveDuration.FULL_DAY else working_days * 0.5
        
        if balance["closing"] < leave_days:
            if not policy.get("allow_negative_balance", False):
                errors.append(f"Insufficient balance. Available: {balance['closing']}, Required: {leave_days}")
        
        # Rule 6: Check timesheet conflicts
        timesheet_conflict = self._check_timesheet_conflict(employee_id, from_date, to_date)
        if timesheet_conflict:
            errors.append(f"Timesheet already filled for dates: {', '.join(timesheet_conflict)}")
        
        # Rule 7: Check overlapping leaves
        overlap = self._check_leave_overlap(employee_id, from_date, to_date)
        if overlap:
            errors.append(f"Leave already exists for dates: {', '.join(overlap)}")
        
        # Rule 8: Check comp-off expiry
        if leave_type == "COMPOFF":
            validity_days = leave_config.get("validity_days", 90)
            # Get oldest comp-off
            oldest_compoff = self.db["leave_balance_transactions"].find_one({
                "employee_id": employee_id,
                "leave_type": "COMPOFF",
                "transaction_type": BalanceTransactionType.COMPOFF_EARNED,
                "is_expired": {"$ne": True}
            }, sort=[("transaction_date", 1)])
            
            if oldest_compoff:
                earned_date = datetime.fromisoformat(oldest_compoff["transaction_date"]).date()
                days_since_earned = (date.today() - earned_date).days
                if days_since_earned > validity_days:
                    warnings.append(f"Some comp-offs are expired (>{validity_days} days old)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "leave_days_calculated": leave_days if len(errors) == 0 else 0
        }
    
    def _get_employee_location_id(self, employee: Dict) -> str:
        """Get employee's location master_id"""
        location = self.db["locations"].find_one({
            "organization_id": employee["organization_id"],
            "name": employee.get("location", "")
        })
        return location["master_id"] if location else None
    
    def _count_working_days_in_range(
        self,
        organization_id: str,
        location_id: str,
        from_date: date,
        to_date: date
    ) -> int:
        """Count working days in date range"""
        resolutions = self.calendar_engine.resolve_date_range(
            organization_id,
            location_id,
            from_date,
            to_date
        )
        
        working_days = len([r for r in resolutions if r["classification"] == "WORKING_DAY"])
        return working_days
    
    def _check_timesheet_conflict(
        self,
        employee_id: str,
        from_date: date,
        to_date: date
    ) -> List[str]:
        """Check if timesheet exists for date range"""
        conflict_dates = []
        current_date = from_date
        
        while current_date <= to_date:
            entries = list(self.db["timesheet_entries"].find({
                "employee_id": employee_id,
                "date": current_date.isoformat()
            }))
            
            if entries:
                conflict_dates.append(current_date.isoformat())
            
            current_date += timedelta(days=1)
        
        return conflict_dates
    
    def _check_leave_overlap(
        self,
        employee_id: str,
        from_date: date,
        to_date: date
    ) -> List[str]:
        """Check if leave already exists for date range"""
        overlap_dates = []
        
        # Get existing approved/pending leaves
        existing_leaves = list(self.db["leave_applications"].find({
            "employee_id": employee_id,
            "status": {"$in": [LeaveStatus.APPROVED, LeaveStatus.PENDING]},
            "$or": [
                {"from_date": {"$lte": to_date.isoformat()}, "to_date": {"$gte": from_date.isoformat()}}
            ]
        }))
        
        if existing_leaves:
            for leave in existing_leaves:
                leave_from = datetime.fromisoformat(leave["from_date"]).date()
                leave_to = datetime.fromisoformat(leave["to_date"]).date()
                
                # Calculate overlap
                overlap_start = max(from_date, leave_from)
                overlap_end = min(to_date, leave_to)
                
                current = overlap_start
                while current <= overlap_end:
                    overlap_dates.append(current.isoformat())
                    current += timedelta(days=1)
        
        return overlap_dates
    
    def post_balance_transaction(
        self,
        organization_id: str,
        employee_id: str,
        leave_type: str,
        transaction_type: BalanceTransactionType,
        amount: float,
        reference_id: str,
        reference_type: str,
        reason: str,
        policy_version: str,
        created_by: str
    ):
        """Post a balance transaction (append-only)"""
        transaction_id = str(uuid.uuid4())
        
        transaction = {
            "transaction_id": transaction_id,
            "organization_id": organization_id,
            "employee_id": employee_id,
            "leave_type": leave_type,
            "transaction_type": transaction_type,
            "amount": amount,
            "transaction_date": datetime.utcnow().isoformat(),
            "reference_id": reference_id,
            "reference_type": reference_type,
            "reason": reason,
            "policy_version": policy_version,
            "created_by": created_by,
            "is_expired": False
        }
        
        self.db["leave_balance_transactions"].insert_one(transaction)
        return transaction_id

# ==================== ROUTER REGISTRATION ====================

def register_leave_routes(app, db, get_current_user, require_firm_admin, calendar_engine):
    """Register all leave management routes"""
    
    leave_engine = LeaveEngine(db, calendar_engine)
    
    # ==================== LEAVE BALANCE ====================
    
    @app.get("/api/leave/balance")
    async def get_my_leave_balance(
        current_user: dict = Depends(get_current_user)
    ):
        """Get current user's leave balance summary"""
        organization_id = current_user["organization_id"]
        employee_id = current_user.get("employee_id")
        
        if not employee_id:
            raise HTTPException(status_code=400, detail="Only employees can view leave balance")
        
        policy = LeavePolicy.get_policy(organization_id)
        
        balances = []
        for leave_type, config in policy["leave_types"].items():
            balance = leave_engine.get_leave_balance(
                organization_id,
                employee_id,
                leave_type
            )
            
            balances.append({
                "leave_type": leave_type,
                "leave_type_name": config["name"],
                "opening": balance["opening"],
                "accrued": balance["accrued"],
                "availed": balance["availed"],
                "lapsed": balance["lapsed"],
                "carried_forward": balance["carried_forward"],
                "closing": balance["closing"]
            })
        
        return {"balances": balances}
    
    @app.get("/api/leave/balance/{employee_id}")
    async def get_employee_leave_balance(
        employee_id: str,
        current_user: dict = Depends(require_firm_admin)
    ):
        """Get employee's leave balance (admin only)"""
        organization_id = current_user["organization_id"]
        
        policy = LeavePolicy.get_policy(organization_id)
        
        balances = []
        for leave_type, config in policy["leave_types"].items():
            balance = leave_engine.get_leave_balance(
                organization_id,
                employee_id,
                leave_type
            )
            
            balances.append({
                "leave_type": leave_type,
                "leave_type_name": config["name"],
                **balance
            })
        
        return {"employee_id": employee_id, "balances": balances}
    
    # ==================== LEAVE APPLICATION ====================
    
    @app.post("/api/leave/apply")
    async def apply_leave(
        application: LeaveApplicationCreate,
        current_user: dict = Depends(get_current_user)
    ):
        """Apply for leave"""
        organization_id = current_user["organization_id"]
        employee_id = current_user.get("employee_id")
        
        if not employee_id:
            raise HTTPException(status_code=400, detail="Only employees can apply for leave")
        
        from_date = datetime.fromisoformat(application.from_date).date()
        to_date = datetime.fromisoformat(application.to_date).date()
        
        # Get policy
        policy = LeavePolicy.get_policy(organization_id)
        
        # Validate application
        validation = leave_engine.validate_leave_application(
            organization_id,
            employee_id,
            application.leave_type,
            from_date,
            to_date,
            application.duration,
            policy
        )
        
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Leave application validation failed",
                    "errors": validation["errors"],
                    "warnings": validation["warnings"]
                }
            )
        
        leave_days = validation["leave_days_calculated"]
        
        # Create leave application
        application_id = str(uuid.uuid4())
        
        leave_config = policy["leave_types"][application.leave_type]
        initial_status = LeaveStatus.PENDING
        
        # Auto-approve if policy says so
        if not leave_config.get("require_approval", True):
            initial_status = LeaveStatus.APPROVED
        
        leave_app = {
            "application_id": application_id,
            "organization_id": organization_id,
            "employee_id": employee_id,
            "leave_type": application.leave_type,
            "from_date": application.from_date,
            "to_date": application.to_date,
            "duration": application.duration,
            "leave_days": leave_days,
            "reason": application.reason,
            "status": initial_status,
            "policy_version": policy["policy_version"],
            "applied_at": datetime.utcnow().isoformat(),
            "created_by": current_user["user_id"]
        }
        
        db["leave_applications"].insert_one(leave_app)
        
        # If auto-approved, post balance transaction
        if initial_status == LeaveStatus.APPROVED:
            leave_engine.post_balance_transaction(
                organization_id,
                employee_id,
                application.leave_type,
                BalanceTransactionType.AVAILED,
                -leave_days,  # Negative because balance reduces
                application_id,
                "leave_application",
                f"Leave from {application.from_date} to {application.to_date}",
                policy["policy_version"],
                current_user["user_id"]
            )
            
            # Create leave entries for timesheet blocking
            current_date = from_date
            while current_date <= to_date:
                entry_id = str(uuid.uuid4())
                self.db["leave_entries"].insert_one({
                    "entry_id": entry_id,
                    "employee_id": employee_id,
                    "date": current_date.isoformat(),
                    "leave_type": application.duration,
                    "status": LeaveStatus.APPROVED,
                    "application_id": application_id
                })
                current_date += timedelta(days=1)
        
        # Log audit
        db["audit_logs"].insert_one({
            "organization_id": organization_id,
            "user_id": current_user["user_id"],
            "action": "APPLY_LEAVE",
            "resource_type": "leave_application",
            "resource_id": application_id,
            "details": {
                "leave_type": application.leave_type,
                "from_date": application.from_date,
                "to_date": application.to_date,
                "days": leave_days,
                "status": initial_status
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "application_id": application_id,
            "message": f"Leave application {'approved' if initial_status == LeaveStatus.APPROVED else 'submitted'} successfully",
            "status": initial_status,
            "warnings": validation.get("warnings", [])
        }
    
    @app.get("/api/leave/applications")
    async def get_my_leave_applications(
        current_user: dict = Depends(get_current_user),
        status: Optional[LeaveStatus] = None
    ):
        """Get current user's leave applications"""
        employee_id = current_user.get("employee_id")
        
        if not employee_id:
            raise HTTPException(status_code=400, detail="Only employees can view leave applications")
        
        query = {"employee_id": employee_id}
        if status:
            query["status"] = status
        
        applications = list(db["leave_applications"].find(query).sort("applied_at", -1))
        
        for app in applications:
            app.pop("_id", None)
        
        return {"applications": applications}
    
    @app.post("/api/leave/applications/{application_id}/approve")
    async def approve_leave(
        application_id: str,
        request: LeaveApprovalRequest,
        current_user: dict = Depends(require_firm_admin)
    ):
        """Approve or reject leave application"""
        organization_id = current_user["organization_id"]
        
        application = db["leave_applications"].find_one({
            "application_id": application_id,
            "organization_id": organization_id
        })
        
        if not application:
            raise HTTPException(status_code=404, detail="Leave application not found")
        
        if application["status"] != LeaveStatus.PENDING:
            raise HTTPException(status_code=400, detail=f"Cannot process leave in {application['status']} status")
        
        new_status = LeaveStatus.APPROVED if request.action == "APPROVE" else LeaveStatus.REJECTED
        
        # Update application
        db["leave_applications"].update_one(
            {"application_id": application_id},
            {"$set": {
                "status": new_status,
                "approval_comment": request.comment,
                "approved_by": current_user["user_id"],
                "approved_at": datetime.utcnow().isoformat()
            }}
        )
        
        # If approved, post balance transaction and create leave entries
        if new_status == LeaveStatus.APPROVED:
            leave_engine.post_balance_transaction(
                organization_id,
                application["employee_id"],
                application["leave_type"],
                BalanceTransactionType.AVAILED,
                -application["leave_days"],
                application_id,
                "leave_application",
                f"Leave from {application['from_date']} to {application['to_date']}",
                application["policy_version"],
                current_user["user_id"]
            )
            
            # Create leave entries for timesheet blocking
            from_date = datetime.fromisoformat(application["from_date"]).date()
            to_date = datetime.fromisoformat(application["to_date"]).date()
            current_date = from_date
            
            while current_date <= to_date:
                entry_id = str(uuid.uuid4())
                db["leave_entries"].insert_one({
                    "entry_id": entry_id,
                    "employee_id": application["employee_id"],
                    "date": current_date.isoformat(),
                    "leave_type": application["duration"],
                    "status": LeaveStatus.APPROVED,
                    "application_id": application_id
                })
                current_date += timedelta(days=1)
        
        return {"message": f"Leave {request.action.lower()}d successfully"}
    
    # ==================== COMP-OFF ====================
    
    @app.post("/api/leave/compoff/earn")
    async def earn_compoff(
        request: CompOffEarnRequest,
        current_user: dict = Depends(get_current_user)
    ):
        """Earn comp-off for working on holiday/weekly-off"""
        organization_id = current_user["organization_id"]
        employee_id = current_user.get("employee_id")
        
        if not employee_id:
            raise HTTPException(status_code=400, detail="Only employees can earn comp-offs")
        
        work_date = datetime.fromisoformat(request.date).date()
        
        # Check if worked on holiday/weekly-off
        timesheet_entry = db["timesheet_entries"].find_one({
            "employee_id": employee_id,
            "date": request.date
        })
        
        if not timesheet_entry:
            raise HTTPException(status_code=400, detail="No timesheet entry found for this date")
        
        # Check if it was a holiday/weekly-off
        employee = db["employees"].find_one({"employee_id": employee_id})
        location_id = leave_engine._get_employee_location_id(employee)
        
        resolution = calendar_engine.resolve_date(
            organization_id,
            location_id,
            work_date
        )
        
        if resolution["classification"] not in ["HOLIDAY", "WEEKLY_OFF"]:
            raise HTTPException(status_code=400, detail="Can only earn comp-off for working on holiday/weekly-off")
        
        # Check if comp-off already earned
        existing = db["leave_balance_transactions"].find_one({
            "employee_id": employee_id,
            "leave_type": "COMPOFF",
            "transaction_type": BalanceTransactionType.COMPOFF_EARNED,
            "reference_id": timesheet_entry["entry_id"]
        })
        
        if existing:
            raise HTTPException(status_code=400, detail="Comp-off already earned for this date")
        
        # Post comp-off earned
        policy = LeavePolicy.get_policy(organization_id)
        
        leave_engine.post_balance_transaction(
            organization_id,
            employee_id,
            "COMPOFF",
            BalanceTransactionType.COMPOFF_EARNED,
            1.0,  # 1 comp-off day
            timesheet_entry["entry_id"],
            "timesheet_entry",
            f"Worked on {resolution['classification'].lower()}: {request.reason}",
            policy["policy_version"],
            current_user["user_id"]
        )
        
        return {"message": "Comp-off earned successfully", "days_earned": 1.0}
    
    # ==================== REPORTS ====================
    
    @app.get("/api/leave/reports/balance-summary")
    async def get_balance_summary_report(
        current_user: dict = Depends(require_firm_admin)
    ):
        """Get leave balance summary for all employees"""
        organization_id = current_user["organization_id"]
        
        employees = list(db["employees"].find({
            "organization_id": organization_id,
            "status": "ACTIVE"
        }))
        
        policy = LeavePolicy.get_policy(organization_id)
        
        summary = []
        
        for emp in employees:
            emp_balances = []
            for leave_type in policy["leave_types"].keys():
                balance = leave_engine.get_leave_balance(
                    organization_id,
                    emp["employee_id"],
                    leave_type
                )
                emp_balances.append({
                    "leave_type": leave_type,
                    "closing_balance": balance["closing"]
                })
            
            summary.append({
                "employee_id": emp["employee_id"],
                "employee_code": emp["employee_code"],
                "full_name": emp["full_name"],
                "department": emp.get("department"),
                "balances": emp_balances
            })
        
        return {"summary": summary}
