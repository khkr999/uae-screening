// ── Shared UI primitives (v2 — CSS variable theming) ─────────────────────

const RISK = {
  5: { label:"Critical", color:"#E11D48", bg:"rgba(225,29,72,0.12)",  border:"rgba(225,29,72,0.3)"  },
  4: { label:"High",     color:"#F97316", bg:"rgba(249,115,22,0.12)", border:"rgba(249,115,22,0.3)" },
  3: { label:"Medium",   color:"#EAB308", bg:"rgba(234,179,8,0.12)",  border:"rgba(234,179,8,0.3)"  },
  2: { label:"Monitor",  color:"#4A7FD4", bg:"rgba(74,127,212,0.12)", border:"rgba(74,127,212,0.3)" },
  1: { label:"Low",      color:"#4A7FD4", bg:"rgba(74,127,212,0.08)", border:"rgba(74,127,212,0.2)" },
  0: { label:"Licensed", color:"#10B981", bg:"rgba(16,185,129,0.12)", border:"rgba(16,185,129,0.3)" },
};

const RiskBadge = ({ level, size = "sm" }) => {
  const r = RISK[level] || RISK[2];
  const pad = size === "lg" ? "5px 14px" : "3px 9px";
  const fs  = size === "lg" ? 12 : 10;
  return (
    <span style={{
      display:"inline-flex", alignItems:"center", gap:5,
      padding:pad, borderRadius:999,
      background:r.bg, border:`1px solid ${r.border}`,
      color:r.color, fontSize:fs, fontWeight:800,
      letterSpacing:"0.05em", whiteSpace:"nowrap",
    }}>
      <span style={{ width:5, height:5, borderRadius:"50%", background:r.color, flexShrink:0 }} />
      {r.label} {level}
    </span>
  );
};

const AlertBadge = ({ status }) => {
  if (!status) return null;
  if (status === "NEW")
    return <span style={{ display:"inline-block", padding:"2px 8px", borderRadius:999, background:"rgba(34,197,94,0.12)", color:"#22C55E", border:"1px solid rgba(34,197,94,0.3)", fontSize:9, fontWeight:800, letterSpacing:"0.08em" }}>NEW</span>;
  if (status === "RISK_UP")
    return <span style={{ display:"inline-block", padding:"2px 8px", borderRadius:999, background:"rgba(249,115,22,0.12)", color:"#F97316", border:"1px solid rgba(249,115,22,0.3)", fontSize:9, fontWeight:800, letterSpacing:"0.08em" }}>↑ RISK UP</span>;
  return null;
};

const Tag = ({ children, color }) => (
  <span style={{
    display:"inline-block", padding:"2px 8px", borderRadius:4,
    background:"var(--tag-bg)", color: color || "var(--text-secondary)",
    fontSize:10, fontWeight:600, letterSpacing:"0.03em",
    border:"1px solid var(--border)",
  }}>{children}</span>
);

const ConfBar = ({ value }) => (
  <div style={{ display:"flex", alignItems:"center", gap:6 }}>
    <div style={{ flex:1, height:4, background:"var(--border)", borderRadius:99 }}>
      <div style={{ width:`${value}%`, height:"100%", borderRadius:99,
        background: value >= 80 ? "#10B981" : value >= 60 ? "#EAB308" : "#4A7FD4" }} />
    </div>
    <span style={{ color:"var(--text-tertiary)", fontSize:10, fontWeight:700, width:28 }}>{value}%</span>
  </div>
);

// Skeleton loader
const Skeleton = ({ width = "100%", height = 16, radius = 4, style = {} }) => (
  <div style={{ width, height, borderRadius:radius,
    background:"linear-gradient(90deg, var(--bg-raised) 25%, var(--bg-hover) 50%, var(--bg-raised) 75%)",
    backgroundSize:"200% 100%",
    animation:"shimmer 1.4s infinite",
    ...style,
  }} />
);

