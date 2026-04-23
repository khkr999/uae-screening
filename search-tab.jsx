// ── Search Tab + Detail Panel (v2) ───────────────────────────────────────

const WORKFLOW_ACTIONS = [
  { id:"reviewed",  label:"Reviewed",  icon:"✓", color:"#10B981", bg:"rgba(16,185,129,0.1)",  border:"rgba(16,185,129,0.25)" },
  { id:"escalated", label:"Escalate",  icon:"↑", color:"#F97316", bg:"rgba(249,115,22,0.1)",  border:"rgba(249,115,22,0.25)" },
  { id:"cleared",   label:"Clear",     icon:"✕", color:"#4A7FD4", bg:"rgba(74,127,212,0.1)",  border:"rgba(74,127,212,0.25)" },
  { id:"annotated", label:"Annotate",  icon:"✎", color:"var(--gold)", bg:"var(--gold-dim)",   border:"var(--gold-border)" },
];

const DetailPanel = ({ entity, onClose, workflowLog, onWorkflowAction }) => {
  const [note, setNote] = React.useState("");
  const [showNote, setShowNote] = React.useState(false);
  const existingAction = workflowLog?.[entity.id];

  React.useEffect(() => {
    const handleKey = e => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  if (!entity) return null;

  return (
    <>
      <div onClick={onClose} role="button" aria-label="Close panel"
        style={{ position:"fixed", inset:0, background:"rgba(6,8,24,0.65)", zIndex:200, backdropFilter:"blur(2px)" }} />
      <div role="dialog" aria-modal="true" aria-label={`Detail: ${entity.brand}`}
        style={{ position:"fixed", top:0, right:0, bottom:0, width:500,
          background:"var(--bg-card)", zIndex:201, overflowY:"auto",
          boxShadow:"-8px 0 40px rgba(0,0,0,0.5)",
          borderLeft:"1px solid var(--border)",
          animation:"slideIn 0.22s cubic-bezier(.4,0,.2,1)" }}>

        {/* Header */}
        <div style={{ padding:"20px 20px 16px", borderBottom:"1px solid var(--border)",
          background:"var(--bg-raised)", position:"sticky", top:0, zIndex:1 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
            <div style={{ flex:1 }}>
              <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:6 }}>
                <RiskBadge level={entity.riskLevel} size="lg" />
                <AlertBadge status={entity.alertStatus} />
                {existingAction && (
                  <span style={{ fontSize:9, fontWeight:800, letterSpacing:"0.06em", padding:"2px 8px", borderRadius:999,
                    background:"rgba(201,168,76,0.12)", color:"var(--gold)", border:"1px solid var(--gold-border)" }}>
                    {existingAction.action.toUpperCase()}
                  </span>
                )}
              </div>
              <div style={{ color:"var(--text-primary)", fontSize:17, fontWeight:800, lineHeight:1.3 }}>{entity.brand}</div>
              <div style={{ color:"var(--text-secondary)", fontSize:11, marginTop:3 }}>{entity.classification}</div>
            </div>
            <button onClick={onClose} aria-label="Close"
              style={{ background:"var(--bg-card)", border:"1px solid var(--border)", borderRadius:6,
                color:"var(--text-secondary)", fontSize:14, cursor:"pointer", width:28, height:28,
                display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, marginLeft:12 }}>✕</button>
          </div>
        </div>

        <div style={{ padding:20, display:"flex", flexDirection:"column", gap:16 }}>

          {/* Workflow Actions */}
          <div>
            <div style={{ color:"var(--text-tertiary)", fontSize:9, fontWeight:800, letterSpacing:"0.1em", textTransform:"uppercase", marginBottom:8 }}>Workflow</div>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:8 }}>
              {WORKFLOW_ACTIONS.map(a => {
                const active = existingAction?.action === a.id;
                return (
                  <button key={a.id}
                    onClick={() => {
                      if (a.id === "annotated") { setShowNote(v=>!v); return; }
                      onWorkflowAction(entity.id, a.id);
                    }}
                    style={{ background: active ? a.bg : "var(--bg-raised)", border:`1px solid ${active ? a.border : "var(--border)"}`,
                      borderRadius:8, padding:"8px 4px", cursor:"pointer", textAlign:"center", transition:"all 0.15s" }}
                    onMouseEnter={e=>{e.currentTarget.style.background=a.bg;e.currentTarget.style.borderColor=a.border;}}
                    onMouseLeave={e=>{if(!active){e.currentTarget.style.background="var(--bg-raised)";e.currentTarget.style.borderColor="var(--border)";}}}
                  >
                    <div style={{ fontSize:15, marginBottom:3 }}>{a.icon}</div>
                    <div style={{ color: active ? a.color : "var(--text-secondary)", fontSize:9, fontWeight:700 }}>{a.label}</div>
                  </button>
                );
              })}
            </div>

            {existingAction && existingAction.action !== "annotated" && (
              <div style={{ marginTop:8, padding:"6px 10px", background:"rgba(16,185,129,0.07)",
                border:"1px solid rgba(16,185,129,0.2)", borderRadius:6 }}>
                <span style={{ color:"#10B981", fontSize:10, fontWeight:700 }}>
                  ✓ Logged as "{existingAction.action}" at {existingAction.ts}
                </span>
                <button onClick={() => onWorkflowAction(entity.id, null)}
                  style={{ marginLeft:8, background:"none", border:"none", color:"#4E5E7A", fontSize:10, cursor:"pointer" }}>undo</button>
              </div>
            )}

            {showNote && (
              <div style={{ marginTop:8 }}>
                <textarea value={note} onChange={e=>setNote(e.target.value)}
                  placeholder="Enter annotation note…"
                  style={{ width:"100%", minHeight:72, background:"var(--bg-raised)",
                    border:"1px solid var(--gold-border)", borderRadius:8, color:"var(--text-primary)",
                    fontSize:11, padding:"8px 10px", resize:"vertical", boxSizing:"border-box",
                    fontFamily:"inherit", outline:"none" }} />
                <button onClick={() => { onWorkflowAction(entity.id, "annotated", note); setShowNote(false); }}
                  style={{ marginTop:4, background:"var(--gold-dim)", border:"1px solid var(--gold-border)",
                    borderRadius:6, color:"var(--gold)", fontSize:10, fontWeight:700, padding:"4px 12px", cursor:"pointer" }}>
                  Save Note
                </button>
              </div>
            )}
            {existingAction?.note && (
              <div style={{ marginTop:8, padding:"8px 10px", background:"var(--bg-raised)", borderRadius:6,
                border:"1px solid var(--border)", fontSize:11, color:"var(--text-secondary)", fontStyle:"italic" }}>
                "{existingAction.note}"
              </div>
            )}
          </div>

          <Divider />

          {[
            ["Service Type",   entity.serviceType],
            ["Regulator",      entity.regulatorScope],
            ["Confidence",     null],
            ["Matched Entity", entity.matchedEntity || "—"],
          ].map(([k,v]) => (
            <div key={k}>
              <div style={{ color:"var(--text-tertiary)", fontSize:9, fontWeight:800, letterSpacing:"0.1em", textTransform:"uppercase", marginBottom:4 }}>{k}</div>
              {k==="Confidence" ? <ConfBar value={entity.confidence} /> : <div style={{ color:"var(--text-primary)", fontSize:12 }}>{v}</div>}
            </div>
          ))}

          <Divider />

          <div>
            <div style={{ color:"var(--text-tertiary)", fontSize:9, fontWeight:800, letterSpacing:"0.1em", textTransform:"uppercase", marginBottom:6 }}>Rationale</div>
            <div style={{ color:"var(--text-secondary)", fontSize:12, lineHeight:1.7 }}>{entity.rationale}</div>
          </div>

          {entity.actionRequired && (
            <div style={{ background:"var(--gold-dim)", border:"1px solid var(--gold-border)", borderRadius:8, padding:"10px 12px" }}>
              <div style={{ color:"var(--gold)", fontSize:9, fontWeight:800, letterSpacing:"0.1em", textTransform:"uppercase", marginBottom:4 }}>Action Required</div>
              <div style={{ color:"var(--text-primary)", fontSize:11, lineHeight:1.65 }}>{entity.actionRequired}</div>
            </div>
          )}

          {entity.topSourceURL && (
            <a href={entity.topSourceURL} target="_blank" rel="noreferrer"
              style={{ display:"inline-flex", alignItems:"center", gap:6, color:"#4A7FD4", fontSize:11, textDecoration:"none" }}>
              ↗ <span style={{ textDecoration:"underline" }}>View Source</span>
            </a>
          )}

          <Divider />
          <TrustBar runDate={window.SCREENING.runDate} dataSource={window.SCREENING.dataSource} runName={window.SCREENING.runName} />
        </div>
      </div>
    </>
  );
};

