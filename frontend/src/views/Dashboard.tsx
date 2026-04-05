import React, { useEffect, useState } from 'react';
import { api, type CompanyCandidate, type TrackedCompany } from '../lib/api';

const normalizeCompanyName = (value: string) => value.trim().toLowerCase();

type TransferFx = {
  id: number;
  companyName: string;
  startX: number;
  startY: number;
  deltaX: number;
  deltaY: number;
};

export const DashboardView: React.FC = () => {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [lastSearchTerm, setLastSearchTerm] = useState('');
  const [candidates, setCandidates] = useState<CompanyCandidate[]>([]);
  const [tracked, setTracked] = useState<TrackedCompany[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [savingCandidateKeys, setSavingCandidateKeys] = useState<Set<string>>(new Set());
  const [deletingTrackedKeys, setDeletingTrackedKeys] = useState<Set<string>>(new Set());
  const [recentlyTrackedNames, setRecentlyTrackedNames] = useState<Set<string>>(new Set());
  const [transferFx, setTransferFx] = useState<TransferFx | null>(null);
  const [trackedPulse, setTrackedPulse] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const trackedSectionRef = React.useRef<HTMLElement | null>(null);

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

  const triggerTrackedHighlight = (companyName: string) => {
    const normalized = normalizeCompanyName(companyName);
    setRecentlyTrackedNames((prev) => {
      const next = new Set(prev);
      next.add(normalized);
      return next;
    });
    window.setTimeout(() => {
      setRecentlyTrackedNames((prev) => {
        const next = new Set(prev);
        next.delete(normalized);
        return next;
      });
    }, 1600);

    setTrackedPulse(true);
    window.setTimeout(() => {
      setTrackedPulse(false);
    }, 1150);
  };

  const triggerTransferFx = (companyName: string, sourceButton: HTMLButtonElement | null) => {
    if (!sourceButton || !trackedSectionRef.current) return;
    const sourceRect = sourceButton.getBoundingClientRect();
    const targetRect = trackedSectionRef.current.getBoundingClientRect();

    const startX = sourceRect.left + sourceRect.width / 2;
    const startY = sourceRect.top + sourceRect.height / 2;
    const targetX = targetRect.left + Math.min(targetRect.width * 0.26, 320);
    const targetY = targetRect.top + 90;

    setTransferFx({
      id: Date.now(),
      companyName,
      startX,
      startY,
      deltaX: targetX - startX,
      deltaY: targetY - startY,
    });

    window.setTimeout(() => {
      setTransferFx(null);
    }, 1450);
  };

  const handleSearchCompanies = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = search.trim();
    if (!name) return;

    setIsSearching(true);
    setError(null);
    setLastSearchTerm(name);
    try {
      const items = await api.searchCompanyCandidates(name);
      setCandidates(items);
    } catch {
      setError('Nu am putut căuta candidații pentru companie.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleTrackCompany = async (companyName: string, candidateKey: string, sourceButton: HTMLButtonElement | null) => {
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
      let wasAdded = false;
      setTracked((prev) => {
        const exists = prev.some((x) => normalizeCompanyName(x.company_name) === normalizeCompanyName(item.company_name));
        if (exists) return prev;
        wasAdded = true;
        return [item, ...prev];
      });
      setCandidates((prev) => prev.filter((candidate) => normalizeCompanyName(candidate.name) !== normalizeCompanyName(item.company_name)));
      if (wasAdded) {
        triggerTransferFx(item.company_name, sourceButton);
        triggerTrackedHighlight(item.company_name);
      }
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

  const availableCandidates = candidates.filter(
    (candidate) => !tracked.some((item) => normalizeCompanyName(item.company_name) === normalizeCompanyName(candidate.name)),
  );
  const allSearchMatchesTracked = candidates.length > 0 && availableCandidates.length === 0;

  return (
    <div className="relative flex h-screen overflow-hidden bg-[#d7e5ff] font-sans">
      <div className="pointer-events-none absolute inset-0">
        <div className="ocean-glow ocean-glow-left" />
        <div className="ocean-glow ocean-glow-right" />
        <div className="ocean-glow ocean-glow-warm" />
        <div className="midnight-veil midnight-veil-top" />
        <div className="midnight-veil midnight-veil-right" />
      </div>

      <aside className="relative z-10 w-64 bg-[#002159] border-r border-[#0b3f93] flex flex-col p-6 shadow-2xl">
        <h1 className="font-display text-[2rem] leading-none text-[#f8fbff] mb-10 tracking-tight">Insight</h1>
        <nav className="flex-1 space-y-1">
          <button className="interactive-btn w-full text-left p-3 rounded-lg bg-[#003DA5] text-white font-semibold transition">Dashboard</button>
        </nav>

        <div className="mt-auto rounded-xl border border-[#2f5dad] bg-[#0a2f73] p-4">
          <p className="text-[11px] uppercase tracking-widest text-[#8fb4ff] font-bold">Session</p>
          <p className="text-sm text-[#dce9ff] mt-1">You are currently authenticated.</p>
          <button
            onClick={() => setConfirmOpen(true)}
            className="interactive-btn mt-3 w-full rounded-md bg-[#F29800] px-3 py-2 text-sm font-semibold text-[#1f1300] hover:bg-[#d88900] transition"
          >
            Sign Out
          </button>
        </div>
      </aside>

      <main className="relative z-10 flex-1 p-12 overflow-auto">
        <header className="mb-8 animate-fade-in-up">
          <h2 className="font-display text-4xl font-extrabold text-[#00163d] tracking-tight">Company Tracking Dashboard</h2>
          <p className="text-[#003DA5] mt-2 font-semibold">Find a company and add it to your tracked companies list.</p>
        </header>

        <section className="glass-panel animate-fade-in-up rounded-2xl p-6 shadow-sm mb-8" style={{ animationDelay: '80ms' }}>
          <form onSubmit={handleSearchCompanies} className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              placeholder="Ex: NVIDIA, Tesla, Microsoft"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 rounded-xl border border-[#bfd2ff] px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-[#0059F2] focus:border-[#0059F2]"
            />
            <button
              type="submit"
              disabled={isSearching}
              className="interactive-btn rounded-xl bg-[#0059F2] px-5 py-3 text-sm font-semibold text-white hover:bg-[#003DA5] disabled:opacity-60"
            >
              {isSearching ? 'Searching...' : 'Search Company'}
            </button>
          </form>
        </section>

        <section className="glass-panel animate-fade-in-up rounded-2xl p-6 shadow-sm mb-8" style={{ animationDelay: '160ms' }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-lg font-bold text-[#00163d]">Search Results</h3>
            {isSearching && <span className="text-sm text-[#0059F2] font-semibold">Searching...</span>}
          </div>

          {availableCandidates.length === 0 && !isSearching ? (
            allSearchMatchesTracked ? (
              <div className="rounded-lg border border-[#cfe0ff] bg-[linear-gradient(135deg,rgba(0,89,242,0.10),rgba(242,152,0,0.14))] px-4 py-3 text-sm text-[#002159]">
                Great. All matches for <span className="font-bold">{lastSearchTerm}</span> are already in Tracked Companies.
              </div>
            ) : (
              <p className="text-sm text-[#003DA5]">No results yet. Search for a company above.</p>
            )
          ) : (
            <div className="space-y-3">
              {availableCandidates.map((candidate, idx) => {
                const candidateKey = `${candidate.name}-${candidate.website}-${idx}`;
                const isSavingCandidate = savingCandidateKeys.has(candidateKey);
                return (
                  <div
                    key={candidateKey}
                    className="animate-fade-in-up flex flex-col gap-2 rounded-xl border border-[#b9d0ff] bg-[linear-gradient(135deg,rgba(255,255,255,0.80),rgba(241,247,255,0.70))] p-4 sm:flex-row sm:items-center sm:justify-between"
                    style={{ animationDelay: `${220 + idx * 35}ms` }}
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[#00163d]">{candidate.name}</p>
                      {candidate.website ? (
                        <a
                          href={candidate.website}
                          target="_blank"
                          rel="noreferrer"
                          className="text-sm text-[#0059F2] hover:text-[#003DA5] break-all"
                        >
                          {candidate.website}
                        </a>
                      ) : (
                        <p className="text-sm text-[#4d6791]">No website available</p>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={(e) => handleTrackCompany(candidate.name, candidateKey, e.currentTarget)}
                      disabled={isSavingCandidate}
                      className="interactive-btn rounded-lg bg-[#0059F2] px-4 py-2 text-sm font-semibold text-white hover:bg-[#003DA5] disabled:opacity-60"
                    >
                      {isSavingCandidate ? 'Adding...' : 'Track'}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <section
          ref={trackedSectionRef}
          className={`glass-panel animate-fade-in-up rounded-2xl p-6 shadow-sm ${trackedPulse ? 'tracked-panel-pulse' : ''}`}
          style={{ animationDelay: '240ms' }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-lg font-bold text-[#00163d]">Tracked Companies</h3>
            {isLoading && <span className="text-sm text-[#0059F2] font-semibold">Loading...</span>}
          </div>

          {error && (
            <div className="mb-4 rounded-md border border-[#f6d7aa] bg-[#fff6e8] p-3 text-sm text-[#8f5600]">
              {error}
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse">
              <thead>
                <tr className="border-b border-[#dbe6ff]">
                  <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-[#4d6791]">#</th>
                  <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-[#4d6791]">Company</th>
                  <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-[#4d6791]">Tracked At</th>
                  <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-[#4d6791]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {tracked.length === 0 && !isLoading ? (
                  <tr>
                    <td colSpan={4} className="py-6 text-sm text-[#4d6791]">
                      Nu ai companii urmărite încă.
                    </td>
                  </tr>
                ) : (
                  tracked.map((item, idx) => {
                    const trackedKey = `${item.id ?? 'na'}-${item.company_name}`;
                    const isDeleting = deletingTrackedKeys.has(trackedKey);
                    const isRecentlyTracked = recentlyTrackedNames.has(normalizeCompanyName(item.company_name));
                    return (
                      <tr
                        key={item.id ?? `${item.company_name}-${idx}`}
                        className={`border-b border-[#e5ecff] ${isRecentlyTracked ? 'tracked-row-flash' : ''}`}
                      >
                        <td className="py-3 text-sm text-[#395581]">{idx + 1}</td>
                        <td className="py-3 text-sm font-medium text-[#00163d]">{item.company_name}</td>
                        <td className="py-3 text-sm text-[#395581]">
                          {item.created_at ? new Date(item.created_at).toLocaleString() : '-'}
                        </td>
                        <td className="py-3 text-sm text-[#395581]">
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => handleOpenDetails(item.company_name)}
                              className="interactive-btn rounded-md border border-[#b7ccff] px-3 py-1.5 text-xs font-semibold text-[#003DA5] hover:bg-[#edf3ff]"
                            >
                              Details
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteTrackedCompany(item.company_name, trackedKey)}
                              disabled={isDeleting}
                              className="interactive-btn rounded-md bg-[#A56800] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#8b5600] disabled:opacity-60"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#00122f]/45 p-4">
          <div className="w-full max-w-sm rounded-xl border border-[#d7e2ff] bg-white p-6 shadow-2xl animate-fade-in-up">
            <h3 className="font-display text-lg font-bold text-[#00163d]">Sign out?</h3>
            <p className="mt-2 text-sm text-[#395581]">You will be redirected to the login page.</p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setConfirmOpen(false)}
                className="interactive-btn rounded-md border border-[#b7ccff] px-4 py-2 text-sm font-semibold text-[#003DA5] hover:bg-[#edf3ff]"
              >
                Cancel
              </button>
              <button
                onClick={handleLogout}
                className="interactive-btn rounded-md bg-[#A56800] px-4 py-2 text-sm font-semibold text-white hover:bg-[#8b5600]"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}

      {transferFx && (
        <div
          className="company-transfer-chip"
          style={{
            left: `${transferFx.startX}px`,
            top: `${transferFx.startY}px`,
            ['--dx' as string]: `${transferFx.deltaX}px`,
            ['--dy' as string]: `${transferFx.deltaY}px`,
          } as React.CSSProperties}
        >
          + {transferFx.companyName}
        </div>
      )}

      {transferFx && (
        <div
          className="company-transfer-trail"
          style={{
            left: `${transferFx.startX}px`,
            top: `${transferFx.startY}px`,
            ['--dx' as string]: `${transferFx.deltaX}px`,
            ['--dy' as string]: `${transferFx.deltaY}px`,
          } as React.CSSProperties}
        />
      )}
    </div>
  );
};
