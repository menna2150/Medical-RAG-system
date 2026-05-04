import React, { useState, useRef } from 'react'
import { useT } from '../i18n.js'

export default function SymptomForm({ onSubmit, loading, lang }) {
  const t = useT(lang)
  const [name, setName] = useState('')
  const [symptoms, setSymptoms] = useState('')
  const [age, setAge] = useState('')
  const [gender, setGender] = useState('')
  const [history, setHistory] = useState('')
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!symptoms.trim() || loading) return
    onSubmit({
      name: name.trim() || undefined,
      symptoms: symptoms.trim(),
      age: age ? Number(age) : undefined,
      gender: gender || undefined,
      history: history.trim() || undefined,
      language: lang === 'ar' ? 'ar' : 'en',
    })
  }

  const startVoice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) {
      alert('Speech recognition not supported in this browser.')
      return
    }
    const r = new SR()
    r.lang = lang === 'ar' ? 'ar-EG' : 'en-US'
    r.interimResults = false
    r.maxAlternatives = 1
    r.onstart = () => setListening(true)
    r.onend = () => setListening(false)
    r.onerror = () => setListening(false)
    r.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      setSymptoms((prev) => (prev ? `${prev}, ${transcript}` : transcript))
    }
    recognitionRef.current = r
    r.start()
  }

  return (
    <form onSubmit={handleSubmit} className="card p-5 space-y-4">
      <h2 className="text-lg font-semibold">{t.formTitle}</h2>

      <div>
        <label className="label" htmlFor="patient-name">{t.patientName}</label>
        <input
          id="patient-name"
          type="text"
          autoComplete="off"
          className="input"
          placeholder={t.patientNamePh}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>

      <div>
        <label className="label" htmlFor="symptoms">{t.symptoms}</label>
        <textarea
          id="symptoms"
          className="input min-h-[96px] resize-y"
          placeholder={t.symptomsPh}
          value={symptoms}
          onChange={(e) => setSymptoms(e.target.value)}
          required
        />
        <div className="mt-2">
          <button type="button" className="btn-ghost" onClick={startVoice} disabled={listening}>
            {listening ? `🎙 ${t.listening}` : `🎙 ${t.voice}`}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="label" htmlFor="age">{t.age}</label>
          <input
            id="age"
            type="number"
            min="0"
            max="120"
            className="input"
            value={age}
            onChange={(e) => setAge(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="gender">{t.gender}</label>
          <select id="gender" className="input" value={gender} onChange={(e) => setGender(e.target.value)}>
            <option value="">—</option>
            <option value="male">{t.male}</option>
            <option value="female">{t.female}</option>
            <option value="other">{t.other}</option>
          </select>
        </div>
      </div>

      <div>
        <label className="label" htmlFor="history">{t.history}</label>
        <textarea
          id="history"
          className="input min-h-[64px] resize-y"
          placeholder={t.historyPh}
          value={history}
          onChange={(e) => setHistory(e.target.value)}
        />
      </div>

      <div className="pt-1">
        <button className="btn-primary w-full sm:w-auto" type="submit" disabled={loading || !symptoms.trim()}>
          {loading ? t.analyzing : t.analyze}
        </button>
      </div>
    </form>
  )
}
