import React, { useState } from 'react';
import { api } from '../lib/api';

export const RegisterView: React.FC = () => {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const data = await api.register({
        email,
        password,
        full_name: fullName || undefined,
      });

      if (data.access_token) {
        window.location.href = '/dashboard';
        return;
      }

      setSuccess('Cont creat. Verifica email-ul pentru confirmare, apoi autentifica-te.');
      setIsLoading(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Register failed. Verifica datele si incearca din nou.';
      setError(message);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white p-8 rounded-xl shadow-sm border border-slate-200">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Insight</h1>
          <p className="text-slate-500 mt-1">Create account</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-md border border-red-100">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-emerald-50 text-emerald-700 text-sm rounded-md border border-emerald-100">
            {success}
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-4">
          <input
            type="text"
            placeholder="Full name (optional)"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full px-4 py-2 border rounded-md outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-2 border rounded-md outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <input
            type="password"
            placeholder="Password (min 6 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-2 border rounded-md outline-none focus:ring-2 focus:ring-blue-500"
            minLength={6}
            required
          />
          <button
            type="submit"
            className="w-full bg-slate-900 text-white py-2.5 rounded-md font-semibold hover:bg-slate-800 transition shadow-sm"
            disabled={isLoading}
          >
            {isLoading ? 'Creating account...' : 'Register'}
          </button>
        </form>

        <div className="mt-5 text-center text-sm text-slate-600">
          <span>Ai deja cont? </span>
          <button
            type="button"
            className="font-semibold text-blue-600 hover:text-blue-700"
            onClick={() => {
              window.location.href = '/login';
            }}
          >
            Sign in
          </button>
        </div>
      </div>
    </div>
  );
};
