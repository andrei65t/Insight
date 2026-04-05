import React, { useEffect, useState } from 'react';
import { api, type CompanyCandidate, type TrackedCompany } from '../lib/api';
import appLogo from '../assets/file.svg';

const normalizeCompanyName = (value: string) => value.trim().toLowerCase();
const AVATAR_STORAGE_KEY = 'dashboard_avatar_image';

const decodeJwtPayload = (token: string): Record<string, unknown> | null => {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;
    const normalized = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=');
    const parsed = JSON.parse(atob(padded));
    if (!parsed || typeof parsed !== 'object') return null;
    return parsed as Record<string, unknown>;
  } catch {
    return null;
  }
};

const displayNameFromToken = (token: string | null): string => {
  if (!token) return 'User';
  const payload = decodeJwtPayload(token);
  if (!payload) return 'User';

  const fullName = payload.full_name;
  if (typeof fullName === 'string' && fullName.trim()) {
    return fullName.trim();
  }

  const username = payload.username;
  if (typeof username === 'string' && username.trim()) {
    return username.trim();
  }

  const email = payload.email;
  if (typeof email === 'string' && email.trim()) {
    const localPart = email.split('@')[0] || '';
    if (localPart) {
      return localPart.charAt(0).toUpperCase() + localPart.slice(1);
    }
  }

  return 'User';
};

type TransferFx = {
  id: number;
  companyName: string;
  startX: number;
  startY: number;
  deltaX: number;
  deltaY: number;
};

