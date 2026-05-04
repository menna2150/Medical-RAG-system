import React, { useState } from 'react'
import MedicationTable from './MedicationTable.jsx'
import { useT } from '../i18n.js'

const confidenceStyles = {
  high:   'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
  medium: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
  low:    'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
}

export default function DiagnosisCard({ diagnosis, rank, lang }) {
  const t = useT(lang)
  const [open, setOpen] = useState(rank === 1)
  const conf = diagnosis.confidence || 'low'
  return (
    <article className="card p-5">
      <header className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <span>#{rank}</span>
            {diagnosis.icd11 && <span>· ICD-11 {diagnosis.icd11}</span>}
          </div>
          <h3 className="text-lg font-semibold mt-0.5">{diagnosis.name}</h3>
        </div>
        <div className="text-end">
          <span className={`badge ${confidenceStyles[conf]}`}>{t.confidence}: {conf}</span>
          <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {(diagnosis.confidence_score * 100).toFixed(0)}%
          </div>
        </div>
      </header>

      <section className="mt-3">
        <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{t.reason}</div>
        <p className="text-sm mt-1 leading-relaxed">{diagnosis.reason}</p>
      </section>

      <button
        className="mt-4 text-sm text-med-700 dark:text-med-300 hover:underline"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        {open ? '▾' : '▸'} {t.tests} · {t.treatments}
      </button>

      {open && (
        <div className="mt-3 space-y-4">
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-1">
              {t.tests}
            </div>
            {diagnosis.tests?.length ? (
              <ul className="list-disc list-inside text-sm space-y-0.5">
                {diagnosis.tests.map((tt) => <li key={tt}>{tt}</li>)}
              </ul>
            ) : <p className="text-sm text-slate-500">—</p>}
          </div>

          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-1">
              {t.treatments}
            </div>
            <MedicationTable treatments={diagnosis.treatments} lang={lang} />
          </div>

          {diagnosis.sources?.length > 0 && (
            <div className="text-xs text-slate-500 dark:text-slate-400">
              <span className="font-medium">{t.sources}:</span> {diagnosis.sources.join(', ')}
            </div>
          )}
        </div>
      )}
    </article>
  )
}
