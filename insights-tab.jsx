// ── Insights Tab (v2 — improved clarity + light theme) ───────────────────

const InsightCallout = ({ children, color = "var(--gold)" }) => (
  <div style={{ marginTop:12, padding:"8px 12px", borderRadius:6,
    background:"var(--bg-raised)", borderLeft:`3px solid ${color}` }}>
    <span style={{ color:"var(--text-secondary)", fontSize:10, lineHeight:1.5 }}>{children}</span>
  </div>
);

const ChartCard = ({ title, subtitle, insight, children, isEmpty }) => (
  <div style={{ background:"var(--bg-card)", borderRadius:10, padding:"16px 18px",
    boxShadow:"var(--shadow)", border:"1px solid var(--border)" }}>
    <div style={{ marginBottom:14 }}>
      <div style={{ color:"var(--text-primary)", fontSize:13, fontWeight:800 }}>{title}</div>
      {subtitle && <div style={{ color:"var(--text-tertiary)", fontSize:10, marginTop:2 }}>{subtitle}</div>}
    </div>
    {isEmpty
      ? <div style={{ padding:"28px 0", textAlign:"center" }}>
          <div style={{ fontSize:28, marginBottom:8 }}>📊</div>
          <div style={{ color:"var(--text-tertiary)", fontSize:11 }}>No data available for this chart</div>
        </div>
      : <>
          {children}
          {insight && <InsightCallout>{insight}</InsightCallout>}
        </>
    }
  </div>
);

