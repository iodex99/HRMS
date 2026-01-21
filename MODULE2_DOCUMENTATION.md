# Module 2: Admin Masters & Reference Data Management

## Overview

Module 2 provides comprehensive master data management capabilities for the HRMS system. It defines the controlled vocabulary and reference structures used by all operational modules.

## Key Principles

1. **Fully Configurable**: No hardcoded values - everything is firm-specific
2. **Dependency-Aware**: Checks usage before allowing changes
3. **Audit-Safe**: Complete audit trail for all changes
4. **Import-First**: Bulk import support for migration scenarios
5. **Change-Resistant**: Prevents accidental breakage through dependency checks

## Master Entities

### Organizational Masters

#### 1. Department Master
- **Purpose**: Define organizational departments
- **Fields**:
  - Code (unique per organization)
  - Name
  - Description
  - Effective From date
  - Status (Active/Inactive)
  
- **Dependencies**: Used by employees
- **API Endpoints**:
  - `POST /api/masters/departments` - Create department
  - `GET /api/masters/departments` - List departments
  - `GET /api/masters/departments/{id}` - Get department details
  - `PUT /api/masters/departments/{id}` - Update department
  - `PATCH /api/masters/departments/{id}/status` - Change status
  - `GET /api/masters/departments/{id}/dependencies` - Check dependencies

#### 2. Designation Master
- **Purpose**: Define job titles and hierarchy levels
- **Fields**:
  - Code (unique per organization)
  - Name
  - Description
  - Level (hierarchy level, optional)
  - Effective From date
  - Status (Active/Inactive)
  
- **Dependencies**: Used by employees
- **Use Cases**: Career progression, reporting hierarchy, pay grade mapping

#### 3. Employee Type Master
- **Purpose**: Define employee categories
- **Fields**:
  - Code (unique per organization)
  - Name
  - Description
  - Effective From date
  - Status (Active/Inactive)
  
- **Dependencies**: Used by employees
- **Examples**: Full-Time, Part-Time, Contract, Intern, Consultant

#### 4. Location Master
- **Purpose**: Define office locations
- **Fields**:
  - Code (unique per organization)
  - Name
  - Address
  - City
  - State
  - Country
  - Timezone
  - Effective From date
  - Status (Active/Inactive)
  
- **Dependencies**: Used by employees, holidays, weekly off rules
- **Use Cases**: Location-based policies, holiday calendars, compliance reporting

### Operational Masters

#### 5. Client Master
- **Purpose**: Define clients for project/task tracking
- **Fields**:
  - Code (unique per organization)
  - Name
  - Description
  - Contact Person
  - Contact Email
  - Contact Phone
  - Effective From date
  - Status (Active/Inactive)
  
- **Dependencies**: Used by tasks, timesheets
- **Use Cases**: Project allocation, billing, timesheet tracking

#### 6. Task Master
- **Purpose**: Define tasks/activities for timesheet tracking
- **Fields**:
  - Code (unique per organization)
  - Name
  - Description
  - Client ID (reference to client)
  - Effective From date
  - Status (Active/Inactive)
  
- **Dependencies**: Used by timesheets
- **Use Cases**: Time tracking, project management, billing

### Calendar-Related Masters

#### 7. Holiday Master
- **Purpose**: Define public holidays per location
- **Fields**:
  - Name
  - Date
  - Location ID (reference to location)
  - Year
  - Is Mandatory (true/false)
  - Description
  - Status (Active/Inactive)
  
- **Special Rules**:
  - Location-wise holidays
  - Year-wise organization
  - Immutable once referenced by leave transactions
  - Changes only via new records with future effective-from
  
- **Use Cases**: Leave calculation, attendance rules, payroll processing

#### 8. Weekly Off Rule Master
- **Purpose**: Define weekly off patterns per location
- **Fields**:
  - Name
  - Location ID
  - Rule Type (FIXED or NTH_WEEKDAY)
  - Fixed Weekdays (for FIXED type): ["SATURDAY", "SUNDAY"]
  - Nth Weekday Config (for NTH_WEEKDAY type): {"weekday": "SATURDAY", "occurrences": [2, 4]}
  - Effective From date
  - Effective To date
  - Status (Active/Inactive)
  
- **Special Rules**:
  - Versioned (multiple rules can exist with different effective dates)
  - Location-specific
  - Read-only at runtime (logic resolved in attendance/timesheet modules)
  
- **Use Cases**: Attendance calculation, timesheet validation, leave policy

### Exit Governance Masters

