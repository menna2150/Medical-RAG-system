import React from 'react'
import { useT } from '../i18n.js'

function Logo({ className = 'h-10 w-10' }) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      role="img"
      aria-label="MennaCare AI logo"
    >
      <path
        d="M 6,14 H 26 L 50,52 L 74,14 H 94 V 92 H 74 V 44 L 56,72 H 44 L 26,44 V 92 H 6 Z"
        fill="#2dd4bf"
      />
      <g
        stroke="#1e40af"
        strokeWidth="3.5"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M 36,8 C 33,20 41,28 50,32" />
        <path d="M 64,8 C 67,20 59,28 50,32" />
        <path d="M 50,32 C 50,52 55,64 65,72 C 73,79 80,81 84,82" />
      </g>
      <circle cx="36" cy="8" r="3.5" fill="#1e40af" />
      <circle cx="64" cy="8" r="3.5" fill="#1e40af" />
      <circle cx="86" cy="84" r="7" fill="#1e40af" />
      <circle cx="86" cy="84" r="4" fill="#2dd4bf" />
    </svg>
  )
}

export default function Header({ lang, setLang, dark, setDark }) {
  const t = useT(lang)
  return (
    <header className="sticky top-0 z-10 backdrop-blur bg-white/80 dark:bg-slate-950/80 border-b border-slate-200 dark:border-slate-800">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Logo />
          <div>
            <div className="font-semibold leading-tight">{t.appTitle}</div>
            <div className="text-xs text-slate-500 dark:text-slate-400 leading-tight">
              {t.appSubtitle}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-ghost" onClick={() => setLang(lang === 'en' ? 'ar' : 'en')}>
            {t.languageToggle}
          </button>
          <button className="btn-ghost" onClick={() => setDark(!dark)} aria-label={t.darkToggle}>
            {dark ? '☀︎' : '☾'}
          </button>
        </div>
      </div>
    </header>
  )
}
