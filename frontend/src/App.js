import React, { useState, useEffect, createContext, useContext } from 'react';
import { 
  User, Users, Building2, Settings, LogOut, Menu, X, Search, Plus,
  ChevronRight, Mail, Phone, Calendar, MapPin, Briefcase, Edit2, 
  Trash2, Eye, EyeOff, Download, Upload, Shield, FileText, Activity,
  CheckCircle, XCircle, AlertCircle, Filter, RefreshCw, Home, Database
} from 'lucide-react';
import './App.css';
import { MasterListPage } from './MasterComponents';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Auth Context
const AuthContext = createContext(null);

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

// API Client
const api = {
  setToken: (token) => {
    localStorage.setItem('token', token);
  },
  
  getToken: () => {
    return localStorage.getItem('token');
  },
  
  clearToken: () => {
    localStorage.removeItem('token');
  },
  
  request: async (endpoint, options = {}) => {
    const token = api.getToken();
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });
    
    if (response.status === 401) {
      api.clearToken();
      window.location.href = '/';
    }
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Something went wrong');
    }
    
    return data;
  },
};

// Auth Provider Component
function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    checkAuth();
  }, []);
  
  const checkAuth = async () => {
    const token = api.getToken();
    if (token) {
      try {
        const userData = await api.request('/api/auth/me');
        setUser(userData);
      } catch (error) {
        api.clearToken();
      }
    }
    setLoading(false);
  };
  
  const login = async (username, pin, organizationId) => {
    const data = await api.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, pin, organization_id: organizationId }),
    });
    
    api.setToken(data.access_token);
    setUser(data.user);
    return data;
  };
  
  const logout = async () => {
    try {
      await api.request('/api/auth/logout', { method: 'POST' });
    } catch (error) {
      console.error('Logout error:', error);
    }
    api.clearToken();
    setUser(null);
  };
  
  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

// Login Page
function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      await login(username, pin);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-bamboo-50 to-bamboo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-bamboo-500 rounded-full mb-4">
            <Building2 className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">HRMS</h1>
          <p className="text-gray-600 mt-2">Employee Master & Identity</p>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Email or Mobile Number
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500 focus:border-transparent"
              placeholder="Enter your email or mobile"
              required
              data-testid="login-username-input"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              4-Digit PIN
            </label>
            <input
              type="password"
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 4))}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500 focus:border-transparent"
              placeholder="Enter your 4-digit PIN"
              maxLength="4"
              required
              data-testid="login-pin-input"
            />
          </div>
          
          <button
            type="submit"
            disabled={loading || pin.length !== 4}
            className="w-full bg-bamboo-600 text-white py-3 rounded-lg font-medium hover:bg-bamboo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            data-testid="login-submit-button"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
          
          <div className="text-center">
            <button
              type="button"
              className="text-sm text-bamboo-600 hover:text-bamboo-700 font-medium"
              onClick={() => alert('Please contact your administrator for password reset')}
            >
              Forgot PIN?
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Layout Components
function Sidebar({ activePage, setActivePage, onClose }) {
  const { user, logout } = useAuth();
  
  const isSuperAdmin = user?.role === 'SUPER_ADMIN';
  const isFirmAdmin = user?.role === 'FIRM_ADMIN' || user?.role === 'SUPER_ADMIN';
  
  const menuItems = [
    { id: 'dashboard', icon: Home, label: 'Dashboard', roles: ['SUPER_ADMIN', 'FIRM_ADMIN', 'EMPLOYEE'] },
    { id: 'organizations', icon: Building2, label: 'Organizations', roles: ['SUPER_ADMIN'] },
    { id: 'employees', icon: Users, label: 'Employees', roles: ['SUPER_ADMIN', 'FIRM_ADMIN', 'EMPLOYEE'] },
    { id: 'masters', icon: Database, label: 'Master Data', roles: ['FIRM_ADMIN'] },
    { id: 'roles', icon: Shield, label: 'Roles & Permissions', roles: ['FIRM_ADMIN'] },
    { id: 'reports', icon: FileText, label: 'Reports', roles: ['FIRM_ADMIN'] },
    { id: 'audit', icon: Activity, label: 'Audit Logs', roles: ['FIRM_ADMIN'] },
    { id: 'settings', icon: Settings, label: 'Settings', roles: ['FIRM_ADMIN'] },
  ];
  
  const filteredMenuItems = menuItems.filter(item => item.roles.includes(user?.role));
  
  return (
    <div className="h-full bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-bamboo-500 rounded-lg flex items-center justify-center">
            <Building2 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="font-bold text-gray-900">HRMS</h2>
            <p className="text-xs text-gray-500">{user?.role?.replace('_', ' ')}</p>
          </div>
        </div>
      </div>
      
      <nav className="flex-1 p-4 space-y-1">
        {filteredMenuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => {
                setActivePage(item.id);
                if (onClose) onClose();
              }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-bamboo-50 text-bamboo-700'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
              data-testid={`sidebar-${item.id}-button`}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </button>
          );
        })}
      </nav>
      
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center gap-3 px-4 py-3 mb-2">
          <div className="w-8 h-8 bg-bamboo-100 rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-bamboo-700" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">{user?.full_name || user?.username}</p>
            <p className="text-xs text-gray-500 truncate">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          data-testid="logout-button"
        >
          <LogOut className="w-5 h-5" />
          <span className="font-medium">Logout</span>
        </button>
      </div>
    </div>
  );
}

