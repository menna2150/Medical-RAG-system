import React from 'react'

export default function Loader({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-3 py-8">
      <span className="inline-block h-5 w-5 rounded-full border-2 border-med-500 border-t-transparent animate-spin" />
      <span className="text-sm text-slate-600 dark:text-slate-300">{label}</span>
    </div>
  )
}

export function StreamingProgress({ label, hint, charsReceived }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-3">
        <span className="inline-block h-4 w-4 rounded-full border-2 border-med-500 border-t-transparent animate-spin" />
        <div className="text-sm">
          <div className="font-medium">{label}</div>
          {hint && <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{hint}</div>}
        </div>
        {charsReceived != null && (
          <div className="ms-auto text-xs tabular-nums text-slate-500 dark:text-slate-400">
            {charsReceived} chars
          </div>
        )}
      </div>
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div className="card p-5 animate-pulse">
      <div className="h-5 w-40 bg-slate-200 dark:bg-slate-800 rounded mb-3" />
      <div className="h-4 w-full bg-slate-200 dark:bg-slate-800 rounded mb-2" />
      <div className="h-4 w-5/6 bg-slate-200 dark:bg-slate-800 rounded mb-2" />
      <div className="h-4 w-3/4 bg-slate-200 dark:bg-slate-800 rounded" />
    </div>
  )
}
