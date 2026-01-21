# 🎯 HRMS Demo Login Credentials

## System Access

**Frontend URL**: http://localhost:3000  
**Backend API**: http://localhost:8001  
**API Docs**: http://localhost:8001/docs

---

## 👤 Login Credentials

### 1. Super Admin (System Owner)
**Role**: SUPER_ADMIN - Manages all organizations

- **Username**: `superadmin`
- **PIN**: `3168`

**Capabilities**:
- Create and manage organizations
- View system-wide data
- Onboard new firms
- Full system control

**Quick Login**:
```bash
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin", "pin": "3168"}'
```

---

### 2. Firm Admin (Test Corp Ltd)
**Role**: FIRM_ADMIN - Manages organization and employees

- **Username**: `john.admin@testcorp.com`
- **PIN**: `7847`
- **Organization**: Test Corp Ltd

**Capabilities**:
- Manage employees (create, update, status changes)
- Manage master data (departments, designations, locations, holidays)
- Configure organization settings
- View reports and audit logs
- Manage calendar (holidays, weekly-off rules)
- Check working days and calendar resolution

**Quick Login**:
```bash
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "john.admin@testcorp.com", "pin": "7847"}'
```

---

### 3. Employee (Alice Johnson)
**Role**: EMPLOYEE - Regular employee access

- **Username**: `alice.johnson@testcorp.com`
- **PIN**: `5288`
- **Organization**: Test Corp Ltd
- **Department**: Engineering
- **Designation**: Software Engineer
- **Location**: San Francisco Office
- **Employee Code**: EMP-00001

**Capabilities**:
- View own profile
- View employee directory
- Access dashboard

**Quick Login**:
```bash
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice.johnson@testcorp.com", "pin": "5288"}'
```

---

## 🎨 UI Demo Flow

### For Super Admin:
1. Go to http://localhost:3000
2. Enter username: `superadmin`, PIN: `3168`
3. Navigate to "Organizations"
4. View Test Corp Ltd and its details
5. Create new organizations if needed

### For Firm Admin:
1. Go to http://localhost:3000
2. Enter username: `john.admin@testcorp.com`, PIN: `7847`
3. **Dashboard**: View statistics (1 total employee, 1 active)
4. **Employees**: View Alice Johnson, create new employees
5. **Master Data**:
   - View Departments (Engineering, HR, Finance)
   - View Designations (Senior Software Engineer, Manager)
   - View Locations (San Francisco Office)
   - Create new masters
6. **Calendar** (Module 3 features):
   - View holidays (New Year, MLK Day, Independence Day)
   - View weekly-off rules (Saturday & Sunday)
   - Test date resolution
7. **Settings**: Configure email/WhatsApp notifications
8. **Audit Logs**: View all system activities

### For Employee:
1. Go to http://localhost:3000
2. Enter username: `alice.johnson@testcorp.com`, PIN: `5288`
3. View dashboard
4. View own profile
5. View employee directory

---

## 📊 Test Data Summary

### Organization
- **Name**: Test Corp Ltd
- **Email**: admin@testcorp.com
- **Phone**: +1234567890
- **ID**: 97e21ec4-c0ee-4d0c-89f4-de7d49529b80

### Master Data Created

**Departments** (3):
- ENG - Engineering
- HR - Human Resources
- FIN - Finance

**Designations** (2):
- SSE - Senior Software Engineer (Level 3)
- MGR - Manager (Level 4)

**Locations** (1):
- SF - San Francisco Office (San Francisco, California, USA)

**Holidays** (3 for 2025):
- January 1 - New Year Day
- January 20 - Martin Luther King Jr. Day
- July 4 - Independence Day

**Weekly-Off Rules** (1):
- WKND - Weekend Off (Every Saturday & Sunday)

**Employees** (1):
- EMP-00001 - Alice Johnson (Active)

---

## 🧪 Testing Scenarios

### Scenario 1: Create New Employee
```bash
TOKEN="<firm_admin_token>"

curl -X POST http://localhost:8001/api/employees \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Bob Smith",
    "email": "bob.smith@testcorp.com",
    "mobile": "+1555777888",
    "date_of_joining": "2025-02-01",
    "employee_type": "FULL_TIME",
    "department": "Engineering",
    "designation": "Senior Software Engineer",
    "location": "San Francisco Office",
    "send_invitation": true
  }'
```

### Scenario 2: Check Date Classification
```bash
# Check if January 25, 2025 is a working day
curl -X POST http://localhost:8001/api/calendar/resolve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "location_id": "851d3cef-8be9-431c-b304-dd586986da1b",
    "date": "2025-01-25"
  }'

# Result: WEEKLY_OFF (Saturday)
```

### Scenario 3: Count Working Days
```bash
# Count working days in January 2025
curl -X POST http://localhost:8001/api/calendar/working-days \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "location_id": "851d3cef-8be9-431c-b304-dd586986da1b",
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
  }'

# Result: 21 working days, 2 holidays, 8 weekly offs
```

