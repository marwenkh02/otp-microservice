import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8 bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold text-gray-800 mb-4">OpenPAM</h1>
        <p className="text-xl text-gray-600 max-w-2xl mb-6">
          Enterprise-grade Privileged Access Management with Advanced OTP Security
        </p>
        <div className="flex flex-wrap justify-center gap-4 mb-8">
          <div className="bg-white/80 backdrop-blur-sm rounded-lg px-4 py-2 shadow-sm">
            <span className="text-green-600 font-semibold">✓</span> Encrypted OTP Secrets
          </div>
          <div className="bg-white/80 backdrop-blur-sm rounded-lg px-4 py-2 shadow-sm">
            <span className="text-green-600 font-semibold">✓</span> Audit Logging
          </div>
          <div className="bg-white/80 backdrop-blur-sm rounded-lg px-4 py-2 shadow-sm">
            <span className="text-green-600 font-semibold">✓</span> Rate Limiting
          </div>
          <div className="bg-white/80 backdrop-blur-sm rounded-lg px-4 py-2 shadow-sm">
            <span className="text-green-600 font-semibold">✓</span> MFA Support
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl w-full">
        <div className="bg-white rounded-lg shadow-lg p-6 flex flex-col">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">Advanced OTP Security</h2>
          <p className="text-gray-600 mb-6 flex-grow">
            Generate and manage TOTP/HOTP codes with enterprise-grade security features including 
            encrypted secret storage, comprehensive audit trails, and real-time monitoring.
          </p>
          <ul className="text-gray-600 mb-6 space-y-2">
            <li className="flex items-center">
              <span className="text-green-500 mr-2">✓</span> Military-grade encryption
            </li>
            <li className="flex items-center">
              <span className="text-green-500 mr-2">✓</span> Comprehensive audit logging
            </li>
            <li className="flex items-center">
              <span className="text-green-500 mr-2">✓</span> Real-time metrics & analytics
            </li>
            <li className="flex items-center">
              <span className="text-green-500 mr-2">✓</span> Admin dashboard
            </li>
          </ul>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6 flex flex-col">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">Get Started</h2>
          <p className="text-gray-600 mb-6 flex-grow">
            Create an account to start managing your OTP configurations with advanced security features 
            or login to access your existing configurations.
          </p>
          
          <div className="space-y-4">
            <Link 
              href="/login"
              className="block w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg text-center transition duration-200 shadow-md"
            >
              Login to Your Account
            </Link>
            
            <Link 
              href="/signup"
              className="block w-full bg-white hover:bg-gray-50 text-blue-600 font-semibold py-3 px-4 rounded-lg border border-blue-600 text-center transition duration-200"
            >
              Create New Account
            </Link>
          </div>

          <div className="mt-6 pt-4 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Features:</h3>
            <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
              <div className="flex items-center">
                <span className="text-blue-500 mr-1">•</span> TOTP & HOTP Support
              </div>
              <div className="flex items-center">
                <span className="text-blue-500 mr-1">•</span> Multiple Algorithms
              </div>
              <div className="flex items-center">
                <span className="text-blue-500 mr-1">•</span> Custom Intervals
              </div>
              <div className="flex items-center">
                <span className="text-blue-500 mr-1">•</span> Bulk Operations
              </div>
            </div>
          </div>
        </div>
      </div>

      <footer className="mt-16 text-center text-gray-500">
        <p>© {new Date().getFullYear()} OpenPAM. Enterprise-grade OTP Security.</p>
      </footer>
    </main>
  );
}