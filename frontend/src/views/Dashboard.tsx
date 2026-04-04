import React from 'react';
import { api } from '../lib/api';

export const DashboardView: React.FC = () => {
  const handleLogout = () => {
    api.logout();
    window.location.href = '/login';
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 flex flex-col p-6 shadow-xl">
        <h1 className="text-xl font-extrabold text-white mb-10 tracking-tighter">TRUSTSCOPE</h1>
        <nav className="flex-1 space-y-1">
          <button className="w-full text-left p-3 rounded-lg bg-slate-800 text-white font-semibold transition">Dashboard</button>
          <button className="w-full text-left p-3 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition">Suppliers</button>
          <button className="w-full text-left p-3 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition">Settings</button>
        </nav>
        <button 
          onClick={handleLogout}
          className="text-left text-slate-500 text-sm hover:text-rose-400 transition mt-auto font-bold uppercase tracking-widest"
        >
          Sign Out
        </button>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-12 overflow-auto">
        <header className="flex justify-between items-center mb-12">
          <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight">Executive Dashboard</h2>
          <div className="w-12 h-12 bg-white rounded-xl shadow-lg border border-slate-100 flex items-center justify-center text-slate-900 font-bold ring-4 ring-slate-100">AD</div>
        </header>

        {/* Minimalist Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
          {[
            { label: 'Total Assessments', value: '0', color: 'slate' },
            { label: 'Trust Rating', value: 'N/A', color: 'blue' },
            { label: 'Active Monitors', value: '0', color: 'emerald' },
            { label: 'System Status', value: 'Nominal', color: 'indigo' }
          ].map((stat, i) => (
            <div key={i} className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition">
              <p className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-3">{stat.label}</p>
              <h4 className={`text-3xl font-black text-slate-900 tracking-tighter`}>{stat.value}</h4>
            </div>
          ))}
        </div>

        <div className="bg-white p-24 rounded-3xl border border-slate-200 flex flex-col items-center justify-center text-center shadow-xl shadow-slate-200/50">
          <div className="w-20 h-20 bg-slate-50 rounded-2xl flex items-center justify-center text-3xl mb-8 border border-slate-100 shadow-inner">⚡</div>
          <h3 className="text-2xl font-black text-slate-900 tracking-tight">Backend Successfully Integrated</h3>
          <p className="text-slate-500 mt-4 max-w-sm leading-relaxed font-medium">
            Your PostgreSQL-backed FastAPI prototype is active. Authentication is now handled via professional JWT flow.
          </p>
          <div className="mt-10 flex gap-4">
            <button className="bg-slate-900 text-white px-8 py-3 rounded-xl font-bold hover:bg-slate-800 transition shadow-xl shadow-slate-200">
              Run Assessment
            </button>
            <button className="bg-white text-slate-900 px-8 py-3 rounded-xl font-bold border border-slate-200 hover:bg-slate-50 transition">
              Export Report
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};
