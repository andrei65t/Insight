import React, { useEffect, useState, useRef } from 'react';
import { api, type CompanyDetails } from '../lib/api';
import { Send, Bot, User, Sparkles, X } from 'lucide-react';

type Props = {
  companyName: string;
};

type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
};

type RiskTrend = {
  deltaRiskPercentage: number;
  direction: 'up' | 'down' | 'stable';
} | null;

export const CompanyDashboardView: React.FC<Props> = ({ companyName }) => {
  const [data, setData] = useState<CompanyDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [reloadTick, setReloadTick] = useState(0);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [riskTrend, setRiskTrend] = useState<RiskTrend>(null);
  const [isEvidenceOpen, setIsEvidenceOpen] = useState(false);

  // Chat State
  const [question, setQuestion] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isAsking]);

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

  const handleAskAI = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isAsking) return;

    const userMsg = question.trim();
    setChatHistory(prev => [...prev, { role: 'user', content: userMsg }]);
    setQuestion('');
    setIsAsking(true);

    try {
      const result = await api.askAI(companyName, userMsg);
      setChatHistory(prev => [...prev, { role: 'assistant', content: result.answer }]);
    } catch (err) {
      setChatHistory(prev => [...prev, { role: 'assistant', content: 'Error: I could not get a response from AI.' }]);
    } finally {
      setIsAsking(false);
    }
  };

  const goBack = () => {
    window.history.pushState({}, '', '/dashboard');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  const reloadDetails = () => {
    setReloadTick((prev: number) => prev + 1);
  };

  const summary = data?.summary;
  const news = data?.news ?? [];
  const riskOverview = data?.risk_overview;

  useEffect(() => {
    if (!riskOverview) {
      setRiskTrend(null);
      return;
    }

    const storageKey = `company_risk_snapshot_${companyName.trim().toLowerCase()}`;
    const raw = localStorage.getItem(storageKey);

    if (raw) {
      try {
        const prev = JSON.parse(raw) as { risk_percentage?: number };
        if (typeof prev.risk_percentage === 'number') {
          const delta = riskOverview.risk_percentage - prev.risk_percentage;
          const rounded = Math.round(delta);
          const direction: 'up' | 'down' | 'stable' = rounded > 0 ? 'up' : rounded < 0 ? 'down' : 'stable';
          setRiskTrend({
            deltaRiskPercentage: rounded,
            direction,
          });
        } else {
          setRiskTrend(null);
        }
      } catch {
        setRiskTrend(null);
      }
    } else {
      setRiskTrend(null);
    }

    localStorage.setItem(
      storageKey,
      JSON.stringify({
        risk_percentage: riskOverview.risk_percentage,
        saved_at: new Date().toISOString(),
      })
    );
  }, [companyName, riskOverview]);

  const safetyTheme = (() => {
    if (!riskOverview) {
      return {
        ring: 'border-[#c8d7ea]',
        pill: 'bg-[#edf2f8] text-[#3c5578]',
        score: 'text-[#24466f]',
      };
    }
    if (riskOverview.color === 'green') {
      return {
        ring: 'border-[#8ed1ad]',
        pill: 'bg-[#e7f7ee] text-[#0f6a43]',
        score: 'text-[#0d6940]',
      };
    }
    if (riskOverview.color === 'red') {
      return {
        ring: 'border-[#f2a8a8]',
        pill: 'bg-[#ffeaea] text-[#9e2f2f]',
        score: 'text-[#9e2f2f]',
      };
    }
    return {
      ring: 'border-[#f1ce8d]',
      pill: 'bg-[#fff4de] text-[#8a5b06]',
      score: 'text-[#8a5b06]',
    };
  })();

  const showLoadingState = isLoading || isRetrying;

  return (
    <div className="company-page min-h-screen p-6 md:p-10">
      <div className="company-page-glow company-page-glow-blue" />
      <div className="company-page-glow company-page-glow-amber" />

      <div className={`company-content-shell ${isChatOpen ? 'company-content-shifted' : ''}`}>
        <button
          type="button"
          onClick={goBack}
          className="company-back-btn mb-6"
        >
          Back to Dashboard
        </button>

        <header className="company-panel mb-8 rounded-2xl p-6">
          <p className="text-sm font-semibold uppercase tracking-wide text-[#4a6287]">Company Dashboard</p>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-[#0d244d]">{companyName}</h1>
          {summary?.latest_date && (
            <p className="mt-2 text-sm text-[#566d8f]">Latest news date: {new Date(summary.latest_date).toLocaleDateString()}</p>
          )}
        </header>

        <section className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="company-metric company-metric-total rounded-xl p-5">
            <p className="text-xs font-bold uppercase tracking-wider text-[#50688d]">Total News</p>
            <p className="mt-2 text-3xl font-extrabold text-[#0f274f]">{summary?.total_news ?? 0}</p>
          </div>
          <div className="company-metric company-metric-factual rounded-xl p-5">
            <p className="text-xs font-bold uppercase tracking-wider text-[#1a6b6f]">Factual</p>
            <p className="mt-2 text-3xl font-extrabold text-[#0f4950]">{summary?.factual_count ?? 0}</p>
          </div>
          <div className="company-metric company-metric-opinion rounded-xl p-5">
            <p className="text-xs font-bold uppercase tracking-wider text-[#8a5608]">Opinion</p>
            <p className="mt-2 text-3xl font-extrabold text-[#5f3803]">{summary?.opinion_count ?? 0}</p>
          </div>
          <div className="company-metric company-metric-inference rounded-xl p-5">
            <p className="text-xs font-bold uppercase tracking-wider text-[#1f5e91]">Inference</p>
            <p className="mt-2 text-3xl font-extrabold text-[#123f68]">{summary?.inference_count ?? 0}</p>
          </div>
        </section>

        <section className="company-panel rounded-2xl p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-[#0f274f]">News from Database</h2>
            {showLoadingState && (
              <span className="text-sm text-[#567094]">{isRetrying ? 'Refreshing data...' : 'Loading...'}</span>
            )}
          </div>

          {showLoadingState ? (
            <div className="rounded-lg border border-[#c8d7ea] bg-[rgba(232,240,250,0.75)] p-4 text-sm text-[#426086]">
              Fetching company data. If this takes too long, you can reload manually.
            </div>
          ) : error ? (
            <div className="rounded-lg border border-[#f0c7a3] bg-[rgba(255,241,226,0.82)] p-4 text-sm text-[#8d4f0b]">
              <p>{error}</p>
              <button
                type="button"
                onClick={reloadDetails}
                className="company-plain-btn mt-3"
              >
                Reload
              </button>
            </div>
          ) : news.length === 0 ? (
            <div className="rounded-lg border border-[#c8d7ea] bg-[rgba(232,240,250,0.75)] p-4 text-sm text-[#426086]">
              <p>There are no news records in the database for this company yet.</p>
              <button
                type="button"
                onClick={reloadDetails}
                className="company-plain-btn mt-3"
              >
                Reload
              </button>
            </div>
          ) : (
            <div>
              <div className="company-table-wrap overflow-x-auto">
                <table className="company-table min-w-full border-collapse">
                  <thead>
                    <tr>
                      <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-[#4e688d]">Title</th>
                      <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-[#4e688d]">Source</th>
                      <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-[#4e688d]">Date</th>
                      <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-[#4e688d]">Fact Label</th>
                      <th className="py-2 text-left text-xs font-bold uppercase tracking-wider text-[#4e688d]">Link</th>
                    </tr>
                  </thead>
                  <tbody>
                    {news.map((item) => (
                      <tr key={item.id}>
                        <td className="py-3 text-sm text-[#182f54]">{item.title}</td>
                        <td className="py-3 text-sm text-[#425f84]">{item.source}</td>
                        <td className="py-3 text-sm text-[#425f84]">
                          {item.date ? new Date(item.date).toLocaleDateString() : '-'}
                        </td>
                        <td className="py-3 text-sm font-semibold text-[#233f65]">{item.fact_label}</td>
                        <td className="py-3 text-sm">
                          <a
                            href={item.link}
                            target="_blank"
                            rel="noreferrer"
                            className="company-open-link"
                          >
                            Open
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {riskOverview && (
                <section className={`mt-6 rounded-2xl border ${safetyTheme.ring} bg-[rgba(245,250,255,0.7)] p-5`}>
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.11em] text-[#5c7498]">Overall Supplier Safety</p>
                      <div className="mt-2 flex items-end gap-3">
                        <span className={`text-4xl font-extrabold leading-none ${safetyTheme.score}`}>
                          {riskOverview.safe_percentage}%
                        </span>
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${safetyTheme.pill}`}>
                          {riskOverview.status_label}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-[#4f678b]">
                        Confidence: <span className="font-semibold">{riskOverview.confidence}%</span> | Based on {summary?.total_news ?? 0} analyzed items
                      </p>
                      <p className="mt-1 text-xs text-[#5a7397]">
                        Thresholds: Safe {'>='} {riskOverview.thresholds?.safe ?? 75}% | Watchlist {'>='} {riskOverview.thresholds?.watchlist ?? 50}%
                      </p>
                      {riskTrend && (
                        <p className={`mt-1 text-xs ${riskTrend.direction === 'up' ? 'text-[#9e2f2f]' : riskTrend.direction === 'down' ? 'text-[#0f6a43]' : 'text-[#557097]'}`}>
                          Trend vs last check:{' '}
                          {riskTrend.direction === 'up'
                            ? `+${Math.abs(riskTrend.deltaRiskPercentage)}% risk (worse)`
                            : riskTrend.direction === 'down'
                              ? `-${Math.abs(riskTrend.deltaRiskPercentage)}% risk (better)`
                              : 'No change'}
                        </p>
                      )}
                      {riskOverview.risk_signal && (
                        <p className="mt-1 text-xs text-[#5a7397]">
                          Risk signal: {riskOverview.risk_signal.risk_relevant ? 'Relevant' : 'Not relevant'} | Category: {riskOverview.risk_signal.category} | Severity: {riskOverview.risk_signal.severity}
                        </p>
                      )}
                    </div>
                    <div className="min-w-[220px] rounded-xl border border-[#c8d7ea] bg-[rgba(234,242,252,0.8)] px-4 py-3 text-sm text-[#35567f]">
                      <p className="font-semibold text-[#254971]">Recommended action</p>
                      <p className="mt-1">{riskOverview.report?.buyer_summary || riskOverview.advice}</p>
                      {!!riskOverview.evidence?.length && (
                        <button
                          type="button"
                          onClick={() => setIsEvidenceOpen((prev) => !prev)}
                          className="company-plain-btn mt-3"
                        >
                          {isEvidenceOpen ? 'Hide evidence' : 'Show evidence'}
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
                    <div className="rounded-xl border border-[#c8d7ea] bg-[rgba(234,242,252,0.75)] p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#587196]">Why this score</p>
                      <p className="mt-2 text-sm text-[#35567f]">{riskOverview.report?.overall_assessment || riskOverview.why_it_matters}</p>
                      {riskOverview.report?.risk_statement && (
                        <p className="mt-2 text-sm text-[#35567f]">
                          <span className="font-semibold text-[#274c78]">Risk statement:</span> {riskOverview.report.risk_statement}
                        </p>
                      )}
                      {riskOverview.report?.political_or_macro_note && (
                        <p className="mt-2 text-sm text-[#35567f]">
                          <span className="font-semibold text-[#274c78]">Political/macro:</span> {riskOverview.report.political_or_macro_note}
                        </p>
                      )}
                      <p className="mt-2 text-sm text-[#35567f]">
                        <span className="font-semibold text-[#274c78]">Why it matters:</span> {riskOverview.why_it_matters}
                      </p>
                      <ul className="mt-3 space-y-1 text-sm text-[#2f4d73]">
                        {riskOverview.key_drivers.map((driver, index) => (
                          <li key={`${driver}-${index}`}>• {driver}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="rounded-xl border border-[#c8d7ea] bg-[rgba(234,242,252,0.75)] p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#587196]">Source quality mix</p>
                      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                        <div className="rounded-lg bg-[#e8f6ed] px-2 py-2">
                          <p className="text-lg font-bold text-[#0f6a43]">{riskOverview.source_mix.high_quality}</p>
                          <p className="text-[11px] text-[#3a5d4c]">High</p>
                        </div>
                        <div className="rounded-lg bg-[#fff5de] px-2 py-2">
                          <p className="text-lg font-bold text-[#8a5b06]">{riskOverview.source_mix.medium_quality}</p>
                          <p className="text-[11px] text-[#6f5933]">Medium</p>
                        </div>
                        <div className="rounded-lg bg-[#ffeaea] px-2 py-2">
                          <p className="text-lg font-bold text-[#9e2f2f]">{riskOverview.source_mix.low_quality}</p>
                          <p className="text-[11px] text-[#7a4b4b]">Low</p>
                        </div>
                      </div>
                      <p className="mt-3 text-xs text-[#587196]">Risk estimate: {riskOverview.risk_percentage}%</p>
                    </div>
                  </div>

                  {isEvidenceOpen && !!riskOverview.evidence?.length && (
                    <div className="mt-4 rounded-xl border border-[#c8d7ea] bg-[rgba(234,242,252,0.75)] p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#587196]">Top evidence behind score</p>
                      <div className="mt-3 space-y-3">
                        {riskOverview.evidence.map((item, index) => (
                          <div key={`${item.title}-${index}`} className="rounded-lg border border-[#d4e0ef] bg-[rgba(248,252,255,0.86)] p-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <p className="text-sm font-semibold text-[#1f3f68]">{item.title}</p>
                              <span className="rounded-full bg-[#e7eef8] px-2 py-0.5 text-xs font-semibold text-[#3f5f86]">
                                Score {item.evidence_score}%
                              </span>
                            </div>
                            <p className="mt-1 text-xs text-[#5d7598]">
                              {item.source} | {item.date ? new Date(item.date).toLocaleDateString() : '-'} | {item.fact_label}
                            </p>
                            <p className="mt-1 text-sm text-[#3a5880]">{item.rationale}</p>
                            {item.link && (
                              <a href={item.link} target="_blank" rel="noreferrer" className="company-open-link mt-2 inline-block text-sm">
                                Open source
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </section>
              )}
            </div>
          )}
        </section>
      </div>

      {!isChatOpen && (
        <button
          type="button"
          onClick={() => setIsChatOpen(true)}
          className="ai-fab"
          aria-label="Open AI chat"
        >
          <span className="ai-fab-aura" />
          <Bot className="h-8 w-8 text-white" />
        </button>
      )}

      {isChatOpen && (
        <button
          type="button"
          onClick={() => setIsChatOpen(false)}
          className="ai-edge-close"
          aria-label="Close AI chat"
        >
          &gt;
        </button>
      )}

      <aside className={`ai-drawer ${isChatOpen ? 'ai-drawer-open' : ''}`}>
        <div className="ai-drawer-header">
          <div className="flex items-center gap-3">
            <div className="ai-drawer-icon-wrap">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white leading-tight">Insight AI</h2>
              <p className="text-xs text-blue-100">Analyze news for {companyName}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setIsChatOpen(false)}
            className="ai-drawer-close"
            aria-label="Close chat"
          >
            <X className="h-4 w-4 text-white" />
          </button>
        </div>

        <div className="ai-drawer-messages">
          {chatHistory.length === 0 && (
            <div className="ai-empty-state">
              <div className="ai-empty-icon">
                <Bot className="h-7 w-7 text-[#0059f2]" />
              </div>
              <h3 className="text-[#14345e] font-semibold mb-2">Ready to help</h3>
              <p className="text-[#557097] text-sm max-w-[280px]">
                Ask me about integrity risks, coverage trends, or potential reputation issues.
              </p>
            </div>
          )}

          {chatHistory.map((msg, idx) => (
            <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
              {msg.role === 'assistant' && (
                <div className="ai-avatar ai-avatar-assistant">
                  <Bot className="h-4 w-4 text-white" />
                </div>
              )}

              <div className={`ai-bubble ${msg.role === 'user' ? 'ai-bubble-user' : 'ai-bubble-assistant'}`}>
                {msg.content}
              </div>

              {msg.role === 'user' && (
                <div className="ai-avatar ai-avatar-user">
                  <User className="h-4 w-4 text-[#4e688d]" />
                </div>
              )}
            </div>
          ))}

          {isAsking && (
            <div className="flex gap-3">
              <div className="ai-avatar ai-avatar-assistant">
                <Bot className="h-4 w-4 text-white" />
              </div>
              <div className="ai-thinking">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        <form onSubmit={handleAskAI} className="ai-drawer-input">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleAskAI(e);
              }
            }}
            placeholder={`Ask something about ${companyName}...`}
            className="ai-input"
            disabled={isAsking}
            rows={1}
          />
          <button
            type="submit"
            disabled={isAsking || !question.trim()}
            className="ai-send-btn"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </aside>
    </div>
  );
};
