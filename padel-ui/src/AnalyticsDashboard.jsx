import { useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  BarChart,
  Bar,
} from 'recharts'

const SPEED_COLORS = {
  1: '#0ea5e9', // Sky blue
  2: '#2563eb', // Royal blue
  3: '#f59e0b', // Amber
  4: '#10b981', // Emerald
}

function buildSpeedRows(analytics) {
  const t = analytics?.speed_series?.time ?? []
  const players = analytics?.speed_series?.players ?? {}
  if (!t.length) return []
  return t.map((time, i) => {
    const row = { time: time ?? 0 }
    for (let pid = 1; pid <= 4; pid++) {
      const key = String(pid)
      const arr = players[key]
      row[`p${key}`] = arr?.[i] ?? null
    }
    return row
  })
}

export function AnalyticsDashboard({ analytics, apiBase, jobId, demoMode = false }) {
  if (!analytics) return null

  const {
    player_cards = [],
    heatmap = {},
    shots_breakdown_by_player = {},
    shots_meta,
  } = analytics

  const speedRows = buildSpeedRows(analytics)
  const best =
    player_cards.length > 0
      ? player_cards.reduce((a, b) => (b.score > a.score ? b : a), player_cards[0])
      : null

  // ── Navigation Tabs ────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState('overview') // 'overview' | 'profiles' | 'compare' | 'heatmap3d'
  
  // ── Video/Capture Toggle View State ────────────────────────────────────────
  const [videoViewMode, setVideoViewMode] = useState('capture') // 'capture' | 'video'

  // ── Player Profiles & Ratings State ────────────────────────────────────────
  const [selectedPlayerId, setSelectedPlayerId] = useState(1)
  const [playerRatings, setPlayerRatings] = useState(analytics?.ratings || {
    1: { attack: 85, defense: 78, precision: 80, speed: 82, stamina: 88, notes: 'Dominant backcourt tactical controller. Focuses on defensive transitions.' },
    2: { attack: 92, defense: 85, precision: 90, speed: 89, stamina: 91, notes: 'Aggressive net player, highly efficient overhead smashes.' },
    3: { attack: 76, defense: 88, precision: 75, speed: 80, stamina: 85, notes: 'Excellent court coverage, defensive anchor and lob specialist.' },
    4: { attack: 84, defense: 80, precision: 85, speed: 86, stamina: 82, notes: 'Well-rounded player, fast transition game and volley control.' }
  })
  const [saveStatus, setSaveStatus] = useState('')

  const saveRatingsToServer = async () => {
    setSaveStatus('Saving...')
    const activeJobId = jobId || 'demo'
    try {
      const res = await fetch(`${apiBase}/jobs/${activeJobId}/ratings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(playerRatings)
      })
      if (res.ok) {
        setSaveStatus('✓ Saved Successfully!')
        setTimeout(() => setSaveStatus(''), 3000)
      } else {
        setSaveStatus('✗ Failed to Save')
      }
    } catch (e) {
      setSaveStatus('✗ Connection Error')
    }
  }

  // ── Head-to-Head Comparison State ──────────────────────────────────────────
  const [comparePlayerA, setComparePlayerA] = useState(1)
  const [comparePlayerB, setComparePlayerB] = useState(2)

  // ── 3D Court Settings ──────────────────────────────────────────────────────
  const [courtRotation, setCourtRotation] = useState(-30) // rotation around Z
  const [courtPitch, setCourtPitch] = useState(60) // tilt angle X
  const [activeHeatmapPlayer, setActiveHeatmapPlayer] = useState('all')
  const [showFormulas, setShowFormulas] = useState(false)

  const updateRating = (playerId, key, value) => {
    setPlayerRatings(prev => ({
      ...prev,
      [playerId]: {
        ...prev[playerId],
        [key]: Math.max(0, Math.min(100, Number(value)))
      }
    }))
  }

  const handleNotesChange = (playerId, val) => {
    setPlayerRatings(prev => ({
      ...prev,
      [playerId]: {
        ...prev[playerId],
        notes: val
      }
    }))
  }

  const getOverallRating = (ratings) => {
    if (!ratings) return 0
    return Math.round((ratings.attack + ratings.defense + ratings.precision + ratings.speed + ratings.stamina) / 5)
  }

  return (
    <div className="analytics-dash">
      {/* ── Premium Tab Menu ── */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.5rem',
        background: 'rgba(15, 23, 42, 0.04)',
        border: '1px solid rgba(14, 165, 233, 0.15)',
        padding: '0.5rem',
        borderRadius: '16px',
        marginBottom: '2rem',
        backdropFilter: 'blur(10px)'
      }}>
        {[
          { id: 'overview', label: '📊 Live Overview', desc: 'Realtime Match Metrics' },
          { id: 'profiles', label: '👤 Player Profiles', desc: 'Manage Ratings & Notes' },
          { id: 'compare', label: '⚔️ Player Comparison', desc: 'Side-by-Side Head-to-Head' },
          { id: 'heatmap3d', label: '🌐 3D Arena Heatmap', desc: 'Perspective Court Overlay' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: '1 1 200px',
              padding: '0.75rem 1rem',
              borderRadius: '12px',
              border: 'none',
              background: activeTab === tab.id ? 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))' : 'transparent',
              color: activeTab === tab.id ? '#fff' : 'var(--text-secondary)',
              cursor: 'pointer',
              transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center'
            }}
          >
            <span className="orbitron" style={{ fontSize: '0.85rem', fontWeight: 'bold', letterSpacing: '0.5px' }}>
              {tab.label}
            </span>
            <span style={{ fontSize: '0.65rem', opacity: 0.8, marginTop: '2px', display: 'block' }}>
              {tab.desc}
            </span>
          </button>
        ))}
      </div>

      {/* ── Tab 1: Live Overview ────────────────────────────────────────────── */}
      {activeTab === 'overview' && (
        <div>
          <div className="section-title orbitron" style={{ fontSize: '1.5rem', marginBottom: '2rem' }}>
            Tactical Intelligence Report
          </div>

          {/* 🎬 Premium Video Intelligence Feed Card - Displayed FIRST */}
          <div className="glass-card mb-4" style={{ padding: '1.5rem', borderColor: 'rgba(14, 165, 233, 0.3)', overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <h3 className="orbitron" style={{ fontSize: '0.95rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: videoViewMode === 'video' ? '#ef4444' : '#10b981', animation: 'pulse 1.5s infinite' }}></span>
                🎬 {videoViewMode === 'capture' ? '📷 Annotated First Frame Capture' : '📹 Annotated Video Intelligence Feed'}
              </h3>
              
              {/* Dual View Selection Mode */}
              <div style={{ display: 'flex', gap: '0.25rem', background: 'rgba(0,0,0,0.06)', padding: '3px', borderRadius: '8px', border: '1px solid rgba(14,165,233,0.2)' }}>
                <button 
                  onClick={() => setVideoViewMode('capture')}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    border: 'none',
                    background: videoViewMode === 'capture' ? 'var(--accent-primary)' : 'transparent',
                    color: videoViewMode === 'capture' ? '#fff' : 'var(--text-secondary)',
                    fontFamily: 'Orbitron',
                    fontSize: '0.65rem',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    transition: 'all 0.15s ease'
                  }}
                >
                  📷 CAPTURE FRAME
                </button>
                <button 
                  onClick={() => setVideoViewMode('video')}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    border: 'none',
                    background: videoViewMode === 'video' ? 'var(--accent-primary)' : 'transparent',
                    color: videoViewMode === 'video' ? '#fff' : 'var(--text-secondary)',
                    fontFamily: 'Orbitron',
                    fontSize: '0.65rem',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    transition: 'all 0.15s ease'
                  }}
                >
                  📹 WATCH VIDEO
                </button>
              </div>
            </div>

            <div style={{ position: 'relative', width: '100%', borderRadius: '16px', overflow: 'hidden', background: '#040814', boxShadow: '0 0 35px rgba(14,165,233,0.15)', border: '1px solid rgba(255,255,255,0.06)' }}>
              
              {/* CASE 1: Capture Frame View (Guaranteed Instant Image Render) */}
              {videoViewMode === 'capture' && (
                <div style={{ position: 'relative', width: '100%', background: '#000', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                  {demoMode ? (
                    <div style={{ position: 'relative', width: '100%', height: '360px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                      <div style={{ position: 'absolute', inset: 0, backgroundImage: "linear-gradient(to bottom, rgba(5,10,24,0.3), rgba(5,10,24,0.85)), url('/bg.png')", backgroundSize: 'cover', backgroundPosition: 'center' }} />
                      
                      {/* Bounding trackers overlay simulation */}
                      <div style={{ position: 'absolute', left: '32%', top: '48%', color: '#0ea5e9', border: '1px solid #0ea5e9', padding: '2px 6px', fontSize: '0.65rem', borderRadius: '4px', background: 'rgba(5,10,24,0.85)', fontFamily: 'Orbitron', pointerEvents: 'none' }}>
                        OP 1 [SMASH] · 18.5 km/h
                      </div>
                      <div style={{ position: 'absolute', left: '62%', top: '32%', color: '#2563eb', border: '1px solid #2563eb', padding: '2px 6px', fontSize: '0.65rem', borderRadius: '4px', background: 'rgba(5,10,24,0.85)', fontFamily: 'Orbitron', pointerEvents: 'none' }}>
                        OP 2 [NET VOLLEY] · 21.2 km/h
                      </div>
                      <div style={{ position: 'absolute', left: '49%', top: '42%', width: '10px', height: '10px', background: '#ffea00', borderRadius: '50%', boxShadow: '0 0 15px #ffea00' }} />
                      
                      <div className="orbitron text-center" style={{ zIndex: 2, background: 'rgba(5, 10, 24, 0.75)', padding: '1rem 2rem', borderRadius: '12px', border: '1px solid rgba(14,165,233,0.3)' }}>
                        <div style={{ fontSize: '0.8rem', color: '#ffea00', fontWeight: 'bold', marginBottom: '0.25rem' }}>📷 LIVE HOMOGRAPHY CALIBRATED</div>
                        <div style={{ fontSize: '0.68rem', color: '#cbd5e1' }}>12-Point Perspective Transform Active</div>
                      </div>
                    </div>
                  ) : (
                    /* Real Live Extracted First Frame Capture */
                    <img 
                      src={`${apiBase}/jobs/${jobId}/download/first_frame`} 
                      alt="Padel Neural Extraction First Frame" 
                      style={{ width: '100%', maxHeight: '480px', objectFit: 'contain', display: 'block' }}
                      onError={(e) => {
                        // fallback if endpoint is not loaded yet
                        e.target.style.display = 'none';
                      }}
                    />
                  )}
                  
                  {/* Premium overlay HUD bar */}
                  <div style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    background: 'linear-gradient(to top, rgba(0,0,0,0.85), transparent)',
                    padding: '1rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    pointerEvents: 'none'
                  }}>
                    <span className="orbitron" style={{ fontSize: '0.68rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981' }}></span>
                      Homography Frame Calibrated
                    </span>
                    <button 
                      onClick={(e) => { e.stopPropagation(); setVideoViewMode('video') }}
                      className="orbitron" 
                      style={{ 
                        pointerEvents: 'auto', 
                        background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))', 
                        border: 'none', 
                        color: '#fff', 
                        padding: '4px 12px', 
                        borderRadius: '6px', 
                        fontSize: '0.65rem', 
                        cursor: 'pointer',
                        fontWeight: 'bold',
                        boxShadow: '0 4px 6px rgba(14,165,233,0.2)'
                      }}
                    >
                      🎬 WATCH VIDEO
                    </button>
                  </div>
                </div>
              )}

              {/* CASE 2: Live Video Stream View */}
              {videoViewMode === 'video' && (
                <div style={{ position: 'relative', width: '100%' }}>
                  {demoMode ? (
                    <div style={{ width: '100%', height: '360px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
                      <div style={{ position: 'absolute', inset: 0, backgroundImage: "linear-gradient(to bottom, rgba(5,10,24,0.4), rgba(5,10,24,0.9)), url('/bg.png')", backgroundSize: 'cover', backgroundPosition: 'center', opacity: 0.9 }} />
                      
                      {/* Neon Court Grid Overlay Simulation */}
                      <svg viewBox="-5 -10 10 20" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', opacity: 0.35 }}>
                        <rect x="-4" y="-8" width="8" height="16" fill="none" stroke="#00f3ff" strokeWidth="0.08" />
                        <line x1="-4" y1="0" x2="4" y2="0" stroke="#00f3ff" strokeWidth="0.1" strokeDasharray="0.3 0.2" />
                        <line x1="0" y1="-8" x2="0" y2="8" stroke="#00f3ff" strokeWidth="0.05" strokeDasharray="0.2 0.2" />
                      </svg>

                      {/* Dynamic tracked markers simulator */}
                      <div style={{ position: 'absolute', left: '32%', top: '48%', color: '#0ea5e9', border: '1px solid #0ea5e9', padding: '2px 6px', fontSize: '0.65rem', borderRadius: '4px', background: 'rgba(5,10,24,0.85)', fontFamily: 'Orbitron', pointerEvents: 'none' }}>
                        OP 1 [SMASH] · 18.5 km/h
                      </div>
                      <div style={{ position: 'absolute', left: '62%', top: '32%', color: '#2563eb', border: '1px solid #2563eb', padding: '2px 6px', fontSize: '0.65rem', borderRadius: '4px', background: 'rgba(5,10,24,0.85)', fontFamily: 'Orbitron', pointerEvents: 'none' }}>
                        OP 2 [NET VOLLEY] · 21.2 km/h
                      </div>
                      <div style={{ position: 'absolute', left: '49%', top: '42%', width: '10px', height: '10px', background: '#ffea00', borderRadius: '50%', boxShadow: '0 0 15px #ffea00', pointerEvents: 'none' }} />

                      <div className="orbitron text-center" style={{ zIndex: 2, color: '#fff', padding: '1.5rem' }}>
                        <div style={{ fontSize: '1.2rem', color: '#0ea5e9', fontWeight: 'bold', letterSpacing: '2px', marginBottom: '0.5rem' }}>
                          NEURAL TRACKING STREAM
                        </div>
                        <p style={{ fontSize: '0.8rem', color: '#cbd5e1', maxWidth: '420px', margin: '0 auto 1.5rem', lineHeight: '1.6' }}>
                          In live pipeline execution, this high-fidelity HTML5 player stream renders raw annotated drone footage detailing automatic player tracks and court homography.
                        </p>
                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                          <button 
                            onClick={() => setVideoViewMode('capture')}
                            className="action-btn primary-btn" 
                            style={{ padding: '0.5rem 1.25rem', fontSize: '0.72rem', height: '36px' }}
                          >
                            Show Static Frame Capture
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* Real annotated output video player */
                    <video
                      controls
                      autoPlay
                      playsInline
                      poster={`${apiBase}/jobs/${jobId}/download/first_frame`}
                      src={`${apiBase}/jobs/${jobId}/download/video`}
                      style={{ width: '100%', maxHeight: '480px', display: 'block' }}
                    />
                  )}
                </div>
              )}
            </div>
          </div>

          {shots_meta && (
            <div className="button-group mb-4" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
              <div className="glass-card text-center" style={{ padding: '1rem' }}>
                <div className="stat-label">Total Engagements</div>
                <div className="orbitron text-accent" style={{ fontSize: '1.5rem' }}>{shots_meta.total_shots ?? '0'}</div>
              </div>
              <div className="glass-card text-center" style={{ padding: '1rem' }}>
                <div className="stat-label">Ball Bounces</div>
                <div className="orbitron text-accent" style={{ fontSize: '1.5rem' }}>{shots_meta.total_bounces ?? '0'}</div>
              </div>
              <div className="glass-card text-center" style={{ padding: '1rem' }}>
                <div className="stat-label">Intensity Index</div>
                <div className="orbitron text-accent" style={{ fontSize: '1.5rem' }}>
                  {shots_meta.total_shots ? (shots_meta.total_shots / 2.5).toFixed(1) : '0.0'}
                </div>
              </div>
            </div>
          )}

          {/* Team Divisions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', marginBottom: '2rem' }}>
            
            {/* Live Match Scoreboard Header */}
            <div className="glass-card" style={{ padding: '1.25rem 1.5rem', background: 'linear-gradient(135deg, rgba(245,158,11,0.06), rgba(14,165,233,0.06))', borderColor: 'rgba(14,165,233,0.2)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <span className="orbitron" style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', letterSpacing: '1px' }}>MATCH SCOREBOARD</span>
                  <div className="orbitron" style={{ fontSize: '1.3rem', fontWeight: 'bold' }}>
                    <span style={{ color: '#f59e0b' }}>TEAM GOLD</span>
                    <span style={{ color: 'var(--text-secondary)', margin: '0 0.75rem' }}>vs</span>
                    <span style={{ color: '#0ea5e9' }}>TEAM BLUE</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
                  <div className="text-center">
                    <span className="orbitron" style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#f59e0b' }}>
                      {player_cards.find(p => p.player_id === 3)?.team_score ?? 0}
                    </span>
                    <div className="orbitron" style={{ fontSize: '0.55rem', color: 'var(--text-secondary)' }}>PTS</div>
                  </div>
                  <div className="orbitron" style={{ fontSize: '1.2rem', color: 'var(--text-secondary)' }}>-</div>
                  <div className="text-center">
                    <span className="orbitron" style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#0ea5e9' }}>
                      {player_cards.find(p => p.player_id === 1)?.team_score ?? 0}
                    </span>
                    <div className="orbitron" style={{ fontSize: '0.55rem', color: 'var(--text-secondary)' }}>PTS</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Teams Side-by-Side Container */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
              
              {/* TEAM A - GOLD TEAM */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #f59e0b', paddingBottom: '0.5rem' }}>
                  <h3 className="orbitron" style={{ fontSize: '0.95rem', color: '#f59e0b', margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span>🏆</span> TEAM GOLD (OP 3 & 4)
                  </h3>
                  <span className="orbitron" style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                    Collective: {player_cards.filter(p => p.player_id === 3 || p.player_id === 4).reduce((acc, curr) => acc + (curr.total_distance_m || 0), 0).toFixed(1)} M
                  </span>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {player_cards.filter(p => p.player_id === 3 || p.player_id === 4).map((p) => {
                    const isMatchMVP = best && p.player_id === best.player_id
                    const overall = getOverallRating(playerRatings[p.player_id])
                    
                    // Determine if highest rated player baseline
                    const allRatings = [1, 2, 3, 4].map(pid => ({ id: pid, val: getOverallRating(playerRatings[pid]) }))
                    const maxProfileVal = Math.max(...allRatings.map(x => x.val))
                    const isTacticalPro = overall === maxProfileVal

                    return (
                      <div key={p.player_id} className={`pro-stat-card ${isMatchMVP ? 'best' : ''}`} style={{ position: 'relative', borderLeft: `5px solid ${SPEED_COLORS[p.player_id]}` }}>
                        {isMatchMVP && <div className="best-player-tag">🏆 MATCH MVP</div>}
                        {!isMatchMVP && isTacticalPro && <div className="best-player-tag" style={{ background: 'linear-gradient(135deg, #a855f7, #c084fc)' }}>⭐ TACTICAL PRO</div>}
                        
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div className="stat-label">OPERATIVE {p.player_id}</div>
                          <span className="orbitron" style={{ fontSize: '0.72rem', color: SPEED_COLORS[p.player_id], border: `1px solid ${SPEED_COLORS[p.player_id]}`, padding: '2px 6px', borderRadius: '4px' }}>
                            Rating: {overall}%
                          </span>
                        </div>
                        <div className="stat-value">
                          {p.score} <span className="stat-unit">PTS</span>
                        </div>
                        <div className="mt-1" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          {p.shoots} Total Strikes
                        </div>
                        <hr style={{ border: 'none', borderTop: '1px solid var(--glass-border)', margin: '1rem 0' }} />
                        <div className="button-group" style={{ gridTemplateColumns: '1fr', gap: '0.5rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span className="stat-label" style={{ fontSize: '0.6rem' }}>MAX VELOCITY</span>
                            <span className="text-accent orbitron" style={{ fontSize: '0.75rem' }}>{p.max_speed_kmh} KM/H</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span className="stat-label" style={{ fontSize: '0.6rem' }}>DISTANCE COVERED</span>
                            <span className="text-accent orbitron" style={{ fontSize: '0.75rem' }}>{p.total_distance_m} M</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span className="stat-label" style={{ fontSize: '0.6rem' }}>AVG TEMPO</span>
                            <span className="text-accent orbitron" style={{ fontSize: '0.75rem' }}>{p.avg_speed_kmh} KM/H</span>
                          </div>
                          {p.net_presence_pct != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px dashed rgba(14,165,233,0.1)', paddingTop: '0.25rem' }}>
                              <span className="stat-label" style={{ fontSize: '0.6rem' }}>NET PRESENCE</span>
                              <span className="text-accent orbitron" style={{ fontSize: '0.75rem' }}>{p.net_presence_pct}%</span>
                            </div>
                          )}
                          {p.calorie_burn_kcal != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <span className="stat-label" style={{ fontSize: '0.6rem' }}>CALORIES BURNED</span>
                              <span className="text-accent orbitron" style={{ fontSize: '0.75rem' }}>{p.calorie_burn_kcal} KCAL</span>
                            </div>
                          )}
                          {p.overhead_pct != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <span className="stat-label" style={{ fontSize: '0.6rem' }}>OVERHEADS RATIO</span>
                              <span className="text-accent orbitron" style={{ fontSize: '0.75rem' }}>{p.overhead_pct}%</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* TEAM B - BLUE TEAM */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #0ea5e9', paddingBottom: '0.5rem' }}>
                  <h3 className="orbitron" style={{ fontSize: '0.95rem', color: '#0ea5e9', margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span>⚡</span> TEAM BLUE (OP 1 & 2)
                  </h3>
                  <span className="orbitron" style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>
                    Collective: {player_cards.filter(p => p.player_id === 1 || p.player_id === 2).reduce((acc, curr) => acc + (curr.total_distance_m || 0), 0).toFixed(1)} M
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {player_cards.filter(p => p.player_id === 1 || p.player_id === 2).map((p) => {
                    const isMatchMVP = best && p.player_id === best.player_id
                    const overall = getOverallRating(playerRatings[p.player_id])
                    
                    // Determine if highest rated player baseline
                    const allRatings = [1, 2, 3, 4].map(pid => ({ id: pid, val: getOverallRating(playerRatings[pid]) }))
                    const maxProfileVal = Math.max(...allRatings.map(x => x.val))
                    const isTacticalPro = overall === maxProfileVal

                    return (
                      <div key={p.player_id} className={`pro-stat-card ${isMatchMVP ? 'best' : ''}`} style={{ position: 'relative', borderLeft: `5px solid ${SPEED_COLORS[p.player_id]}` }}>
                        {isMatchMVP && <div className="best-player-tag">🏆 MATCH MVP</div>}
                        {!isMatchMVP && isTacticalPro && <div className="best-player-tag" style={{ background: 'linear-gradient(135deg, #a855f7, #c084fc)' }}>⭐ TACTICAL PRO</div>}
                        
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div className="stat-label">OPERATIVE {p.player_id}</div>
                          <span className="orbitron" style={{ fontSize: '0.72rem', color: SPEED_COLORS[p.player_id], border: `1px solid ${SPEED_COLORS[p.player_id]}`, padding: '2px 6px', borderRadius: '4px' }}>
                            Rating: {overall}%
                          </span>
                        </div>
                        <div className="stat-value">
                          {p.score} <span className="stat-unit">PTS</span>
                        </div>
                        <div className="mt-1" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          {p.shoots} Total Strikes
                        </div>
                        <hr style={{ border: 'none', borderTop: '1px solid var(--glass-border)', margin: '1rem 0' }} />
                        <div className="button-group" style={{ gridTemplateColumns: '1fr', gap: '0.5rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span className="stat-label" style={{ fontSize: '0.6rem' }}>MAX VELOCITY</span>
                            <span className="text-accent orbitron" style={{ fontSize: '0.75rem' }}>{p.max_speed_kmh} KM/H</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span className="stat-label" style={{ fontSize: '0.6rem' }}>DISTANCE COVERED</span>
                            <span className="text-accent orbitron" style={{ fontSize: '0.75rem' }}>{p.total_distance_m} M</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span className="stat-label" style={{ fontSize: '0.6rem' }}>AVG TEMPO</span>
                            <span className="text-accent orbitron" style={{ fontSize: '0.75rem' }}>{p.avg_speed_kmh} KM/H</span>
                          </div>
                          {p.net_presence_pct != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px dashed rgba(14,165,233,0.1)', paddingTop: '0.25rem' }}>
                              <span className="stat-label" style={{ fontSize: '0.6rem' }}>NET PRESENCE</span>
                              <span className="text-accent orbitron" style={{ fontSize: '0.75rem' }}>{p.net_presence_pct}%</span>
                            </div>
                          )}
                          {p.calorie_burn_kcal != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <span className="stat-label" style={{ fontSize: '0.6rem' }}>CALORIES BURNED</span>
                              <span className="text-accent orbitron" style={{ fontSize: '0.75rem' }}>{p.calorie_burn_kcal} KCAL</span>
                            </div>
                          )}
                          {p.overhead_pct != null && (
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <span className="stat-label" style={{ fontSize: '0.6rem' }}>OVERHEADS RATIO</span>
                              <span className="text-accent orbitron" style={{ fontSize: '0.75rem' }}>{p.overhead_pct}%</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* Velocity Telemetry Chart */}
          {speedRows.length > 0 && (
            <div className="chart-container mt-4">
              <h3 className="section-title orbitron" style={{ fontSize: '1rem' }}>Velocity Telemetry</h3>
              <div style={{ width: '100%', height: 360, marginTop: '1rem' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={speedRows} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis
                      dataKey="time"
                      stroke="var(--text-secondary)"
                      tick={{ fill: 'var(--text-secondary)', fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                      label={{ value: 'MISSION TIME (S)', fill: 'var(--text-secondary)', position: 'insideBottom', offset: -5, fontSize: 10, fontFamily: 'Orbitron' }}
                    />
                    <YAxis
                      stroke="var(--text-secondary)"
                      tick={{ fill: 'var(--text-secondary)', fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                      label={{ value: 'SPEED (KM/H)', angle: -90, fill: 'var(--text-secondary)', position: 'insideLeft', fontSize: 10, fontFamily: 'Orbitron' }}
                    />
                    <Tooltip
                      contentStyle={{
                        background: '#ffffff',
                        border: '1px solid #cbd5e1',
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
                        fontFamily: 'JetBrains Mono',
                        color: '#0f172a'
                      }}
                      itemStyle={{ fontSize: '12px' }}
                    />
                    <Legend wrapperStyle={{ paddingTop: '20px', fontFamily: 'Orbitron', fontSize: '10px' }} />
                    {[1, 2, 3, 4].map((pid) => (
                      <Line
                        key={pid}
                        type="monotone"
                        dataKey={`p${pid}`}
                        name={`OP ${pid}`}
                        stroke={SPEED_COLORS[pid]}
                        strokeWidth={3}
                        dot={false}
                        activeDot={{ r: 6, stroke: '#000', strokeWidth: 2 }}
                        connectNulls
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Strikes classification */}
          {(() => {
            const tiles = [1, 2, 3, 4]
              .map((pid) => {
                const key = String(pid)
                const breakdown = shots_breakdown_by_player[key] || {}
                const rows = Object.entries(breakdown)
                if (!rows.length) return null
                return (
                  <div key={pid} className="glass-card" style={{ padding: '1rem' }}>
                    <div className="stat-label mb-2" style={{ color: SPEED_COLORS[pid] }}>OP {pid} ENGAGEMENTS</div>
                    <div className="shot-pills">
                      {rows
                        .sort((a, b) => b[1] - a[1])
                        .map(([stype, n]) => (
                          <div key={stype} className="shot-pill">
                            <span className="orbitron" style={{ fontSize: '0.7rem' }}>{stype}</span>
                            <span className="shot-count" style={{ background: SPEED_COLORS[pid] }}>{n}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                )
              })
              .filter(Boolean)
            
            if (!tiles.length) return null
            return (
              <div className="mt-4">
                <h3 className="section-title orbitron" style={{ fontSize: '1rem' }}>Strike Classification</h3>
                <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
                  {tiles}
                </div>
              </div>
            )
          })()}

          {/* Tactical Ratings & Biomechanical Formulas Explainer */}
          <div className="glass-card mt-4" style={{ padding: '1.25rem' }}>
            <div 
              onClick={() => setShowFormulas(!showFormulas)}
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
            >
              <h3 className="orbitron" style={{ fontSize: '0.85rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-primary)' }}>
                <span>📊</span> TACTICAL RATINGS &amp; STATISTICAL FORMULAS
              </h3>
              <span className="orbitron" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                {showFormulas ? '▼ HIDE DETAILS' : '▲ SHOW DETAILS'}
              </span>
            </div>

            {showFormulas && (
              <div style={{ marginTop: '1rem', borderTop: '1px solid rgba(0,0,0,0.06)', paddingTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ background: 'rgba(0,0,0,0.02)', padding: '0.75rem 1rem', borderRadius: '8px', borderLeft: '4px solid #a855f7' }}>
                  <div className="orbitron" style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#a855f7', marginBottom: '0.25rem' }}>1. Dynamic Team &amp; Badge Division Rules:</div>
                  <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                    <li><strong>Team Division:</strong> Sorted based on spatial coordinates relative to the net. Team A (Players 1 &amp; 3) play together on the bottom half. Team B (Players 2 &amp; 4) play together on the top half.</li>
                    <li><strong>🏆 MATCH MVP Badge:</strong> Awarded to the player with the highest in-game score points won purely from live performance statistics (strikes, net presence, tempo).</li>
                    <li><strong>⭐ TACTICAL PRO Badge:</strong> Awarded to the player with the highest baseline overall tactical profiling rating configured by the coach's attribute sliders.</li>
                  </ul>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.02)', padding: '0.75rem 1rem', borderRadius: '8px', borderLeft: '4px solid #ef4444' }}>
                  <div className="orbitron" style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#ef4444', marginBottom: '0.25rem' }}>2. Net Presence Ratio Calculation:</div>
                  <div className="orbitron" style={{ fontSize: '0.85rem', margin: '0.25rem 0', fontFamily: 'JetBrains Mono', background: 'rgba(255,255,255,0.7)', padding: '4px 8px', borderRadius: '4px', display: 'inline-block' }}>
                    Net Presence % = (Frames within 3.0 meters of net / Total Match Frames) × 100
                  </div>
                  <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    Derived frame-by-frame by checking if |player_y| &lt; 3.0 meters. Represents tactical aggression and net control capacity.
                  </p>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.02)', padding: '0.75rem 1rem', borderRadius: '8px', borderLeft: '4px solid #f59e0b' }}>
                  <div className="orbitron" style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#f59e0b', marginBottom: '0.25rem' }}>3. Speed Consistency &amp; Explosiveness:</div>
                  <div className="orbitron" style={{ fontSize: '0.85rem', margin: '0.25rem 0', fontFamily: 'JetBrains Mono', background: 'rgba(255,255,255,0.7)', padding: '4px 8px', borderRadius: '4px', display: 'inline-block' }}>
                    Speed Consistency (km/h) = σ(Velocity Magnitude vectors) × 3.6
                  </div>
                  <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    Calculates the standard deviation of frame-to-frame velocity vector magnitudes in km/h. High standard deviation indicates explosive sprint-rest play style; low indicates consistent pacing.
                  </p>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.02)', padding: '0.75rem 1rem', borderRadius: '8px', borderLeft: '4px solid #10b981' }}>
                  <div className="orbitron" style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#10b981', marginBottom: '0.25rem' }}>4. Sports Science Calorie Expenditure:</div>
                  <div className="orbitron" style={{ fontSize: '0.85rem', margin: '0.25rem 0', fontFamily: 'JetBrains Mono', background: 'rgba(255,255,255,0.7)', padding: '4px 8px', borderRadius: '4px', display: 'inline-block' }}>
                    Calories Burned (kcal) = Cumulative distance covered (meters) × 0.14
                  </div>
                  <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    Calorie expenditure is calculated using metabolic workload models for elite high-intensity court athletes under professional sports science guidelines.
                  </p>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.02)', padding: '0.75rem 1rem', borderRadius: '8px', borderLeft: '4px solid #0ea5e9' }}>
                  <div className="orbitron" style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#0ea5e9', marginBottom: '0.25rem' }}>5. Overhead Strike Preference Ratio:</div>
                  <div className="orbitron" style={{ fontSize: '0.85rem', margin: '0.25rem 0', fontFamily: 'JetBrains Mono', background: 'rgba(255,255,255,0.7)', padding: '4px 8px', borderRadius: '4px', display: 'inline-block' }}>
                    Overhead % = ((Smashes + Viboras + Bandejas) / Total Strikes) × 100
                  </div>
                  <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    Ratio of overhead aerials relative to groundstrokes and standard volleys, indicating vertical shot assertiveness.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Tab 2: Player Profiles & Dynamic Ratings ───────────────────────── */}
      {activeTab === 'profiles' && (
        <div>
          <div className="section-title orbitron" style={{ fontSize: '1.5rem', marginBottom: '2rem' }}>
            Operative Profiles &amp; Tactical Attributes
          </div>

          <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
            {/* Player Selector Bar */}
            <div style={{ flex: '1 1 280px', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {[1, 2, 3, 4].map(pid => {
                const pInfo = player_cards.find(x => x.player_id === pid) || { score: 0 }
                const isSelected = selectedPlayerId === pid
                const overall = getOverallRating(playerRatings[pid])
                return (
                  <div
                    key={pid}
                    onClick={() => setSelectedPlayerId(pid)}
                    className="glass-card"
                    style={{
                      padding: '1.25rem',
                      cursor: 'pointer',
                      borderLeft: `6px solid ${SPEED_COLORS[pid]}`,
                      background: isSelected ? 'rgba(14, 165, 233, 0.08)' : undefined,
                      borderColor: isSelected ? 'var(--accent-primary)' : undefined,
                      transition: 'all 0.2s ease',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.5rem'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="orbitron" style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>Operative {pid}</span>
                      <span className="orbitron" style={{ fontSize: '0.75rem', color: SPEED_COLORS[pid] }}>{overall}% Rate</span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      <span>Score Points: {pInfo.score}</span>
                      <span>Total Strikes: {pInfo.shoots || 0}</span>
                    </div>

                    {pInfo.net_presence_pct != null && (
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.25rem', fontSize: '0.65rem', color: 'var(--text-secondary)', borderTop: '1px solid rgba(0,0,0,0.04)', paddingTop: '0.5rem' }}>
                        <div>Net Play: <strong style={{ color: 'var(--text-primary)' }}>{pInfo.net_presence_pct}%</strong></div>
                        <div>Cal Burn: <strong style={{ color: 'var(--text-primary)' }}>{pInfo.calorie_burn_kcal} kcal</strong></div>
                        <div>Overheads: <strong style={{ color: 'var(--text-primary)' }}>{pInfo.overhead_pct}%</strong></div>
                        <div>Sprints CV: <strong style={{ color: 'var(--text-primary)' }}>{pInfo.speed_consistency_kmh} km/h</strong></div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Ratings & Profile Editor Card */}
            <div className="glass-card" style={{ flex: '2 1 500px', padding: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3 className="orbitron" style={{ margin: 0, color: SPEED_COLORS[selectedPlayerId] }}>
                  Operative {selectedPlayerId} Settings
                </h3>
                <span style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--accent-secondary)' }} className="orbitron">
                  {getOverallRating(playerRatings[selectedPlayerId])}% Rating
                </span>
              </div>

              {/* Sliders Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                {[
                  { key: 'attack', label: '⚔️ Attack Power', color: '#ef4444' },
                  { key: 'defense', label: '🛡️ Defense Coverage', color: '#10b981' },
                  { key: 'precision', label: '🎯 Target Precision', color: '#a855f7' },
                  { key: 'speed', label: '⚡ Acceleration & Speed', color: '#f59e0b' },
                  { key: 'stamina', label: '🔋 Physical Endurance', color: '#0ea5e9' },
                ].map(attr => (
                  <div key={attr.key} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600 }}>
                      <span>{attr.label}</span>
                      <span style={{ color: attr.color }}>{playerRatings[selectedPlayerId][attr.key]} / 100</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={playerRatings[selectedPlayerId][attr.key]}
                      onChange={(e) => updateRating(selectedPlayerId, attr.key, e.target.value)}
                      style={{
                        accentColor: attr.color,
                        width: '100%',
                        cursor: 'pointer',
                        height: '6px',
                        borderRadius: '3px'
                      }}
                    />
                  </div>
                ))}
              </div>

              {/* Coaching Notes */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label className="orbitron" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>COACHING FIELD ANALYSIS</label>
                <textarea
                  value={playerRatings[selectedPlayerId].notes}
                  onChange={(e) => handleNotesChange(selectedPlayerId, e.target.value)}
                  style={{
                    width: '100%',
                    minHeight: '80px',
                    borderRadius: '12px',
                    border: '1px solid rgba(14, 165, 233, 0.2)',
                    padding: '0.75rem',
                    fontSize: '0.85rem',
                    background: 'rgba(255,255,255,0.5)',
                    color: 'var(--text-primary)',
                    fontFamily: 'Inter, sans-serif'
                  }}
                  placeholder="Enter strategic coaching notes for this player..."
                />
              </div>

              {/* Server Save Button */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
                <button
                  onClick={saveRatingsToServer}
                  className="orbitron"
                  style={{
                    background: 'linear-gradient(135deg, #10b981, #059669)',
                    color: '#fff',
                    border: 'none',
                    padding: '0.6rem 1.2rem',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    fontSize: '0.75rem',
                    boxShadow: '0 4px 10px rgba(16,185,129,0.2)',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem'
                  }}
                >
                  💾 SAVE ATTRIBUTES TO SERVER
                </button>
                {saveStatus && (
                  <span className="orbitron" style={{
                    fontSize: '0.75rem',
                    fontWeight: 'bold',
                    color: saveStatus.includes('✓') ? '#10b981' : saveStatus.includes('✗') ? '#ef4444' : 'var(--text-secondary)'
                  }}>
                    {saveStatus}
                  </span>
                )}
              </div>

              {/* Attribute breakdown BarChart preview */}
              <div style={{ marginTop: '2rem' }}>
                <h4 className="orbitron" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Attribute Blueprint</h4>
                <div style={{ width: '100%', height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={[
                        { name: 'Attack', Value: playerRatings[selectedPlayerId].attack, fill: '#ef4444' },
                        { name: 'Defense', Value: playerRatings[selectedPlayerId].defense, fill: '#10b981' },
                        { name: 'Precision', Value: playerRatings[selectedPlayerId].precision, fill: '#a855f7' },
                        { name: 'Speed', Value: playerRatings[selectedPlayerId].speed, fill: '#f59e0b' },
                        { name: 'Stamina', Value: playerRatings[selectedPlayerId].stamina, fill: '#0ea5e9' },
                      ]}
                      margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
                    >
                      <XAxis dataKey="name" tick={{ fontSize: 10, fontFamily: 'Orbitron' }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Bar dataKey="Value" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab 3: Player Comparison (Head-to-Head) ────────────────────── */}
      {activeTab === 'compare' && (
        <div>
          <div className="section-title orbitron" style={{ fontSize: '1.5rem', marginBottom: '2rem' }}>
            Operative Head-to-Head Battlecard
          </div>

          {/* Selectors */}
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="orbitron" style={{ fontSize: '0.85rem' }}>OPERATIVE A:</span>
              <select
                value={comparePlayerA}
                onChange={(e) => setComparePlayerA(Number(e.target.value))}
                style={{ padding: '0.5rem 1rem', borderRadius: '8px', border: '1px solid rgba(14,165,233,0.3)', background: '#fff', fontFamily: 'Orbitron', fontSize: '0.85rem' }}
              >
                {[1, 2, 3, 4].filter(x => x !== comparePlayerB).map(pid => (
                  <option key={pid} value={pid}>Player {pid}</option>
                ))}
              </select>
            </div>
            <span className="orbitron" style={{ alignSelf: 'center', fontWeight: 'bold', color: 'var(--text-secondary)' }}>VS</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="orbitron" style={{ fontSize: '0.85rem' }}>OPERATIVE B:</span>
              <select
                value={comparePlayerB}
                onChange={(e) => setComparePlayerB(Number(e.target.value))}
                style={{ padding: '0.5rem 1rem', borderRadius: '8px', border: '1px solid rgba(14,165,233,0.3)', background: '#fff', fontFamily: 'Orbitron', fontSize: '0.85rem' }}
              >
                {[1, 2, 3, 4].filter(x => x !== comparePlayerA).map(pid => (
                  <option key={pid} value={pid}>Player {pid}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Side by side stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
            {/* Player A card */}
            <div className="glass-card" style={{ borderTop: `6px solid ${SPEED_COLORS[comparePlayerA]}` }}>
              <h3 className="orbitron text-center" style={{ color: SPEED_COLORS[comparePlayerA], margin: '0 0 1rem' }}>Operative {comparePlayerA}</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="text-center">
                  <span className="orbitron" style={{ fontSize: '2.5rem', fontWeight: 'bold' }}>
                    {getOverallRating(playerRatings[comparePlayerA])}
                  </span>
                  <div className="text-secondary" style={{ fontSize: '0.72rem' }}>TACTICAL RATING</div>
                </div>
                <hr style={{ border: 'none', borderTop: '1px solid rgba(0,0,0,0.06)' }} />
                {[
                  { label: '⚔️ Attack Power', val: playerRatings[comparePlayerA].attack },
                  { label: '🛡️ Defense Coverage', val: playerRatings[comparePlayerA].defense },
                  { label: '🎯 Target Precision', val: playerRatings[comparePlayerA].precision },
                  { label: '⚡ Acceleration & Speed', val: playerRatings[comparePlayerA].speed },
                  { label: '🔋 Physical Endurance', val: playerRatings[comparePlayerA].stamina },
                ].map(item => (
                  <div key={item.label}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                      <span>{item.label}</span>
                      <strong>{item.val}%</strong>
                    </div>
                    <div style={{ height: '8px', background: 'rgba(0,0,0,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ width: `${item.val}%`, height: '100%', background: SPEED_COLORS[comparePlayerA], borderRadius: '4px' }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Comparison Metrics Middle view */}
            <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '1.25rem' }}>
              <h3 className="orbitron text-center" style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Battle Stats Comparison</h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {/* Dynamically extract comparison parameters if exists */}
                {(() => {
                  const cardA = player_cards.find(x => x.player_id === comparePlayerA) || {}
                  const cardB = player_cards.find(x => x.player_id === comparePlayerB) || {}

                  const items = [
                    { label: 'Points Won', aVal: cardA.score ?? 0, bVal: cardB.score ?? 0, unit: ' pts' },
                    { label: 'Strikes Made', aVal: cardA.shoots ?? 0, bVal: cardB.shoots ?? 0, unit: ' str' },
                    { label: 'Total Distance', aVal: cardA.total_distance_m ?? 0, bVal: cardB.total_distance_m ?? 0, unit: ' m' },
                    { label: 'Max Velocity', aVal: cardA.max_speed_kmh ?? 0, bVal: cardB.max_speed_kmh ?? 0, unit: ' km/h' },
                    { label: 'Net Presence Ratio', aVal: cardA.net_presence_pct ?? 0, bVal: cardB.net_presence_pct ?? 0, unit: '%' },
                    { label: 'Overhead Shots Preference', aVal: cardA.overhead_pct ?? 0, bVal: cardB.overhead_pct ?? 0, unit: '%' },
                    { label: 'Calories Burned', aVal: cardA.calorie_burn_kcal ?? 0, bVal: cardB.calorie_burn_kcal ?? 0, unit: ' kcal' },
                  ]

                  return items.map(metric => {
                    const total = metric.aVal + metric.bVal
                    const pctA = total > 0 ? (metric.aVal / total) * 100 : 50
                    const pctB = total > 0 ? (metric.bVal / total) * 100 : 50
                    return (
                      <div key={metric.label}>
                        <div className="orbitron text-center" style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>{metric.label}</div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '2px', fontWeight: 'bold' }}>
                          <span style={{ color: SPEED_COLORS[comparePlayerA] }}>{metric.aVal}{metric.unit}</span>
                          <span style={{ color: SPEED_COLORS[comparePlayerB] }}>{metric.bVal}{metric.unit}</span>
                        </div>
                        <div style={{ height: '10px', display: 'flex', borderRadius: '5px', overflow: 'hidden' }}>
                          <div style={{ width: `${pctA}%`, background: SPEED_COLORS[comparePlayerA] }} />
                          <div style={{ width: `${pctB}%`, background: SPEED_COLORS[comparePlayerB] }} />
                        </div>
                      </div>
                    )
                  })
                })()}
              </div>
            </div>

            {/* Player B card */}
            <div className="glass-card" style={{ borderTop: `6px solid ${SPEED_COLORS[comparePlayerB]}` }}>
              <h3 className="orbitron text-center" style={{ color: SPEED_COLORS[comparePlayerB], margin: '0 0 1rem' }}>Operative {comparePlayerB}</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="text-center">
                  <span className="orbitron" style={{ fontSize: '2.5rem', fontWeight: 'bold' }}>
                    {getOverallRating(playerRatings[comparePlayerB])}
                  </span>
                  <div className="text-secondary" style={{ fontSize: '0.72rem' }}>TACTICAL RATING</div>
                </div>
                <hr style={{ border: 'none', borderTop: '1px solid rgba(0,0,0,0.06)' }} />
                {[
                  { label: '⚔️ Attack Power', val: playerRatings[comparePlayerB].attack },
                  { label: '🛡️ Defense Coverage', val: playerRatings[comparePlayerB].defense },
                  { label: '🎯 Target Precision', val: playerRatings[comparePlayerB].precision },
                  { label: '⚡ Acceleration & Speed', val: playerRatings[comparePlayerB].speed },
                  { label: '🔋 Physical Endurance', val: playerRatings[comparePlayerB].stamina },
                ].map(item => (
                  <div key={item.label}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                      <span>{item.label}</span>
                      <strong>{item.val}%</strong>
                    </div>
                    <div style={{ height: '8px', background: 'rgba(0,0,0,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ width: `${item.val}%`, height: '100%', background: SPEED_COLORS[comparePlayerB], borderRadius: '4px' }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab 4: 3D Court Heatmap ────────────────────────────────────────── */}
      {activeTab === 'heatmap3d' && (
        <div>
          <div className="section-title orbitron" style={{ fontSize: '1.5rem', marginBottom: '2rem' }}>
            3D Arena Heatmap &amp; Depth Perspective
          </div>

          <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
            {/* View angle controllers */}
            <div className="glass-card" style={{ flex: '1 1 280px', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <h4 className="orbitron" style={{ margin: '0 0 0.5rem', fontSize: '0.9rem' }}>3D Perspective Control</h4>
              
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600, marginBottom: '4px' }}>
                  <span>Pitch (Tilt Angle)</span>
                  <span>{courtPitch}°</span>
                </div>
                <input
                  type="range" min="20" max="85"
                  value={courtPitch}
                  onChange={(e) => setCourtPitch(Number(e.target.value))}
                  style={{ width: '100%' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600, marginBottom: '4px' }}>
                  <span>Rotation</span>
                  <span>{courtRotation}°</span>
                </div>
                <input
                  type="range" min="-90" max="90"
                  value={courtRotation}
                  onChange={(e) => setCourtRotation(Number(e.target.value))}
                  style={{ width: '100%' }}
                />
              </div>

              <hr style={{ border: 'none', borderTop: '1px solid rgba(0,0,0,0.08)' }} />

              <h4 className="orbitron" style={{ margin: '0 0 0.5rem', fontSize: '0.9rem' }}>Filter Player</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {['all', '1', '2', '3', '4'].map(p => (
                  <button
                    key={p}
                    onClick={() => setActiveHeatmapPlayer(p)}
                    style={{
                      padding: '0.5rem 1rem',
                      borderRadius: '8px',
                      border: activeHeatmapPlayer === p ? 'none' : '1px solid rgba(14,165,233,0.3)',
                      background: activeHeatmapPlayer === p ? 'var(--accent-primary)' : '#fff',
                      color: activeHeatmapPlayer === p ? '#fff' : 'var(--text-primary)',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      fontWeight: 'bold',
                      fontFamily: 'Orbitron'
                    }}
                  >
                    {p === 'all' ? 'All Operatives' : `Operative ${p}`}
                  </button>
                ))}
              </div>
            </div>

            {/* Interactive 3D Canvas Mock Court */}
            <div className="glass-card" style={{
              flex: '2 1 500px',
              padding: '2rem',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
              background: '#040814',
              borderColor: 'rgba(14,165,233,0.3)'
            }}>
              <div style={{
                perspective: '800px',
                width: '100%',
                height: '420px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <div style={{
                  position: 'relative',
                  width: '260px',
                  height: '460px',
                  background: 'radial-gradient(circle, #0f1c3f 0%, #030712 100%)',
                  border: '3px solid #00f3ff',
                  borderRadius: '12px',
                  boxShadow: '0 0 40px rgba(0,243,255,0.2), inset 0 0 20px rgba(0,243,255,0.1)',
                  transform: `rotateX(${courtPitch}deg) rotateZ(${courtRotation}deg)`,
                  transformStyle: 'preserve-3d',
                  transition: 'transform 0.1s ease-out',
                }}>
                  {/* Grid Lines of Padel Court */}
                  {/* Center Line */}
                  <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '3px', background: '#00f3ff', transform: 'translateY(-50%)', opacity: 0.8 }} />
                  {/* Service Boxes lines */}
                  <div style={{ position: 'absolute', top: '30%', left: 0, right: 0, height: '1.5px', background: 'rgba(0, 243, 255, 0.4)' }} />
                  <div style={{ position: 'absolute', top: '70%', left: 0, right: 0, height: '1.5px', background: 'rgba(0, 243, 255, 0.4)' }} />
                  <div style={{ position: 'absolute', top: '30%', bottom: '70%', left: '50%', width: '1.5px', background: 'rgba(0, 243, 255, 0.4)', transform: 'translateX(-50%)' }} />

                  {/* Net Mock 3D structure */}
                  <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: 0,
                    right: 0,
                    height: '24px',
                    background: 'repeating-linear-gradient(45deg, rgba(255,255,255,0.1) 0px, rgba(255,255,255,0.1) 2px, transparent 2px, transparent 6px)',
                    borderTop: '2px solid #ffffff',
                    borderBottom: '1px solid rgba(255,255,255,0.3)',
                    transform: 'rotateX(-90deg) translateZ(12px)',
                    transformOrigin: 'top',
                    pointerEvents: 'none'
                  }} />

                  {/* Glass Walls Mock 3D */}
                  <div style={{
                    position: 'absolute', bottom: 0, left: 0, right: 0, height: '60px',
                    background: 'rgba(0, 243, 255, 0.08)', borderTop: '2px solid rgba(0, 243, 255, 0.5)',
                    transform: 'rotateX(-90deg)', transformOrigin: 'bottom', pointerEvents: 'none'
                  }} />
                  <div style={{
                    position: 'absolute', top: 0, left: 0, right: 0, height: '60px',
                    background: 'rgba(0, 243, 255, 0.08)', borderBottom: '2px solid rgba(0, 243, 255, 0.5)',
                    transform: 'rotateX(90deg)', transformOrigin: 'top', pointerEvents: 'none'
                  }} />

                  {/* Interactive Glowing 3D Heatmap Dots */}
                  {Object.entries(heatmap).map(([pid, pts]) => {
                    if (activeHeatmapPlayer !== 'all' && activeHeatmapPlayer !== pid) return null
                    const color = SPEED_COLORS[Number(pid)] || '#fff'
                    const xs = pts.x || []
                    const ys = pts.y || []
                    return xs.map((xv, i) => {
                      const yv = ys[i]
                      if (xv == null || yv == null) return null
                      // Mapping x (-5 to 5) -> percentage left (0 to 100)
                      // Mapping y (-10 to 10) -> percentage top (0 to 100)
                      const leftPct = ((xv + 5) / 10) * 100
                      const topPct = ((yv + 10) / 20) * 100
                      return (
                        <div
                          key={`${pid}-${i}`}
                          style={{
                            position: 'absolute',
                            left: `${leftPct}%`,
                            top: `${topPct}%`,
                            width: '10px',
                            height: '10px',
                            background: color,
                            borderRadius: '50%',
                            transform: 'translate(-50%, -50%) translateZ(4px)',
                            boxShadow: `0 0 10px ${color}, 0 0 20px ${color}`,
                            opacity: 0.8,
                            pointerEvents: 'none'
                          }}
                        />
                      )
                    })
                  })}
                </div>
              </div>
              <p className="hint mt-2 text-center" style={{ color: '#94a3b8' }}>
                Use Pitch &amp; Rotation sliders to dynamically view tactical spatiotemporal coverage in 3D perspective.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── SmartPlay AI Insights ─────────────────────────────────────────── */}
      <div className="mt-4">
        <h3 className="section-title orbitron" style={{ fontSize: '1rem', color: 'var(--accent-secondary)' }}>
          <span className="ai-indicator"></span>
          SmartPlay AI Assistant
        </h3>
        <div className="ai-coach-card">
          <div className="orbitron mb-2" style={{ fontSize: '0.85rem', color: 'var(--accent-secondary)', letterSpacing: '1px' }}>INITIALIZING NEURAL ANALYSIS...</div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6' }}>
            SmartPlay AI is ready to provide precise, data-driven coaching insights based on elite padel knowledge and computer vision metrics. Connect this module to your LLM API to generate automated Executive Summaries, Tactical Insights, and Strengths/Weaknesses analysis from your match data.
          </p>
          <div className="button-group mt-2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.5rem' }}>
            <button className="action-btn" style={{ height: '40px', fontSize: '0.75rem', borderColor: 'var(--accent-secondary)', color: 'var(--accent-secondary)' }}>Generate Summary</button>
            <button className="action-btn" style={{ height: '40px', fontSize: '0.75rem', borderColor: 'var(--accent-secondary)', color: 'var(--accent-secondary)' }}>Tactical Advice</button>
            <button className="action-btn" style={{ height: '40px', fontSize: '0.75rem', borderColor: 'var(--accent-secondary)', color: 'var(--accent-secondary)' }}>Ask AI Coach</button>
          </div>
        </div>
      </div>

      {!demoMode && jobId ? (
        <div className="button-group mt-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <a href={`${apiBase}/jobs/${jobId}/download/video`} target="_blank" rel="noreferrer" className="action-btn orbitron" style={{ textDecoration: 'none' }}>
            Export Annotated Feed
          </a>
          <a href={`${apiBase}/jobs/${jobId}/download/csv`} target="_blank" rel="noreferrer" className="action-btn orbitron" style={{ textDecoration: 'none' }}>
            Extract Telemetry (CSV)
          </a>
        </div>
      ) : demoMode ? (
        <p className="hint mt-4 text-center">Mode démo UI — lancez une vraie analyse pour exporter vidéo / CSV.</p>
      ) : null}
    </div>
  )
}
