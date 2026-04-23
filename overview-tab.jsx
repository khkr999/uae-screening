// ── Overview Tab (v2) ─────────────────────────────────────────────────────

const KPICards = ({ entities, loading }) => {
  if (loading) return (
    <div style={{ display:"grid", gridTemplateColumns:"repeat(5,1fr)", gap:12, marginBottom:24 }}>
      {[...Array(5)].map((_,i) => (
        <div key={i} style={{ background:"var(--bg-card)", borderRadius:10, padding:"14px 16px", borderLeft:"3px solid var(--border)" }}>
          <Skeleton width="60%" height={10} style={{ marginBottom:10 }} />
          <Skeleton width="40%" height={28} style={{ marginBottom:8 }} />
          <Skeleton width="70%" height={9} />
        </div>
      ))}
    </div>
  );

  const total    = entities.length;
  const critical = entities.filter(e => e.riskLevel >= 5).length;
  const high     = entities.filter(e => e.riskLevel === 4).length;
  const review   = entities.filter(e => e.riskLevel >= 2 && e.riskLevel <= 3).length;
  const licensed = entities.filter(e => e.riskLevel === 0).length;
  const newEnts  = entities.filter(e => e.alertStatus === "NEW").length;
  const riskUp   = entities.filter(e => e.alertStatus === "RISK_UP").length;

  const cards = [
    { label:"Total Screened",    value:total,             sub:"This run",                          accent:"var(--gold)" },
    { label:"Critical / High",   value:critical + high,   sub:`${Math.round((critical+high)/total*100)}% of total`, accent:"#E11D48", warn:critical+high>0 },
    { label:"Needs Review",      value:review,            sub:"Risk levels 2–3",                   accent:"#EAB308" },
    { label:"Licensed / Clear",  value:licensed,          sub:"No action required",                accent:"#10B981" },
    { label:"New This Run",      value:newEnts,           sub:`↑ ${riskUp} risk increased`,        accent:"#22C55E" },
  ];

  return (
    <div style={{ display:"grid", gridTemplateColumns:"repeat(5,1fr)", gap:12, marginBottom:24 }}>
      {cards.map(c => (
        <div key={c.label} style={{
          background:"var(--bg-card)", borderRadius:10, padding:"14px 16px",
          borderLeft:`3px solid ${c.accent}`,
          boxShadow:"var(--shadow)", transition:"transform 0.15s",
        }}
        onMouseEnter={e=>e.currentTarget.style.transform="translateY(-2px)"}
        onMouseLeave={e=>e.currentTarget.style.transform="translateY(0)"}>
          <div style={{ color:"var(--text-tertiary)", fontSize:9, fontWeight:800, letterSpacing:"0.1em", textTransform:"uppercase", marginBottom:6 }}>{c.label}</div>
          <div style={{ color: c.warn ? c.accent : "var(--text-primary)", fontSize:28, fontWeight:800, letterSpacing:"-0.03em", lineHeight:1 }}>{c.value}</div>
          <div style={{ color:"var(--text-tertiary)", fontSize:10, marginTop:4 }}>{c.sub}</div>
        </div>
      ))}
    </div>
  );
};

const PriorityCard = ({ entity, onClick }) => {
  const [hovered, setHovered] = React.useState(false);
  return (
    <div onClick={() => onClick(entity)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      role="button" tabIndex={0}
      onKeyDown={e => e.key==="Enter" && onClick(entity)}
      aria-label={`View details for ${entity.brand}, risk level ${RISK[entity.riskLevel]?.label}`}
      style={{
        background: hovered ? "var(--bg-hover)" : "var(--bg-card)",
        borderRadius:10, padding:"12px 14px", marginBottom:8, cursor:"pointer",
        border:`1px solid ${hovered ? "var(--gold-border)" : "var(--border)"}`,
        boxShadow: hovered ? "var(--shadow-raised)" : "var(--shadow)",
        transition:"all 0.15s", outline:"none",
      }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", gap:10 }}>
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:4 }}>
            <span style={{ color:"var(--text-primary)", fontSize:13, fontWeight:800 }}>{entity.brand}</span>
            <AlertBadge status={entity.alertStatus} />
          </div>
          <div style={{ display:"flex", gap:6, flexWrap:"wrap", marginBottom:6 }}>
            <Tag>{entity.serviceType}</Tag>
            <Tag color="var(--gold)">{entity.regulatorScope}</Tag>
          </div>
          <div style={{ color:"var(--text-secondary)", fontSize:11, lineHeight:1.55,
            overflow:"hidden", display:"-webkit-box", WebkitLineClamp:2, WebkitBoxOrient:"vertical" }}>
            {entity.rationale}
          </div>
        </div>
        <div style={{ flexShrink:0, textAlign:"right" }}>
          <RiskBadge level={entity.riskLevel} />
          <div style={{ marginTop:6, color:"var(--text-tertiary)", fontSize:9 }}>CONF {entity.confidence}%</div>
        </div>
      </div>
      {entity.actionRequired && (
        <div style={{ marginTop:8, paddingLeft:10, borderLeft:"2px solid var(--gold-border)",
          color:"var(--text-secondary)", fontSize:10, lineHeight:1.5 }}>
          {entity.actionRequired}
        </div>
      )}
    </div>
  );
};