// Empty state
const EmptyState = ({ icon = "📭", title, desc, action }) => (
  <div style={{ padding:"48px 24px", textAlign:"center" }}>
    <div style={{ fontSize:36, marginBottom:12 }}>{icon}</div>
    <div style={{ color:"var(--text-primary)", fontSize:14, fontWeight:700, marginBottom:6 }}>{title}</div>
    <div style={{ color:"var(--text-tertiary)", fontSize:12, marginBottom:action?16:0 }}>{desc}</div>
    {action}
  </div>
);

// Error state
const ErrorState = ({ message }) => (
  <div style={{ padding:"24px", background:"rgba(225,29,72,0.07)", border:"1px solid rgba(225,29,72,0.2)", borderRadius:10 }}>
    <div style={{ color:"#E11D48", fontSize:12, fontWeight:700, marginBottom:4 }}>⚠ Error loading data</div>
    <div style={{ color:"var(--text-secondary)", fontSize:11 }}>{message}</div>
  </div>
);

// Horizontal bar chart
const HBarChart = ({ data, colorFn, maxVal, showValues = true }) => {
  const max = maxVal || Math.max(...data.map(d => d.value), 1);
  if (!data.length) return <EmptyState icon="📊" title="No data" desc="Nothing to display for this chart" />;
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:7 }}>
      {data.map(({ label, value }) => (
        <div key={label} style={{ display:"grid", gridTemplateColumns:"130px 1fr 36px", alignItems:"center", gap:8 }}>
          <span style={{ color:"var(--text-secondary)", fontSize:11, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }} title={label}>{label}</span>
          <div style={{ height:22, background:"var(--bg-raised)", borderRadius:4, overflow:"hidden", position:"relative" }}>
            <div style={{
              width:`${(value/max)*100}%`, height:"100%", borderRadius:4,
              background: colorFn ? colorFn(label) : "var(--gold)",
              transition:"width 0.7s cubic-bezier(.4,0,.2,1)",
              minWidth: value > 0 ? 4 : 0,
            }} />
            {value > 0 && (
              <span style={{ position:"absolute", left:6, top:"50%", transform:"translateY(-50%)",
                fontSize:9, fontWeight:700, color:"rgba(255,255,255,0.7)", mixBlendMode:"screen" }}>
              </span>
            )}
          </div>
          <span style={{ color:"var(--text-primary)", fontSize:11, fontWeight:700, textAlign:"right" }}>{value}</span>
        </div>
      ))}
    </div>
  );
};

const Divider = ({ my = 16 }) => <div style={{ height:1, background:"var(--border)", margin:`${my}px 0` }} />;

const SectionLabel = ({ children, action }) => (
  <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:12 }}>
    <span style={{ color:"var(--text-primary)", fontSize:11, fontWeight:800, letterSpacing:"0.07em", textTransform:"uppercase" }}>{children}</span>
    {action}
  </div>
);

// Trust indicator bar
const TrustBar = ({ runDate, dataSource, runName }) => (
  <div style={{ display:"flex", gap:16, flexWrap:"wrap", alignItems:"center",
    padding:"8px 0", borderTop:"1px solid var(--border)" }}>
    <div style={{ display:"flex", alignItems:"center", gap:5 }}>
      <span style={{ width:6, height:6, borderRadius:"50%", background:"#10B981", flexShrink:0 }} />
      <span style={{ color:"var(--text-tertiary)", fontSize:10 }}>Last run: <b style={{ color:"var(--text-secondary)" }}>{runDate}</b></span>
    </div>
    <span style={{ color:"var(--text-tertiary)", fontSize:10 }}>Sources: <b style={{ color:"var(--text-secondary)" }}>{dataSource}</b></span>
    <span style={{ color:"var(--text-tertiary)", fontSize:10 }}>📁 {runName.replace("UAE_Screening_","").replace(".xlsx","")}</span>
    <span style={{ color:"var(--text-tertiary)", fontSize:10 }}>ℹ️ Not a legal determination</span>
  </div>
);

