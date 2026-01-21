# HRMS - Employee Master & Identity Foundation

## Multi-Tenant HRMS System

This is a comprehensive, enterprise-grade HRMS (Human Resource Management System) built with FastAPI backend and React frontend. The system supports multi-tenancy where you (as super admin) can onboard multiple organizations (firms) who will manage their own employees.

## Tech Stack

- **Backend**: FastAPI + Python 3.9+
- **Frontend**: React 18 + Tailwind CSS
- **Database**: MongoDB
- **Authentication**: Custom 4-digit PIN system with JWT

## System Architecture

### User Roles

1. **Super Admin**: You (system owner) who manages all organizations
2. **Firm Admin**: Organization administrators who manage employees
3. **Employee**: Regular users within an organization

### Key Features

#### Module 1: Employee Master & Identity Foundation

✅ **Super Admin Features**:
- Create and manage organizations (firms)
- View all organizations
- System-wide control

✅ **Firm Admin Features**:
- Employee CRUD operations
- Status management (Draft/Active/Inactive)
- Reporting hierarchy with circular reference validation
- Organization settings configuration
- Email/WhatsApp notification toggles
- Audit logs viewing

✅ **Employee Features**:
- View own profile
- Access employee directory
- Dashboard view

✅ **Authentication System**:
- Email or Mobile as username
- 4-digit PIN authentication
- Auto-generated PINs on account creation
- Forgot password with new PIN generation
- Token-based session management

✅ **Employee Master Data**:
- Complete identity & contact information
- Personal details (DOB, Blood Group, Aadhaar, PAN)
- Employment details (DOJ, Type, Department, Designation)
- Asset tracking (Laptop, Serial Numbers)
- Reporting hierarchy (Primary & Secondary RA)
- Status lifecycle management

✅ **Organization Settings** (per firm):
- Email notifications (ON/OFF + sender configuration)
- WhatsApp notifications (ON/OFF + API configuration)
- Authentication method preference

✅ **Audit & Compliance**:
- Complete audit trail for all actions
- Employee history snapshots
- No hard deletes (all changes tracked)
- Immutable logs

✅ **BambooHR-Inspired UI**:
- Clean, calm design
- Card-based layouts
- Side panel interactions
- Responsive design
- Search and filter capabilities

## Initial Setup Credentials

### Super Admin Access
- **Username**: `superadmin`
- **PIN**: `3168`
- **Note**: This is a one-time generated PIN. Please change it after first login.

## Quick Start

### Backend
```bash
cd /app/backend
pip install -r requirements.txt
python server.py
```
Backend runs on: http://localhost:8001

### Frontend
```bash
cd /app/frontend
yarn install
yarn start
```
Frontend runs on: http://localhost:3000

### Using Supervisor (Recommended)
```bash
sudo supervisorctl restart all
sudo supervisorctl status
```

## API Endpoints

### Authentication
- `POST /api/super-admin/init` - Initialize super admin (one-time)
- `POST /api/auth/login` - User login
- `POST /api/auth/forgot-password` - Reset PIN
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

### Organizations (Super Admin)
- `POST /api/organizations` - Create organization
- `GET /api/organizations` - List all organizations
- `GET /api/organizations/{id}` - Get organization details
- `PUT /api/organizations/{id}` - Update organization

### Organization Settings (Firm Admin)
- `GET /api/organizations/{id}/settings` - Get settings
- `PUT /api/organizations/{id}/settings` - Update settings

### Employees (Firm Admin)
- `POST /api/employees` - Create employee
- `GET /api/employees` - List employees (with filters)
- `GET /api/employees/{id}` - Get employee details
- `PUT /api/employees/{id}` - Update employee
- `PATCH /api/employees/{id}/status` - Change status
- `GET /api/employees/{id}/history` - Get change history

### Roles & Permissions
- `GET /api/permissions` - List permissions
- `POST /api/roles` - Create role
- `GET /api/roles` - List roles
- `PUT /api/roles/{id}` - Update role
- `POST /api/employees/{id}/assign-role` - Assign role

### Reporting Hierarchy
- `GET /api/reporting-hierarchy/{id}` - Get hierarchy
- `GET /api/reporting-hierarchy/validate` - Validate circular reference

### Bulk Import
- `POST /api/import/upload` - Upload CSV/Excel
- `POST /api/import/preview` - Validate and preview
- `POST /api/import/execute` - Execute import

### Reports
- `GET /api/reports/directory` - Employee directory
- `GET /api/reports/department-wise` - Department breakdown
- `GET /api/reports/location-wise` - Location breakdown

### Audit Logs
- `GET /api/audit-logs` - Get audit logs (with filters)

## Database Collections

- `organizations` - Organization master data
- `organization_settings` - Per-organization configuration
- `users` - User accounts (super admin, firm admin, employees)
- `employees` - Employee master data
- `employee_history` - Audit snapshots
- `roles` - Role definitions
- `permissions` - Permission catalog
- `reporting_hierarchy` - Reporting structure
- `audit_logs` - Immutable audit trail
- `import_batches` - Bulk import tracking
- `auth_tokens` - Authentication tokens

## Usage Flow

### 1. Super Admin Onboards an Organization

1. Login as super admin
2. Navigate to "Organizations"
3. Click "Add Organization"
4. Fill organization and admin details
5. System creates firm admin account with auto-generated PIN
6. Credentials sent to admin via email/WhatsApp

### 2. Firm Admin Sets Up Their Organization

1. Login with provided credentials
2. Go to "Settings" to configure:
   - Email notifications (toggle + sender email)
   - WhatsApp notifications (toggle + phone + API key)
3. Start adding employees

### 3. Creating Employees

1. Navigate to "Employees"
2. Click "Add Employee"
3. Fill complete employee information
4. Choose to send invitation (auto-generates PIN)
5. Employee account created in "Draft" status
6. Change status to "Active" to enable login

### 4. Employee Status Lifecycle

- **Draft**: Created but not activated
- **Active**: Can login and use system
- **Inactive**: Exited or disabled (historical data preserved)

### 5. Reporting Hierarchy

- Assign Primary Reporting Authority (RA1)
- Optionally assign Secondary RA (RA2)
- System validates circular references
- Either RA can approve requests (first action wins)

## Configuration

### Environment Variables

**Backend (.env)**:
```
MONGO_URL=mongodb://localhost:27017/hrms_db
JWT_SECRET_KEY=your-secret-key-change-in-production-min-32-chars-long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

**Frontend (.env)**:
```
REACT_APP_BACKEND_URL=http://localhost:8001
```

## Security Features

- JWT-based authentication
- 4-digit PIN hashing (SHA-256)
- Role-based access control
- Organization-level data isolation
- Audit logging for all actions
- No hard deletes (soft delete only)
- Secure token expiration

## Compliance & Audit

- All changes tracked with timestamps
- Employee history snapshots before updates
- Immutable audit logs
- Reason required for status changes
- Change attribution (who made the change)
- Historical data preservation

## Multi-Tenant Architecture

- Complete data isolation per organization
- Organization-specific settings
- Independent employee numbering per org
- Separate notification configurations
- Organization-scoped roles and permissions

## Planned Features (Future Modules)

- Leave Management
- Attendance & Timesheet
- Performance Management
- Payroll Integration
- Document Management
- Employee Self-Service Portal
- Mobile App

## Support

For issues or questions, contact the system administrator.

## License

Proprietary - All rights reserved