const TrendSparkline = ({ trends }) => {
  const W = 100, H = 100, PAD = 10;
  const cats = [
    { key:"high",     color:"#E11D48", label:"Critical / High" },
    { key:"review",   color:"#EAB308", label:"Needs Review" },
    { key:"licensed", color:"#10B981", label:"Licensed" },
  ];
  const allVals = trends.flatMap(t => cats.map(c => t[c.key]));
  const maxV = Math.max(...allVals, 1);
  const xStep = (W - PAD*2) / Math.max(trends.length - 1, 1);
  const yScale = v => H - PAD - (v / maxV) * (H - PAD*2);
  const pathFor = key => trends.map((t, i) =>
    `${i===0?"M":"L"}${PAD + i*xStep},${yScale(t[key])}`
  ).join(" ");

  return (
    <div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
        style={{ display:"block", height:100 }} aria-hidden="true">
        {[0, 0.33, 0.66, 1].map(f => (
          <line key={f} x1={PAD} y1={PAD + f*(H-PAD*2)} x2={W-PAD} y2={PAD + f*(H-PAD*2)}
            stroke="var(--border)" strokeWidth="0.5" />
        ))}
        {cats.map(c => (
          <React.Fragment key={c.key}>
            <path d={pathFor(c.key)} fill="none" stroke={c.color} strokeWidth="1.5"
              strokeLinecap="round" strokeLinejoin="round" opacity="0.9" />
            {trends.map((t,i) => (
              <circle key={i} cx={PAD+i*xStep} cy={yScale(t[c.key])} r="2"
                fill={c.color} opacity="0.9">
                <title>{c.label}: {t[c.key]} ({t.run})</title>
              </circle>
            ))}
          </React.Fragment>
        ))}
      </svg>
      <div style={{ display:"flex", justifyContent:"space-between", marginTop:4, padding:`0 ${PAD}px` }}>
        {trends.map(t => (
          <span key={t.run} style={{ color:"var(--text-tertiary)", fontSize:9 }}>{t.run}</span>
        ))}
      </div>
      <div style={{ display:"flex", gap:16, marginTop:10, flexWrap:"wrap" }}>
        {cats.map(c => (
          <div key={c.key} style={{ display:"flex", alignItems:"center", gap:5 }}>
            <div style={{ width:14, height:3, borderRadius:99, background:c.color }} />
            <span style={{ color:"var(--text-secondary)", fontSize:10 }}>{c.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const InsightsTab = ({ entities, trends, loading }) => {
  const total = entities.length;

  const riskDist = [5,4,3,2,1,0].map(l => ({
    label: `${RISK[l].label} (${l})`,
    value: entities.filter(e=>e.riskLevel===l).length,
    color: RISK[l].color,
  })).filter(d=>d.value>0);

  const regCounts = React.useMemo(() => {
    const m = {}; entities.forEach(e=>{ m[e.regulatorScope]=(m[e.regulatorScope]||0)+1; });
    return Object.entries(m).map(([label,value])=>({label,value})).sort((a,b)=>b.value-a.value).slice(0,8);
  }, [entities]);

  const svcCounts = React.useMemo(() => {
    const m = {}; entities.forEach(e=>{ m[e.serviceType]=(m[e.serviceType]||0)+1; });
    return Object.entries(m).map(([label,value])=>({label,value})).sort((a,b)=>b.value-a.value).slice(0,8);
  }, [entities]);

  const alertCounts = [
    { label:"New Entities",   value:entities.filter(e=>e.alertStatus==="NEW").length,     color:"#22C55E" },
    { label:"Risk Increased", value:entities.filter(e=>e.alertStatus==="RISK_UP").length, color:"#F97316" },
    { label:"No Change",      value:entities.filter(e=>!e.alertStatus).length,             color:"#4A7FD4" },
  ].filter(d=>d.value>0);

  const classBreakdown = React.useMemo(() => {
    const m = {}; entities.forEach(e=>{ m[e.classification]=(m[e.classification]||0)+1; });
    return Object.entries(m).map(([cls,cnt])=>({cls,cnt,pct:((cnt/total)*100).toFixed(1)})).sort((a,b)=>b.cnt-a.cnt);
  }, [entities]);

  const topRisk = riskDist[0];
  const topReg  = regCounts[0];
  const topSvc  = svcCounts[0];
  const newCount = alertCounts.find(a=>a.label==="New Entities")?.value || 0;

  if (loading) return (
    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
      {[...Array(4)].map((_,i) => (
        <div key={i} style={{ background:"var(--bg-card)", borderRadius:10, padding:18, boxShadow:"var(--shadow)" }}>
          <Skeleton width="50%" height={13} style={{ marginBottom:12 }} />
          {[...Array(5)].map((__,j) => <Skeleton key={j} height={22} style={{ marginBottom:7, borderRadius:4 }} />)}
        </div>
      ))}
    </div>
  );

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

      {/* Summary stat row */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:10 }}>
        {[
          { label:"Most Common Risk",   value: topRisk ? topRisk.label.split(" (")[0] : "—", color: topRisk ? RISK[parseInt(topRisk.label.match(/\((\d)\)/)?.[1])]?.color : "var(--text-primary)" },
          { label:"Top Regulator",      value: topReg?.label || "—",   color:"#4A7FD4" },
          { label:"Top Service Type",   value: topSvc?.label || "—",   color:"var(--gold)" },
          { label:"New This Run",       value: `+${newCount}`,         color:"#22C55E" },
        ].map(s => (
          <div key={s.label} style={{ background:"var(--bg-card)", borderRadius:8, padding:"10px 14px",
            border:"1px solid var(--border)", boxShadow:"var(--shadow)" }}>
            <div style={{ color:"var(--text-tertiary)", fontSize:9, fontWeight:800, letterSpacing:"0.09em", textTransform:"uppercase", marginBottom:4 }}>{s.label}</div>
            <div style={{ color:s.color, fontSize:14, fontWeight:800, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Charts row 1 */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
        <ChartCard title="Risk Level Distribution" subtitle="Entities by risk category — highest risk shown first"
          isEmpty={!riskDist.length}
          insight={topRisk ? `${topRisk.value} entities (${((topRisk.value/total)*100).toFixed(0)}%) fall under "${topRisk.label.split(" (")[0]}" — the most common category.` : null}>
          <HBarChart data={riskDist} colorFn={label => {
            const l = parseInt(label.match(/\((\d)\)/)?.[1]);
            return RISK[l]?.color || "var(--text-secondary)";
          }} />
        </ChartCard>
        <ChartCard title="Regulator Scope" subtitle="Distribution across regulatory bodies"
          isEmpty={!regCounts.length}
          insight={topReg ? `${topReg.label} accounts for ${topReg.value} entities (${((topReg.value/total)*100).toFixed(0)}% of all results).` : null}>
          <HBarChart data={regCounts} colorFn={()=>"#4A7FD4"} />
        </ChartCard>
      </div>

      {/* Charts row 2 */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
        <ChartCard title="Service Type Mix" subtitle="Top service categories identified in this run"
          isEmpty={!svcCounts.length}
          insight={topSvc ? `"${topSvc.label}" is the most common service type with ${topSvc.value} entities.` : null}>
          <HBarChart data={svcCounts} colorFn={()=>"var(--gold)"} />
        </ChartCard>
        <ChartCard title="Alert Status" subtitle="Entities with changes detected vs. prior run"
          isEmpty={!alertCounts.length}>
          <HBarChart data={alertCounts} colorFn={label =>
            label==="New Entities"?"#22C55E":label==="Risk Increased"?"#F97316":"#4A7FD4"
          } />
          <div style={{ display:"flex", gap:16, marginTop:14, paddingTop:12, borderTop:"1px solid var(--border)", flexWrap:"wrap" }}>
            {alertCounts.map(a => (
              <div key={a.label}>
                <div style={{ color:a.color, fontSize:22, fontWeight:800 }}>{a.value}</div>
                <div style={{ color:"var(--text-tertiary)", fontSize:9, fontWeight:700 }}>{a.label.toUpperCase()}</div>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>

      {/* Trend */}
      {trends && trends.length >= 2 && (
        <ChartCard title="Risk Trend Across Runs" subtitle={`${trends.length} runs archived — tracking Critical/High, Needs Review, and Licensed entities`}
          insight="Upward trends in Critical/High require immediate attention. A growing Licensed count indicates successful clearance.">
          <TrendSparkline trends={trends} />
        </ChartCard>
      )}

      {/* Classification breakdown */}
      <ChartCard title="Classification Breakdown" subtitle="Full entity type distribution — all categories">
        <div style={{ borderRadius:8, overflow:"hidden", border:"1px solid var(--border)" }}>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 60px 60px 1fr",
            padding:"7px 12px", background:"var(--bg-raised)" }}>
            {["Classification","Count","% Total","Distribution"].map(h=>(
              <div key={h} style={{ color:"var(--text-tertiary)", fontSize:9, fontWeight:800, letterSpacing:"0.08em", textTransform:"uppercase" }}>{h}</div>
            ))}
          </div>
          {classBreakdown.map((row, i) => (
            <React.Fragment key={row.cls}>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 60px 60px 1fr",
                padding:"8px 12px", background: i%2===0 ? "var(--bg-card)" : "var(--bg-raised)",
                borderTop:"1px solid var(--border-mid)", alignItems:"center" }}>
                <div style={{ color:"var(--text-primary)", fontSize:11 }}>{row.cls}</div>
                <div style={{ color:"var(--gold)", fontSize:11, fontWeight:700 }}>{row.cnt}</div>
                <div style={{ color:"var(--text-secondary)", fontSize:11 }}>{row.pct}%</div>
                <div style={{ height:8, background:"var(--bg-raised)", borderRadius:4, overflow:"hidden", border:"1px solid var(--border)" }}>
                  <div style={{ width:`${row.pct}%`, height:"100%", borderRadius:4, background:"var(--gold)", opacity:0.7, maxWidth:"100%", transition:"width 0.6s" }} />
                </div>
              </div>
            </React.Fragment>
          ))}
        </div>
      </ChartCard>

      <TrustBar runDate={window.SCREENING.runDate} dataSource={window.SCREENING.dataSource} runName={window.SCREENING.runName} />
    </div>
  );
};

window.InsightsTab = InsightsTab;