// TopBar with theme toggle
const TopBar = ({ activeTab, setActiveTab, runDate, dataSource, dark, toggleTheme }) => {
  const tabs = [
    { id:"overview", label:"Overview" },
    { id:"search",   label:"Search & Filter" },
    { id:"insights", label:"Insights" },
  ];
  return (
    <div style={{ position:"sticky", top:0, zIndex:100, background:"var(--bg-deep)", borderBottom:"1px solid var(--border)" }}>
      <div style={{ display:"flex", alignItems:"center", gap:16, padding:"0 24px", height:52, borderBottom:"1px solid var(--border-mid)" }}>
        {/* Logo */}
        <div style={{ display:"flex", alignItems:"center", gap:10, flexShrink:0 }}>
          <div style={{ width:30, height:30, borderRadius:8, background:"linear-gradient(135deg,var(--gold),#7A5B10)",
            display:"flex", alignItems:"center", justifyContent:"center", fontSize:14,
            boxShadow:"0 4px 12px rgba(201,168,76,0.25)", flexShrink:0 }}>🛡️</div>
          <div>
            <div style={{ color:"var(--text-primary)", fontSize:13, fontWeight:800, letterSpacing:"-0.01em", lineHeight:1.2 }}>UAE Regulatory Screening</div>
            <div style={{ color:"var(--text-tertiary)", fontSize:9, fontWeight:700, letterSpacing:"0.08em" }}>INTERNAL RISK MONITORING</div>
          </div>
        </div>
        <div style={{ flex:1 }} />
        {/* Run info */}
        <div style={{ textAlign:"right", marginRight:8 }}>
          <div style={{ color:"var(--text-secondary)", fontSize:10 }}>Run: <span style={{ color:"var(--text-primary)", fontWeight:600 }}>{runDate}</span></div>
          <div style={{ color:"var(--text-tertiary)", fontSize:9 }}>{dataSource}</div>
        </div>
        {/* Live badge */}
        <div style={{ display:"flex", alignItems:"center", gap:5, padding:"4px 10px", borderRadius:999,
          background:"rgba(16,185,129,0.1)", border:"1px solid rgba(16,185,129,0.25)" }}>
          <span style={{ width:5, height:5, borderRadius:"50%", background:"#10B981" }} />
          <span style={{ color:"#10B981", fontSize:10, fontWeight:800, letterSpacing:"0.06em" }}>LIVE</span>
        </div>
        {/* Theme toggle */}
        <button onClick={toggleTheme} title={dark ? "Switch to light mode" : "Switch to dark mode"}
          style={{ background:"var(--bg-card)", border:"1px solid var(--border)", borderRadius:8,
            color:"var(--text-secondary)", fontSize:14, cursor:"pointer", width:32, height:32,
            display:"flex", alignItems:"center", justifyContent:"center", transition:"all 0.15s", flexShrink:0 }}
          onMouseEnter={e=>{e.currentTarget.style.borderColor="var(--gold)";e.currentTarget.style.color="var(--gold)";}}
          onMouseLeave={e=>{e.currentTarget.style.borderColor="var(--border)";e.currentTarget.style.color="var(--text-secondary)";}}>
          {dark ? "☀" : "☾"}
        </button>
      </div>
      {/* Tab nav */}
      <div style={{ display:"flex", alignItems:"center", gap:4, padding:"0 24px", height:40 }}>
        {tabs.map(t => {
          const active = activeTab === t.id;
          return (
            <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
              background: active ? "var(--gold-dim)" : "transparent",
              border: active ? "1px solid var(--gold-border)" : "1px solid transparent",
              borderRadius:6, padding:"4px 14px", cursor:"pointer",
              color: active ? "var(--gold)" : "var(--text-secondary)",
              fontSize:12, fontWeight: active ? 800 : 600,
              letterSpacing:"0.01em", transition:"all 0.15s",
            }}
            onMouseEnter={e=>{ if(!active){e.currentTarget.style.color="var(--text-primary)";e.currentTarget.style.background="var(--bg-raised)";}}}
            onMouseLeave={e=>{ if(!active){e.currentTarget.style.color="var(--text-secondary)";e.currentTarget.style.background="transparent";}}}
            >{t.label}</button>
          );
        })}
      </div>
    </div>
  );
};

Object.assign(window, { RISK, RiskBadge, AlertBadge, Tag, ConfBar, HBarChart, Divider, SectionLabel, TrustBar, TopBar, Skeleton, EmptyState, ErrorState });
