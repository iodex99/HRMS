// Module 2: Master Data Management Components
import React, { useState, useEffect } from 'react';
import { 
  Plus, Search, Edit2, X, AlertCircle, CheckCircle, Download, Upload, 
  Database, Building, MapPin, Users, Briefcase, Calendar, List, Settings as SettingsIcon
} from 'lucide-react';

// API helper
const api = {
  getToken: () => localStorage.getItem('token'),
  
  request: async (endpoint, options = {}) => {
    const token = api.getToken();
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });
    
    if (response.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/';
    }
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Something went wrong');
    }
    
    return data;
  },
};

// Generic Master List Component
export function MasterListPage({ 
  masterType, 
  title, 
  icon: Icon,
  fields,
  createFields,
  user 
}) {
  const [masters, setMasters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedMaster, setSelectedMaster] = useState(null);
  const [showDependenciesModal, setShowDependenciesModal] = useState(false);
  
  useEffect(() => {
    loadMasters();
  }, [statusFilter, masterType]);
  
  const loadMasters = async () => {
    try {
      let endpoint = `/api/masters/${masterType}?limit=1000`;
      if (statusFilter) endpoint += `&status=${statusFilter}`;
      
      const data = await api.request(endpoint);
      setMasters(data[masterType] || []);
    } catch (error) {
      console.error('Error loading masters:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const filteredMasters = masters.filter(master =>
    (master.name?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
    (master.code?.toLowerCase() || '').includes(searchTerm.toLowerCase())
  );
  
  const getStatusColor = (status) => {
    return status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800';
  };
  
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-bamboo-100 rounded-lg flex items-center justify-center">
            <Icon className="w-6 h-6 text-bamboo-700" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-bamboo-600 text-white rounded-lg hover:bg-bamboo-700 transition-colors"
          data-testid={`create-${masterType}-button`}
        >
          <Plus className="w-5 h-5" />
          Add {title.slice(0, -1)}
        </button>
      </div>
      
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-4 border-b border-gray-200 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder={`Search ${title.toLowerCase()}...`}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500 focus:border-transparent"
              data-testid={`search-${masterType}-input`}
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
                {fields.map(field => (
                  <th key={field} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{field}</th>
                ))}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={fields.length + 4} className="px-6 py-8 text-center text-gray-500">Loading...</td>
                </tr>
              ) : filteredMasters.length === 0 ? (
                <tr>
                  <td colSpan={fields.length + 4} className="px-6 py-8 text-center text-gray-500">No {title.toLowerCase()} found</td>
                </tr>
              ) : (
                filteredMasters.map((master) => (
                  <tr key={master.master_id} className="hover:bg-gray-50" data-testid={`${masterType}-row-${master.master_id}`}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{master.code}</td>
                    <td className="px-6 py-4 text-sm text-gray-900">{master.name}</td>
                    {fields.map(field => (
                      <td key={field} className="px-6 py-4 text-sm text-gray-600">
                        {master[field.toLowerCase().replace(' ', '_')] || '-'}
                      </td>
                    ))}
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(master.status)}`}>
                        {master.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() => setSelectedMaster(master)}
                          className="text-bamboo-600 hover:text-bamboo-700 text-sm"
                          data-testid={`view-${masterType}-${master.master_id}`}
                        >
                          View
                        </button>
                        {master.status === 'ACTIVE' && (
                          <button
                            onClick={() => {
                              setSelectedMaster(master);
                              setShowDependenciesModal(true);
                            }}
                            className="text-gray-600 hover:text-gray-700 text-sm"
                          >
                            Check Usage
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      {showCreateModal && (
        <CreateMasterModal
          masterType={masterType}
          title={title}
          fields={createFields}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            loadMasters();
          }}
        />
      )}
      
      {selectedMaster && !showDependenciesModal && (
        <MasterDetailPanel
          masterType={masterType}
          master={selectedMaster}
          onClose={() => setSelectedMaster(null)}
          onUpdate={loadMasters}
        />
      )}
      
      {showDependenciesModal && selectedMaster && (
        <DependenciesModal
          masterType={masterType}
          master={selectedMaster}
          onClose={() => {
            setShowDependenciesModal(false);
            setSelectedMaster(null);
          }}
          onDeactivate={() => {
            setShowDependenciesModal(false);
            setSelectedMaster(null);
            loadMasters();
          }}
        />
      )}
    </div>
  );
}

// Create Master Modal
function CreateMasterModal({ masterType, title, fields, onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    effective_from: new Date().toISOString().split('T')[0],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      await api.request(`/api/masters/${masterType}`, {
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
      <div className="bg-white rounded-lg max-w-md w-full">
        <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Add {title.slice(0, -1)}</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Code *</label>
            <input
              type="text"
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
              rows="3"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Effective From *</label>
            <input
              type="date"
              value={formData.effective_from}
              onChange={(e) => setFormData({ ...formData, effective_from: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
              required
            />
          </div>
          
          {/* Additional fields based on master type */}
          {fields && fields.map(field => (
            <div key={field.name}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.label} {field.required && '*'}
              </label>
              <input
                type={field.type || 'text'}
                value={formData[field.name] || ''}
                onChange={(e) => setFormData({ ...formData, [field.name]: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bamboo-500"
                required={field.required}
              />
            </div>
          ))}
          
          <div className="flex gap-3 pt-4 border-t border-gray-200">
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
              {loading ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Master Detail Panel
function MasterDetailPanel({ masterType, master, onClose, onUpdate }) {
  const [showStatusModal, setShowStatusModal] = useState(false);
  
  return (
    <>
      <div className="fixed inset-y-0 right-0 w-full max-w-md bg-white shadow-2xl z-50 overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Master Details</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        
        <div className="p-6 space-y-6">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-lg font-bold text-gray-900">{master.name}</h3>
              <p className="text-sm text-gray-500">Code: {master.code}</p>
            </div>
            <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${
              master.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
            }`}>
              {master.status}
            </span>
          </div>
          
          {master.description && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Description</h4>
              <p className="text-sm text-gray-600">{master.description}</p>
            </div>
          )}
          
          <div className="bg-gray-50 rounded-lg p-4 space-y-2">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Details</h4>
            <div className="text-sm">
              <span className="text-gray-500">Effective From: </span>
              <span className="text-gray-900">{master.effective_from}</span>
            </div>
            <div className="text-sm">
              <span className="text-gray-500">Created: </span>
              <span className="text-gray-900">{new Date(master.created_at).toLocaleString()}</span>
            </div>
            {master.updated_at !== master.created_at && (
              <div className="text-sm">
                <span className="text-gray-500">Last Updated: </span>
                <span className="text-gray-900">{new Date(master.updated_at).toLocaleString()}</span>
              </div>
            )}
          </div>
          
          {master.status === 'ACTIVE' && (
            <button
              onClick={() => setShowStatusModal(true)}
              className="w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Deactivate
            </button>
          )}
        </div>
      </div>
      
      <div className="fixed inset-0 bg-black bg-opacity-50 z-40" onClick={onClose} />
      
      {showStatusModal && (
        <ChangeStatusModal
          masterType={masterType}
          master={master}
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
function ChangeStatusModal({ masterType, master, onClose, onSuccess }) {
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      await api.request(`/api/masters/${masterType}/${master.master_id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'INACTIVE', reason }),
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
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Deactivate Master</h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
          
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
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-300"
            >
              {loading ? 'Deactivating...' : 'Deactivate'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Dependencies Modal
function DependenciesModal({ masterType, master, onClose, onDeactivate }) {
  const [dependencies, setDependencies] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadDependencies();
  }, []);
  
  const loadDependencies = async () => {
    try {
      const data = await api.request(`/api/masters/${masterType}/${master.master_id}/dependencies`);
      setDependencies(data);
    } catch (error) {
      console.error('Error loading dependencies:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-[60]">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Usage Check</h3>
        
        {loading ? (
          <div className="py-8 text-center text-gray-500">Checking dependencies...</div>
        ) : (
          <div className="space-y-4">
            {dependencies && dependencies.can_deactivate ? (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-green-700 mb-2">
                  <CheckCircle className="w-5 h-5" />
                  <span className="font-semibold">Safe to Deactivate</span>
                </div>
                <p className="text-sm text-green-600">
                  This master is not currently being used anywhere in the system.
                </p>
              </div>
            ) : (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-red-700 mb-2">
                  <AlertCircle className="w-5 h-5" />
                  <span className="font-semibold">Cannot Deactivate</span>
                </div>
                <p className="text-sm text-red-600 mb-3">
                  This master is currently being used:
                </p>
                <ul className="text-sm text-red-600 space-y-1">
                  {dependencies && Object.entries(dependencies.dependencies || {}).map(([key, count]) => (
                    <li key={key}>• {count} {key}</li>
                  ))}
                </ul>
              </div>
            )}
            
            <button
              onClick={onClose}
              className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default MasterListPage;
