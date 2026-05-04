import React from 'react'
import { useT } from '../i18n.js'

export default function MedicationTable({ treatments, lang }) {
  const t = useT(lang)
  if (!treatments?.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">—</p>
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 dark:bg-slate-900/50 text-slate-600 dark:text-slate-300">
          <tr>
            <th className="text-start px-3 py-2 font-medium">{t.drug}</th>
            <th className="text-start px-3 py-2 font-medium">{t.brands}</th>
            <th className="text-start px-3 py-2 font-medium">{t.price}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {treatments.map((tr, i) => (
            <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-900/40">
              <td className="px-3 py-2 align-top font-medium">{tr.drug}</td>
              <td className="px-3 py-2 align-top">
                <div className="flex flex-wrap gap-1">
                  {tr.brands_in_egypt?.length
                    ? tr.brands_in_egypt.map((b) => (
                        <span key={b} className="badge bg-med-50 text-med-800 dark:bg-med-900/40 dark:text-med-200">
                          {b}
                        </span>
                      ))
                    : <span className="text-slate-400">—</span>}
                </div>
                {tr.notes && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{tr.notes}</p>}
              </td>
              <td className="px-3 py-2 align-top whitespace-nowrap">{tr.price_egp || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
