"use client";
import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

interface OTPConfig {
  id: number;
  name: string;
  otp_type: 'totp' | 'hotp';
  algorithm: string;
  digits: number;
  interval: number;
  counter: number;
  issuer: string;
}

interface ValidationResult {
  is_valid: boolean;
  config_id: number;
  message: string;
}

export default function ValidateOTP() {
  const params = useParams();
  const router = useRouter();
  const configId = params.id as string;

  const [config, setConfig] = useState<OTPConfig | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    otp_code: '',
    counter: ''
  });

  useEffect(() => {
    fetchConfig();
  }, [configId]);

  const fetchConfig = async () => {
    try {
      const token = localStorage.getItem('token');
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/otp/configs/${configId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch OTP configuration');
      }

      const data = await response.json();
      setConfig(data);
      
      // Set current counter for HOTP
      if (data.otp_type === 'hotp') {
        setFormData(prev => ({ ...prev, counter: data.counter.toString() }));
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const validateOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidating(true);
    setError('');
    setValidationResult(null);

    try {
      const token = localStorage.getItem('token');
      const payload: any = {
        config_id: parseInt(configId),
        otp_code: formData.otp_code
      };

      if (config?.otp_type === 'hotp' && formData.counter) {
        payload.counter = parseInt(formData.counter);
      }

      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/otp/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to validate OTP');
      }

      const data: ValidationResult = await response.json();
      setValidationResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setValidating(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading configuration...</p>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-red-600">Configuration not found</h2>
          <button 
            onClick={() => router.push('/otp/configs')}
            className="mt-4 text-blue-600 hover:text-blue-800"
          >
            Back to Configurations
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <button 
            onClick={() => router.push('/otp/configs')}
            className="text-blue-600 hover:text-blue-800 mb-4"
          >
            ← Back to Configurations
          </button>
          <h1 className="text-3xl font-bold text-gray-900">Validate OTP</h1>
          <p className="text-gray-600 mt-2">Validate one-time passwords for: {config.name}</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-md">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Configuration Details */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">Configuration Details</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium text-gray-500">Name</label>
                  <p className="text-gray-900">{config.name}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Type</label>
                  <p className="text-gray-900">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {config.otp_type.toUpperCase()}
                    </span>
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Digits</label>
                  <p className="text-gray-900">{config.digits}</p>
                </div>
                {config.otp_type === 'hotp' && (
                  <div>
                    <label className="text-sm font-medium text-gray-500">Current Counter</label>
                    <p className="text-gray-900">{config.counter}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="mt-6 bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
              <div className="space-y-3">
                <button
                  onClick={() => router.push(`/otp/generate/${configId}`)}
                  className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 text-left"
                >
                  Generate OTP
                </button>
                <button
                  onClick={() => router.push('/otp/configs')}
                  className="w-full bg-gray-600 text-white py-2 px-4 rounded-md hover:bg-gray-700 text-left"
                >
                  Manage Configurations
                </button>
              </div>
            </div>
          </div>

          {/* Validation Form */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-6">Validate OTP Code</h2>
              
              <form onSubmit={validateOTP} className="space-y-6">
                <div>
                  <label htmlFor="otp_code" className="block text-sm font-medium text-gray-700 mb-2">
                    OTP Code *
                  </label>
                  <input
                    type="text"
                    id="otp_code"
                    name="otp_code"
                    value={formData.otp_code}
                    onChange={handleChange}
                    required
                    maxLength={8}
                    pattern="[0-9]*"
                    className="w-full px-4 py-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-2xl text-center font-mono tracking-widest"
                    placeholder="Enter OTP code"
                  />
                  <p className="text-sm text-gray-500 mt-2">
                    Enter the {config.digits}-digit OTP code to validate
                  </p>
                </div>

                {config.otp_type === 'hotp' && (
                  <div>
                    <label htmlFor="counter" className="block text-sm font-medium text-gray-700 mb-2">
                      Counter Value *
                    </label>
                    <input
                      type="number"
                      id="counter"
                      name="counter"
                      value={formData.counter}
                      onChange={handleChange}
                      required
                      min="0"
                      className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-sm text-gray-500 mt-2">
                      Enter the counter value used when generating this OTP
                    </p>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={validating}
                  className="w-full bg-green-600 text-white py-3 px-4 rounded-md text-lg font-semibold hover:bg-green-700 disabled:opacity-50"
                >
                  {validating ? 'Validating...' : 'Validate OTP'}
                </button>
              </form>

              {/* Validation Result */}
              {validationResult && (
                <div className={`mt-6 p-4 rounded-md ${
                  validationResult.is_valid 
                    ? 'bg-green-50 border border-green-200' 
                    : 'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex items-center">
                    <div className={`flex-shrink-0 ${
                      validationResult.is_valid ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {validationResult.is_valid ? (
                        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      )}
                    </div>
                    <div className="ml-3">
                      <h3 className={`text-sm font-medium ${
                        validationResult.is_valid ? 'text-green-800' : 'text-red-800'
                      }`}>
                        {validationResult.is_valid ? 'Valid OTP Code' : 'Invalid OTP Code'}
                      </h3>
                      <p className={`text-sm ${
                        validationResult.is_valid ? 'text-green-700' : 'text-red-700'
                      }`}>
                        {validationResult.message}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Usage Tips */}
              <div className="mt-6 bg-blue-50 border border-blue-200 rounded-md p-4">
                <h3 className="text-lg font-semibold text-blue-800 mb-2">Validation Tips</h3>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• For TOTP: Ensure the code is entered within the valid time window</li>
                  <li>• For HOTP: Use the correct counter value that matches the generation</li>
                  <li>• OTP codes are typically {config.digits} digits long</li>
                  <li>• Codes expire after one use (HOTP) or time window (TOTP)</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}