#### 9. Exit Support Function Master
- **Purpose**: Define support functions involved in exit process
- **Fields**:
  - Code (unique per organization)
  - Name
  - Description
  - Responsible Email
  - Effective From date
  - Status (Active/Inactive)
  
- **Examples**: HR, IT, Finance, Admin, Facilities
- **Dependencies**: Used by exit checklist items

#### 10. Exit Checklist Item Master
- **Purpose**: Define checklist items for exit clearance
- **Fields**:
  - Name
  - Support Function ID (reference to support function)
  - Description
  - Is Mandatory (true/false)
  - Sequence (display order)
  - Effective From date
  - Status (Active/Inactive)
  
- **Special Rules**:
  - Checklist items are snapshotted when an exit starts
  - Later changes MUST NOT affect ongoing exits
  
- **Use Cases**: Exit clearance tracking, compliance, asset recovery

## Key Features

### 1. Dependency Checking

Before allowing deactivation or structural changes, the system:
- Checks usage across all modules
- Shows impact preview (e.g., "Used by 23 employees")
- Blocks destructive actions if active usage exists

**Example Flow**:
```bash
# Check if department can be deactivated
GET /api/masters/departments/{id}/dependencies

# Response:
{
  "dependencies": {
    "employees": 23,
    "timesheets": 418
  },
  "can_deactivate": false
}
```

### 2. Status Management

- **Active**: Currently in use, available for selection
- **Inactive**: Archived, not available for new transactions
- **No Hard Delete**: All historical data preserved

**Rules**:
- Cannot deactivate if dependencies exist
- Must provide reason for status change
- Status changes are audited

### 3. Effective Dating

All masters support effective-from dates for:
- Future-dated changes
- Historical tracking
- Version control

**Example**:
- Create "Engineering Dept" effective from 2025-01-01
- Update to "Engineering & Technology" effective from 2025-07-01
- Both records exist with different effective dates

### 4. Bulk Import

Every master supports CSV/Excel bulk import with:
- Template download
- Field mapping (auto + manual)
- Pre-validation (duplicate checks, invalid references)
- Dry-run preview
- Async commit
- Rollback support

**Import Flow**:
```bash
# 1. Download template
GET /api/masters/import/template?master_type=department

# 2. Upload file
POST /api/masters/import/upload?master_type=department
(multipart/form-data with file)

# 3. Review validation results
{
  "batch_id": "uuid",
  "total_rows": 50,
  "valid_rows": 48,
  "error_rows": 2,
  "errors": [
    {"row": 15, "error": "Code 'ENG' already exists"},
    {"row": 23, "error": "Name is required"}
  ],
  "can_proceed": false
}

# 4. If valid, execute import
POST /api/masters/import/execute?batch_id=uuid
```

### 5. Reporting & Exports

For each master, the system provides:
- In-system reports with filters
- Active vs Inactive breakdown
- Usage/dependency reports
- Change history

**Export Formats**:
- Excel (XLSX)
- CSV
- PDF
- JSON

**Example**:
```bash
# Get department report as Excel
GET /api/masters/reports/departments?format=excel
```

### 6. Complete Audit Trail

Every action is logged:
- Master creation
- Updates
- Status changes
- Effective-from changes
- Bulk imports
- Dependency blocks
- Admin overrides

**Audit Log Fields**:
- Organization ID
- User ID
- Action type
- Resource type
- Resource ID
- Details (JSON)
- Timestamp
- IP Address

## UI/UX Design

### Master Management Interface

1. **List View**:
   - Search by code/name
   - Filter by status
   - Sort by multiple columns
   - Pagination
   - Bulk actions

2. **Detail Panel** (Side Drawer):
   - Complete master information
   - Change history
   - Dependency information
   - Action buttons (Edit, Deactivate)

3. **Create/Edit Form** (Modal):
   - Inline validation
   - Clear error messages
   - Required field indicators
   - Help text where needed

4. **Dependency Warning Dialog**:
   - Clear impact preview
   - List of affected records
   - Block or warn based on severity

### Master Type Navigation

- Sidebar with master categories
- Quick switching between master types
- Breadcrumb navigation
- Consistent layout across all masters

## API Reference

### Common Endpoints Pattern

All masters follow the same RESTful pattern:

```
GET    /api/masters/{master_type}                    - List all
POST   /api/masters/{master_type}                    - Create new
GET    /api/masters/{master_type}/{id}               - Get details
PUT    /api/masters/{master_type}/{id}               - Update
PATCH  /api/masters/{master_type}/{id}/status        - Change status
GET    /api/masters/{master_type}/{id}/dependencies  - Check dependencies
```

