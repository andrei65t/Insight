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
          setError('Nu am putut incarca detaliile companiei.');
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

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-10">
      <div className="mx-auto max-w-7xl">
        <button
          type="button"
          onClick={goBack}
          className="mb-6 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
        >
          Back to Dashboard
        </button>

        <header className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Company Dashboard</p>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900">{companyName}</h1>
          {summary?.latest_date && (
            <p className="mt-2 text-sm text-slate-500">Ultima stire: {new Date(summary.latest_date).toLocaleDateString()}</p>
          )}
        </header>

        <section className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Total News</p>
            <p className="mt-2 text-3xl font-extrabold text-slate-900">{summary?.total_news ?? 0}</p>
          </div>
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-wider text-emerald-700">Factual</p>
            <p className="mt-2 text-3xl font-extrabold text-emerald-900">{summary?.factual_count ?? 0}</p>
          </div>
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-wider text-amber-700">Opinion</p>
            <p className="mt-2 text-3xl font-extrabold text-amber-900">{summary?.opinion_count ?? 0}</p>
          </div>
          <div className="rounded-xl border border-sky-200 bg-sky-50 p-5 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-wider text-sky-700">Inference</p>
            <p className="mt-2 text-3xl font-extrabold text-sky-900">{summary?.inference_count ?? 0}</p>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">News from Database</h2>
            {showLoadingState && (
              <span className="text-sm text-slate-500">{isRetrying ? 'Actualizam datele...' : 'Loading...'}</span>
            )}
          </div>

          {showLoadingState ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              Colectam datele companiei. Daca dureaza prea mult, poti reincarca manual.
            </div>
          ) : error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <p>{error}</p>
              <button
                type="button"
                onClick={reloadDetails}
                className="mt-3 rounded-md border border-red-300 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100"
              >
                Reincarca
              </button>
            </div>
          ) : news.length === 0 ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              <p>Nu exista inca stiri in baza de date pentru aceasta companie.</p>
              <button
                type="button"
                onClick={reloadDetails}
                className="mt-3 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
              >
                Reincarca
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-500">Title</th>
                    <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-500">Source</th>
                    <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-500">Date</th>
                    <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-500">Fact Label</th>
                    <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-500">Link</th>
                  </tr>
                </thead>
                <tbody>
                  {news.map((item) => (
                    <tr key={item.id} className="border-b border-slate-100">
                      <td className="py-3 text-sm text-slate-900">{item.title}</td>
                      <td className="py-3 text-sm text-slate-700">{item.source}</td>
                      <td className="py-3 text-sm text-slate-700">
                        {item.date ? new Date(item.date).toLocaleDateString() : '-'}
                      </td>
                      <td className="py-3 text-sm font-semibold text-slate-800">{item.fact_label}</td>
                      <td className="py-3 text-sm">
                        <a
                          href={item.link}
                          target="_blank"
                          rel="noreferrer"
                          className="text-blue-600 hover:text-blue-500"
                        >
                          Open
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
