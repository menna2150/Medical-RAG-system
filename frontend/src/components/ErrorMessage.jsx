import React from 'react'
import { useT } from '../i18n.js'

export default function ErrorMessage({ message, onRetry, lang }) {
  const t = useT(lang)
  return (
    <div className="rounded-xl border border-rose-300 bg-rose-50 dark:border-rose-700/60 dark:bg-rose-950/30 text-rose-900 dark:text-rose-100 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold">{t.error}</div>
          <p className="text-sm mt-0.5">{message}</p>
        </div>
        {onRetry && (
          <button className="btn-ghost border-rose-300 dark:border-rose-700/60" onClick={onRetry}>
            {t.retry}
          </button>
        )}
      </div>
    </div>
  )
}