### Master Types

- `departments`
- `designations`
- `employee_types`
- `locations`
- `clients`
- `tasks`
- `holidays`
- `weekly_off_rules`
- `exit_support_functions`
- `exit_checklist_items`

## Database Collections

### Schema Structure

Each master collection contains:
```json
{
  "master_id": "uuid",
  "organization_id": "uuid",
  "code": "string (unique per org)",
  "name": "string",
  "description": "string (optional)",
  "effective_from": "ISO date",
  "status": "ACTIVE | INACTIVE",
  "created_by": "user_id",
  "created_at": "ISO datetime",
  "updated_by": "user_id",
  "updated_at": "ISO datetime",
  ... additional fields specific to master type
}
```

### Indexes

All master collections have indexes on:
- `organization_id`
- `code` + `organization_id` (compound, unique for active records)
- `status`
- `effective_from`

## Testing Guide

### Create Master Data

```bash
# Login as firm admin
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@firm.com", "pin": "1234"}' \
  | jq -r '.access_token')

# Create department
curl -X POST http://localhost:8001/api/masters/departments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "ENG",
    "name": "Engineering",
    "description": "Engineering Department",
    "effective_from": "2025-01-01"
  }'
```

### Check Dependencies

```bash
# Get department ID
DEPT_ID=$(curl -s http://localhost:8001/api/masters/departments \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.departments[0].master_id')

# Check dependencies
curl -X GET "http://localhost:8001/api/masters/departments/$DEPT_ID/dependencies" \
  -H "Authorization: Bearer $TOKEN"
```

### Change Status

```bash
# Deactivate (only if no dependencies)
curl -X PATCH "http://localhost:8001/api/masters/departments/$DEPT_ID/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "INACTIVE",
    "reason": "Department restructuring"
  }'
```

## Best Practices

### 1. Migration Strategy

When migrating from existing HRMS:
1. Start with organizational masters (departments, designations, locations)
2. Use bulk import for historical data
3. Validate all data before going live
4. Test dependency checking with sample transactions

### 2. Data Governance

- Define naming conventions for codes
- Maintain consistent effective dates
- Document the reason for every status change
- Regular audit log reviews

### 3. Performance Optimization

- Use appropriate filters when listing masters
- Cache active masters at application level
- Paginate large result sets
- Use bulk operations for mass updates

### 4. Security

- Only firm admins can create/modify masters
- All employees can view active masters
- Audit logs accessible only to admins
- Organization-level data isolation enforced

## Integration with Other Modules

### Module 1: Employee Master
- Employees reference departments, designations, locations
- Employee type master used for classification
- Dependency checking prevents orphaned employees

### Module 3: Leave Management (Future)
- Holiday master used for leave calculations
- Location-wise holiday calendars
- Weekly off rules for leave policy

### Module 4: Attendance & Timesheet (Future)
- Client and task masters for timesheet tracking
- Weekly off rules for attendance calculation
- Holiday master for absent/present logic

### Module 5: Exit Management (Future)
- Exit support functions for clearance workflow
- Exit checklist items for compliance
- Snapshotted data ensures consistency

## Troubleshooting

### Cannot Deactivate Master

**Problem**: Getting error "Cannot deactivate: Used by X employees"

**Solution**: 
1. Check dependencies using `/dependencies` endpoint
2. Reassign affected employees to different department/designation
3. Retry deactivation

### Duplicate Code Error

**Problem**: Getting error "Code already exists"

**Solution**:
1. Codes must be unique per organization for active records
2. Check existing masters with same code
3. Either use different code or deactivate existing master first

### Import Validation Failed

**Problem**: Bulk import showing validation errors

**Solution**:
1. Download template to ensure correct format
2. Check for duplicate codes in import file
3. Ensure all required fields are provided
4. Fix errors and re-upload

## Future Enhancements

1. **Master Versioning**: Full version history with rollback capability
2. **Custom Fields**: Allow firms to add custom fields to masters
3. **Workflow Approvals**: Require approval for master changes
4. **Data Validation Rules**: Custom validation rules per master type
5. **Master Relationships**: Define relationships between masters
6. **Scheduled Changes**: Schedule future-dated changes automatically

## Support

For issues or questions:
- Check audit logs for recent changes
- Review dependency reports
- Contact system administrator

---

**Module Status**: ✅ Complete and Production-Ready
**Last Updated**: January 21, 2026
**Version**: 2.0
