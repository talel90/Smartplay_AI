import { useCallback, useEffect, useRef, useState } from 'react'
import { AnalyticsDashboard } from './AnalyticsDashboard.jsx'

const API_BASE =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? '/api' : 'http://localhost:8000')

const LS_JOBS = 'smartplay_recent_jobs'
const KP_COUNT = 12

function isPollableJobId(id) {
  if (!id || typeof id !== 'string') return false
  if (id.startsWith('mock-') || id === 'demo') return false
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
}

function loadRecentJobs() {
  try {
    const raw = localStorage.getItem(LS_JOBS)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    const cleaned = parsed.filter(isPollableJobId)
    if (cleaned.length !== parsed.length) localStorage.setItem(LS_JOBS, JSON.stringify(cleaned))
    return cleaned
  } catch { return [] }
}

function saveRecentJob(id) {
  if (!isPollableJobId(id)) return
  const prev = loadRecentJobs().filter((x) => x !== id)
  prev.unshift(id)
  localStorage.setItem(LS_JOBS, JSON.stringify(prev.slice(0, 12)))
}

const DEMO_ANALYTICS = {
  warning: null,
  shots_meta: { total_shots: 145, total_bounces: 312 },
  player_cards: [
    { player_id: 1, label: 'Player 1', score: 85, shoots: 42, max_speed_kmh: 18.5, total_distance_m: 1250, avg_speed_kmh: 4.2, net_presence_pct: 35.2, speed_consistency_kmh: 2.1, calorie_burn_kcal: 175.0, overhead_pct: 28.5 },
    { player_id: 2, label: 'Player 2', score: 92, shoots: 55, max_speed_kmh: 21.2, total_distance_m: 1420, avg_speed_kmh: 5.1, net_presence_pct: 68.4, speed_consistency_kmh: 3.4, calorie_burn_kcal: 198.8, overhead_pct: 54.5 },
    { player_id: 3, label: 'Player 3', score: 78, shoots: 38, max_speed_kmh: 17.8, total_distance_m: 1180, avg_speed_kmh: 3.9, net_presence_pct: 22.1, speed_consistency_kmh: 1.8, calorie_burn_kcal: 165.2, overhead_pct: 15.8 },
    { player_id: 4, label: 'Player 4', score: 88, shoots: 48, max_speed_kmh: 19.5, total_distance_m: 1300, avg_speed_kmh: 4.6, net_presence_pct: 48.0, speed_consistency_kmh: 2.8, calorie_burn_kcal: 182.0, overhead_pct: 37.5 },
  ],
  speed_series: { time: [0,1,2,3,4,5], players: { 1:[0,5,12,8,15,18.5], 2:[0,8,15,21.2,12,5], 3:[0,3,8,17.8,10,4], 4:[0,6,14,19.5,16,8] } },
  heatmap: { 1:{x:[-2,-3,-1],y:[4,5,6]}, 2:{x:[2,3,1],y:[4,5,6]}, 3:{x:[-2,-3,-1],y:[-4,-5,-6]}, 4:{x:[2,3,1],y:[-4,-5,-6]} },
  shots_breakdown_by_player: { 1:{Smash:12,Volley:20,Lob:10}, 2:{Smash:18,Volley:25,Lob:12}, 3:{Smash:8,Volley:18,Lob:12}, 4:{Smash:15,Volley:22,Lob:11} },
}

