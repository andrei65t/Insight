import React, { useEffect, useState, useRef } from 'react';
import { api, type CompanyDetails } from '../lib/api';
import { MessageSquare, Send, Bot, User, Sparkles } from 'lucide-react';

type Props = {
  companyName: string;
};

type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
};

export const CompanyDashboardView: React.FC<Props> = ({ companyName }) => {
  const [data, setData] = useState<CompanyDetails | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [reloadTick, setReloadTick] = useState(0);

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
      setChatHistory(prev => [...prev, { role: 'assistant', content: 'Eroare: Nu am putut obține un răspuns de la AI.' }]);
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

  const showLoadingState = isLoading || isRetrying;

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-10">
      <div className="mx-auto max-w-7xl">
        <button
          type="button"
          onClick={goBack}
          className="mb-6 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 transition"
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

        {/* --- AI CHAT BOT SECTION --- */}
        <section className="mb-8 rounded-2xl border border-blue-100 bg-white shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-hidden flex flex-col relative">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-white/20 p-2 rounded-lg backdrop-blur-sm">
                <Sparkles className="text-white h-5 w-5" />
              </div>
              <div>
                <h2 className="text-white font-bold text-lg leading-tight">TrustScope AI</h2>
                <p className="text-blue-100 text-xs">Analizează știrile: {companyName}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
              </span>
              <span className="text-xs text-white/90 font-medium">Online</span>
            </div>
          </div>
          
          {/* Chat Messages */}
          <div className="p-6 bg-slate-50 flex-1 max-h-[500px] overflow-y-auto space-y-5 scroll-smooth">
            {chatHistory.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center px-4 py-8">
                <div className="bg-blue-100 p-4 rounded-full mb-4">
                  <Bot className="h-8 w-8 text-blue-600" />
                </div>
                <h3 className="text-slate-800 font-semibold mb-2">Sunt pregătit!</h3>
                <p className="text-slate-500 text-sm max-w-[280px]">
                  Întreabă-mă despre riscurile de integritate, rezumatul știrilor sau eventualele scandaluri mediatice.
                </p>
              </div>
            )}
            
            {chatHistory.map((msg, idx) => (
              <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                {msg.role === 'assistant' && (
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                    <Bot className="h-5 w-5 text-white" />
                  </div>
                )}
                
                <div className={`max-w-[85%] rounded-2xl px-5 py-3 text-sm shadow-sm whitespace-pre-wrap leading-relaxed ${
                  msg.role === 'user' 
                    ? 'bg-blue-600 text-white rounded-tr-none' 
                    : 'bg-white text-slate-800 border border-slate-200/60 rounded-tl-none font-medium'
                }`}>
                  {msg.content}
                </div>

                {msg.role === 'user' && (
                  <div className="w-9 h-9 rounded-full bg-slate-200 border border-slate-300 flex items-center justify-center flex-shrink-0">
                    <User className="h-5 w-5 text-slate-600" />
                  </div>
                )}
              </div>
            ))}
            
            {isAsking && (
              <div className="flex gap-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-sm">
                  <Bot className="h-5 w-5 text-white" />
                </div>
                <div className="bg-white rounded-2xl rounded-tl-none px-5 py-4 border border-slate-200/60 flex items-center gap-1.5 shadow-sm">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
                </div>
              </div>
            )}
            
            <div ref={chatEndRef} />
          </div>

          {/* Input Area */}
          <form onSubmit={handleAskAI} className="p-4 bg-white border-t border-slate-200 flex gap-3 items-end">
            <textarea 
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleAskAI(e);
                }
              }}
              placeholder={`Întreabă ceva despre ${companyName}...`}
              className="flex-1 max-h-32 min-h-[44px] px-4 py-3 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-blue-500 transition text-sm resize-none"
              disabled={isAsking}
              rows={1}
            />
            <button 
              type="submit"
              disabled={isAsking || !question.trim()}
              className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-3 rounded-xl hover:shadow-md hover:from-blue-700 hover:to-indigo-700 transition disabled:opacity-50 disabled:hover:shadow-none flex-shrink-0 h-[44px] w-[44px] flex items-center justify-center"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
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