const RunSummaryPanel = ({ entities, runName, newEnts, riskUp, loading }) => {
  const total = entities.length;
  const dominant_reg = React.useMemo(() => {
    const m = {}; entities.forEach(e => { m[e.regulatorScope]=(m[e.regulatorScope]||0)+1; });
    return Object.entries(m).sort((a,b)=>b[1]-a[1])[0]?.[0] || "—";
  }, [entities]);
  const dominant_svc = React.useMemo(() => {
    const m = {}; entities.forEach(e => { m[e.serviceType]=(m[e.serviceType]||0)+1; });
    return Object.entries(m).sort((a,b)=>b[1]-a[1])[0]?.[0] || "—";
  }, [entities]);

  const riskDist = [5,4,3,2,1,0].map(l => ({
    label: RISK[l].label, value: entities.filter(e=>e.riskLevel===l).length, color: RISK[l].color,
  })).filter(d=>d.value>0);

  if (loading) return (
    <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
      <div style={{ background:"var(--bg-card)", borderRadius:10, padding:14 }}>
        {[...Array(4)].map((_,i)=><Skeleton key={i} height={12} style={{ marginBottom:10 }} />)}
      </div>
    </div>
  );

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
      {(newEnts > 0 || riskUp > 0) && (
        <div style={{ background:"rgba(249,115,22,0.07)", border:"1px solid rgba(249,115,22,0.2)", borderRadius:10, padding:"12px 14px" }}>
          <div style={{ color:"#F97316", fontSize:9, fontWeight:800, letterSpacing:"0.1em", marginBottom:8 }}>ALERTS THIS RUN</div>
          {newEnts > 0 && <div style={{ color:"var(--text-secondary)", fontSize:11, marginBottom:3 }}><span style={{ color:"#22C55E", fontWeight:700 }}>{newEnts} new</span> entities added</div>}
          {riskUp  > 0 && <div style={{ color:"var(--text-secondary)", fontSize:11 }}><span style={{ color:"#F97316", fontWeight:700 }}>{riskUp}</span> risk level increases detected</div>}
        </div>
      )}

      <div style={{ background:"var(--bg-card)", borderRadius:10, padding:"14px", boxShadow:"var(--shadow)" }}>
        <SectionLabel>Run Summary</SectionLabel>
        {[["File", runName.replace("UAE_Screening_","").replace(".xlsx","")],
          ["Top Regulator", dominant_reg], ["Top Service", dominant_svc], ["Total Entities", total]
        ].map(([k,v]) => (
          <div key={k} style={{ display:"flex", justifyContent:"space-between", padding:"6px 0",
            borderBottom:"1px solid var(--border-mid)", gap:8 }}>
            <span style={{ color:"var(--text-tertiary)", fontSize:10 }}>{k}</span>
            <span style={{ color:"var(--text-primary)", fontSize:10, fontWeight:700, textAlign:"right", maxWidth:160, wordBreak:"break-word" }}>{v}</span>
          </div>
        ))}
      </div>

      <div style={{ background:"var(--bg-card)", borderRadius:10, padding:"14px", boxShadow:"var(--shadow)" }}>
        <SectionLabel>Risk Distribution</SectionLabel>
        <HBarChart data={riskDist} colorFn={label => Object.values(RISK).find(r=>r.label===label)?.color || "#8896B4"} />
      </div>
    </div>
  );
};

const OverviewTab = ({ entities, runName, onSelectEntity, loading }) => {
  const priorityQueue = React.useMemo(() =>
    entities.filter(e => e.riskLevel >= 4).sort((a,b) => b.riskLevel - a.riskLevel),
  [entities]);
  const newEnts = entities.filter(e=>e.alertStatus==="NEW").length;
  const riskUp  = entities.filter(e=>e.alertStatus==="RISK_UP").length;

  return (
    <div style={{ display:"grid", gridTemplateColumns:"1fr 320px", gap:20, alignItems:"start" }}>
      <div>
        <SectionLabel action={<span style={{ color:"var(--text-tertiary)", fontSize:10 }}>{priorityQueue.length} entities — click to open detail</span>}>
          Priority Review Queue
        </SectionLabel>
        {loading
          ? [...Array(4)].map((_,i) => (
              <div key={i} style={{ background:"var(--bg-card)", borderRadius:10, padding:"12px 14px", marginBottom:8 }}>
                <Skeleton width="50%" height={13} style={{ marginBottom:8 }} />
                <Skeleton width="30%" height={9} style={{ marginBottom:8 }} />
                <Skeleton width="90%" height={10} />
              </div>
            ))
          : priorityQueue.length === 0
            ? <div style={{ background:"rgba(16,185,129,0.07)", border:"1px solid rgba(16,185,129,0.2)", borderRadius:10, padding:24, color:"#10B981", fontSize:12, textAlign:"center" }}>✓ No high-risk entities to review this run</div>
            : priorityQueue.map(e => <PriorityCard key={e.id} entity={e} onClick={onSelectEntity} />)
        }
      </div>
      <RunSummaryPanel entities={entities} runName={runName} newEnts={newEnts} riskUp={riskUp} loading={loading} />
    </div>
  );
};

window.OverviewTab = OverviewTab;
window.KPICards = KPICards;
