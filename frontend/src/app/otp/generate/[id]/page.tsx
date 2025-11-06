"use client";
import { useState, useEffect, useCallback } from "react";
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
  secret_key: string;
}

interface OTPResponse {
  otp_code: string;
  config_id: number;
  remaining_seconds?: number;
  next_counter?: number;
  generated_at: string;
}

export default function GenerateOTP() {
  const params = useParams();
  const router = useRouter();
  const configId = params.id as string;

  const [config, setConfig] = useState<OTPConfig | null>(null);
  const [otpData, setOtpData] = useState<OTPResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [countdown, setCountdown] = useState<number | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchConfig = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }

      console.log(`Fetching config for ID: ${configId}`);

      const response = await fetch(`http://localhost:8000/otp/configs/${configId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('token');
          router.push('/login');
          return;
        }
        throw new Error(`Failed to fetch OTP configuration: ${response.status}`);
      }

      const data = await response.json();
      console.log('Config data received:', data);
      setConfig(data);
    } catch (err: any) {
      console.error('Error fetching config:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [configId, router]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  // Enhanced countdown with auto-refresh
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (countdown !== null && countdown > 0) {
      interval = setInterval(() => {
        setCountdown(prev => {
          if (prev === null) return null;
          if (prev <= 1) {
            // Auto-refresh when countdown ends
            if (autoRefresh && config?.otp_type === 'totp') {
              generateOTP();
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [countdown, autoRefresh, config?.otp_type]);

  const generateOTP = async () => {
    setGenerating(true);
    setError('');

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }

      const response = await fetch('http://localhost:8000/otp/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          config_id: parseInt(configId),
          counter_increment: config?.otp_type === 'hotp'
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `HTTP error! status: ${response.status}`;
        
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorData.error || errorMessage;
        } catch {
          errorMessage = errorText || errorMessage;
        }
        
        throw new Error(errorMessage);
      }

      const data: OTPResponse = await response.json();
      setOtpData(data);
      
      if (data.remaining_seconds) {
        setCountdown(data.remaining_seconds);
      }
    } catch (err: any) {
      console.error('Generate OTP error:', err);
      setError(err.message || 'Failed to generate OTP.');
    } finally {
      setGenerating(false);
    }
  };

  const copyToClipboard = async () => {
    if (otpData) {
      try {
        await navigator.clipboard.writeText(otpData.otp_code);
        // Show temporary success message
        const copyButton = document.querySelector('.copy-btn') as HTMLButtonElement;
        if (copyButton) {
          const originalText = copyButton.textContent;
          copyButton.textContent = "Copied!";
          copyButton.classList.add('bg-green-700');
          setTimeout(() => {
            copyButton.textContent = originalText;
            copyButton.classList.remove('bg-green-700');
          }, 2000);
        }
      } catch (err) {
        setError('Failed to copy to clipboard');
      }
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Debug: Check what's happening
  useEffect(() => {
    console.log('Current state:', { configId, config, loading, error });
  }, [configId, config, loading, error]);

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

  if (error && !config) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center max-w-md">
          <div className="bg-red-100 p-4 rounded-lg mb-4">
            <svg className="w-12 h-12 text-red-500 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <h2 className="text-xl font-semibold text-red-700 mb-2">Error Loading Configuration</h2>
            <p className="text-red-600 mb-4">{error}</p>
          </div>
          <button 
            onClick={() => router.push('/otp/configs')}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
          >
            Back to Configurations
          </button>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center max-w-md">
          <div className="bg-yellow-100 p-4 rounded-lg mb-4">
            <svg className="w-12 h-12 text-yellow-500 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <h2 className="text-xl font-semibold text-yellow-700 mb-2">Configuration Not Found</h2>
            <p className="text-yellow-600 mb-4">
              The OTP configuration with ID "{configId}" was not found or you don't have permission to access it.
            </p>
          </div>
          <div className="space-y-2">
            <button 
              onClick={() => router.push('/otp/configs')}
              className="w-full bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
            >
              Back to Configurations
            </button>
            <button 
              onClick={fetchConfig}
              className="w-full bg-gray-600 text-white px-6 py-2 rounded-md hover:bg-gray-700"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <button 
            onClick={() => router.push('/otp/configs')}
            className="text-blue-600 hover:text-blue-800 mb-4 flex items-center"
          >
            ← Back to Configurations
          </button>
          <h1 className="text-3xl font-bold text-gray-900">Generate OTP</h1>
          <p className="text-gray-600 mt-2">Generate one-time passwords for: {config.name}</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-md flex items-center">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Configuration Details */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-md p-6 sticky top-8">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <svg className="w-5 h-5 mr-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Configuration Details
              </h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-sm font-medium text-gray-500">Type</span>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    config.otp_type === 'totp' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                  }`}>
                    {config.otp_type.toUpperCase()}
                  </span>
                </div>
                
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-sm font-medium text-gray-500">Algorithm</span>
                  <span className="text-sm text-gray-900">{config.algorithm.toUpperCase()}</span>
                </div>
                
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-sm font-medium text-gray-500">Digits</span>
                  <span className="text-sm text-gray-900">{config.digits}</span>
                </div>
                
                {config.otp_type === 'totp' && (
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-sm font-medium text-gray-500">Interval</span>
                    <span className="text-sm text-gray-900">{config.interval}s</span>
                  </div>
                )}
                
                {config.otp_type === 'hotp' && (
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-sm font-medium text-gray-500">Counter</span>
                    <span className="text-sm text-gray-900">{config.counter}</span>
                  </div>
                )}
                
                <div className="flex justify-between items-center py-2">
                  <span className="text-sm font-medium text-gray-500">Issuer</span>
                  <span className="text-sm text-gray-900">{config.issuer}</span>
                </div>
              </div>

              {/* Auto-refresh toggle for TOTP */}
              {config.otp_type === 'totp' && (
                <div className="mt-6 pt-4 border-t border-gray-200">
                  <label className="flex items-center cursor-pointer">
                    <div className="relative">
                      <input
                        type="checkbox"
                        className="sr-only"
                        checked={autoRefresh}
                        onChange={(e) => setAutoRefresh(e.target.checked)}
                      />
                      <div className={`block w-10 h-6 rounded-full ${
                        autoRefresh ? 'bg-blue-600' : 'bg-gray-300'
                      }`}></div>
                      <div className={`dot absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition ${
                        autoRefresh ? 'transform translate-x-4' : ''
                      }`}></div>
                    </div>
                    <div className="ml-3 text-sm font-medium text-gray-700">
                      Auto-refresh
                    </div>
                  </label>
                </div>
              )}
            </div>
          </div>

          {/* OTP Generation Panel */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-lg shadow-md p-8">
              <div className="text-center mb-8">
                <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-10 h-10 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <h2 className="text-2xl font-bold text-gray-900">Generate OTP Code</h2>
                <p className="text-gray-600 mt-2">For configuration: <strong>{config.name}</strong></p>
              </div>

              {!otpData ? (
                <div className="text-center py-12">
                  <div className="text-6xl mb-6">🔐</div>
                  <p className="text-gray-600 mb-8 text-lg">
                    {config.otp_type === 'totp' 
                      ? 'Generate a time-based one-time password' 
                      : 'Generate a counter-based one-time password'
                    }
                  </p>
                  <button
                    onClick={generateOTP}
                    disabled={generating}
                    className="bg-blue-600 text-white px-10 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-lg"
                  >
                    {generating ? (
                      <span className="flex items-center">
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Generating...
                      </span>
                    ) : (
                      'Generate OTP'
                    )}
                  </button>
                </div>
              ) : (
                <div className="text-center">
                  {/* OTP Code Display */}
                  <div className="mb-8">
                    <p className="text-sm text-gray-500 mb-4 uppercase tracking-wider">Your OTP Code</p>
                    <div className="text-5xl font-mono font-bold text-gray-900 tracking-wider mb-6 bg-gray-50 py-4 rounded-lg border-2 border-gray-200">
                      {otpData.otp_code}
                    </div>
                    
                    {/* Enhanced Countdown Timer */}
                    {countdown !== null && (
                      <div className="mb-6">
                        <div className="flex items-center justify-center space-x-4 mb-2">
                          <div className="w-48 bg-gray-200 rounded-full h-3">
                            <div 
                              className="h-3 rounded-full transition-all duration-1000 ease-linear"
                              style={{ 
                                width: `${(countdown / (config.interval || 30)) * 100}%`,
                                background: countdown < 10 
                                  ? 'linear-gradient(to right, #ef4444, #f59e0b)'
                                  : 'linear-gradient(to right, #10b981, #f59e0b)'
                              }}
                            ></div>
                          </div>
                          <span className={`text-lg font-semibold ${
                            countdown < 10 ? 'text-red-600' : 'text-gray-700'
                          }`}>
                            {formatTime(countdown)}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500">
                          {countdown > 0 ? `Expires in ${countdown} seconds` : 'Expired - Generate new code'}
                        </p>
                      </div>
                    )}

                    {/* Next Counter for HOTP */}
                    {otpData.next_counter !== undefined && (
                      <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                        <p className="text-sm text-blue-700">
                          Next counter: <strong>{otpData.next_counter}</strong>
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-col sm:flex-row justify-center gap-4 mb-8">
                    <button
                      onClick={copyToClipboard}
                      className="copy-btn bg-green-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-green-700 transition-colors flex items-center justify-center"
                    >
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      Copy OTP
                    </button>
                    
                    <button
                      onClick={generateOTP}
                      disabled={generating}
                      className="bg-blue-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center justify-center"
                    >
                      {generating ? 'Generating...' : 'Generate New'}
                    </button>
                    
                    <button
                      onClick={() => router.push(`/otp/validate/${configId}`)}
                      className="bg-purple-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-purple-700 transition-colors flex items-center justify-center"
                    >
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Validate OTP
                    </button>
                  </div>

                  {/* Generation Info */}
                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <p className="text-sm text-gray-600">
                      <strong>Generated at:</strong> {new Date(otpData.generated_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Enhanced Usage Instructions */}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-blue-800 mb-3 flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Usage Instructions
                </h3>
                <ul className="text-sm text-blue-700 space-y-2">
                  <li className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>Copy the OTP code and use it in your application</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>TOTP codes automatically refresh every {config.interval} seconds</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>HOTP codes require manual generation for each use</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>Enable auto-refresh for automatic TOTP regeneration</span>
                  </li>
                </ul>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-yellow-800 mb-3 flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  Security Tips
                </h3>
                <ul className="text-sm text-yellow-700 space-y-2">
                  <li className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>Keep your secret key secure and never share it</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>OTP codes are valid for one use only (HOTP) or time window (TOTP)</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>Monitor your OTP usage in the dashboard</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-2">•</span>
                    <span>Report any suspicious activity immediately</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}