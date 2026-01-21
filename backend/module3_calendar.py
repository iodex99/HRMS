"""
Module 3: Calendar, Holiday & Weekly-Off Engine
Single source of truth for "what is a working day"
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from enum import Enum
import calendar
import uuid
import pandas as pd
import io

# Date Classification Enum
class DateClassification(str, Enum):
    WORKING_DAY = "WORKING_DAY"
    HOLIDAY = "HOLIDAY"
    WEEKLY_OFF = "WEEKLY_OFF"

# Week Days Enum
class WeekDay(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"

# ==================== CALENDAR RESOLUTION ENGINE ====================

class CalendarResolutionEngine:
    """
    Core engine for determining date classification
    Location-aware, policy-driven, deterministic
    """
    
    def __init__(self, db):
        self.db = db
        self.cache = {}  # Simple in-memory cache
    
    def resolve_date(
        self,
        organization_id: str,
        location_id: str,
        target_date: date,
        policy_version: str = "v1"
    ) -> Dict[str, Any]:
        """
        Resolve a single date classification
        
        Returns:
        {
            "date": "2025-01-21",
            "day_of_week": "TUESDAY",
            "classification": "WORKING_DAY",
            "reference_id": null,
            "reference_type": null,
            "policy_version_used": "v1"
        }
        """
        
        # Check cache
        cache_key = f"{organization_id}:{location_id}:{target_date}:{policy_version}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        result = {
            "date": target_date.isoformat(),
            "day_of_week": self._get_day_name(target_date),
            "classification": DateClassification.WORKING_DAY,
            "reference_id": None,
            "reference_type": None,
            "policy_version_used": policy_version
        }
        
        # Step 1: Check if it's a holiday
        holiday = self.db["holidays"].find_one({
            "organization_id": organization_id,
            "location_id": location_id,
            "date": target_date.isoformat(),
            "status": "ACTIVE"
        })
        
        if holiday:
            result["classification"] = DateClassification.HOLIDAY
            result["reference_id"] = holiday["master_id"]
            result["reference_type"] = "holiday"
            result["holiday_name"] = holiday["name"]
            result["is_mandatory"] = holiday.get("is_mandatory", True)
            self.cache[cache_key] = result
            return result
        
        # Step 2: Check if it's a weekly off
        is_weekly_off, rule = self._check_weekly_off(
            organization_id,
            location_id,
            target_date
        )
        
        if is_weekly_off:
            result["classification"] = DateClassification.WEEKLY_OFF
            result["reference_id"] = rule["master_id"]
            result["reference_type"] = "weekly_off_rule"
            result["rule_name"] = rule["name"]
            result["rule_type"] = rule["rule_type"]
            self.cache[cache_key] = result
            return result
        
        # Step 3: It's a working day
        self.cache[cache_key] = result
        return result
    
    def resolve_date_range(
        self,
        organization_id: str,
        location_id: str,
        start_date: date,
        end_date: date,
        policy_version: str = "v1"
    ) -> List[Dict[str, Any]]:
        """
        Resolve multiple dates in a range
        """
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            resolution = self.resolve_date(
                organization_id,
                location_id,
                current_date,
                policy_version
            )
            results.append(resolution)
            current_date += timedelta(days=1)
        
        return results
    
    def count_working_days(
        self,
        organization_id: str,
        location_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, int]:
        """
        Count working days, holidays, and weekly offs in a range
        """
        resolutions = self.resolve_date_range(
            organization_id,
            location_id,
            start_date,
            end_date
        )
        
        counts = {
            "total_days": len(resolutions),
            "working_days": 0,
            "holidays": 0,
            "weekly_offs": 0
        }
        
        for r in resolutions:
            if r["classification"] == DateClassification.WORKING_DAY:
                counts["working_days"] += 1
            elif r["classification"] == DateClassification.HOLIDAY:
                counts["holidays"] += 1
            elif r["classification"] == DateClassification.WEEKLY_OFF:
                counts["weekly_offs"] += 1
        
        return counts
    
    def _check_weekly_off(
        self,
        organization_id: str,
        location_id: str,
        target_date: date
    ) -> tuple:
        """
        Check if date is a weekly off based on rules
        Returns: (is_weekly_off: bool, rule: dict or None)
        """
        
        # Get active weekly off rules for location
        rules = list(self.db["weekly_off_rules"].find({
            "organization_id": organization_id,
            "location_id": location_id,
            "status": "ACTIVE",
            "effective_from": {"$lte": target_date.isoformat()}
        }))
        
        # Filter by effective_to if present
        active_rules = []
        for rule in rules:
            if rule.get("effective_to"):
                if target_date.isoformat() <= rule["effective_to"]:
                    active_rules.append(rule)
            else:
                active_rules.append(rule)
        
        # Check each rule
        for rule in active_rules:
            if rule["rule_type"] == "FIXED":
                # Check if day matches fixed weekdays
                day_name = self._get_day_name(target_date)
                if day_name in rule.get("fixed_weekdays", []):
                    return True, rule
            
            elif rule["rule_type"] == "NTH_WEEKDAY":
                # Check nth weekday pattern
                config = rule.get("nth_weekday_config", {})
                if self._is_nth_weekday(target_date, config):
                    return True, rule
        
        return False, None
    
    def _is_nth_weekday(self, target_date: date, config: dict) -> bool:
        """
        Check if date matches nth weekday pattern
        Example: 2nd and 4th Saturday
        config = {"weekday": "SATURDAY", "occurrences": [2, 4]}
        """
        target_weekday = config.get("weekday")
        target_occurrences = config.get("occurrences", [])
        
        if not target_weekday or not target_occurrences:
            return False
        
        # Check if day matches
        day_name = self._get_day_name(target_date)
        if day_name != target_weekday:
            return False
        
        # Calculate which occurrence this is in the month
        occurrence = self._get_weekday_occurrence(target_date)
        
        return occurrence in target_occurrences
    
    def _get_weekday_occurrence(self, target_date: date) -> int:
        """
        Get which occurrence of the weekday this is in the month
        Example: 2nd Saturday, 4th Tuesday, etc.
        """
        occurrence = 1
        current_date = target_date.replace(day=1)
        
        while current_date < target_date:
            if current_date.weekday() == target_date.weekday():
                occurrence += 1
            current_date += timedelta(days=1)
        
        return occurrence
    
    def _get_day_name(self, target_date: date) -> str:
        """Get day name as enum value"""
        day_names = [
            WeekDay.MONDAY,
            WeekDay.TUESDAY,
            WeekDay.WEDNESDAY,
            WeekDay.THURSDAY,
            WeekDay.FRIDAY,
            WeekDay.SATURDAY,
            WeekDay.SUNDAY
        ]
        return day_names[target_date.weekday()]
    
    def clear_cache(self):
        """Clear resolution cache"""
        self.cache = {}

# ==================== CALENDAR SNAPSHOT MANAGER ====================

class CalendarSnapshotManager:
    """
    Manages calendar snapshots for immutability
    Once a date is referenced by transactions, its classification is locked
    """
    
    def __init__(self, db):
        self.db = db
    
    def create_snapshot(
        self,
        organization_id: str,
        location_id: str,
        date_range: tuple,
        reason: str,
        created_by: str
    ):
        """
        Create a calendar snapshot for a date range
        """
        snapshot_id = str(uuid.uuid4())
        start_date, end_date = date_range
        
        # Get calendar resolutions
        engine = CalendarResolutionEngine(self.db)
        resolutions = engine.resolve_date_range(
            organization_id,
            location_id,
            start_date,
            end_date
        )
        
        snapshot = {
            "snapshot_id": snapshot_id,
            "organization_id": organization_id,
            "location_id": location_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "reason": reason,
            "resolutions": resolutions,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.db["calendar_snapshots"].insert_one(snapshot)
        return snapshot_id
    
    def get_snapshot(self, snapshot_id: str):
        """Get calendar snapshot"""
        return self.db["calendar_snapshots"].find_one({"snapshot_id": snapshot_id})
    
    def is_date_locked(
        self,
        organization_id: str,
        location_id: str,
        target_date: date
    ) -> bool:
        """
        Check if date classification is locked by any transaction
        """
        # Check if date is referenced in any snapshot
        snapshot = self.db["calendar_snapshots"].find_one({
            "organization_id": organization_id,
            "location_id": location_id,
            "start_date": {"$lte": target_date.isoformat()},
            "end_date": {"$gte": target_date.isoformat()}
        })
        
        return snapshot is not None

# ==================== PYDANTIC MODELS ====================

class CalendarResolutionRequest(BaseModel):
    location_id: str
    date: Optional[str] = None  # Single date
    start_date: Optional[str] = None  # Range start
    end_date: Optional[str] = None  # Range end
    policy_version: str = "v1"

class WorkingDayCountRequest(BaseModel):
    location_id: str
    start_date: str
    end_date: str

class BulkHolidayImportRequest(BaseModel):
    location_id: str
    year: int

class CalendarSnapshotRequest(BaseModel):
    location_id: str
    start_date: str
    end_date: str
    reason: str

# ==================== ROUTER REGISTRATION ====================

def register_calendar_routes(app, db, get_current_user, require_firm_admin):
    """Register all calendar module routes"""
    
    # Initialize engines
    resolution_engine = CalendarResolutionEngine(db)
    snapshot_manager = CalendarSnapshotManager(db)
    
    # ==================== CALENDAR RESOLUTION API ====================
    
    @app.post("/api/calendar/resolve")
    async def resolve_calendar(
        request: CalendarResolutionRequest,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Resolve calendar for date or date range
        This is the ONLY way other modules should determine working days
        """
        organization_id = current_user["organization_id"]
        
        # Validate location exists
        location = db["locations"].find_one({
            "master_id": request.location_id,
            "organization_id": organization_id
        })
        
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        
        # Single date resolution
        if request.date:
            target_date = datetime.fromisoformat(request.date).date()
            resolution = resolution_engine.resolve_date(
                organization_id,
                request.location_id,
                target_date,
                request.policy_version
            )
            return {"resolution": resolution}
        
        # Date range resolution
        elif request.start_date and request.end_date:
            start_date = datetime.fromisoformat(request.start_date).date()
            end_date = datetime.fromisoformat(request.end_date).date()
            
            if start_date > end_date:
                raise HTTPException(status_code=400, detail="Start date must be before end date")
            
            resolutions = resolution_engine.resolve_date_range(
                organization_id,
                request.location_id,
                start_date,
                end_date,
                request.policy_version
            )
            return {"resolutions": resolutions}
        
        else:
            raise HTTPException(status_code=400, detail="Provide either 'date' or 'start_date' and 'end_date'")
    
    @app.post("/api/calendar/working-days")
    async def count_working_days(
        request: WorkingDayCountRequest,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Count working days in a date range
        """
        organization_id = current_user["organization_id"]
        
        start_date = datetime.fromisoformat(request.start_date).date()
        end_date = datetime.fromisoformat(request.end_date).date()
        
        counts = resolution_engine.count_working_days(
            organization_id,
            request.location_id,
            start_date,
            end_date
        )
        
        return counts
    
    @app.get("/api/calendar/month/{location_id}/{year}/{month}")
    async def get_month_calendar(
        location_id: str,
        year: int,
        month: int,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Get complete month calendar with classifications
        """
        organization_id = current_user["organization_id"]
        
        # Validate month
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="Invalid month")
        
        # Get month date range
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        
        # Resolve entire month
        resolutions = resolution_engine.resolve_date_range(
            organization_id,
            location_id,
            first_day,
            last_day
        )
        
        # Add month summary
        summary = {
            "total_days": len(resolutions),
            "working_days": len([r for r in resolutions if r["classification"] == DateClassification.WORKING_DAY]),
            "holidays": len([r for r in resolutions if r["classification"] == DateClassification.HOLIDAY]),
            "weekly_offs": len([r for r in resolutions if r["classification"] == DateClassification.WEEKLY_OFF])
        }
        
        return {
            "year": year,
            "month": month,
            "month_name": calendar.month_name[month],
            "summary": summary,
            "calendar": resolutions
        }
    
    # ==================== CALENDAR SNAPSHOTS ====================
    
    @app.post("/api/calendar/snapshot")
    async def create_calendar_snapshot(
        request: CalendarSnapshotRequest,
        current_user: dict = Depends(require_firm_admin)
    ):
        """
        Create a calendar snapshot (locks date classifications)
        """
        organization_id = current_user["organization_id"]
        
        start_date = datetime.fromisoformat(request.start_date).date()
        end_date = datetime.fromisoformat(request.end_date).date()
        
        snapshot_id = snapshot_manager.create_snapshot(
            organization_id,
            request.location_id,
            (start_date, end_date),
            request.reason,
            current_user["user_id"]
        )
        
        return {
            "snapshot_id": snapshot_id,
            "message": "Calendar snapshot created successfully"
        }
    
    @app.get("/api/calendar/snapshot/{snapshot_id}")
    async def get_calendar_snapshot(
        snapshot_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Get calendar snapshot details
        """
        snapshot = snapshot_manager.get_snapshot(snapshot_id)
        
        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        
        if snapshot["organization_id"] != current_user["organization_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        snapshot.pop("_id", None)
        return snapshot
    
    # ==================== BULK HOLIDAY IMPORT ====================
    
    @app.post("/api/calendar/holidays/bulk-import")
    async def bulk_import_holidays(
        location_id: str,
        year: int,
        file: UploadFile = File(...),
        current_user: dict = Depends(require_firm_admin)
    ):
        """
        Bulk import holidays for a location and year
        """
        organization_id = current_user["organization_id"]
        
        # Validate file
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
        
        # Validate columns
        required_cols = {"date", "name"}
        if not required_cols.issubset(set(df.columns)):
            raise HTTPException(status_code=400, detail=f"Missing required columns: {required_cols}")
        
        # Validate and import
        errors = []
        imported_count = 0
        
        for idx, row in df.iterrows():
            try:
                # Parse date
                holiday_date = pd.to_datetime(row['date']).date()
                
                # Check if already exists
                existing = db["holidays"].find_one({
                    "organization_id": organization_id,
                    "location_id": location_id,
                    "date": holiday_date.isoformat(),
                    "status": "ACTIVE"
                })
                
                if existing:
                    errors.append({"row": idx + 2, "error": f"Holiday on {holiday_date} already exists"})
                    continue
                
                # Create holiday
                master_id = str(uuid.uuid4())
                holiday = {
                    "master_id": master_id,
                    "organization_id": organization_id,
                    "location_id": location_id,
                    "name": row['name'],
                    "date": holiday_date.isoformat(),
                    "year": year,
                    "is_mandatory": row.get('is_mandatory', True),
                    "description": row.get('description', ''),
                    "status": "ACTIVE",
                    "source": "IMPORT",
                    "created_by": current_user["user_id"],
                    "created_at": datetime.utcnow().isoformat()
                }
                
                db["holidays"].insert_one(holiday)
                imported_count += 1
                
                # Clear cache
                resolution_engine.clear_cache()
                
            except Exception as e:
                errors.append({"row": idx + 2, "error": str(e)})
        
        return {
            "total_rows": len(df),
            "imported": imported_count,
            "errors": len(errors),
            "error_details": errors[:50]  # Return first 50 errors
        }
    
    # ==================== CALENDAR REPORTS ====================
    
    @app.get("/api/calendar/reports/holidays")
    async def get_holiday_calendar_report(
        location_id: str,
        year: int,
        current_user: dict = Depends(get_current_user),
        format: str = "json"
    ):
        """
        Get holiday calendar report for a location and year
        """
        organization_id = current_user["organization_id"]
        
        holidays = list(db["holidays"].find({
            "organization_id": organization_id,
            "location_id": location_id,
            "year": year,
            "status": "ACTIVE"
        }).sort("date", 1))
        
        for h in holidays:
            h.pop("_id", None)
        
        if format == "excel":
            df = pd.DataFrame(holidays)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name=f'Holidays {year}')
            output.seek(0)
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                output,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={"Content-Disposition": f"attachment; filename=holidays_{year}.xlsx"}
            )
        
        return {"holidays": holidays}
    
    @app.get("/api/calendar/reports/working-days")
    async def get_working_days_report(
        location_id: str,
        start_date: str,
        end_date: str,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Get working days analysis report
        """
        organization_id = current_user["organization_id"]
        
        start = datetime.fromisoformat(start_date).date()
        end = datetime.fromisoformat(end_date).date()
        
        # Get all resolutions
        resolutions = resolution_engine.resolve_date_range(
            organization_id,
            location_id,
            start,
            end
        )
        
        # Analyze by month
        monthly_analysis = {}
        for r in resolutions:
            date_obj = datetime.fromisoformat(r["date"]).date()
            month_key = f"{date_obj.year}-{date_obj.month:02d}"
            
            if month_key not in monthly_analysis:
                monthly_analysis[month_key] = {
                    "month": calendar.month_name[date_obj.month],
                    "year": date_obj.year,
                    "working_days": 0,
                    "holidays": 0,
                    "weekly_offs": 0
                }
            
            if r["classification"] == DateClassification.WORKING_DAY:
                monthly_analysis[month_key]["working_days"] += 1
            elif r["classification"] == DateClassification.HOLIDAY:
                monthly_analysis[month_key]["holidays"] += 1
            elif r["classification"] == DateClassification.WEEKLY_OFF:
                monthly_analysis[month_key]["weekly_offs"] += 1
        
        return {
            "location_id": location_id,
            "start_date": start_date,
            "end_date": end_date,
            "monthly_breakdown": list(monthly_analysis.values()),
            "total_summary": {
                "working_days": sum([m["working_days"] for m in monthly_analysis.values()]),
                "holidays": sum([m["holidays"] for m in monthly_analysis.values()]),
                "weekly_offs": sum([m["weekly_offs"] for m in monthly_analysis.values()])
            }
        }
    
    @app.get("/api/calendar/cache/clear")
    async def clear_calendar_cache(
        current_user: dict = Depends(require_firm_admin)
    ):
        """
        Clear calendar resolution cache
        """
        resolution_engine.clear_cache()
        return {"message": "Calendar cache cleared successfully"}