const CourtGuide = ({ currentPoint }) => {
  const points = [
    { id:1,x:20,y:180 }, { id:2,x:80,y:180 },
    { id:3,x:20,y:140 }, { id:4,x:50,y:140 }, { id:5,x:80,y:140 },
    { id:6,x:20,y:100 }, { id:7,x:80,y:100 },
    { id:8,x:20,y:60  }, { id:9,x:50,y:60  }, { id:10,x:80,y:60 },
    { id:11,x:20,y:20 }, { id:12,x:80,y:20 },
  ]
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center' }}>
      <h4 className="orbitron text-accent mb-2" style={{ fontSize:'0.85rem', textAlign:'center', margin:'0 0 0.5rem' }}>Calibration Guide</h4>
      <p className="text-secondary" style={{ fontSize:'0.72rem', textAlign:'center', lineHeight:'1.4', margin:'0 0 0.75rem' }}>
        {currentPoint < 12 ? `Click point K${currentPoint+1} on the image.` : 'All 12 points placed!'}
      </p>
      <svg viewBox="0 0 100 200" style={{ width:'100%', maxWidth:'130px', height:'auto', display:'block', background:'rgba(0,0,0,0.25)', border:'1px solid rgba(14,165,233,0.2)', borderRadius:'8px' }}>
        <rect x="20" y="20" width="60" height="160" fill="none" stroke="#475569" strokeWidth="2"/>
        <line x1="20" y1="100" x2="80" y2="100" stroke="#0ea5e9" strokeWidth="1.5" strokeDasharray="4"/>
        <line x1="20" y1="60"  x2="80" y2="60"  stroke="#475569" strokeWidth="2"/>
        <line x1="20" y1="140" x2="80" y2="140" stroke="#475569" strokeWidth="2"/>
        <line x1="50" y1="60"  x2="50" y2="140" stroke="#475569" strokeWidth="2"/>
        {points.map((p, idx) => {
          const isActive = idx === currentPoint
          const isDone = idx < currentPoint
          return (
            <g key={p.id}>
              <circle cx={p.x} cy={p.y} r={isActive ? 8 : 6.5}
                fill={isActive ? '#0ea5e9' : isDone ? '#10b981' : '#1e293b'}
                stroke={isActive ? '#fff' : isDone ? '#059669' : '#475569'}
                strokeWidth="1.5"/>
              <text x={p.x} y={p.y} fill={isActive||isDone ? '#fff' : '#94a3b8'}
                fontSize="6" fontFamily="Orbitron" fontWeight="bold"
                textAnchor="middle" dominantBaseline="central">
                {p.id}
              </text>
            </g>
          )
        })}
      </svg>
      {currentPoint >= 12 && (
        <div style={{ marginTop:'0.75rem', padding:'4px 10px', background:'rgba(16,185,129,0.2)', color:'#10b981', borderRadius:'6px', fontSize:'0.72rem', fontWeight:'bold' }}>
          ✓ CALIBRATED
        </div>
      )}
    </div>
  )
}

