import React from 'react'
import { useT } from '../i18n.js'

export default function Disclaimer({ lang }) {
  const t = useT(lang)
  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-100 p-4">
      <div className="flex items-start gap-3">
        <span aria-hidden className="text-xl leading-none">⚠</span>
        <div>
          <div className="font-semibold">{t.disclaimerTitle}</div>
          <p className="text-sm mt-0.5">{t.disclaimer}</p>
        </div>
      </div>
    </div>
  )
}