// ── Active chip strip ────────────────────────────────────────────────────
const ActiveChips = ({ chips, onRemove, onClearAll }) => {
  if (!chips.length) return null;
  return (
    <div style={{ display:"flex", alignItems:"center", gap:6, flexWrap:"wrap", padding:"6px 0" }}>
      <span style={{ color:"var(--text-tertiary)", fontSize:9, fontWeight:800, letterSpacing:"0.08em" }}>ACTIVE:</span>
      {chips.map(c => (
        <span key={c.id} style={{ display:"inline-flex", alignItems:"center", gap:4,
          padding:"2px 8px 2px 10px", borderRadius:999,
          background:"var(--gold-dim)", border:"1px solid var(--gold-border)",
          color:"var(--gold)", fontSize:10, fontWeight:700 }}>
          {c.label}
          <button onClick={() => onRemove(c.id)} style={{ background:"none", border:"none", color:"var(--gold)",
            cursor:"pointer", fontSize:11, lineHeight:1, padding:"0 0 0 2px" }}>×</button>
        </span>
      ))}
      <button onClick={onClearAll} style={{ background:"none", border:"none", color:"#E11D48",
        fontSize:10, fontWeight:700, cursor:"pointer", marginLeft:4 }}>✕ Clear all</button>
    </div>
  );
};

