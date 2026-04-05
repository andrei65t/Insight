import React, { useEffect, useState } from 'react';
import { api, type CompanyCandidate, type TrackedCompany } from '../lib/api';

const normalizeCompanyName = (value: string) => value.trim().toLowerCase();

export const DashboardView: React.FC = () => {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [candidates, setCandidates] = useState<CompanyCandidate[]>([]);
  const [tracked, setTracked] = useState<TrackedCompany[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [savingCandidateKeys, setSavingCandidateKeys] = useState<Set<string>>(new Set());
  const [deletingTrackedKeys, setDeletingTrackedKeys] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const handleLogout = () => {
    api.logout();
    window.location.href = '/login';
  };

  const loadTrackedCompanies = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const items = await api.getTrackedCompanies();
      setTracked(items);
    } catch {
      setError('Nu am putut încărca companiile urmărite.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTrackedCompanies();
  }, []);

  const handleSearchCompanies = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = search.trim();
    if (!name) return;

    setIsSearching(true);
    setError(null);
    try {
      const items = await api.searchCompanyCandidates(name);
      setCandidates(items);
    } catch {
      setError('Nu am putut căuta candidații pentru companie.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleTrackCompany = async (companyName: string, candidateKey: string) => {
    const name = companyName.trim();
    if (!name) return;

    setSavingCandidateKeys((prev) => {
      const next = new Set(prev);
      next.add(candidateKey);
      return next;
    });
    setError(null);
    try {
      const item = await api.trackCompany(name);
      setTracked((prev) => {
        const exists = prev.some((x) => normalizeCompanyName(x.company_name) === normalizeCompanyName(item.company_name));
        if (exists) return prev;
        return [item, ...prev];
      });
      setCandidates((prev) => prev.filter((candidate) => normalizeCompanyName(candidate.name) !== normalizeCompanyName(item.company_name)));
    } catch {
      setError('Nu am putut salva compania în tracked list.');
    } finally {
      setSavingCandidateKeys((prev) => {
        const next = new Set(prev);
        next.delete(candidateKey);
        return next;
      });
    }
  };

  const handleDeleteTrackedCompany = async (companyName: string, trackedKey: string) => {
    setDeletingTrackedKeys((prev) => {
      const next = new Set(prev);
      next.add(trackedKey);
      return next;
    });
    setError(null);
    try {
      await api.deleteTrackedCompany(companyName);
      setTracked((prev) => prev.filter((x) => x.company_name.toLowerCase() !== companyName.toLowerCase()));
    } catch {
      setError('Nu am putut șterge compania din tracked list.');
    } finally {
      setDeletingTrackedKeys((prev) => {
        const next = new Set(prev);
        next.delete(trackedKey);
        return next;
      });
    }
  };

  const handleOpenDetails = (companyName: string) => {
    const encodedName = encodeURIComponent(companyName);
    window.history.pushState({}, '', `/dashboard?company=${encodedName}`);
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans">
      <aside className="w-64 bg-slate-900 flex flex-col p-6 shadow-xl">
        <h1 className="text-xl font-extrabold text-white mb-10 tracking-tighter">TRUSTSCOPE</h1>
        <nav className="flex-1 space-y-1">
          <button className="w-full text-left p-3 rounded-lg bg-slate-800 text-white font-semibold transition">Dashboard</button>
        </nav>

        <div className="mt-auto rounded-xl border border-slate-700 bg-slate-800/70 p-4">
          <p className="text-[11px] uppercase tracking-widest text-slate-400 font-bold">Session</p>
          <p className="text-sm text-slate-200 mt-1">You are currently authenticated.</p>
          <button
            onClick={() => setConfirmOpen(true)}
            className="mt-3 w-full rounded-md bg-rose-600 px-3 py-2 text-sm font-semibold text-white hover:bg-rose-500 transition"
          >
            Sign Out
          </button>
        </div>
      </aside>

      <main className="flex-1 p-12 overflow-auto">
        <header className="mb-8">
          <h2 className="text-4xl font-extrabold text-slate-900 tracking-tight">Company Tracking Dashboard</h2>
          <p className="text-slate-500 mt-2">Caută o firmă și adaug-o în lista de companii urmărite.</p>
        </header>

        <section className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-8">
          <form onSubmit={handleSearchCompanies} className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              placeholder="Ex: NVIDIA, Tesla, Microsoft"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={isSearching}
              className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
            >
              {isSearching ? 'Searching...' : 'Search Company'}
            </button>
          </form>
        </section>

        <section className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-slate-900">Search Results</h3>
            {isSearching && <span className="text-sm text-slate-500">Searching...</span>}
          </div>

          {candidates.filter((candidate) => !tracked.some((item) => normalizeCompanyName(item.company_name) === normalizeCompanyName(candidate.name))).length === 0 && !isSearching ? (
            <p className="text-sm text-slate-500">Nu există rezultate încă. Caută o companie mai sus.</p>
          ) : (
            <div className="space-y-3">
              {candidates
                .filter((candidate) => !tracked.some((item) => normalizeCompanyName(item.company_name) === normalizeCompanyName(candidate.name)))
                .map((candidate, idx) => {
                const candidateKey = `${candidate.name}-${candidate.website}-${idx}`;
                const isSavingCandidate = savingCandidateKeys.has(candidateKey);
                return (
                  <div
                    key={candidateKey}
                    className="flex flex-col gap-2 rounded-xl border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-900">{candidate.name}</p>
                      {candidate.website ? (
                        <a
                          href={candidate.website}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sm text-blue-600 hover:text-blue-500 break-all"
                        >
                          {candidate.website}
                        </a>
                      ) : (
                        <p className="text-sm text-slate-500">No website available</p>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleTrackCompany(candidate.name, candidateKey)}
                      disabled={isSavingCandidate}
                      className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
                    >
                      {isSavingCandidate ? 'Adding...' : 'Track'}
                    </button>
                  </div>
                );
                })}
            </div>
          )}
        </section>

        <section className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-slate-900">Tracked Companies</h3>
            {isLoading && <span className="text-sm text-slate-500">Loading...</span>}
          </div>

          {error && (
            <div className="mb-4 rounded-md border border-red-100 bg-red-50 p-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-500">#</th>
                  <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-500">Company</th>
                  <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-500">Tracked At</th>
                  <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {tracked.length === 0 && !isLoading ? (
                  <tr>
                    <td colSpan={4} className="py-6 text-sm text-slate-500">
                      Nu ai companii urmărite încă.
                    </td>
                  </tr>
                ) : (
                  tracked.map((item, idx) => {
                    const trackedKey = `${item.id ?? 'na'}-${item.company_name}`;
                    const isDeleting = deletingTrackedKeys.has(trackedKey);
                    return (
                      <tr key={item.id ?? `${item.company_name}-${idx}`} className="border-b border-slate-100">
                        <td className="py-3 text-sm text-slate-600">{idx + 1}</td>
                        <td className="py-3 text-sm font-medium text-slate-900">{item.company_name}</td>
                        <td className="py-3 text-sm text-slate-600">
                          {item.created_at ? new Date(item.created_at).toLocaleString() : '-'}
                        </td>
                        <td className="py-3 text-sm text-slate-600">
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => handleOpenDetails(item.company_name)}
                              className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                            >
                              Details
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteTrackedCompany(item.company_name, trackedKey)}
                              disabled={isDeleting}
                              className="rounded-md bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-500 disabled:opacity-60"
                            >
                              {isDeleting ? 'Deleting...' : 'Delete'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      {confirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
          <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900">Sign out?</h3>
            <p className="mt-2 text-sm text-slate-600">You will be redirected to the login page.</p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setConfirmOpen(false)}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleLogout}
                className="rounded-md bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-500"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
