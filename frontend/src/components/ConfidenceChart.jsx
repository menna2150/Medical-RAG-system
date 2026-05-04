import React from 'react'
import { useT } from '../i18n.js'

const barColor = {
  high:   'bg-emerald-500',
  medium: 'bg-amber-500',
  low:    'bg-slate-400',
}

export default function ConfidenceChart({ diagnoses, lang }) {
  const t = useT(lang)
  if (!diagnoses?.length) return null
  return (
    <div className="card p-4">
      <h3 className="font-semibold mb-3">{t.confidenceChart}</h3>
      <div className="space-y-2">
        {diagnoses.map((d, i) => {
          const pct = Math.round((d.confidence_score || 0) * 100)
          const tier = d.confidence || 'low'
          return (
            <div key={i} className="flex items-center gap-3">
              <div className="w-40 shrink-0 text-sm truncate" title={d.name}>
                <span className="text-slate-400 me-1">#{i + 1}</span>
                {d.name}
              </div>
              <div className="flex-1 h-3 rounded bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className={`h-full ${barColor[tier]} transition-[width] duration-500`}
                  style={{ width: `${pct}%` }}
                  role="meter"
                  aria-valuenow={pct}
                  aria-valuemin="0"
                  aria-valuemax="100"
                  aria-label={`${d.name} ${pct}%`}
                />
              </div>
              <div className="w-12 shrink-0 text-end text-sm tabular-nums">{pct}%</div>
            </div>
          )
        })}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded bg-emerald-500" />
          {t.confHigh}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded bg-amber-500" />
          {t.confMedium}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded bg-slate-400" />
          {t.confLow}
        </span>
      </div>
    </div>
  )
}