const SORT_OPTIONS = [
  { value:"risk_desc", label:"Risk: High → Low" },
  { value:"risk_asc",  label:"Risk: Low → High" },
  { value:"name_asc",  label:"Name A → Z" },
  { value:"conf_desc", label:"Confidence: High" },
];

const QUICK_CHIPS = [
  { key:"high",     label:"Critical/High" },
  { key:"new",      label:"New Entities" },
  { key:"riskup",   label:"Risk Up" },
  { key:"licensed", label:"Licensed" },
  { key:"vasp",     label:"VASP/Crypto" },
];

const SearchTab = ({ entities, onSelectEntity, workflowLog, onWorkflowAction, loading }) => {
  const [query, setQuery]       = React.useState("");
  const [suggestions, setSugg]  = React.useState([]);
  const [showSugg, setShowSugg] = React.useState(false);
  const [riskFilter, setRisk]   = React.useState([]);
  const [regFilter, setReg]     = React.useState("");
  const [chipFilter, setChip]   = React.useState(null);
  const [sort, setSort]         = React.useState("risk_desc");
  const [page, setPage]         = React.useState(1);
  const [hovRow, setHovRow]     = React.useState(null);
  const [sortDir, setSortDir]   = React.useState({});
  const PER_PAGE = 12;

  const allBrands = React.useMemo(() => [...new Set(entities.map(e=>e.brand))].sort(), [entities]);
  const allRegs   = React.useMemo(() => [...new Set(entities.map(e=>e.regulatorScope))].sort(), [entities]);

  const handleQuery = v => {
    setQuery(v); setPage(1);
    if (!v.trim()) { setSugg([]); setShowSugg(false); return; }
    const q = v.toLowerCase();
    const starts   = allBrands.filter(b=>b.toLowerCase().startsWith(q));
    const contains = allBrands.filter(b=>b.toLowerCase().includes(q)&&!b.toLowerCase().startsWith(q));
    setSugg([...starts,...contains].slice(0,8));
    setShowSugg(true);
  };

  const toggleRisk = lvl => { setRisk(prev=>prev.includes(lvl)?prev.filter(x=>x!==lvl):[...prev,lvl]); setPage(1); };

  // Build active chip list
  const activeChips = React.useMemo(() => {
    const chips = [];
    if (query) chips.push({ id:"query", label:`"${query}"` });
    riskFilter.forEach(l => chips.push({ id:`risk_${l}`, label:`${RISK[l].label}` }));
    if (regFilter) chips.push({ id:"reg", label:regFilter });
    const qc = QUICK_CHIPS.find(c=>c.key===chipFilter);
    if (qc) chips.push({ id:"chip", label:qc.label });
    return chips;
  }, [query, riskFilter, regFilter, chipFilter]);

  const removeChip = id => {
    if (id==="query")     { setQuery(""); }
    else if (id==="reg")  { setReg(""); }
    else if (id==="chip") { setChip(null); }
    else if (id.startsWith("risk_")) { setRisk(prev=>prev.filter(l=>l!==parseInt(id.replace("risk_","")))); }
    setPage(1);
  };

  const clearAll = () => { setQuery(""); setRisk([]); setReg(""); setChip(null); setPage(1); };

  let filtered = React.useMemo(() => {
    let f = entities.filter(e => {
      if (query && !e.brand.toLowerCase().includes(query.toLowerCase())) return false;
      if (riskFilter.length && !riskFilter.includes(e.riskLevel)) return false;
      if (regFilter && e.regulatorScope !== regFilter) return false;
      if (chipFilter === "high")     return e.riskLevel >= 4;
      if (chipFilter === "new")      return e.alertStatus === "NEW";
      if (chipFilter === "riskup")   return e.alertStatus === "RISK_UP";
      if (chipFilter === "licensed") return e.riskLevel === 0;
      if (chipFilter === "vasp")     return e.regulatorScope === "VARA" || e.serviceType.toLowerCase().includes("crypto");
      return true;
    });
    if (sort === "risk_desc") f = [...f].sort((a,b)=>b.riskLevel-a.riskLevel);
    if (sort === "risk_asc")  f = [...f].sort((a,b)=>a.riskLevel-b.riskLevel);
    if (sort === "name_asc")  f = [...f].sort((a,b)=>a.brand.localeCompare(b.brand));
    if (sort === "conf_desc") f = [...f].sort((a,b)=>b.confidence-a.confidence);
    return f;
  }, [entities, query, riskFilter, regFilter, chipFilter, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length/PER_PAGE));
  const pageData   = filtered.slice((page-1)*PER_PAGE, page*PER_PAGE);

  const inp = { background:"var(--bg-raised)", border:"1px solid var(--border)", borderRadius:8,
    color:"var(--text-primary)", fontSize:12, padding:"7px 12px", outline:"none",
    width:"100%", boxSizing:"border-box", fontFamily:"inherit" };
  const sel = { ...inp, cursor:"pointer", width:"auto" };

  const COLS = [
    { key:"brand",    label:"Brand / Entity",  flex:"2fr" },
    { key:"risk",     label:"Risk",            flex:"90px" },
    { key:"reg",      label:"Regulator",       flex:"100px" },
    { key:"svc",      label:"Service",         flex:"110px" },
    { key:"conf",     label:"Conf.",           flex:"80px" },
    { key:"action",   label:"Action Required", flex:"1fr" },
    { key:"status",   label:"Status",          flex:"80px" },
  ];
  const gridCols = COLS.map(c=>c.flex).join(" ");

  return (
    <div>
      {/* Filter Toolbar */}
      <div style={{ background:"var(--bg-card)", borderRadius:10, padding:"14px 16px", marginBottom:12,
        boxShadow:"var(--shadow)", border:"1px solid var(--border)" }}>

        <div style={{ display:"grid", gridTemplateColumns:"1fr 240px 160px 140px", gap:10, marginBottom:10, alignItems:"center" }}>
          {/* Search */}
          <div style={{ position:"relative" }}>
            <span style={{ position:"absolute", left:10, top:"50%", transform:"translateY(-50%)",
              color:"var(--text-tertiary)", fontSize:13, pointerEvents:"none" }}>⌕</span>
            <input value={query} onChange={e=>handleQuery(e.target.value)}
              onFocus={()=>suggestions.length>0&&setShowSugg(true)}
              onBlur={()=>setTimeout(()=>setShowSugg(false),150)}
              placeholder="Search entity or brand…" aria-label="Search entities"
              style={{ ...inp, paddingLeft:30,
                borderColor: query ? "var(--gold-border)" : "var(--border)",
                boxShadow: query ? "0 0 0 2px var(--gold-dim)" : "none",
              }} />
            {showSugg && suggestions.length > 0 && (
              <div style={{ position:"absolute", top:"100%", left:0, right:0, zIndex:50, marginTop:4,
                background:"var(--bg-raised)", border:"1px solid var(--gold-border)", borderRadius:8,
                overflow:"hidden", boxShadow:"0 8px 24px rgba(0,0,0,0.4)" }}>
                {suggestions.map(s => (
                  <div key={s} onMouseDown={()=>{setQuery(s);setSugg([]);setShowSugg(false);setPage(1);}}
                    style={{ padding:"8px 12px", cursor:"pointer", color:"var(--text-primary)", fontSize:11,
                      borderBottom:"1px solid var(--border-mid)" }}
                    onMouseEnter={e=>e.currentTarget.style.background="var(--gold-dim)"}
                    onMouseLeave={e=>e.currentTarget.style.background="transparent"}>
                    <span style={{ color:"var(--gold)", fontWeight:700 }}>{s.slice(0,query.length)}</span>{s.slice(query.length)}
                  </div>
                ))}
              </div>
            )}
          </div>
          <select value={regFilter} onChange={e=>{setReg(e.target.value);setPage(1);}} style={sel} aria-label="Filter by regulator">
            <option value="">All Regulators</option>
            {allRegs.map(r=><option key={r} value={r}>{r}</option>)}
          </select>
          <select value={sort} onChange={e=>setSort(e.target.value)} style={sel} aria-label="Sort results">
            {SORT_OPTIONS.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <div style={{ color:"var(--text-secondary)", fontSize:10, textAlign:"right" }}>
            <span style={{ color:"var(--text-primary)", fontWeight:700 }}>{filtered.length}</span> of {entities.length}
          </div>
        </div>

        {/* Risk toggles + quick chips */}
        <div style={{ display:"flex", alignItems:"center", gap:6, flexWrap:"wrap" }}>
          <span style={{ color:"var(--text-tertiary)", fontSize:9, fontWeight:800, letterSpacing:"0.08em" }}>RISK</span>
          {[5,4,3,2,1,0].map(l => {
            const r = RISK[l]; const active = riskFilter.includes(l);
            return (
              <button key={l} onClick={()=>toggleRisk(l)} aria-pressed={active}
                style={{ background: active ? r.bg : "var(--bg-raised)", border:`1px solid ${active ? r.border : "var(--border)"}`,
                  borderRadius:999, padding:"3px 10px", cursor:"pointer",
                  color: active ? r.color : "var(--text-secondary)", fontSize:10, fontWeight:700, transition:"all 0.1s" }}
              >{r.label}</button>
            );
          })}
          <div style={{ width:1, height:14, background:"var(--border)", margin:"0 4px" }} />
          <span style={{ color:"var(--text-tertiary)", fontSize:9, fontWeight:800, letterSpacing:"0.08em" }}>QUICK</span>
          {QUICK_CHIPS.map(c => {
            const active = chipFilter===c.key;
            return (
              <button key={c.key} onClick={()=>{setChip(active?null:c.key);setPage(1);}} aria-pressed={active}
                style={{ background: active ? "var(--gold-dim)" : "var(--bg-raised)",
                  border:`1px solid ${active ? "var(--gold-border)" : "var(--border)"}`,
                  borderRadius:999, padding:"3px 10px", cursor:"pointer",
                  color: active ? "var(--gold)" : "var(--text-secondary)", fontSize:10, fontWeight:700, transition:"all 0.1s" }}>
                {active?"✓ ":""}{c.label}
              </button>
            );
          })}
        </div>

        {/* Active chips */}
        <ActiveChips chips={activeChips} onRemove={removeChip} onClearAll={clearAll} />
      </div>

      {/* Table */}
      <div style={{ background:"var(--bg-card)", borderRadius:10, overflow:"hidden",
        boxShadow:"var(--shadow)", border:"1px solid var(--border)" }}>
        {/* Header */}
        <div style={{ display:"grid", gridTemplateColumns:gridCols,
          padding:"8px 14px", borderBottom:"1px solid var(--border)", background:"var(--bg-raised)" }}>
          {COLS.map(c => (
            <div key={c.key} style={{ color:"var(--text-tertiary)", fontSize:9, fontWeight:800,
              letterSpacing:"0.09em", textTransform:"uppercase" }}>{c.label}</div>
          ))}
        </div>

        {loading
          ? [...Array(6)].map((_,i) => (
              <div key={i} style={{ display:"grid", gridTemplateColumns:gridCols, padding:"10px 14px",
                borderBottom:"1px solid var(--border-mid)", gap:10, alignItems:"center" }}>
                <Skeleton height={12} width="70%" />
                <Skeleton height={18} width={60} style={{ borderRadius:999 }} />
                <Skeleton height={18} width={50} style={{ borderRadius:4 }} />
                <Skeleton height={18} width={70} style={{ borderRadius:4 }} />
                <Skeleton height={6} />
                <Skeleton height={10} width="80%" />
                <Skeleton height={16} width={40} style={{ borderRadius:999 }} />
              </div>
            ))
          : filtered.length === 0
            ? <EmptyState icon="🔍" title="No entities found" desc="Try adjusting your search or clearing some filters"
                action={<button onClick={clearAll} style={{ background:"var(--gold-dim)", border:"1px solid var(--gold-border)",
                  borderRadius:6, color:"var(--gold)", fontSize:11, fontWeight:700, padding:"6px 16px", cursor:"pointer" }}>Clear filters</button>} />
            : pageData.map(e => {
                const wAction = workflowLog?.[e.id];
                return (
                  <div key={e.id} onClick={()=>onSelectEntity(e)}
                    onMouseEnter={()=>setHovRow(e.id)} onMouseLeave={()=>setHovRow(null)}
                    role="row" tabIndex={0} aria-label={`${e.brand}, ${RISK[e.riskLevel]?.label} risk`}
                    onKeyDown={ev=>ev.key==="Enter"&&onSelectEntity(e)}
                    style={{ display:"grid", gridTemplateColumns:gridCols, padding:"9px 14px", cursor:"pointer",
                      borderBottom:"1px solid var(--border-mid)",
                      background: hovRow===e.id ? "var(--bg-hover)" : "transparent",
                      transition:"background 0.1s", outline:"none",
                    }}>
                    <div style={{ minWidth:0 }}>
                      <div style={{ display:"flex", alignItems:"center", gap:5 }}>
                        <span style={{ color:"var(--text-primary)", fontSize:12, fontWeight:700,
                          overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{e.brand}</span>
                        {wAction && <span style={{ fontSize:9, color:"var(--text-tertiary)" }}>{wAction.action==="reviewed"?"✓":wAction.action==="escalated"?"↑":wAction.action==="cleared"?"✕":"✎"}</span>}
                      </div>
                      <div style={{ color:"var(--text-tertiary)", fontSize:9, marginTop:1 }}>{e.classification}</div>
                    </div>
                    <div style={{ display:"flex", alignItems:"center" }}><RiskBadge level={e.riskLevel} /></div>
                    <div style={{ display:"flex", alignItems:"center" }}><Tag color="var(--gold)">{e.regulatorScope}</Tag></div>
                    <div style={{ display:"flex", alignItems:"center" }}>
                      <Tag>{e.serviceType.length>14?e.serviceType.slice(0,13)+"…":e.serviceType}</Tag>
                    </div>
                    <div style={{ display:"flex", alignItems:"center" }}><ConfBar value={e.confidence} /></div>
                    <div style={{ display:"flex", alignItems:"center", color:"var(--text-secondary)", fontSize:10,
                      overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap", paddingRight:8 }}>
                      {e.actionRequired || <span style={{ color:"var(--text-tertiary)" }}>—</span>}
                    </div>
                    <div style={{ display:"flex", alignItems:"center", gap:4 }}>
                      <AlertBadge status={e.alertStatus} />
                      {!e.alertStatus && <span style={{ color:"var(--text-tertiary)", fontSize:9 }}>—</span>}
                    </div>
                  </div>
                );
              })
        }
      </div>

      {/* Pagination */}
      {!loading && filtered.length > 0 && (
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginTop:10 }}>
          <span style={{ color:"var(--text-tertiary)", fontSize:10 }}>
            Page <b style={{ color:"var(--text-primary)" }}>{page}</b> of {totalPages} · {filtered.length} results
          </span>
          <div style={{ display:"flex", gap:6 }}>
            {[["⏮",1],["◀",page-1],["▶",page+1],["⏭",totalPages]].map(([lbl,pg])=>(
              <button key={lbl} onClick={()=>{if(pg>=1&&pg<=totalPages)setPage(pg);}}
                disabled={lbl==="⏮"||lbl==="◀"?page<=1:page>=totalPages}
                style={{ background:"var(--bg-card)", border:"1px solid var(--border)", borderRadius:6,
                  color:(lbl==="⏮"||lbl==="◀"?page<=1:page>=totalPages) ? "var(--text-tertiary)" : "var(--text-secondary)",
                  fontSize:11, padding:"4px 10px", cursor:"pointer", fontFamily:"inherit" }}>{lbl}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

window.SearchTab = SearchTab;
window.DetailPanel = DetailPanel;