export default function App() {
  // ── State ──────────────────────────────────────────────────────────────────
  const [videoFile, setVideoFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [calibrationPoints, setCalibrationPoints] = useState([])
  const [page, setPage] = useState('main') // 'main' | 'calibration'
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [hoverPos, setHoverPos] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const clickStartPos = useRef(null)
  const imgRef = useRef(null)

  const [uploading, setUploading] = useState(false)
  const [jobId, setJobId] = useState('')
  const [jobStatus, setJobStatus] = useState(null)
  const [error, setError] = useState('')
  const [results, setResults] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [uiDemoMode, setUiDemoMode] = useState(false)
  const [courtKeypointsText, setCourtKeypointsText] = useState('')
  const [kpFile, setKpFile] = useState(null)
  const pollRef = useRef(null)

  // ── Polling ────────────────────────────────────────────────────────────────
  const fetchStatus = useCallback(async (id) => {
    const r = await fetch(`${API_BASE}/jobs/${id}`)
    if (r.status === 404) { const e = new Error('Job not found'); e.status = 404; throw e }
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  }, [])

  const fetchResults = useCallback(async (id) => {
    const r = await fetch(`${API_BASE}/jobs/${id}/results`)
    if (!r.ok) throw new Error(await r.text())
    return r.json()
  }, [])

  useEffect(() => { return () => { if (pollRef.current) clearInterval(pollRef.current) } }, [])

  useEffect(() => {
    if (!isPollableJobId(jobId)) return
    setUiDemoMode(false)
    const poll = async () => {
      try {
        const st = await fetchStatus(jobId)
        setJobStatus(st); setError('')
        if (st.status === 'completed') {
          clearInterval(pollRef.current); pollRef.current = null
          const res = await fetchResults(jobId); setResults(res)
          try { const ar = await fetch(`${API_BASE}/jobs/${jobId}/analytics`); if (ar.ok) setAnalytics(await ar.json()); else setAnalytics(null) } catch { setAnalytics(null) }
        }
        if (st.status === 'failed') { clearInterval(pollRef.current); pollRef.current = null; setError(st.error || 'Job failed') }
      } catch (e) {
        if (e?.status === 404) { clearInterval(pollRef.current); pollRef.current = null; setJobId(''); setError('Job not found.'); return }
        setError(String(e.message || e))
      }
    }
    poll(); pollRef.current = setInterval(poll, 2500)
    return () => { clearInterval(pollRef.current); pollRef.current = null }
  }, [jobId, fetchStatus, fetchResults])

  // ── Handlers ───────────────────────────────────────────────────────────────
  function onPickVideo(e) {
    const file = e.target.files?.[0]; e.target.value = ''
    if (!file) return
    setVideoFile(file); setPreview(null); setCalibrationPoints([]); setCourtKeypointsText(''); setError('')
  }

  async function loadFirstFrame() {
    if (!videoFile) return
    setLoadingPreview(true); setError(''); setPreview(null); setCalibrationPoints([])
    const fd = new FormData(); fd.append('file', videoFile)
    try {
      const r = await fetch(`${API_BASE}/tools/first-frame`, { method:'POST', body:fd })
      const text = await r.text()
      if (!r.ok) throw new Error(text)
      const data = JSON.parse(text)
      setPreview({ width: data.width, height: data.height, dataUrl: `data:${data.mime};base64,${data.image_base64}` })
      setZoom(1); setPan({ x:0, y:0 })
      setPage('calibration')
    } catch (err) { setError(String(err.message || err)) }
    finally { setLoadingPreview(false) }
  }

  function onCalibrationClick(e) {
    if (!preview || calibrationPoints.length >= KP_COUNT) return
    const img = imgRef.current; if (!img) return
    const rect = img.getBoundingClientRect()
    if (rect.width < 1 || rect.height < 1) return
    const x = ((e.clientX - rect.left) / rect.width) * preview.width
    const y = ((e.clientY - rect.top) / rect.height) * preview.height
    setCalibrationPoints((prev) => [...prev, { x, y }])
  }

  function handleWheel(e) {
    const delta = e.deltaY * -0.002
    setZoom(z => Math.max(1, Math.min(8, z + delta)))
  }

  function handleMouseDown(e) {
    if (e.button !== 0) return
    setIsDragging(true)
    clickStartPos.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y, moved: false }
  }

  function handleMouseMove(e) {
    if (isDragging && clickStartPos.current) {
      const dx = e.clientX - clickStartPos.current.x
      const dy = e.clientY - clickStartPos.current.y
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) clickStartPos.current.moved = true
      setPan({ x: clickStartPos.current.panX + dx, y: clickStartPos.current.panY + dy })
      setHoverPos(null)
    } else {
      const img = imgRef.current
      if (img && page === 'calibration' && calibrationPoints.length < KP_COUNT) {
        const rect = img.getBoundingClientRect()
        if (e.clientX >= rect.left && e.clientX <= rect.right && e.clientY >= rect.top && e.clientY <= rect.bottom) {
          const xPct = (e.clientX - rect.left) / rect.width
          const yPct = (e.clientY - rect.top) / rect.height
          setHoverPos({ x: e.clientX, y: e.clientY, xPct, yPct })
        } else {
          setHoverPos(null)
        }
      }
    }
  }

  function handleMouseUp(e) {
    setIsDragging(false)
    if (clickStartPos.current && !clickStartPos.current.moved && e.button === 0) onCalibrationClick(e)
    clickStartPos.current = null
  }

  function handleMouseLeave() { 
    setIsDragging(false)
    clickStartPos.current = null
    setHoverPos(null)
  }

  function resetCalibration() { setCalibrationPoints([]); setZoom(1); setPan({ x:0, y:0 }) }

  function saveCalibration() { setPage('main') }

  function buildKeypointsForJob() {
    if (kpFile) return { mode: 'file' }
    if (calibrationPoints.length === KP_COUNT) {
      const json = JSON.stringify(calibrationPoints.map((p) => [Math.round(p.x), Math.round(p.y)]))
      return { mode: 'json', json }
    }
    const trimmed = courtKeypointsText.trim()
    if (trimmed) return { mode: 'json', json: trimmed }
    return { mode: 'none' }
  }

  async function submitJob() {
    if (!videoFile) { setError('Choose a video first.'); return }
    const kp = buildKeypointsForJob()
    setUploading(true); setError(''); setResults(null); setAnalytics(null); setUiDemoMode(false); setJobStatus(null); setJobId('')
    const fd = new FormData(); fd.append('file', videoFile)
    if (kp.mode === 'file') fd.append('keypoints_file', kpFile)
    else if (kp.mode === 'json') fd.append('court_keypoints_json', kp.json)
    try {
      const r = await fetch(`${API_BASE}/jobs`, { method:'POST', body:fd })
      const text = await r.text()
      if (!r.ok) throw new Error(text)
      const data = JSON.parse(text); setJobId(data.job_id); saveRecentJob(data.job_id)
    } catch (err) { setError(String(err.message || err)) }
    finally { setUploading(false) }
  }

  const recent = loadRecentJobs()

  const setPreviewMode = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    setJobId(''); setJobStatus(null); setError(''); setUiDemoMode(true); setResults({ demo:true }); setAnalytics(DEMO_ANALYTICS)
  }

  // ── Calibration Page ───────────────────────────────────────────────────────
  if (page === 'calibration' && preview) {
    return (
      <div
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        style={{
          position: 'fixed', inset: 0, backgroundColor: '#050a14',
          display: 'flex', flexDirection: 'column',
          cursor: isDragging ? 'grabbing' : (calibrationPoints.length < KP_COUNT ? 'crosshair' : 'default'),
          overflow: 'hidden', userSelect: 'none',
        }}
      >
        {/* Top bar */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '0.75rem 1.5rem', flexShrink: 0,
          background: 'rgba(5,10,20,0.97)',
          borderBottom: '1px solid rgba(14,165,233,0.2)',
          zIndex: 10,
        }}>
          <div>
            <h2 className="orbitron" style={{ fontSize:'1.1rem', color:'#fff', margin:0 }}>
              Tactical Calibration &nbsp;
              <span style={{ color:'#0ea5e9', fontSize:'1.25rem' }}>{calibrationPoints.length}</span>
              <span style={{ color:'#334155' }}> / {KP_COUNT}</span>
            </h2>
            <p style={{ color:'#475569', fontSize:'0.7rem', margin:0 }}>
              Scroll to zoom · Drag to pan · Click to place keypoint
            </p>
          </div>
          <div style={{ display:'flex', gap:'0.75rem' }}>
            <button className="action-btn" onClick={resetCalibration}
              style={{ height:'38px', fontSize:'0.75rem', background:'rgba(255,255,255,0.05)', borderColor:'rgba(255,255,255,0.15)', color:'#94a3b8' }}>
              ↺ Reset
            </button>
            <button className="action-btn" onClick={saveCalibration}
              style={{ height:'38px', fontSize:'0.75rem', background:'rgba(255,255,255,0.05)', borderColor:'rgba(255,255,255,0.15)', color:'#94a3b8' }}>
              ← Back
            </button>
            <button className="action-btn primary-btn" onClick={saveCalibration}
              style={{ height:'38px', fontSize:'0.75rem', opacity: calibrationPoints.length === KP_COUNT ? 1 : 0.7 }}>
              {calibrationPoints.length === KP_COUNT ? '✓ Save Calibration' : `Save (${calibrationPoints.length}/${KP_COUNT})`}
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div style={{ flex:1, position:'relative', display:'flex', justifyContent:'center', alignItems:'center', overflow:'hidden' }}>
          <div style={{
            position:'relative', display:'inline-block',
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin:'center',
            transition: isDragging ? 'none' : 'transform 0.1s ease-out',
          }}>
            <img
              ref={imgRef}
              src={preview.dataUrl}
              alt="Calibration Frame"
              draggable={false}
              style={{ maxWidth:'100vw', maxHeight:'calc(100vh - 64px)', display:'block' }}
            />
            {calibrationPoints.map((p, i) => (
              <div key={`${i}`} className="kp-dot" style={{
                left: `${(p.x / preview.width) * 100}%`,
                top:  `${(p.y / preview.height) * 100}%`,
                transform: `translate(-50%, -50%) scale(${1 / zoom})`,
              }}>
                {i + 1}
              </div>
            ))}
          </div>

          {/* Court guide — bottom-right */}
          <div style={{
            position:'absolute', bottom:'1.25rem', right:'1.25rem', zIndex:10,
            background:'rgba(5,10,20,0.9)', backdropFilter:'blur(16px)',
            border:'1px solid rgba(14,165,233,0.3)', borderRadius:'16px', padding:'1rem',
            width:'210px', pointerEvents:'none',
          }}>
            <CourtGuide currentPoint={calibrationPoints.length} />
          </div>

          {/* Zoom — bottom-left */}
          <div style={{
            position:'absolute', bottom:'1.25rem', left:'1.25rem', zIndex:10,
            padding:'0.4rem 0.85rem', background:'rgba(5,10,20,0.85)', backdropFilter:'blur(8px)',
            borderRadius:'10px', color:'#0ea5e9',
            fontFamily:'Orbitron, sans-serif', fontSize:'0.8rem', fontWeight:'700',
            border:'1px solid rgba(14,165,233,0.25)', pointerEvents:'none',
          }}>
            {zoom.toFixed(1)}×
          </div>

          {/* Magnifying Glass Cursor */}
          {hoverPos && (
            <div style={{
              position: 'fixed',
              left: hoverPos.x - 75,
              top: hoverPos.y - 150,
              width: 150, height: 150,
              borderRadius: '50%',
              border: '3px solid #0ea5e9',
              backgroundColor: '#000',
              backgroundImage: `url(${preview.dataUrl})`,
              backgroundPosition: `${75 - (hoverPos.xPct * preview.width * 3)}px ${75 - (hoverPos.yPct * preview.height * 3)}px`,
              backgroundSize: `${preview.width * 3}px ${preview.height * 3}px`,
              backgroundRepeat: 'no-repeat',
              pointerEvents: 'none',
              zIndex: 100,
              boxShadow: '0 8px 32px rgba(0,0,0,0.5)'
            }}>
              <div style={{ position: 'absolute', top: '50%', left: '50%', width: 4, height: 4, transform: 'translate(-50%, -50%)', backgroundColor: '#ef4444', borderRadius: '50%' }} />
              <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: 1, backgroundColor: 'rgba(239, 68, 68, 0.5)' }} />
              <div style={{ position: 'absolute', top: 0, bottom: 0, left: '50%', width: 1, backgroundColor: 'rgba(239, 68, 68, 0.5)' }} />
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Main Page ──────────────────────────────────────────────────────────────
  return (
    <div className="app">
      <header>
        <h1 className="main-title orbitron">SmartPlay AI</h1>
        <div className="sub-header">Advanced Padel Analytics System v2.0</div>
      </header>

      <div className="dashboard-grid">
        {/* Left: Config */}
        <div className="glass-card">
          <h2 className="section-title orbitron">System Configuration</h2>

          <div className="upload-zone">
            <input type="file" accept="video/*" onChange={onPickVideo} id="video-upload" />
            <div className="orbitron" style={{ fontSize:'1.25rem', color: videoFile ? 'var(--accent-primary)' : 'inherit' }}>
              {videoFile ? 'Video Synchronized' : 'Initialize Video Feed'}
            </div>
            {videoFile && <div className="file-name mt-1">{videoFile.name}</div>}
            {!videoFile && <div className="text-secondary mt-1">Click to browse or drag &amp; drop MP4 file</div>}
          </div>

          <div className="button-group">
            <button className="action-btn" disabled={!videoFile || loadingPreview} onClick={loadFirstFrame}>
              {loadingPreview ? 'Capturing...' : 'Capture Frame'}
            </button>
          </div>

          {preview && (
            <div className="glass-card mt-4" style={{ background: calibrationPoints.length === KP_COUNT ? 'rgba(16,185,129,0.05)' : 'rgba(14,165,233,0.05)', borderColor: calibrationPoints.length === KP_COUNT ? '#10b981' : 'var(--accent-primary)' }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <div>
                  <h3 className="section-title orbitron" style={{ fontSize:'0.9rem', color: calibrationPoints.length === KP_COUNT ? '#10b981' : 'var(--accent-primary)', marginBottom:'0.25rem' }}>
                    {calibrationPoints.length === KP_COUNT ? '✓ Calibration Complete' : '◎ Calibration Needed'}
                  </h3>
                  <div className="text-secondary" style={{ fontSize:'0.75rem' }}>
                    {calibrationPoints.length} / {KP_COUNT} keypoints saved.
                  </div>
                </div>
                <button className="action-btn" onClick={() => setPage('calibration')}
                  style={{ height:'36px', fontSize:'0.75rem', borderColor: calibrationPoints.length === KP_COUNT ? '#10b981' : 'var(--accent-primary)', color: calibrationPoints.length === KP_COUNT ? '#10b981' : 'var(--accent-primary)' }}>
                  {calibrationPoints.length > 0 ? 'Edit Calibration' : 'Start Calibration'}
                </button>
              </div>
            </div>
          )}

          <div className="mt-4">
            <h3 className="section-title orbitron" style={{ fontSize:'1rem' }}>Advanced Parameters (JSON)</h3>
            <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
              <textarea className="kp-json"
                placeholder="Manual JSON Overrides: [[x1,y1],...]"
                value={courtKeypointsText}
                onChange={(ev) => { setCourtKeypointsText(ev.target.value); setKpFile(null) }}
                spellCheck={false}
                style={{ background:'#f8fafc', border:'1px solid #cbd5e1', color:'var(--text-primary)', padding:'1rem', width:'100%', borderRadius:'12px', minHeight:'80px' }}
              />
              <div style={{ position:'relative', overflow:'hidden', display:'inline-block' }}>
                <button className="action-btn" style={{ width:'100%', height:'40px', fontSize:'0.8rem', background:'rgba(14,165,233,0.05)' }}>
                  {kpFile ? `📁 ${kpFile.name}` : '📁 Upload Keypoints (.json)'}
                </button>
                <input type="file" accept=".json"
                  onChange={(e) => { setKpFile(e.target.files?.[0] || null); if (e.target.files?.[0]) setCourtKeypointsText('') }}
                  style={{ position:'absolute', top:0, left:0, width:'100%', height:'100%', opacity:0, cursor:'pointer' }}
                />
              </div>
            </div>
          </div>

          <button className="action-btn primary-btn mt-4" disabled={uploading || !videoFile} onClick={submitJob} style={{ width:'100%' }}>
            {uploading ? 'UPLOADING DATA...' : 'LAUNCH NEURAL ANALYSIS'}
          </button>
        </div>

        {/* Right: Status */}
        <div className="glass-card">
          <h2 className="section-title orbitron">Mission Status</h2>
          <div className="terminal">
            {jobId
              ? <div className="terminal-line text-accent">{`[SYSTEM] Job UUID: ${jobId}`}</div>
              : <div className="terminal-line text-secondary">[SYSTEM] Awaiting initialization...</div>}
            {jobStatus && (
              <div className="terminal-line">
                {`[SYSTEM] Status: `}
                <span className={jobStatus.status === 'completed' ? 'text-accent' : ''}>{jobStatus.status.toUpperCase()}</span>
              </div>
            )}
            {jobStatus?.progress !== undefined && (
              <div className="terminal-line">{`[SYSTEM] Processing: ${Math.round(jobStatus.progress * 100)}%`}</div>
            )}
            {error && <div className="terminal-line" style={{ color:'#dc2626' }}>{`[ERROR] ${error}`}</div>}
            {results && <div className="terminal-line text-accent">[SYSTEM] Neural processing complete.</div>}
          </div>

          {jobStatus && (
            <div className={`status-badge ${jobStatus.status === 'processing' ? 'status-running' : ''}`}>
              {jobStatus.status}
            </div>
          )}

          <div className="mt-4">
            <button className="action-btn" style={{ width:'100%', borderColor:'var(--accent-secondary)', color:'var(--accent-secondary)' }} onClick={setPreviewMode}>
              [DEV] PREVIEW DASHBOARD UI
            </button>
          </div>

          {recent.length > 0 && (
            <div className="mt-4">
              <h3 className="section-title orbitron" style={{ fontSize:'1rem' }}>Recent Operations</h3>
              <div className="button-group" style={{ gridTemplateColumns:'repeat(auto-fill, minmax(80px, 1fr))' }}>
                {recent.map((id) => (
                  <button key={id} className="action-btn" style={{ height:'36px', fontSize:'0.7rem' }}
                    onClick={() => { setUiDemoMode(false); setJobId(id); setResults(null); setAnalytics(null); setError('') }}>
                    {id.slice(0, 6)}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {(results || (uiDemoMode && analytics)) && (
        <div className="glass-card mt-4 analytics-dash">
          {analytics
            ? <AnalyticsDashboard analytics={analytics} apiBase={API_BASE} jobId={jobId} demoMode={uiDemoMode} />
            : <div className="text-center p-4"><div className="status-running mb-2"></div><p className="orbitron">Synthesizing Analytics...</p></div>
          }
          <details className="mt-4">
            <summary className="raw-data-trigger orbitron">Inspect Raw Neural Stream (JSON)</summary>
            <pre className="terminal mt-2" style={{ maxHeight:'400px' }}>{JSON.stringify(results, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  )
}