### Scenario 4: Get Month Calendar
```bash
# Get complete January 2025 calendar
curl -X GET "http://localhost:8001/api/calendar/month/851d3cef-8be9-431c-b304-dd586986da1b/2025/1" \
  -H "Authorization: Bearer $TOKEN"
```

### Scenario 5: Create Department
```bash
curl -X POST http://localhost:8001/api/masters/departments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "MKT",
    "name": "Marketing",
    "description": "Marketing Department",
    "effective_from": "2025-01-01"
  }'
```

### Scenario 6: Check Master Dependencies
```bash
# Check if Engineering department can be deactivated
DEPT_ID="<department_master_id>"

curl -X GET "http://localhost:8001/api/masters/departments/$DEPT_ID/dependencies" \
  -H "Authorization: Bearer $TOKEN"

# Result: Cannot deactivate (1 employee using it)
```

---

## 🔐 Password Reset

If you forget your PIN:

```bash
curl -X POST http://localhost:8001/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice.johnson@testcorp.com",
    "organization_id": "97e21ec4-c0ee-4d0c-89f4-de7d49529b80"
  }'
```

A new 4-digit PIN will be sent (currently logged to console).

---

## 📈 Calendar Resolution Examples

### January 2025 Analysis:
- **Total Days**: 31
- **Working Days**: 21
- **Holidays**: 2 (New Year, MLK Day)
- **Weekly Offs**: 8 (4 Saturdays + 4 Sundays)

### Date Classifications:
- **Jan 1 (Wed)**: HOLIDAY (New Year Day)
- **Jan 4 (Sat)**: WEEKLY_OFF (Weekend)
- **Jan 5 (Sun)**: WEEKLY_OFF (Weekend)
- **Jan 6 (Mon)**: WORKING_DAY
- **Jan 20 (Mon)**: HOLIDAY (MLK Day)
- **Jan 21 (Tue)**: WORKING_DAY
- **Jan 25 (Sat)**: WEEKLY_OFF (Weekend)

---

## 🎯 Module-wise Testing

### Module 1: Employee Master
- ✅ Super admin creates organizations
- ✅ Firm admin creates employees
- ✅ Employee status lifecycle (Draft → Active → Inactive)
- ✅ Authentication (4-digit PIN)
- ✅ Audit trail

### Module 2: Master Data
- ✅ Create departments, designations, locations
- ✅ Dependency checking
- ✅ Status management (Active/Inactive)
- ✅ Search and filter
- ✅ Effective-from dating

### Module 3: Calendar Engine
- ✅ Date classification (WORKING_DAY/HOLIDAY/WEEKLY_OFF)
- ✅ Location-wise holidays
- ✅ Weekly-off rules (Fixed pattern)
- ✅ Working day counting
- ✅ Month calendar resolution
- ✅ Policy version tracking

---

## 🔧 Troubleshooting

### Issue: Cannot Login
**Solution**: Check that services are running:
```bash
sudo supervisorctl status
```

### Issue: Date Showing as WORKING_DAY (Should be Holiday)
**Solution**: Check if holiday exists for that location:
```bash
curl -X GET "http://localhost:8001/api/masters/holidays?location_id=<location_id>" \
  -H "Authorization: Bearer $TOKEN"
```

### Issue: Weekend Not Detected
**Solution**: Check weekly-off rule exists:
```bash
curl -X GET "http://localhost:8001/api/masters/weekly_off_rules?location_id=<location_id>" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📝 Important Notes

1. **PINs are 4 digits only** - System validates this
2. **Employee codes are auto-generated** - EMP-00001, EMP-00002, etc.
3. **No hard deletes** - Everything is soft-deleted (status = INACTIVE)
4. **Organization-scoped data** - Each firm sees only their data
5. **Calendar is location-aware** - Same date can be different in different locations
6. **Audit logs are immutable** - All changes are tracked
7. **Dependency checking** - Cannot deactivate masters with active usage

---

## 🚀 Next Steps

1. **Add More Employees**: Create diverse employee profiles
2. **Configure Notifications**: Set up email/WhatsApp in Settings
3. **Import Holidays**: Bulk import holidays via CSV
4. **Create More Locations**: Add different office locations
5. **Test Calendar**: Verify working day calculations
6. **Set Up Reporting Hierarchy**: Assign RAs to employees
7. **Create Custom Roles**: Define custom permission sets
8. **Test Nth Weekday**: Create 2nd & 4th Saturday off rule

---

## 💡 Pro Tips

- Use the search feature in all list pages
- Check dependencies before deactivating any master
- Use month calendar view for visual verification
- Export reports to Excel for offline analysis
- Review audit logs regularly for compliance
- Test calendar resolution before timesheet entry
- Keep weekly-off rules versioned with effective dates

---

**System Status**: ✅ All 3 Modules Operational  
**Last Updated**: January 21, 2026  
**Version**: 3.0
