import React, { useEffect, useState } from 'react';
import { api, type CompanyDetails } from '../lib/api';

type Props = {
  companyName: string;
};

export const CompanyDashboardView: React.FC<Props> = ({ companyName }) => {
  const [data, setData] = useState<CompanyDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const normalizeLabel = (value: string): 'Fact' | 'Opinion' | 'Inference' => {
      const lowered = String(value || '').trim().toLowerCase();
      if (lowered.startsWith('fact') || lowered === 'factual') return 'Fact';
      if (lowered.startsWith('opinion')) return 'Opinion';
      return 'Inference';
    };

    const withFallbackSummary = (details: CompanyDetails): CompanyDetails => {
      const computed = details.news.reduce(
        (acc, row) => {
          const label = normalizeLabel(row.fact_label);
          if (label === 'Fact') acc.factual_count += 1;
          else if (label === 'Opinion') acc.opinion_count += 1;
          else acc.inference_count += 1;
          return acc;
        },
        { factual_count: 0, opinion_count: 0, inference_count: 0 }
      );

      return {
        ...details,
        summary: {
          ...details.summary,
          total_news: details.news.length,
          factual_count: computed.factual_count,
          opinion_count: computed.opinion_count,
          inference_count: computed.inference_count,
        },
      };
    };

    const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    const loadDetails = async () => {
      setIsLoading(true);
      setError(null);
      setIsRetrying(false);
      try {
        let finalData: CompanyDetails | null = null;

        for (let attempt = 0; attempt < 4; attempt++) {
          const details = withFallbackSummary(await api.getCompanyDetails(companyName));
          finalData = details;

          if (details.summary.total_news > 0 || attempt === 3) {
            break;
          }

          if (!cancelled) {
            setIsRetrying(true);
          }
          await sleep(2000);
        }

        if (!cancelled) {
          setData(finalData);
        }
      } catch {
        if (!cancelled) {
          setError('Could not load company details.');
        }
      } finally {
        if (!cancelled) {
          setIsRetrying(false);
          setIsLoading(false);
        }
      }
    };

    loadDetails();

    return () => {
      cancelled = true;
    };
  }, [companyName, reloadTick]);

  const goBack = () => {
    window.history.pushState({}, '', '/dashboard');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  const reloadDetails = () => {
    setReloadTick((prev: number) => prev + 1);
  };

  const summary = data?.summary;
  const news = data?.news ?? [];

  const showLoadingState = isLoading || isRetrying;

  const getLabelTheme = (label: string) => {
    const lowered = (label || '').toLowerCase();
    if (lowered.startsWith('fact')) {
      return {
        row: 'border-l-2 border-l-[#4c8fff]',
        pill: 'bg-[linear-gradient(135deg,#eaf3ff,#d4e7ff)] text-[#003DA5] border-[#8fb7ff] shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]',
      };
    }
    if (lowered.startsWith('opinion')) {
      return {
        row: 'border-l-2 border-l-[#f1a426]',
        pill: 'bg-[linear-gradient(135deg,#fff3de,#ffe1ae)] text-[#8f5600] border-[#eeb968] shadow-[inset_0_1px_0_rgba(255,255,255,0.72)]',
      };
    }
    return {
      row: 'border-l-2 border-l-[#002159]',
      pill: 'bg-[linear-gradient(135deg,#e2edff,#cadfff)] text-[#002159] border-[#9fbeff] shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]',
    };
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#d7e5ff] p-6 md:p-10">
      <div className="pointer-events-none absolute inset-0">
        <div className="ocean-glow ocean-glow-left" />
        <div className="ocean-glow ocean-glow-right" />
        <div className="ocean-glow ocean-glow-warm" />
        <div className="midnight-veil midnight-veil-top" />
        <div className="midnight-veil midnight-veil-right" />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl">
        <button
          type="button"
          onClick={goBack}
          className="interactive-btn mb-6 rounded-md border border-[#9dbdff] bg-[linear-gradient(120deg,rgba(255,255,255,0.88),rgba(232,243,255,0.88))] px-4 py-2 text-sm font-semibold text-[#002159] hover:bg-[#edf4ff]"
        >
          Back to Dashboard
        </button>

        <header className="glass-panel mb-8 rounded-2xl p-6 shadow-sm animate-fade-in-up">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="inline-flex rounded-full border border-[#9cbcff] bg-[linear-gradient(120deg,#ecf4ff,#dbe9ff)] px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.15em] text-[#003DA5]">Company Dashboard</span>
            <span className="inline-flex rounded-full border border-[#f2be6d] bg-[linear-gradient(120deg,#fff2dc,#ffe4b6)] px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.15em] text-[#8f5600]">Insight Lens</span>
            <span className="inline-flex rounded-full border border-[#9db8ea] bg-[linear-gradient(120deg,#e9efff,#dae4ff)] px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.15em] text-[#002159]">Signals</span>
          </div>
          <h1 className="font-display mt-2 text-3xl font-extrabold tracking-tight text-[#00163d]">
            <span className="bg-[linear-gradient(110deg,#00163d_0%,#003DA5_52%,#A56800_100%)] bg-clip-text text-transparent">{companyName}</span>
          </h1>
          {summary?.latest_date && (
            <p className="mt-2 text-sm text-[#003DA5]">Latest article: {new Date(summary.latest_date).toLocaleDateString()}</p>
          )}
        </header>

        <section className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="glass-panel rounded-xl p-5 shadow-sm animate-fade-in-up" style={{ animationDelay: '70ms' }}>
            <p className="text-xs font-bold uppercase tracking-wider text-[#3d6398]">Total News</p>
            <p className="mt-2 text-3xl font-extrabold text-[#00163d]">{summary?.total_news ?? 0}</p>
          </div>
          <div className="rounded-xl border p-5 shadow-sm animate-fade-in-up border-[#67a8ff]/70 bg-[linear-gradient(135deg,rgba(0,89,242,0.30),rgba(0,61,165,0.16))]" style={{ animationDelay: '110ms' }}>
            <p className="text-xs font-bold uppercase tracking-wider text-[#004bc7]">Factual</p>
            <p className="mt-2 text-3xl font-extrabold text-[#002159]">{summary?.factual_count ?? 0}</p>
          </div>
          <div className="rounded-xl border p-5 shadow-sm animate-fade-in-up border-[#f2b04d]/80 bg-[linear-gradient(135deg,rgba(242,152,0,0.30),rgba(255,227,170,0.28))]" style={{ animationDelay: '150ms' }}>
            <p className="text-xs font-bold uppercase tracking-wider text-[#a56800]">Opinion</p>
            <p className="mt-2 text-3xl font-extrabold text-[#6f4300]">{summary?.opinion_count ?? 0}</p>
          </div>
          <div className="rounded-xl border p-5 shadow-sm animate-fade-in-up border-[#7da2f5]/75 bg-[linear-gradient(135deg,rgba(0,33,89,0.42),rgba(0,89,242,0.14))]" style={{ animationDelay: '190ms' }}>
            <p className="text-xs font-bold uppercase tracking-wider text-[#dbe8ff]">Inference</p>
            <p className="mt-2 text-3xl font-extrabold text-white">{summary?.inference_count ?? 0}</p>
          </div>
        </section>

        <section className="glass-panel rounded-2xl p-6 shadow-sm animate-fade-in-up" style={{ animationDelay: '230ms' }}>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-lg font-bold text-[#00163d]">News from Database</h2>
            {showLoadingState && (
              <span className="text-sm text-[#0059F2] font-semibold">{isRetrying ? 'Refreshing data...' : 'Loading...'}</span>
            )}
          </div>

          {showLoadingState ? (
            <div className="rounded-lg border border-[#bfd2ff] bg-[linear-gradient(130deg,rgba(255,255,255,0.8),rgba(228,240,255,0.7))] p-4 text-sm text-[#274d85]">
              We are collecting company data. If it takes too long, you can reload manually.
            </div>
          ) : error ? (
            <div className="rounded-lg border border-[#f6d7aa] bg-[#fff6e8] p-4 text-sm text-[#8f5600]">
              <p>{error}</p>
              <button
                type="button"
                onClick={reloadDetails}
                className="interactive-btn mt-3 rounded-md border border-[#f2c47e] bg-white px-3 py-1.5 text-xs font-semibold text-[#8f5600] hover:bg-[#fff1d8]"
              >
                Reload
              </button>
            </div>
          ) : news.length === 0 ? (
            <div className="rounded-lg border border-[#bfd2ff] bg-[linear-gradient(130deg,rgba(255,255,255,0.8),rgba(228,240,255,0.7))] p-4 text-sm text-[#274d85]">
              <p>There are no articles in the database for this company yet.</p>
              <button
                type="button"
                onClick={reloadDetails}
                className="interactive-btn mt-3 rounded-md border border-[#9dbdff] bg-white px-3 py-1.5 text-xs font-semibold text-[#003DA5] hover:bg-[#e8f1ff]"
              >
                Reload
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse">
                <thead>
                  <tr className="border-b border-[#c2d6ff]">
                    <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-[#45689a]">Title</th>
                    <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-[#45689a]">Source</th>
                    <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-[#45689a]">Date</th>
                    <th className="py-2 text-center text-xs font-bold uppercase tracking-wider text-[#45689a]">Fact Label</th>
                    <th className="py-2 text-center text-xs font-bold uppercase tracking-wider text-[#45689a]">Link</th>
                  </tr>
                </thead>
                <tbody>
                  {news.map((item) => {
                    const theme = getLabelTheme(item.fact_label);
                    return (
                      <tr key={item.id} className={`border-b border-[#d8e4ff] transition-colors hover:bg-[#eef4ff]/55 ${theme.row}`}>
                        <td className="py-3 text-sm text-[#00163d]">{item.title}</td>
                        <td className="py-3 text-sm text-[#274d85]">{item.source}</td>
                        <td className="py-3 text-sm text-[#274d85]">
                          {item.date ? new Date(item.date).toLocaleDateString() : '-'}
                        </td>
                        <td className="py-3 text-center text-sm font-semibold align-middle">
                          <span className={`inline-flex min-w-[104px] items-center justify-center rounded-full border px-2.5 py-1 text-xs font-bold ${theme.pill}`}>
                            {item.fact_label}
                          </span>
                        </td>
                        <td className="py-3 text-center text-sm align-middle">
                          <a
                            href={item.link}
                            target="_blank"
                            rel="noreferrer"
                            className="open-action-btn"
                          >
                            <span>Open</span>
                            <span aria-hidden="true" className="open-action-btn-icon">↗</span>
                          </a>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
