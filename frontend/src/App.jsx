import React, { useEffect, useMemo, useState } from 'react'
import Header from './components/Header.jsx'
import SymptomForm from './components/SymptomForm.jsx'
import DiagnosisCard from './components/DiagnosisCard.jsx'
import Disclaimer from './components/Disclaimer.jsx'
import Loader, { SkeletonCard, StreamingProgress } from './components/Loader.jsx'
import ErrorMessage from './components/ErrorMessage.jsx'
import SavedCases from './components/SavedCases.jsx'
import ConfidenceChart from './components/ConfidenceChart.jsx'
import { analyzeCaseStream } from './api.js'
import { useT } from './i18n.js'

const SAVED_KEY = 'medrag.saved'
const PREF_KEY  = 'medrag.prefs'

export default function App() {
  const [lang, setLang] = useState('en')
  const [dark, setDark] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [lastInput, setLastInput] = useState(null)
  const [saved, setSaved] = useState([])
  const [formKey, setFormKey] = useState(0)
  const [streamInfo, setStreamInfo] = useState(null) // { candidates, top_score, language }
  const [streamChars, setStreamChars] = useState(0)
  const t = useT(lang)

  const onNewCase = () => {
    setResult(null)
    setError(null)
    setLastInput(null)
    setStreamInfo(null)
    setStreamChars(0)
    setFormKey((k) => k + 1)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Load prefs + saved cases
  useEffect(() => {
    try {
      const prefs = JSON.parse(localStorage.getItem(PREF_KEY) || '{}')
      if (prefs.lang) setLang(prefs.lang)
      if (typeof prefs.dark === 'boolean') setDark(prefs.dark)
      const s = JSON.parse(localStorage.getItem(SAVED_KEY) || '[]')
      setSaved(Array.isArray(s) ? s : [])
    } catch {}
  }, [])

  // Persist prefs + apply theme/RTL
  useEffect(() => {
    localStorage.setItem(PREF_KEY, JSON.stringify({ lang, dark }))
    document.documentElement.classList.toggle('dark', dark)
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr'
    document.documentElement.lang = lang
  }, [lang, dark])

  const onSubmit = async (input) => {
    setLoading(true)
    setError(null)
    setResult(null)
    setLastInput(input)
    setStreamInfo(null)
    setStreamChars(0)
    let chars = 0
    try {
      const { name: _name, ...apiPayload } = input
      await analyzeCaseStream(apiPayload, {
        onRetrieval: (info) => setStreamInfo(info),
        onDelta: (chunk) => {
          chars += chunk.length
          setStreamChars(chars)
        },
        onComplete: (data) => setResult(data),
        onError: (msg) => setError(msg || 'Network error'),
      })
    } catch (e) {
      const msg = e?.message || 'Network error'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  const onSave = () => {
    if (!lastInput || !result) return
    const entry = {
      id: crypto.randomUUID(),
      savedAt: new Date().toISOString(),
      input: lastInput,
      result,
    }
    const next = [entry, ...saved].slice(0, 20)
    setSaved(next)
    localStorage.setItem(SAVED_KEY, JSON.stringify(next))
  }

  const onLoadCase = (c) => {
    setLastInput(c.input)
    setResult(c.result)
    setError(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const onDeleteCase = (id) => {
    const next = saved.filter((c) => c.id !== id)
    setSaved(next)
    localStorage.setItem(SAVED_KEY, JSON.stringify(next))
  }

  const ranked = useMemo(
    () => (result?.diagnoses || []).map((d, i) => ({ ...d, _rank: i + 1 })),
    [result],
  )

  return (
    <div className="min-h-screen flex flex-col">
      <Header lang={lang} setLang={setLang} dark={dark} setDark={setDark} />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        <section className="lg:col-span-5 space-y-4">
          <Disclaimer lang={lang} />
          <SymptomForm key={formKey} onSubmit={onSubmit} loading={loading} lang={lang} />
          <SavedCases cases={saved} onLoad={onLoadCase} onDelete={onDeleteCase} lang={lang} />
        </section>

        <section className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">{t.results}</h2>
            <div className="flex items-center gap-3">
              {result && (
                <>
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {t.retrievalQuality}: {(result.retrieval_quality * 100).toFixed(0)}%
                  </span>
                  <button className="btn-ghost" onClick={onSave}>{t.saveCase}</button>
                </>
              )}
              <button className="btn-ghost" onClick={onNewCase}>＋ {t.newCase}</button>
            </div>
          </div>

          {loading && (
            <div className="space-y-4">
              {streamInfo ? (
                <StreamingProgress
                  label={t.reasoning}
                  hint={`${t.candidatesFound}: ${streamInfo.candidates}`}
                  charsReceived={streamChars}
                />
              ) : (
                <Loader label={t.retrieving} />
              )}
              <SkeletonCard />
              <SkeletonCard />
            </div>
          )}

          {error && !loading && (
            <ErrorMessage
              message={error}
              onRetry={lastInput ? () => onSubmit(lastInput) : null}
              lang={lang}
            />
          )}

          {!loading && !error && result && ranked.length === 0 && (
            <div className="card p-5 text-sm text-slate-600 dark:text-slate-300">{t.noResults}</div>
          )}

          {!loading && !error && ranked.length > 0 && (
            <div className="space-y-4">
              <ConfidenceChart diagnoses={ranked} lang={lang} />
              {ranked.map((d) => (
                <DiagnosisCard key={d._rank} rank={d._rank} diagnosis={d} lang={lang} />
              ))}
            </div>
          )}
        </section>
      </main>

      <footer className="border-t border-slate-200 dark:border-slate-800 py-4 text-center text-xs text-slate-500 dark:text-slate-400">
        {t.disclaimerTitle} · MennaCare AI — {t.appSubtitle}
      </footer>
    </div>
  )
}