export const DashboardView: React.FC = () => {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isOptionsOpen, setIsOptionsOpen] = useState(false);
  const [isEditProfileOpen, setIsEditProfileOpen] = useState(false);
  const [userDisplayName, setUserDisplayName] = useState('User');
  const [avatarImage, setAvatarImage] = useState<string | null>(null);
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
  const [retryAttempts, setRetryAttempts] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const trackedSectionRef = React.useRef<HTMLElement | null>(null);
  const userMenuRef = React.useRef<HTMLDivElement | null>(null);
  const avatarInputRef = React.useRef<HTMLInputElement | null>(null);

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

  useEffect(() => {
    const displayName = displayNameFromToken(api.getToken());
    setUserDisplayName(displayName);

    const savedAvatar = localStorage.getItem(AVATAR_STORAGE_KEY);
    if (savedAvatar) {
      setAvatarImage(savedAvatar);
    }
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!userMenuRef.current) return;
      if (!userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
        setIsOptionsOpen(false);
        setIsEditProfileOpen(false);
      }
    };

    window.addEventListener('mousedown', handleClickOutside);
    return () => {
      window.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleAvatarFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === 'string' ? reader.result : null;
      if (!result) return;
      setAvatarImage(result);
      localStorage.setItem(AVATAR_STORAGE_KEY, result);
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  const handleToggleUserMenu = () => {
    setIsUserMenuOpen((prev) => !prev);
    setIsOptionsOpen(false);
    setIsEditProfileOpen(false);
  };

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

  const runCompanySearch = async (name: string): Promise<CompanyCandidate[] | null> => {
    setIsSearching(true);
    setError(null);
    setLastSearchTerm(name);
    try {
      const items = await api.searchCompanyCandidates(name);
      setCandidates(items);
      return items;
    } catch {
      setError('Nu am putut căuta candidații pentru companie.');
      return null;
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchCompanies = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = search.trim();
    if (!name) return;
    setRetryAttempts(0);
    await runCompanySearch(name);
  };

  const handleRetrySearch = async () => {
    const name = lastSearchTerm.trim();
    if (!name || isSearching || retryAttempts >= 3) return;
    const items = await runCompanySearch(name);
    if (!items) return;
    if (items.length === 0) {
      setRetryAttempts((prev) => Math.min(prev + 1, 3));
      return;
    }
    setRetryAttempts(0);
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
  const retryLimitReached = retryAttempts >= 3;
  const showRetrySearch = !isSearching && lastSearchTerm.trim().length > 0 && candidates.length === 0 && !retryLimitReached;

  return (
    <div className="relative flex h-screen overflow-hidden bg-transparent font-sans">
      <div className="pointer-events-none absolute inset-0">
        <div className="ocean-glow ocean-glow-left" />
        <div className="ocean-glow ocean-glow-right" />
        <div className="ocean-glow ocean-glow-warm" />
        <div className="midnight-veil midnight-veil-top" />
        <div className="midnight-veil midnight-veil-right" />
      </div>

      <aside className="sidebar-shell relative z-10 m-3 flex w-44 flex-col rounded-[42px] p-4">
        <div className="sidebar-shell-overlay pointer-events-none absolute inset-0 rounded-[42px]" />
        <div className="sidebar-accent sidebar-accent-blue pointer-events-none absolute" />
        <div className="sidebar-accent sidebar-accent-amber pointer-events-none absolute" />
        <div className="sidebar-accent-line pointer-events-none absolute" />
        <div className="relative z-10 mb-8 -mx-2">
          <img
            src={appLogo}
            alt="Insight"
            className="h-auto w-[calc(100%+1rem)] max-w-none -translate-x-1"
          />
        </div>
        <div className="flex-1" />

        <div ref={userMenuRef} className="absolute bottom-7 left-1/2 z-20 -translate-x-1/2">
          <input
            ref={avatarInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleAvatarFileChange}
          />

          {isUserMenuOpen && (
            <div className="absolute bottom-[4.7rem] left-1/2 z-50 w-48 -translate-x-1/2 rounded-2xl border border-[#b7ccff] bg-white p-4 shadow-xl">
              {!isEditProfileOpen && (
                <>
                  <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-[#4d6791]">Session</p>
                  <p className="mt-2 text-sm text-[#1d3866]">You are currently authenticated.</p>
                </>
              )}

              {!isOptionsOpen ? (
                <button
                  type="button"
                  onClick={() => {
                    setIsOptionsOpen(true);
                    setIsEditProfileOpen(false);
                  }}
                  className="interactive-btn mt-4 w-full rounded-md border border-[#b7ccff] bg-[#edf3ff] px-3 py-2 text-sm font-semibold text-[#003DA5] hover:bg-[#dfeaff]"
                >
                  Options
                </button>
              ) : isEditProfileOpen ? (
                <div>
                  <button
                    type="button"
                    onClick={() => avatarInputRef.current?.click()}
                    className="interactive-btn w-full rounded-md border border-[#b7ccff] bg-white px-3 py-2 text-sm font-semibold text-[#1d3866] hover:bg-[#f3f7ff]"
                  >
                    Edit Profile Photo
                  </button>
                </div>
              ) : (
                <div className="mt-4 space-y-2">
                  <button
                    type="button"
                    onClick={() => setIsEditProfileOpen(true)}
                    className="interactive-btn w-full rounded-md border border-[#b7ccff] bg-[#edf3ff] px-3 py-2 text-sm font-semibold text-[#003DA5] hover:bg-[#dfeaff]"
                  >
                    Edit Profile
                  </button>

                  <button
                    type="button"
                    onClick={handleLogout}
                    className="interactive-btn w-full rounded-md bg-[#F29800] px-3 py-2 text-sm font-semibold text-[#1f1300] hover:bg-[#d88900] transition"
                  >
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          )}

          <button
            type="button"
            onClick={handleToggleUserMenu}
            className="interactive-btn relative flex h-14 w-14 items-center justify-center overflow-hidden rounded-full border border-[#b7ccff] bg-[#eef2f7] shadow-[0_10px_25px_rgba(0,0,0,0.28)]"
          >
            {avatarImage ? (
              <img src={avatarImage} alt="User avatar" className="h-full w-full object-cover" />
            ) : (
              <span className="text-xl font-extrabold text-[#0059F2]">{userDisplayName.charAt(0).toUpperCase()}</span>
            )}
          </button>
        </div>
      </aside>

      <main className="relative z-10 flex-1 p-12 overflow-auto">
        <header className="mb-8 animate-fade-in-up">
          <h2 className="font-display text-4xl font-extrabold text-[#00163d] tracking-tight">AI Supplier Intelligence Platform</h2>
          <p className="text-[#003DA5] mt-2 font-semibold">Find a company and add it to your tracked companies list.</p>
        </header>

        <section className="glass-panel animate-fade-in-up rounded-2xl p-6 shadow-sm mb-8" style={{ animationDelay: '80ms' }}>
          <form onSubmit={handleSearchCompanies} className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              placeholder="Ex: NVIDIA, Tesla, Microsoft"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 rounded-xl border border-[#bfd2ff] bg-[#eef1f4] px-4 py-3 text-sm text-[#2c3d56] placeholder:text-[#5f718f] outline-none focus:ring-2 focus:ring-[#0059F2] focus:border-[#0059F2]"
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
              <div className="flex items-center justify-between gap-3 text-sm text-[#003DA5]">
                <p className="min-w-0 flex-1">
                  {lastSearchTerm.trim().length > 0
                    ? retryLimitReached
                      ? `Sorry, we couldn't find a company for "${lastSearchTerm}" after several attempts. Please try another name.`
                      : `No companies found for "${lastSearchTerm}".`
                    : 'No results yet. Search for a company above.'}
                </p>
                {showRetrySearch && (
                  <button
                    type="button"
                    onClick={handleRetrySearch}
                    className="retry-action-btn"
                  >
                    Retry
                  </button>
                )}
              </div>
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
                  <th className="py-2 text-right text-xs font-bold uppercase tracking-wider text-[#4d6791]">Actions</th>
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
                          <div className="flex items-center justify-end gap-2">
                            <button
                              type="button"
                              onClick={() => handleOpenDetails(item.company_name)}
                              className="details-action-btn"
                            >
                              Details
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteTrackedCompany(item.company_name, trackedKey)}
                              disabled={isDeleting}
                              className="delete-action-btn"
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
