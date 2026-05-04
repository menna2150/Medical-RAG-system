import React from 'react'
import { useT } from '../i18n.js'

function csvEscape(value) {
  if (value === null || value === undefined) return ''
  const s = String(value)
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

function buildCsv(cases) {
  const headers = [
    'saved_at',
    'patient_name',
    'age',
    'gender',
    'symptoms',
    'history',
    'language',
    'top_diagnosis',
    'top_confidence',
    'all_diagnoses',
    'retrieval_quality',
  ]
  const rows = cases.map((c) => {
    const top = c.result?.diagnoses?.[0]
    const all = (c.result?.diagnoses || [])
      .map((d) => `${d.name || d.condition || ''} (${Math.round((d.confidence ?? 0) * 100)}%)`)
      .join('; ')
    return [
      c.savedAt,
      c.input?.name || '',
      c.input?.age ?? '',
      c.input?.gender || '',
      c.input?.symptoms || '',
      c.input?.history || '',
      c.input?.language || '',
      top?.name || top?.condition || '',
      top?.confidence != null ? Math.round(top.confidence * 100) + '%' : '',
      all,
      c.result?.retrieval_quality != null ? Math.round(c.result.retrieval_quality * 100) + '%' : '',
    ]
  })
  return [headers, ...rows].map((r) => r.map(csvEscape).join(',')).join('\r\n')
}

function downloadCsv(cases) {
  const csv = buildCsv(cases)
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  a.href = url
  a.download = `mennacare-cases-${stamp}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export default function SavedCases({ cases, onLoad, onDelete, lang }) {
  const t = useT(lang)
  if (!cases?.length) return null
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold">{t.history_h}</h3>
        <button className="btn-ghost" onClick={() => downloadCsv(cases)}>
          ⬇ {t.exportCsv}
        </button>
      </div>
      <ul className="divide-y divide-slate-100 dark:divide-slate-800">
        {cases.map((c) => (
          <li key={c.id} className="py-2 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="text-sm font-medium truncate">
                {c.input?.name?.trim() || t.unnamedPatient}
              </div>
              <div className="text-xs text-slate-600 dark:text-slate-300 truncate">
                {c.input.symptoms}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400">
                {new Date(c.savedAt).toLocaleString()}
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              <button className="btn-ghost" onClick={() => onLoad(c)}>{t.load}</button>
              <button className="btn-ghost" onClick={() => onDelete(c.id)}>{t.delete}</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
