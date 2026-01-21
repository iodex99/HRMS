# Test Credentials - HRMS System

## System Access URLs

- **Backend API**: http://localhost:8001
- **Frontend UI**: http://localhost:3000
- **API Documentation**: http://localhost:8001/docs (FastAPI auto-generated)
- **Health Check**: http://localhost:8001/api/health

---

## Super Admin (System Owner)

**Role**: SUPER_ADMIN
- **Username**: `superadmin`
- **PIN**: `3168`
- **Capabilities**:
  - Manage all organizations
  - View system-wide data
  - Create firm admins
  - Full system control

---

## Test Organization: Test Corp Ltd

**Organization Details**:
- **ID**: `97e21ec4-c0ee-4d0c-89f4-de7d49529b80`
- **Name**: Test Corp Ltd
- **Email**: admin@testcorp.com
- **Phone**: +1234567890
- **Address**: 123 Business St, Tech City

### Firm Admin

**Role**: FIRM_ADMIN
- **Name**: John Admin
- **Username**: `john.admin@testcorp.com`
- **PIN**: `7847`
- **Mobile**: +1987654321
- **Capabilities**:
  - Manage employees
  - Configure organization settings
  - View reports
  - Access audit logs
  - Manage roles & permissions

### Employees

#### Employee 1: Alice Johnson

**Role**: EMPLOYEE
- **Employee Code**: `EMP-00001`
- **Biometric Code**: `EMP-00001`
- **Full Name**: Alice Johnson
- **Username**: `alice.johnson@testcorp.com`
- **PIN**: `5288`
- **Email**: alice.johnson@testcorp.com
- **Mobile**: +1555123456
- **Emergency Contact**: +1555999888
- **Department**: Engineering
- **Designation**: Software Engineer
- **Location**: New York
- **Employee Type**: Full Time
- **Date of Joining**: 2025-01-15
- **Date of Birth**: 1990-05-15
- **Status**: ACTIVE
- **Monthly Salary**: $5,000

---

## Quick Login Guide

### Via Frontend (http://localhost:3000):

1. **Super Admin Login**:
   - Username: `superadmin`
   - PIN: `3168`

2. **Firm Admin Login**:
   - Username: `john.admin@testcorp.com`
   - PIN: `7847`

3. **Employee Login**:
   - Username: `alice.johnson@testcorp.com`
   - PIN: `5288`

### Via API (cURL):

```bash
# Super Admin Login
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin", "pin": "3168"}'

# Firm Admin Login
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "john.admin@testcorp.com", "pin": "7847"}'

# Employee Login
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice.johnson@testcorp.com", "pin": "5288"}'
```

---

## Testing Scenarios

### 1. Super Admin Creates New Organization

```bash
TOKEN="<super_admin_token>"

curl -X POST http://localhost:8001/api/organizations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "New Company Inc",
    "email": "info@newcompany.com",
    "phone": "+1999888777",
    "address": "456 Corporate Ave",
    "admin_name": "Jane Doe",
    "admin_email": "jane@newcompany.com",
    "admin_mobile": "+1888777666"
  }'
```

### 2. Firm Admin Creates Employee

```bash
TOKEN="<firm_admin_token>"

curl -X POST http://localhost:8001/api/employees \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "full_name": "Bob Smith",
    "email": "bob.smith@testcorp.com",
    "mobile": "+1555222333",
    "date_of_joining": "2025-02-01",
    "employee_type": "FULL_TIME",
    "department": "Marketing",
    "designation": "Marketing Manager",
    "location": "San Francisco",
    "send_invitation": true
  }'
```

### 3. Change Employee Status

```bash
TOKEN="<firm_admin_token>"
EMPLOYEE_ID="<employee_id>"

curl -X PATCH http://localhost:8001/api/employees/$EMPLOYEE_ID/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "status": "ACTIVE",
    "reason": "Completed onboarding and training"
  }'
```

### 4. View Audit Logs

```bash
TOKEN="<firm_admin_token>"

curl -X GET "http://localhost:8001/api/audit-logs?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Update Organization Settings

```bash
TOKEN="<firm_admin_token>"
ORG_ID="<organization_id>"

curl -X PUT http://localhost:8001/api/organizations/$ORG_ID/settings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "email_notifications_enabled": true,
    "email_sender_address": "noreply@testcorp.com",
    "email_sender_name": "Test Corp HRMS",
    "whatsapp_notifications_enabled": false,
    "auth_method": "BOTH"
  }'
```

---

## Database Information

**MongoDB Connection**: mongodb://localhost:27017/hrms_db

**Collections**:
- `organizations` - 1 record (Test Corp Ltd)
- `organization_settings` - 1 record
- `users` - 3 records (1 super admin, 1 firm admin, 1 employee)
- `employees` - 1 record (Alice Johnson)
- `employee_history` - 2 records (creation + status change snapshots)
- `audit_logs` - 5+ records (all actions tracked)

---

## Features Implemented

✅ Multi-tenant architecture
✅ Super admin organization management
✅ Firm admin employee management
✅ 4-digit PIN authentication
✅ Role-based access control
✅ Employee status lifecycle (Draft → Active → Inactive)
✅ Organization settings (email/WhatsApp notifications)
✅ Complete audit trail
✅ Employee history snapshots
✅ BambooHR-inspired UI
✅ Reporting hierarchy support
✅ Circular reference validation
✅ Search and filter capabilities
✅ Responsive design

---

## Next Steps

1. **Add More Employees**: Create a diverse set of employees with different departments and roles
2. **Set Up Reporting Hierarchy**: Assign primary and secondary reporting authorities
3. **Configure Organization Settings**: Enable email/WhatsApp notifications
4. **Test Bulk Import**: Upload CSV with multiple employees
5. **Generate Reports**: Export employee directory, department-wise reports
6. **Create Custom Roles**: Define custom roles with specific permissions
7. **Test Forgot Password**: Reset PIN flow
8. **View Audit Logs**: Track all system activities

---

## Important Notes

- All PINs are 4 digits only
- Employee codes are auto-generated sequentially (EMP-00001, EMP-00002, etc.)
- Biometric code matches employee code
- No hard deletes - all changes create history snapshots
- Audit logs are immutable
- Organization settings are independent per firm
- Employees in DRAFT status cannot login
- Only ACTIVE employees can access the system
- Reporting hierarchy prevents circular references
- First action wins in dual-RA approval scenarios

---

## Support & Troubleshooting

**Check Services Status**:
```bash
sudo supervisorctl status
```

**Restart Services**:
```bash
sudo supervisorctl restart all
```

**View Logs**:
```bash
# Backend logs
tail -f /var/log/supervisor/backend.out.log
tail -f /var/log/supervisor/backend.err.log

# Frontend logs
tail -f /var/log/supervisor/frontend.out.log
tail -f /var/log/supervisor/frontend.err.log
```

**MongoDB Access**:
```bash
mongosh mongodb://localhost:27017/hrms_db
```

---

**Last Updated**: January 21, 2026
**System Version**: Module 1 - Employee Master & Identity Foundation
