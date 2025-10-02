// pages/index.jsx
// UXXCA — Next.js + React + Tailwind starter with in-browser OCR (Tesseract) and Supabase integration (client-side).
// Instructions:
// 1) Create a Next.js project (e.g., using `npx create-next-app@latest --typescript` or JS variant).
// 2) Install dependencies: `npm install @supabase/supabase-js tesseract.js`
// 3) Add Tailwind CSS (official docs) or adapt styles as needed.
// 4) Place this file at `pages/index.jsx` and set env vars NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY for Supabase.

import React, { useEffect, useState, useRef } from 'react'
import Head from 'next/head'
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
const supabase = supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null

export default function Home(){
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [ocrText, setOcrText] = useState('')
  const [isOcrRunning, setIsOcrRunning] = useState(false)
  const parsedRef = useRef(null)

  useEffect(()=>{
    (async ()=>{
      if(supabase){
        try{
          const { data, error } = await supabase.from('transactions').select('*').order('id',{ascending:false}).limit(100)
          if(error) console.warn('Supabase fetch error', error)
          else if(data) setTransactions(data)
        }catch(e){console.error(e)}
      } else {
        setTransactions([
          {id:1, date:'2025-09-01', account:'Cash', type:'Income', category:'Sales', desc:'Cake sales', amount:8500},
          {id:2, date:'2025-09-03', account:'Bank', type:'Expense', category:'Rent', desc:'Shop rent', amount:5000}
        ])
      }
      setLoading(false)
    })()
  },[])

  const loadTesseract = async (file) =>{
    setIsOcrRunning(true)
    const { createWorker } = await import('tesseract.js')
    const worker = await createWorker({ logger: m=> console.log(m) })
    await worker.load(); await worker.loadLanguage('eng'); await worker.initialize('eng')
    const { data } = await worker.recognize(file)
    await worker.terminate()
    setIsOcrRunning(false)
    return data.text
  }

  const handleFile = async (e)=>{
    const f = e.target.files[0]
    if(!f) return
    setOcrText('')
    try{
      const text = await loadTesseract(f)
      setOcrText(text)
      // naive parsing
      const amountMatch = text.match(/(₹|Rs\.?|INR)?\s?([0-9,]+(\.[0-9]{1,2})?)/g)
      const amount = amountMatch ? Number(amountMatch[amountMatch.length-1].replace(/[₹,Rs.\s]/g,'')) : 0
      const dateMatch = text.match(/(\d{4}-\d{2}-\d{2})|(\d{2}\/\d{2}\/\d{4})/g)
      const date = dateMatch ? dateMatch[0] : new Date().toISOString().slice(0,10)
      parsedRef.current = { date, account:'Bank', type:'Expense', category:'Supplies', desc: text.slice(0,200), amount }
      setShowModal(true)
    }catch(err){console.error(err); alert('OCR failed — check console'); setIsOcrRunning(false)}
  }

  const saveParsed = async ()=>{
    const parsed = parsedRef.current
    if(!parsed) return
    if(supabase){
      try{
        const { data, error } = await supabase.from('transactions').insert([parsed]).select()
        if(error) { console.warn('Save error', error); alert('Save failed') }
        else setTransactions(prev=>[...data, ...prev])
      }catch(e){console.error(e)}
    } else {
      parsed.id = Math.floor(Math.random()*100000000)
      setTransactions(prev=>[parsed, ...prev])
    }
    parsedRef.current = null
    setShowModal(false)
  }

  const exportCsv = ()=>{
    const rows = [['Date','Account','Type','Category','Amount','Description']]
    transactions.forEach(t=> rows.push([t.date,t.account,t.type,t.category,t.amount,t.desc||'']))
    const csv = rows.map(r=> r.map(c=> '"'+String(c).replace(/"/g,'""')+'"').join(',')).join('\n')
    const blob = new Blob([csv],{type:'text/csv;charset=utf-8;'}); const url = URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='uxxca_transactions.csv'; a.click(); URL.revokeObjectURL(url)
  }

  return (
    <div>
      <Head>
        <title>UXXCA — Dashboard</title>
      </Head>

      <main className="min-h-screen bg-gradient-to-b from-gray-900 to-black text-white p-6">
        <div className="max-w-6xl mx-auto">
          <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-serif text-yellow-400">UXXCA</h1>
              <p className="text-sm text-gray-400">Automated accounting & AI advisor</p>
            </div>
            <div className="flex items-center gap-4">
              <label className="bg-yellow-400 text-black px-4 py-2 rounded font-semibold cursor-pointer">Upload Invoice
                <input type="file" accept="image/*,application/pdf" onChange={handleFile} className="hidden" />
              </label>
              <button onClick={exportCsv} className="bg-yellow-400 text-black px-4 py-2 rounded font-semibold">Export CSV</button>
            </div>
          </header>

          <section className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <div className="bg-gray-800 p-4 rounded shadow"> <div className="text-xs text-gray-400">Revenue (month)</div><div className="text-2xl font-bold">₹{transactions.filter(t=>t.type==='Income').reduce((s,t)=>s+t.amount,0).toLocaleString()}</div></div>
            <div className="bg-gray-800 p-4 rounded shadow"> <div className="text-xs text-gray-400">Expenses (month)</div><div className="text-2xl font-bold">₹{transactions.filter(t=>t.type==='Expense').reduce((s,t)=>s+t.amount,0).toLocaleString()}</div></div>
            <div className="bg-gray-800 p-4 rounded shadow"> <div className="text-xs text-gray-400">Net</div><div className="text-2xl font-bold">₹{(transactions.filter(t=>t.type==='Income').reduce((s,t)=>s+t.amount,0)-transactions.filter(t=>t.type==='Expense').reduce((s,t)=>s+t.amount,0)).toLocaleString()}</div></div>
          </section>

          <section className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              <div className="bg-gray-800 p-4 rounded shadow">
                <div className="flex items-center justify-between"><h2 className="font-semibold">Recent Transactions</h2>
                  <div className="flex items-center gap-2">
                    <input type="text" placeholder="Search" className="bg-gray-900 px-3 py-2 rounded text-sm" />
                  </div>
                </div>
                <table className="w-full mt-4 text-sm table-auto">
                  <thead className="text-gray-400 text-xs"><tr><th className="text-left">Date</th><th>Account</th><th>Type</th><th>Category</th><th className="text-right">Amount</th></tr></thead>
                  <tbody>
                    {transactions.map(tx=> (
                      <tr key={tx.id} className="border-t border-gray-700">
                        <td className="py-2">{tx.date}</td>
                        <td className="py-2">{tx.account}</td>
                        <td className="py-2">{tx.type}</td>
                        <td className="py-2">{tx.category}</td>
                        <td className="py-2 text-right">₹{Number(tx.amount).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="bg-gray-800 p-4 rounded shadow">
                <h3 className="font-semibold">AI Insights</h3>
                <p className="text-gray-400 text-sm mt-2">UXXCA will suggest: reduce Vendor X spend, forecast cash, flag overdue payments — powered by AI.</p>
              </div>
            </div>

            <aside className="space-y-4">
              <div className="bg-gray-800 p-4 rounded shadow">
                <h3 className="font-semibold">OCR Output</h3>
                <div className="mt-3 text-sm text-gray-400">{isOcrRunning? 'Running OCR...' : 'Upload a photo or PDF of an invoice to extract data.'}</div>
                {ocrText && <pre className="mt-3 text-xs bg-black p-2 rounded max-h-40 overflow-auto">{ocrText}</pre>}
              </div>

              <div className="bg-gray-800 p-4 rounded shadow">
                <h3 className="font-semibold">Quick Actions</h3>
                <div className="mt-3 flex flex-col gap-2">
                  <button className="bg-transparent border border-gray-700 px-3 py-2 rounded text-sm">Send to Accountant</button>
                  <button className="bg-transparent border border-gray-700 px-3 py-2 rounded text-sm">Backup / Sync</button>
                  <button className="bg-transparent border border-gray-700 px-3 py-2 rounded text-sm">Settings</button>
                </div>
              </div>
            </aside>
          </section>

          <footer className="text-gray-500 text-sm mt-10">UXXCA • MVP demo · Built by Nandini</footer>
        </div>
      </main>

      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 p-6 rounded max-w-xl w-full">
            <h3 className="font-semibold">Confirm parsed invoice</h3>
            <p className="text-sm text-gray-400 mt-2">Review the parsed data and save to your transactions.</p>
            <div className="mt-4 space-y-2">
              <div className="flex gap-2">
                <label className="w-28 text-gray-400">Date</label>
                <input className="flex-1 bg-gray-800 p-2 rounded" defaultValue={parsedRef.current?.date || new Date().toISOString().slice(0,10)} />
              </div>
              <div className="flex gap-2">
                <label className="w-28 text-gray-400">Amount</label>
                <input className="flex-1 bg-gray-800 p-2 rounded" defaultValue={parsedRef.current?.amount || 0} />
              </div>
              <div className="flex gap-2">
                <label className="w-28 text-gray-400">Category</label>
                <input className="flex-1 bg-gray-800 p-2 rounded" defaultValue={parsedRef.current?.category || 'Supplies'} />
              </div>
            </div>
            <div className="mt-4 flex gap-2 justify-end">
              <button onClick={()=>{ setShowModal(false); parsedRef.current=null }} className="bg-gray-700 px-3 py-2 rounded">Cancel</button>
              <button onClick={saveParsed} className="bg-yellow-400 text-black px-3 py-2 rounded">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