function Header({ onMenuClick }) {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 hover:bg-gray-100 rounded-lg"
        >
          <Menu className="w-6 h-6 text-gray-600" />
        </button>
        <div className="flex-1" />
      </div>
    </header>
  );
}

// Dashboard Page
function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState({ total: 0, active: 0, draft: 0, inactive: 0 });
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadStats();
  }, []);
  
  const loadStats = async () => {
    if (user?.role === 'EMPLOYEE') {
      setLoading(false);
      return;
    }
    
    try {
      const data = await api.request('/api/employees?limit=1000');
      const employees = data.employees || [];
      
      setStats({
        total: employees.length,
        active: employees.filter(e => e.status === 'ACTIVE').length,
        draft: employees.filter(e => e.status === 'DRAFT').length,
        inactive: employees.filter(e => e.status === 'INACTIVE').length,
      });
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const statCards = [
    { label: 'Total Employees', value: stats.total, color: 'bg-blue-500', icon: Users },
    { label: 'Active', value: stats.active, color: 'bg-green-500', icon: CheckCircle },
    { label: 'Draft', value: stats.draft, color: 'bg-yellow-500', icon: AlertCircle },
    { label: 'Inactive', value: stats.inactive, color: 'bg-gray-500', icon: XCircle },
  ];
  
  if (user?.role === 'EMPLOYEE') {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Welcome, {user.full_name}!</h1>
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <p className="text-gray-600">Your employee dashboard will be available here.</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
      
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
              <div className="h-8 bg-gray-200 rounded w-1/3"></div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {statCards.map((stat, idx) => {
            const Icon = stat.icon;
            return (
              <div key={idx} className="bg-white rounded-lg border border-gray-200 p-6" data-testid={`stat-card-${stat.label.toLowerCase().replace(' ', '-')}`}>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm font-medium text-gray-600">{stat.label}</span>
                  <div className={`w-10 h-10 ${stat.color} rounded-lg flex items-center justify-center`}>
                    <Icon className="w-5 h-5 text-white" />
                  </div>
                </div>
                <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Organizations Page (Super Admin Only)
function OrganizationsPage() {
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  useEffect(() => {
    loadOrganizations();
  }, []);
  
  const loadOrganizations = async () => {
    try {
      const data = await api.request('/api/organizations');
      setOrganizations(data.organizations || []);
    } catch (error) {
      console.error('Error loading organizations:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const filteredOrgs = organizations.filter(org =>
    org.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    org.email.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Organizations</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-bamboo-600 text-white rounded-lg hover:bg-bamboo-700 transition-colors"
          data-testid="create-organization-button"
        >
          <Plus className="w-5 h-5" />
          Add Organization
        </button>
      </div>
      
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-4 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search organizations..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500 focus:border-transparent"
              data-testid="search-organizations-input"
            />
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Organization</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Contact</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="4" className="px-6 py-8 text-center text-gray-500">Loading...</td>
                </tr>
              ) : filteredOrgs.length === 0 ? (
                <tr>
                  <td colSpan="4" className="px-6 py-8 text-center text-gray-500">No organizations found</td>
                </tr>
              ) : (
                filteredOrgs.map((org) => (
                  <tr key={org.organization_id} className="hover:bg-gray-50" data-testid={`organization-row-${org.organization_id}`}>
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{org.name}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-600">{org.email}</div>
                      <div className="text-sm text-gray-500">{org.phone}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        org.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {org.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {new Date(org.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      {showCreateModal && (
        <CreateOrganizationModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            loadOrganizations();
          }}
        />
      )}
    </div>
  );
}

// Create Organization Modal
function CreateOrganizationModal({ onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    address: '',
    admin_name: '',
    admin_email: '',
    admin_mobile: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      const data = await api.request('/api/organizations', {
        method: 'POST',
        body: JSON.stringify(formData),
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  if (result) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white rounded-lg max-w-md w-full p-6">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-green-100 rounded-full mb-4">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Organization Created!</h3>
            <p className="text-sm text-gray-600">Admin credentials have been sent.</p>
          </div>
          
          <div className="bg-gray-50 rounded-lg p-4 mb-6 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Admin Username:</span>
              <span className="font-medium text-gray-900">{result.admin_username}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Admin PIN:</span>
              <span className="font-medium text-gray-900">{result.admin_pin}</span>
            </div>
          </div>
          
          <button
            onClick={onSuccess}
            className="w-full px-4 py-2 bg-bamboo-600 text-white rounded-lg hover:bg-bamboo-700"
          >
            Done
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Create Organization</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}
          
          <div className="space-y-4">
            <h3 className="font-medium text-gray-900">Organization Details</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Organization Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                required
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone *</label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                  required
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
              <textarea
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                rows="2"
              />
            </div>
          </div>
          
          <div className="space-y-4 border-t border-gray-200 pt-6">
            <h3 className="font-medium text-gray-900">Admin User Details</h3>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Admin Name *</label>
              <input
                type="text"
                value={formData.admin_name}
                onChange={(e) => setFormData({ ...formData, admin_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                required
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Admin Email *</label>
                <input
                  type="email"
                  value={formData.admin_email}
                  onChange={(e) => setFormData({ ...formData, admin_email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Admin Mobile *</label>
                <input
                  type="tel"
                  value={formData.admin_mobile}
                  onChange={(e) => setFormData({ ...formData, admin_mobile: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                  required
                />
              </div>
            </div>
          </div>
          
          <div className="flex gap-3 pt-6 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-bamboo-600 text-white rounded-lg hover:bg-bamboo-700 disabled:bg-gray-300"
            >
              {loading ? 'Creating...' : 'Create Organization'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Employees Page
function EmployeesPage() {
  const { user } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  
  const canManage = user?.role === 'FIRM_ADMIN' || user?.role === 'SUPER_ADMIN';
  
  useEffect(() => {
    loadEmployees();
  }, [statusFilter]);
  
  const loadEmployees = async () => {
    try {
      let endpoint = '/api/employees?limit=1000';
      if (statusFilter) endpoint += `&status=${statusFilter}`;
      
      const data = await api.request(endpoint);
      setEmployees(data.employees || []);
    } catch (error) {
      console.error('Error loading employees:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const filteredEmployees = employees.filter(emp =>
    emp.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    emp.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    emp.employee_code.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'ACTIVE': return 'bg-green-100 text-green-800';
      case 'DRAFT': return 'bg-yellow-100 text-yellow-800';
      case 'INACTIVE': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };
  
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Employees</h1>
        {canManage && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-bamboo-600 text-white rounded-lg hover:bg-bamboo-700 transition-colors"
            data-testid="create-employee-button"
          >
            <Plus className="w-5 h-5" />
            Add Employee
          </button>
        )}
      </div>
      
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-4 border-b border-gray-200 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search employees..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500 focus:border-transparent"
              data-testid="search-employees-input"
            />
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={() => setStatusFilter('')}
              className={`px-3 py-1 text-sm rounded-full ${!statusFilter ? 'bg-bamboo-100 text-bamboo-700' : 'bg-gray-100 text-gray-600'}`}
            >
              All
            </button>
            <button
              onClick={() => setStatusFilter('ACTIVE')}
              className={`px-3 py-1 text-sm rounded-full ${statusFilter === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}
            >
              Active
            </button>
            <button
              onClick={() => setStatusFilter('DRAFT')}
              className={`px-3 py-1 text-sm rounded-full ${statusFilter === 'DRAFT' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-600'}`}
            >
              Draft
            </button>
            <button
              onClick={() => setStatusFilter('INACTIVE')}
              className={`px-3 py-1 text-sm rounded-full ${statusFilter === 'INACTIVE' ? 'bg-gray-200 text-gray-700' : 'bg-gray-100 text-gray-600'}`}
            >
              Inactive
            </button>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contact</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Department</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="6" className="px-6 py-8 text-center text-gray-500">Loading...</td>
                </tr>
              ) : filteredEmployees.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-8 text-center text-gray-500">No employees found</td>
                </tr>
              ) : (
                filteredEmployees.map((emp) => (
                  <tr key={emp.employee_id} className="hover:bg-gray-50" data-testid={`employee-row-${emp.employee_id}`}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{emp.employee_code}</td>
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">{emp.full_name}</div>
                      <div className="text-sm text-gray-500">{emp.designation}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-600">{emp.email}</div>
                      <div className="text-sm text-gray-500">{emp.mobile}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{emp.department}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(emp.status)}`}>
                        {emp.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => setSelectedEmployee(emp)}
                        className="text-bamboo-600 hover:text-bamboo-700"
                        data-testid={`view-employee-${emp.employee_id}`}
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      {showCreateModal && (
        <CreateEmployeeModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            loadEmployees();
          }}
        />
      )}
      
      {selectedEmployee && (
        <EmployeeDetailPanel
          employee={selectedEmployee}
          onClose={() => setSelectedEmployee(null)}
          onUpdate={loadEmployees}
        />
      )}
    </div>
  );
}

// Create Employee Modal
function CreateEmployeeModal({ onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    mobile: '',
    emergency_contact: '',
    date_of_birth: '',
    date_of_joining: '',
    employee_type: 'FULL_TIME',
    department: '',
    designation: '',
    location: '',
    send_invitation: true,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      await api.request('/api/employees', {
        method: 'POST',
        body: JSON.stringify(formData),
      });
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Add Employee</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}
          
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Mobile *</label>
              <input
                type="tel"
                value={formData.mobile}
                onChange={(e) => setFormData({ ...formData, mobile: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Emergency Contact</label>
              <input
                type="tel"
                value={formData.emergency_contact}
                onChange={(e) => setFormData({ ...formData, emergency_contact: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date of Birth</label>
              <input
                type="date"
                value={formData.date_of_birth}
                onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date of Joining *</label>
              <input
                type="date"
                value={formData.date_of_joining}
                onChange={(e) => setFormData({ ...formData, date_of_joining: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Employee Type *</label>
              <select
                value={formData.employee_type}
                onChange={(e) => setFormData({ ...formData, employee_type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                required
              >
                <option value="FULL_TIME">Full Time</option>
                <option value="PART_TIME">Part Time</option>
                <option value="CONTRACT">Contract</option>
                <option value="INTERN">Intern</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Department *</label>
              <input
                type="text"
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Designation *</label>
              <input
                type="text"
                value={formData.designation}
                onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Location *</label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                required
              />
            </div>
            
            <div className="col-span-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.send_invitation}
                  onChange={(e) => setFormData({ ...formData, send_invitation: e.target.checked })}
                  className="w-4 h-4 text-bamboo-600 border-gray-300 rounded focus:ring-bamboo-500"
                />
                <span className="text-sm text-gray-700">Send invitation with credentials</span>
              </label>
            </div>
          </div>
          
          <div className="flex gap-3 pt-6 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-bamboo-600 text-white rounded-lg hover:bg-bamboo-700 disabled:bg-gray-300"
            >
              {loading ? 'Creating...' : 'Create Employee'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Employee Detail Panel
function EmployeeDetailPanel({ employee, onClose, onUpdate }) {
  const { user } = useAuth();
  const canManage = user?.role === 'FIRM_ADMIN' || user?.role === 'SUPER_ADMIN';
  const [showStatusModal, setShowStatusModal] = useState(false);
  
  return (
    <>
      <div className="fixed inset-y-0 right-0 w-full max-w-2xl bg-white shadow-2xl z-50 overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Employee Details</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        
        <div className="p-6 space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-2xl font-bold text-gray-900">{employee.full_name}</h3>
              <p className="text-gray-600">{employee.designation}</p>
              <p className="text-sm text-gray-500 mt-1">Code: {employee.employee_code}</p>
            </div>
            <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${
              employee.status === 'ACTIVE' ? 'bg-green-100 text-green-800' :
              employee.status === 'DRAFT' ? 'bg-yellow-100 text-yellow-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {employee.status}
            </span>
          </div>
          
          {/* Contact Information */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            <h4 className="font-semibold text-gray-900">Contact Information</h4>
            <div className="space-y-2">
              <div className="flex items-center gap-3 text-sm">
                <Mail className="w-4 h-4 text-gray-400" />
                <span className="text-gray-600">{employee.email}</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Phone className="w-4 h-4 text-gray-400" />
                <span className="text-gray-600">{employee.mobile}</span>
              </div>
              {employee.emergency_contact && (
                <div className="flex items-center gap-3 text-sm">
                  <Phone className="w-4 h-4 text-red-400" />
                  <span className="text-gray-600">Emergency: {employee.emergency_contact}</span>
                </div>
              )}
            </div>
          </div>
          
          {/* Employment Details */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            <h4 className="font-semibold text-gray-900">Employment Details</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Department</span>
                <p className="font-medium text-gray-900">{employee.department}</p>
              </div>
              <div>
                <span className="text-gray-500">Location</span>
                <p className="font-medium text-gray-900">{employee.location}</p>
              </div>
              <div>
                <span className="text-gray-500">Employee Type</span>
                <p className="font-medium text-gray-900">{employee.employee_type?.replace('_', ' ')}</p>
              </div>
              <div>
                <span className="text-gray-500">Date of Joining</span>
                <p className="font-medium text-gray-900">
                  {employee.date_of_joining ? new Date(employee.date_of_joining).toLocaleDateString() : '-'}
                </p>
              </div>
            </div>
          </div>
          
          {/* Actions */}
          {canManage && (
            <div className="flex gap-3 pt-6 border-t border-gray-200">
              <button
                onClick={() => setShowStatusModal(true)}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Change Status
              </button>
            </div>
          )}
        </div>
      </div>
      
      <div className="fixed inset-0 bg-black bg-opacity-50 z-40" onClick={onClose} />
      
      {showStatusModal && (
        <ChangeStatusModal
          employee={employee}
          onClose={() => setShowStatusModal(false)}
          onSuccess={() => {
            setShowStatusModal(false);
            onUpdate();
            onClose();
          }}
        />
      )}
    </>
  );
}

// Change Status Modal
function ChangeStatusModal({ employee, onClose, onSuccess }) {
  const [status, setStatus] = useState(employee.status);
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      await api.request(`/api/employees/${employee.employee_id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status, reason }),
      });
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-[60]">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Change Employee Status</h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">New Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
            >
              <option value="DRAFT">Draft</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Reason *</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
              rows="3"
              required
            />
          </div>
          
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-bamboo-600 text-white rounded-lg hover:bg-bamboo-700 disabled:bg-gray-300"
            >
              {loading ? 'Updating...' : 'Update Status'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Placeholder Pages
function MastersPage() {
  const { user } = useAuth();
  const [activeMaster, setActiveMaster] = useState('departments');
  
  const masterTypes = [
    { id: 'departments', label: 'Departments', icon: Building2, fields: ['Description'], createFields: [] },
    { id: 'designations', label: 'Designations', icon: Briefcase, fields: ['Description', 'Level'], createFields: [{name: 'level', label: 'Level', type: 'number'}] },
    { id: 'locations', label: 'Locations', icon: MapPin, fields: ['City', 'State'], createFields: [{name: 'city', label: 'City'}, {name: 'state', label: 'State'}, {name: 'country', label: 'Country'}] },
    { id: 'clients', label: 'Clients', icon: Users, fields: ['Contact Person'], createFields: [{name: 'contact_person', label: 'Contact Person'}, {name: 'contact_email', label: 'Contact Email', type: 'email'}] },
  ];
  
  const activeMasterType = masterTypes.find(m => m.id === activeMaster);
  
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Master Data Management</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Master Type Selector */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">Master Types</h2>
            <nav className="space-y-1">
              {masterTypes.map((master) => {
                const Icon = master.icon;
                const isActive = activeMaster === master.id;
                return (
                  <button
                    key={master.id}
                    onClick={() => setActiveMaster(master.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                      isActive
                        ? 'bg-bamboo-50 text-bamboo-700 font-medium'
                        : 'text-gray-600 hover:bg-gray-50'
                    }`}
                    data-testid={`master-type-${master.id}`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{master.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
        
        {/* Master Data Content */}
        <div className="lg:col-span-3">
          {activeMasterType && (
            <MasterListPage
              masterType={activeMaster}
              title={activeMasterType.label}
              icon={activeMasterType.icon}
              fields={activeMasterType.fields}
              createFields={activeMasterType.createFields}
              user={user}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function RolesPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Roles & Permissions</h1>
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <p className="text-gray-600">Roles and permissions management will be available here.</p>
      </div>
    </div>
  );
}

function ReportsPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Reports</h1>
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <p className="text-gray-600">Reports and analytics will be available here.</p>
      </div>
    </div>
  );
}

function AuditPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Audit Logs</h1>
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <p className="text-gray-600">Audit trail will be available here.</p>
      </div>
    </div>
  );
}

function SettingsPage() {
  const { user } = useAuth();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  useEffect(() => {
    loadSettings();
  }, []);
  
  const loadSettings = async () => {
    try {
      const data = await api.request(`/api/organizations/${user.organization_id}/settings`);
      setSettings(data);
    } catch (error) {
      console.error('Error loading settings:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    
    try {
      await api.request(`/api/organizations/${user.organization_id}/settings`, {
        method: 'PUT',
        body: JSON.stringify(settings),
      });
      alert('Settings saved successfully!');
    } catch (error) {
      alert('Error saving settings: ' + error.message);
    } finally {
      setSaving(false);
    }
  };
  
  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Organization Settings</h1>
      
      <form onSubmit={handleSave} className="bg-white rounded-lg border border-gray-200 p-6 space-y-6">
        <div className="space-y-4">
          <h3 className="font-semibold text-gray-900">Email Notifications</h3>
          
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={settings?.email_notifications_enabled || false}
              onChange={(e) => setSettings({ ...settings, email_notifications_enabled: e.target.checked })}
              className="w-4 h-4 text-bamboo-600 border-gray-300 rounded focus:ring-bamboo-500"
            />
            <span className="text-sm text-gray-700">Enable email notifications</span>
          </label>
          
          {settings?.email_notifications_enabled && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sender Email Address</label>
                <input
                  type="email"
                  value={settings?.email_sender_address || ''}
                  onChange={(e) => setSettings({ ...settings, email_sender_address: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sender Name</label>
                <input
                  type="text"
                  value={settings?.email_sender_name || ''}
                  onChange={(e) => setSettings({ ...settings, email_sender_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                />
              </div>
            </>
          )}
        </div>
        
        <div className="space-y-4 border-t border-gray-200 pt-6">
          <h3 className="font-semibold text-gray-900">WhatsApp Notifications</h3>
          
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={settings?.whatsapp_notifications_enabled || false}
              onChange={(e) => setSettings({ ...settings, whatsapp_notifications_enabled: e.target.checked })}
              className="w-4 h-4 text-bamboo-600 border-gray-300 rounded focus:ring-bamboo-500"
            />
            <span className="text-sm text-gray-700">Enable WhatsApp notifications</span>
          </label>
          
          {settings?.whatsapp_notifications_enabled && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">WhatsApp Phone Number</label>
                <input
                  type="tel"
                  value={settings?.whatsapp_phone_number || ''}
                  onChange={(e) => setSettings({ ...settings, whatsapp_phone_number: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">WhatsApp API Key</label>
                <input
                  type="password"
                  value={settings?.whatsapp_api_key || ''}
                  onChange={(e) => setSettings({ ...settings, whatsapp_api_key: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                />
              </div>
            </>
          )}
        </div>
        
        <div className="border-t border-gray-200 pt-6">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2 bg-bamboo-600 text-white rounded-lg hover:bg-bamboo-700 disabled:bg-gray-300"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
}

// Main App Layout
function AppLayout() {
  const [activePage, setActivePage] = useState('dashboard');
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);
  
  const renderPage = () => {
    switch (activePage) {
      case 'dashboard': return <DashboardPage />;
      case 'organizations': return <OrganizationsPage />;
      case 'employees': return <EmployeesPage />;
      case 'roles': return <RolesPage />;
      case 'reports': return <ReportsPage />;
      case 'audit': return <AuditPage />;
      case 'settings': return <SettingsPage />;
      default: return <DashboardPage />;
    }
  };
  
  return (
    <div className="h-screen flex overflow-hidden bg-gray-50">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block w-64 flex-shrink-0">
        <Sidebar activePage={activePage} setActivePage={setActivePage} />
      </div>
      
      {/* Mobile Sidebar */}
      {showMobileSidebar && (
        <>
          <div className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden" onClick={() => setShowMobileSidebar(false)} />
          <div className="fixed inset-y-0 left-0 w-64 z-50 lg:hidden">
            <Sidebar activePage={activePage} setActivePage={setActivePage} onClose={() => setShowMobileSidebar(false)} />
          </div>
        </>
      )}
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header onMenuClick={() => setShowMobileSidebar(true)} />
        <main className="flex-1 overflow-y-auto">
          {renderPage()}
        </main>
      </div>
    </div>
  );
}

// Main App Component
function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

function AppContent() {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-bamboo-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }
  
  return user ? <AppLayout /> : <LoginPage />;
}

export default App;
