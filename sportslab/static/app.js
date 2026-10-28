'use strict';
const $=id=>document.getElementById(id);
const state={sport:'football',page:'overview',overview:null,names:{},models:[],analysis:null,epoch:0,requests:{},offsets:{fixtures:0,results:0}};
const fmt=new Intl.NumberFormat('en-GB');
const pct=p=>`${(Number(p)*100).toFixed(1)}%`;
const date=d=>d?(String(d).length===10?new Date(Number(d.slice(0,4)),Number(d.slice(5,7))-1,Number(d.slice(8,10))):new Date(d)).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):'Not available';
const labels={home_win:'Home win',draw:'Draw',away_win:'Away win',over_1_5:'Over 1.5 goals',over_2_5:'Over 2.5 goals',over_3_5:'Over 3.5 goals',btts:'Both teams to score',home_clean_sheet:'Home clean sheet',away_clean_sheet:'Away clean sheet'};
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
function empty(parent,message){parent.replaceChildren(el('div','empty-state',message));}
function loading(parent){const n=el('div','loading');n.append(el('span','spinner'),el('span','', 'Checking the evidence…'));parent.replaceChildren(n);}
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,6000);}
async function api(path,body){
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),90000);
  try{const response=await fetch(path,{signal:controller.signal,method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:body===undefined?undefined:JSON.stringify(body)});
    const data=await response.json().catch(()=>({error:'The server returned an unreadable response. Please retry.'}));
    if(!response.ok)throw new Error(data.error||'Request failed');return data;
  }catch(e){if(e.name==='AbortError')throw new Error('The request timed out. Please try again.');throw e;}finally{clearTimeout(timer);}
}
function ticket(key){const n=(state.requests[key]||0)+1;state.requests[key]=n;const epoch=state.epoch;return ()=>state.requests[key]===n&&state.epoch===epoch;}
function retryPanel(parent,message,retry){empty(parent,message);parent.firstChild.append(button('Try again','button secondary',retry));}
function debounce(action){let timer;return ()=>{clearTimeout(timer);timer=setTimeout(action,300);};}
function route(){const [name,query]=location.hash.slice(1).split('?');const sport=new URLSearchParams(query).get('sport');return {page:headings[name]?name:location.pathname==='/live-predictions'?'live':'overview',sport:['football','basketball','tennis'].includes(sport)?sport:'football'};}
function metric(label,value,note,symbol='↗'){const n=el('article','metric');n.append(el('span','metric-symbol',symbol),el('div','metric-label',label),el('div','metric-value',value),el('div','metric-note',note));return n;}
function pill(text,type=''){return el('span',`pill ${type}`,text);}
function button(text,cls,action){const n=el('button',cls,text);n.addEventListener('click',action);return n;}
const headings={live:['The match as it unfolds.','Reported scores and match status, with source freshness visible.'],overview:['Your matchday, decoded.','Explore the numbers. Understand the matchup. Keep an honest record.'],explorer:['Go deeper into the matchup.','The probabilities are only the beginning. Explore the evidence behind them.'],journal:['Track the forecast, not the feeling.','A private, immutable record of predictions made before kickoff.'],results:['The results are in.','See completed matches exactly as reported by their data source.'],models:['Open the black box.','Measured performance, honest baselines and clearly defined test periods.'],coverage:['Better analysis starts here.','Understand the sources, freshness and limits of your match data.']};
async function page(name,push=true,focus=true,load=true){
  if(!headings[name])name='overview';const entering=state.page!==name;clearTimeout(state.liveTimer);state.page=name;
  document.querySelectorAll('.page').forEach(n=>n.classList.toggle('active-page',n.id===name));
  document.querySelectorAll('[data-page]').forEach(n=>{n.classList.toggle('active',n.dataset.page===name);if(n.dataset.page===name)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});
  $('page-title').textContent={live:'Live / today',overview:'Overview',explorer:'Match explorer',journal:'Prediction journal',results:'Results',models:'Model lab',coverage:'Data coverage'}[name];
  [$('heading').textContent,$('subtitle').textContent]=headings[name];document.title=`${$('page-title').textContent} · Matchday`;
  const hash=`#${name}?sport=${state.sport}`;if(push&&location.hash!==hash)history.pushState(null,'',hash);
  if(state.overview)renderFreshness();if(focus)$('heading').focus({preventScroll:true});
  const loaders={live:loadLive,journal:loadJournal,models:loadModels,coverage:loadCoverage,results:loadResults};
  const targets={live:'live-matches',journal:'journal-list',models:'model-list',coverage:'coverage-summary',results:'results-list'};
  try{if(load&&name==='overview'&&entering&&state.overview)await loadFixtures();if(load&&loaders[name])await loaders[name]();}catch(e){retryPanel($(targets[name]),e.message,()=>page(name,false));}
}
function setCompetitions(){const comps=state.overview.competitions.filter(c=>c.sport===state.sport);state.names=Object.fromEntries(state.overview.competitions.map(c=>[c.competition,c.name]));for(const id of ['competition','analysis-competition','results-competition']){const select=$(id);select.disabled=false;const previous=select.value;select.replaceChildren();if(id!=='analysis-competition')select.append(new Option('All competitions',''));for(const c of comps)select.append(new Option(c.name,c.competition));if(comps.some(c=>c.competition===previous))select.value=previous;else if(id==='analysis-competition'){const preferred={football:'E0',basketball:'NBA',tennis:'ATP'}[state.sport];if(comps.some(c=>c.competition===preferred))select.value=preferred;}}$('surface-field').hidden=state.sport!=='tennis';}
function renderTeamOptions(id,previous=$(id).value){
  const query=$(id+'-search').value.trim().toLocaleLowerCase();
  const teams=(state.teams||[]).filter(t=>t.id===previous||t.name.toLocaleLowerCase().includes(query));
  $(id).replaceChildren(new Option(teams.length?'Select a participant':'No matching participants',''));
  teams.forEach(t=>$(id).append(new Option(t.name,t.id)));if(teams.some(t=>t.id===previous))$(id).value=previous;participantNote(id);
}
function participantNote(id){const t=(state.teams||[]).find(t=>t.id===$(id).value);const n=$(id+'-note');n.textContent=t?`${fmt.format(t.completed)} completed appearances · latest ${date(t.latest_result)}.`:'';const old=t&&(!t.latest_result||Date.now()-new Date(t.latest_result)>90*86400000);n.classList.toggle('warning',!!old);if(old)n.textContent+=' Older or missing history: check the participant identity and source coverage.';}
async function loadTeams(){
  const current=ticket('teams');const selects=['home-team','away-team'];selects.forEach(id=>{$(id).disabled=true;$(id+'-search').disabled=true;});
  try{const d=await api(`/api/teams?sport=${state.sport}&competition=${encodeURIComponent($('analysis-competition').value)}`);if(!current())return;
    for(const id of selects){const previous=$(id).value;state.teams=d.teams;$(id+'-search').value='';renderTeamOptions(id,previous);}
  }catch(e){if(current()){selects.forEach(id=>$(id).replaceChildren(new Option('Could not load participants','')));toast(e.message);}}finally{if(current())selects.forEach(id=>{$(id).disabled=false;$(id+'-search').disabled=false;});}
}
async function loadOverview(){const current=ticket('overview');const data=await api('/api/overview');if(!current())return;state.overview=data;setCompetitions();renderFreshness();const s=state.overview.totals[state.sport];const m=state.models.find(m=>m.sport===state.sport&&!m.unavailable);$('summary-metrics').replaceChildren(metric('Historical matches',fmt.format(s.matches),'Completed results in the dataset','▤'),metric('Competitions covered',fmt.format(s.competitions),'Explore coverage by league','◎'),metric('Benchmark accuracy',m?pct(m.evaluation.accuracy):'Not trained',m?`${fmt.format(m.evaluation.n)} untouched test matches`:'No accuracy claim until evaluation','◈'));await loadTeams();if(state.page==='overview')await loadFixtures();}
function renderFreshness(){
  if(!state.overview)return;
  const selected=state.page==='overview'?$('competition').value:state.page==='results'?$('results-competition').value:state.page==='explorer'?$('analysis-competition').value:'';const comps=state.overview.competitions.filter(c=>c.sport===state.sport&&(!selected||c.competition===selected));
  const latest=comps.map(c=>c.latest_result).filter(Boolean).sort().at(-1);const m=state.models.find(m=>m.sport===state.sport&&!m.unavailable);
  const old=comps.filter(c=>!c.latest_result||(Date.now()-new Date(c.latest_result))>45*86400000).length;
  const text=el('div');text.append(el('strong','',`Latest ${selected?state.names[selected]:state.sport} result: ${date(latest)}`),el('span','',`Model calibrated through ${date(m?.calibrated_through)}. ${old?`${old} competition(s) have no result within 45 days; check coverage and season dates.`:'Freshness varies by competition.'}`));
  $('freshness').replaceChildren(text,button('Inspect data coverage →','text-button',()=>page('coverage')));
}
function matchCard(m,allowAnalyse=true){const card=el('article','match-card');const meta=el('div','match-meta');meta.append(el('strong','',state.names[m.competition]||m.competition),el('span','',m.status==='finished'?'FINAL':['scheduled','timed'].includes(m.status)?(m.date_precision==='day'?'Time unconfirmed':new Date(m.date).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'})):m.status.toUpperCase()));card.append(meta);for(const side of ['home','away']){const row=el('div','team-row');const initials=m[side].split(' ').slice(0,2).map(s=>s[0]).join('').toUpperCase();row.append(el('span','team-badge',initials),el('span','',m[side]));if(m.status==='finished')row.append(el('span','score',m.sport==='tennis'?(m[side==='home'?'hg':'ag']>m[side==='home'?'ag':'hg']?'W':'L'):(m[side==='home'?'hg':'ag']??'—')));card.append(row);}const bottom=el('div','card-bottom');bottom.append(el('span','',date(m.date_precision==='day'?m.date.slice(0,10):m.date)));if(allowAnalyse&&['scheduled','timed'].includes(m.status)&&new Date(m.date)>new Date())bottom.append(button('Analyse match ↗','',()=>analyse({fixture_id:m.id})));else bottom.append(el('span','',m.source.split(' (')[0]));card.append(bottom);return card;}
async function loadFixtures(){return loadMatchList('fixtures');}
function pagination(id,data,change){
  const prev=button('← Previous','button secondary',()=>change(Math.max(0,data.offset-data.limit)));prev.disabled=data.offset===0;
  const next=button('Next →','button secondary',()=>change(data.offset+data.limit));next.disabled=!data.has_more;
  $(id).replaceChildren(prev,el('span','',data.total?`${fmt.format(data.offset+1)}–${fmt.format(Math.min(data.offset+data.limit,data.total))} of ${fmt.format(data.total)}`:'0 matches'),next);
}
async function loadMatchList(kind){
  const fixture=kind==='fixtures',target=$(fixture?'matchboard':'results-list'),pages=fixture?'fixture-pages':'results-pages';
  const current=ticket(kind);loading(target);$(pages).replaceChildren();if(fixture)$('prediction-progress').textContent='';
  const q=new URLSearchParams({sport:state.sport,offset:state.offsets[kind],limit:24});
  for(const [key,id] of [['competition',fixture?'competition':'results-competition'],['date',fixture?'fixture-date':'results-date'],['q',fixture?'fixture-search':'results-search']])if($(id).value)q.set(key,$(id).value);
  if(fixture)q.set('status',$('fixture-status').value);renderFreshness();
  try{const data=await api(`/api/${kind}?${q}`);if(!current())return;
    if(data.total&&data.offset>=data.total){state.offsets[kind]=0;return loadMatchList(kind);}
    const records=data[kind];const cards=records.map(m=>matchCard(m));target.replaceChildren(...cards);if(fixture&&state.page==='overview')loadBoardForecasts(records,cards,current);
    if(!records.length)empty(target,'No matches match these filters. Try another date, competition or participant.');
    if(fixture){$('match-count').textContent=fmt.format(data.total);$('match-context').textContent={upcoming:'Upcoming verified fixtures, earliest first.',finished:$('fixture-status').value==='auto'?'No upcoming fixtures match these filters. Showing completed results, newest first.':'Completed results, newest first.',all:'All recorded statuses for your selection.'}[data.mode];}
    else $('results-count').textContent=`${fmt.format(data.total)} completed matches · newest first`;
    pagination(pages,data,offset=>{state.offsets[kind]=offset;loadMatchList(kind);});
  }catch(e){if(current())retryPanel(target,e.message,()=>loadMatchList(kind));}
}
function forecastBlock(d,m,reference=false){
  const box=el('div','card-forecast');box.append(el('div','forecast-label',reference?'Saved pre-match reference · not in-play':'Pre-match probabilities'));
  const grid=el('div','forecast-outcomes');const keys=m.sport==='football'?['home_win','draw','away_win']:['home_win','away_win'];
  grid.style.gridTemplateColumns=`repeat(${keys.length},minmax(0,1fr))`;
  for(const k of keys){const cell=el('div');const label=k==='home_win'?m.home:k==='away_win'?m.away:'Draw';cell.append(el('strong','',pct(d.probabilities[k])),el('span','',label));grid.append(cell);}box.append(grid);
  if(d.scorelines?.length)box.append(el('p','model-caption',`Most likely score: ${d.scorelines[0].score} (${pct(d.scorelines[0].probability)})`));
  if(m.sport==='basketball'&&d.expected)box.append(el('p','model-caption',`Model points: ${d.expected.home.toFixed(1)} – ${d.expected.away.toFixed(1)}`));
  if(d.warnings?.length){const details=el('details','forecast-warnings');details.append(el('summary','',`Data limits (${d.warnings.length})`));d.warnings.forEach(w=>details.append(el('p','',w)));box.append(details);}
  box.append(el('div','model-caption',`Calculated ${new Date(d.created_at).toLocaleString('en-GB')} · model ${d.model_version}`));return box;
}
async function loadBoardForecasts(records,cards,current){
  if(!$('show-predictions').checked)return;
  const eligible=records.map((m,i)=>({m,card:cards[i]})).filter(({m})=>['scheduled','timed'].includes(m.status)&&new Date(m.date)>new Date());
  if(!eligible.length){$('prediction-progress').textContent='Pre-match predictions require upcoming fixtures.';return;}
  const targets=new Map();for(const {m,card} of eligible){const n=el('div','card-forecast model-caption','Calculating pre-match probabilities…');card.append(n);targets.set(m.id,n);}
  $('prediction-progress').textContent=`Calculating ${eligible.length} forecasts…`;
  try{const data=await api('/api/predictions',{fixture_ids:eligible.map(({m})=>m.id)});if(!current()||!$('show-predictions').checked)return;
    let count=0;for(const {m} of eligible){const result=data.predictions[m.id];const target=targets.get(m.id);if(new Date(m.date)<=new Date()){target.textContent='Kickoff has passed. See Live / today for reported status.';continue;}
      if(result?.forecast){target.replaceWith(forecastBlock(result.forecast,m));count++;}else target.textContent=result?.unavailable||'Forecast unavailable.';}
    $('prediction-progress').textContent=`${count} of ${eligible.length} forecasts available`;
  }catch(e){if(current()){for(const n of targets.values())n.textContent=e.message;$('prediction-progress').textContent='Forecasts unavailable. Refresh the matchboard to retry.';}}
}
function reportedTime(value){return value?new Date(value).toLocaleString('en-GB'):'Not supplied';}
function renderLive(){
  const d=state.liveData;if(!d||state.liveSport!==state.sport)return;const filter=$('live-status').value,q=$('live-search').value.trim().toLocaleLowerCase();
  const matches=d.matches.filter(m=>(!q||`${m.home} ${m.away}`.toLocaleLowerCase().includes(q))&&(filter==='all'||filter==='playing'&&['in_play','paused'].includes(m.status)||filter==='finished'&&m.status==='finished'||filter==='upcoming'&&['scheduled','timed'].includes(m.status)));
  const priority=m=>['in_play','paused'].includes(m.status)?0:m.status==='finished'?2:1;matches.sort((a,b)=>priority(a)-priority(b)||a.date.localeCompare(b.date));
  $('live-status-message').textContent=`${d.error||d.notice||''} ${d.fetched_at?`Feed fetched ${reportedTime(d.fetched_at)}. `:''}${d.refreshing?'First refresh is in progress. ':''}${d.available?`${matches.length} matching fixtures for ${date(d.date)} (UTC).`:''}`;
  const awaiting=d.matches.filter(m=>['scheduled','timed'].includes(m.status)&&new Date(m.date)<new Date()).length;if(awaiting)$('live-status-message').textContent+=` ${awaiting} fixtures have passed their scheduled kickoff but the provider has not reported a start. Live coverage may be delayed or unavailable on this plan.`;
  $('live-status-message').classList.toggle('warning',!!d.error||awaiting>0);
  const cards=matches.map(m=>{const card=el('article','match-card live-card');const head=el('div','match-meta');
    const statuses={in_play:'IN PLAY',paused:'HALF-TIME',finished:'FINAL',timed:'SCHEDULED',scheduled:'TIME UNCONFIRMED',postponed:'POSTPONED',cancelled:'CANCELLED',suspended:'SUSPENDED',awarded:'AWARDED'};
    head.append(el('strong','',state.names[m.competition]||m.competition),pill(statuses[m.status]||m.status,['in_play','paused'].includes(m.status)?'live-pill':''));card.append(head);
    for(const side of ['home','away']){const row=el('div','team-row');row.append(el('span','',m[side]),el('span','score',m[side==='home'?'hg':'ag']??'—'));card.append(row);}
    const playing=['in_play','paused'].includes(m.status);card.append(el('div','model-caption',playing?(m.minute==null?'Match clock not supplied':`Reported minute: ${m.minute}′`):`${['scheduled','timed'].includes(m.status)&&new Date(m.date)<new Date()?'Awaiting provider status · scheduled kickoff':'Kickoff'}: ${reportedTime(m.date)}`));
    if(m.duration&&m.duration!=='REGULAR')card.append(pill(m.duration.replaceAll('_',' '),'warn'));
    card.append(el('div','model-caption',`Source updated: ${reportedTime(m.updated_at)}`));
    if(playing&&(!m.updated_at||Date.now()-new Date(m.updated_at)>300000))card.append(el('p','analysis-note warning','This match has no recent source timestamp. The score or status may be out of date.'));
    if(m.prematch)card.append(forecastBlock(m.prematch,m,true));else if(playing)card.append(el('p','model-caption','No pre-kickoff forecast was captured for this match. In-play probabilities are unavailable.'));
    return card;});$('live-matches').replaceChildren(...cards);
  if(!cards.length)empty($('live-matches'),d.available?'No matches match these filters in the connected football feed.':d.error||'Waiting for the first provider refresh…');
}
async function loadLive(){
  clearTimeout(state.liveTimer);const current=ticket('live');const sport=state.sport;$('refresh-live').disabled=true;
  if(!state.liveData||state.liveSport!==sport){state.liveData=null;loading($('live-matches'));$('live-status-message').textContent='Checking the connected score provider…';}
  try{const d=await api(`/api/live?sport=${sport}`);if(!current())return;state.liveData=d;state.liveSport=sport;renderLive();}
  catch(e){if(current()){$('live-status-message').textContent=`Refresh failed: ${e.message} Any scores still visible are from an earlier fetch.`;if(!state.liveData)retryPanel($('live-matches'),e.message,loadLive);}}
  finally{if(current()){$('refresh-live').disabled=false;if(state.page==='live'&&sport==='football'&&$('auto-live').checked&&!document.hidden)state.liveTimer=setTimeout(loadLive,60000);}}
}
async function analyse(body){
  const current=ticket('analysis');await page('explorer');loading($('analysis'));const submit=$('analyse-form').querySelector('[type="submit"]');submit.disabled=true;
  try{const d=await api('/api/analyse',body);if(!current())return;state.analysis=d;renderAnalysis(d);
    const f=d.fixture;if(body.fixture_id){$('analysis-competition').value=f.competition;renderFreshness();await loadTeams();if(!current())return;for(const side of ['home','away']){if(!Array.from($(side+'-team').options).some(o=>o.value===f[side+'_id']))$(side+'-team').append(new Option(f[side],f[side+'_id']));$(side+'-team').value=f[side+'_id'];participantNote(side+'-team');}$('analysis-date').value=f.date.slice(0,10);if(f.surface)$('surface').value=f.surface;}
    if(state.page==='explorer')$('analysis').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
  }catch(e){if(current())retryPanel($('analysis'),e.message,()=>analyse(body));}finally{if(current())submit.disabled=false;}
}
function renderAnalysis(d,frozen=false){const container=$('analysis');container.replaceChildren();const f=d.fixture;const headline=el('article','panel analysis-card');const header=el('div','analysis-head');const left=el('div');left.append(el('div','eyebrow',state.names[f.competition]||f.competition),el('h2','',`${f.home} vs ${f.away}`),el('div','analysis-caption',`${date(f.id==='scenario'?f.date.slice(0,10):f.date)} · ${f.id==='scenario'?'Custom scenario':'Verified fixture'}`));header.append(left,pill(frozen?'SAVED FORECAST':'PRE-MATCH'));headline.append(header);if(frozen)headline.append(el('p','analysis-note','This is the original saved forecast. Its probabilities, evidence and model version have not been recalculated.'));d.warnings.forEach(w=>headline.append(el('div','analysis-note warning',w)));
  const keys=f.sport==='football'?['home_win','draw','away_win']:['home_win','away_win'];const bar=el('div','probability-bar');const outcomes=el('div','outcomes');outcomes.style.gridTemplateColumns=`repeat(${keys.length},1fr)`;keys.forEach((k,i)=>{const n=el('div','probability-segment');n.style.width=pct(d.probabilities[k]);bar.append(n);const out=el('div','outcome');out.append(el('strong','',pct(d.probabilities[k])),el('span','',k==='home_win'?f.home:k==='away_win'?f.away:'Draw'));outcomes.append(out);});headline.append(bar,outcomes);if(!frozen&&f.id!=='scenario')headline.append(button('Record pre-match prediction','button primary full',async e=>{const b=e.currentTarget;b.disabled=true;try{await api('/api/journal',{fixture_id:f.id});b.textContent='Recorded in your journal';toast('Prediction recorded using the current server model. Open the journal to inspect the saved forecast.');}catch(e){b.disabled=false;toast(e.message);}}));else if(!frozen)headline.append(el('div','analysis-note','This is a custom matchup, not a verified scheduled fixture. Scenarios cannot be added to the results journal.'));container.append(headline);
  if(d.expected){const exp=el('article','panel analysis-card');exp.append(el('h3','',f.sport==='football'?'Expected goals':'Expected points'));const n=el('div','outcomes');for(const s of ['home','away']){const c=el('div','outcome');c.append(el('strong','',d.expected[s].toFixed(2)),el('span','',f[s]));n.append(c);}n.style.gridTemplateColumns='repeat(2,minmax(0,1fr))';exp.append(n,el('p','model-caption',d.expected.kind));container.append(exp);}
  const columns=el('div','analysis-columns');const markets=el('article','panel analysis-card');markets.append(el('h3','',f.sport==='football'?'Goal markets':'Recent form'));if(f.sport==='football'){Object.entries(d.probabilities).filter(([k])=>!keys.includes(k)).forEach(([k,p])=>{const row=el('div','market');row.append(el('span','',labels[k]),el('strong','',pct(p)));markets.append(row);});}else{markets.append(el('p','muted','Winner probabilities come from the dedicated sport model. Unsupported markets are not estimated.'));}
  const form=el('article','panel analysis-card');form.append(el('h3','','Last five appearances'));for(const side of ['home','away']){form.append(el('div','analysis-caption',f[side]));const strip=el('div','form-strip');d.form[side].forEach(r=>{const badge=el('span',`form-result ${r.result}`,r.result);badge.title=f.sport==='tennis'?`${date(r.date)} · ${r.result}`:`${date(r.date)} · ${r.scored}–${r.conceded}`;const detail=el('div','form-appearance');detail.append(badge,el('span','',f.sport==='tennis'?{W:'Win',L:'Loss',D:'Draw'}[r.result]:`${r.scored}–${r.conceded}`),el('small','',date(r.date)));strip.append(detail);});form.append(strip);}if(d.scorelines.length){form.append(el('h3','','Likely scorelines'));d.scorelines.slice(0,3).forEach(s=>{const row=el('div','score-pill');row.append(el('strong','',s.score),el('span','',pct(s.probability)));form.append(row);});}columns.append(markets,form);container.append(columns);
  container.append(comparison(d));const evidence=el('article','panel analysis-card');evidence.append(el('h3','','What informs this forecast'));const list=el('ul','evidence-list');d.analysis.forEach(s=>list.append(el('li','',s)));evidence.append(list);evidence.append(el('div','model-detail',`History through ${date(d.history_through)} · Model ${d.model_version}`),el('div','model-caption','Lineups and injury reports are not included unless explicitly stated. Probabilities are estimates, not guarantees.'));container.append(evidence);
}
function comparison(d){
  const panel=el('article','panel analysis-card');panel.append(el('h3','','The matchup in numbers'),el('p','model-caption','Recent averages use up to 10 earlier appearances. Elo is the model’s relative strength rating. Missing observations are shown as unavailable.'));
  const table=el('table');const head=el('thead');const row=el('tr');['Evidence',d.fixture.home,d.fixture.away].forEach(v=>{const th=el('th','',v);th.scope='col';row.append(th);});head.append(row);table.append(head);const body=el('tbody');
  const specs=[['elo','Elo rating',0],['matches','Available history (up to 50)',0],['form','Recent form (win = 1, draw = 0.5)',2],['scored',d.fixture.sport==='tennis'?'Sets won / match':'Scored / match',2],['conceded',d.fixture.sport==='tennis'?'Sets lost / match':'Conceded / match',2],['rest','Days since last match (capped at 90)',0],['density','Appearances in last 14 days',0]];
  if(d.fixture.sport==='football')specs.push(['xg','Observed xG / match',2],['xga','Observed xG conceded / match',2],['xg_coverage','Recent appearances with observed xG','pct']);
  if(d.fixture.sport==='tennis'){specs.splice(3,2);specs.push(['surface_form','Recent win rate on selected surface','pct']);}
  for(const [key,label,precision] of specs){const r=el('tr');const th=el('th','',label);th.scope='row';r.append(th);for(const side of ['home','away']){const v=d.features?.[`${side}_${key}`];r.append(el('td','',v==null?'Unavailable':precision==='pct'?pct(v):Number(v).toFixed(precision)));}body.append(r);}table.append(body);const wrap=el('div','table-scroll');wrap.append(table);panel.append(wrap);return panel;
}
async function loadJournal(){loading($('journal-list'));const current=ticket('journal');const data=await api('/api/journal');if(!current())return;data.predictions=data.predictions.filter(r=>r.payload.fixture.sport===state.sport);const settled=data.predictions.filter(r=>r.settlement&&r.settlement.status!=='void');const correct=settled.filter(r=>r.settlement.outcome_correct).length;$('journal-summary').replaceChildren(metric('Recorded forecasts',fmt.format(data.predictions.length),'Frozen before kickoff'),metric('Settled forecasts',fmt.format(settled.length),'Matched by provider fixture'),metric('Observed accuracy',settled.length?pct(correct/settled.length):'—',`${correct} correct · ${data.predictions.filter(r=>!r.settlement).length} pending`));if(!data.predictions.length)return empty($('journal-list'),'Your journal starts with the next verified fixture. Open a match analysis and record its pre-match prediction.');const list=el('div','match-grid');data.predictions.filter(r=>{const filter=$('journal-status').value;return filter==='all'||(filter==='pending'&&!r.settlement)||(filter==='void'&&r.settlement?.status==='void')||(filter==='settled'&&r.settlement&&r.settlement.status!=='void');}).forEach(r=>{const d=r.payload;const n=matchCard(d.fixture,false);n.append(pill(r.settlement?(r.settlement.status==='void'?'Voided forecast':r.settlement.outcome_correct?'Correct outcome':'Incorrect outcome'):'Awaiting result',r.settlement&&!r.settlement.outcome_correct?'warn':''),el('div','model-detail',`Recorded ${date(r.created_at)} · ${r.model_version}`));if(r.settlement)n.append(el('div','model-caption',r.settlement.status==='void'?r.settlement.reason:d.fixture.sport==='tennis'?`Recorded winner indicator ${r.settlement.score} (1 = win, 0 = loss)`:`Final score ${r.settlement.score}`));n.append(button('View saved forecast →','text-button',async()=>{state.requests.analysis=(state.requests.analysis||0)+1;await page('explorer');renderAnalysis(d,true);}));list.append(n);});$('journal-list').replaceChildren(list);if(!list.children.length)empty($('journal-list'),'No forecasts with this status for the selected sport.');}
async function loadResults(){return loadMatchList('results');}
function calibrationChart(bins){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 520 190');svg.classList.add('chart');svg.setAttribute('role','img');svg.setAttribute('aria-label','Confidence calibration. Observed accuracy versus predicted probability.');function shape(tag,attrs){const n=document.createElementNS(svg.namespaceURI,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));svg.append(n);return n;}for(let i=0;i<=5;i++){const x=40+i*88,y=160-i*28;shape('line',{x1:40,y1:y,x2:480,y2:y,stroke:'#edf1e5'});const t=shape('text',{x:10,y:y+3,fill:'#96a18c','font-size':9});t.textContent=`${i*20}%`;}shape('line',{x1:40,y1:160,x2:480,y2:20,stroke:'#c5ceb8','stroke-dasharray':'5 5'});const points=bins.map(b=>`${40+b.probability*440},${160-b.observed*140}`).join(' ');shape('polyline',{points,fill:'none',stroke:'#4c7737','stroke-width':2.5});bins.forEach(b=>shape('circle',{cx:40+b.probability*440,cy:160-b.observed*140,r:4,fill:'#4c7737'}));const t=shape('text',{x:190,y:185,fill:'#839473','font-size':9});t.textContent='PREDICTED CONFIDENCE →';return svg;}
async function loadModels(){await Promise.all([loadPerformance().catch(e=>retryPanel($('prospective-results'),e.message,loadPerformance)),loadPlayerReadiness().catch(e=>retryPanel($('player-readiness'),e.message,loadPlayerReadiness))]);loading($('model-list'));const current=ticket('models');const d=await api('/api/models');if(!current())return;state.models=d.models;const selected=d.models.filter(m=>m.sport===state.sport);$('model-list').replaceChildren();for(const m of selected){if(m.unavailable){empty($('model-list'),m.unavailable);continue;}const c=el('article','panel model-card');const head=el('div','analysis-head');head.append(el('h2','',`${m.sport} model`),pill('CHRONOLOGICAL BENCHMARK'));c.append(head,el('p','muted',`Held-out test: ${date(m.evaluation.test_start)} – ${date(m.evaluation.test_end)} · ${fmt.format(m.evaluation.n)} matches`));const grid=el('div','model-metrics');grid.append(metric('Accuracy',pct(m.evaluation.accuracy),'Selected outcome hit rate'),metric('Log loss',m.evaluation.log_loss.toFixed(3),'Lower is better'),metric('Prior baseline',m.evaluation.baseline.log_loss.toFixed(3),'Baseline log loss'),metric('Brier score',m.evaluation.brier.toFixed(3),'Lower is better'));c.append(grid,el('h3','','Does confidence match reality?'),calibrationChart(m.evaluation.calibration),el('div','model-caption','The dashed line is perfect calibration. The solid line shows observed accuracy within confidence bands.'));c.append(el('div','analysis-note',m.evaluation_scope),el('div','model-detail',`Serving model trained through ${date(m.trained_through)} · calibrated through ${date(m.calibrated_through)}`));
  const wrap=el('div','table-scroll');const table=el('table');const h=el('thead');const hr=el('tr');['Competition','Test matches','Accuracy','Log loss'].forEach(s=>hr.append(el('th','',s)));h.append(hr);table.append(h);const body=el('tbody');Object.entries(m.evaluation.competition).forEach(([comp,e])=>{const row=el('tr');[state.names[comp]||comp,fmt.format(e.n),pct(e.accuracy),e.log_loss.toFixed(3)].forEach(s=>row.append(el('td','',s)));body.append(row);});table.append(body);wrap.append(table);c.append(wrap);$('model-list').append(c);}}
async function loadCoverage(){loading($('coverage-summary'));const current=ticket('coverage');const d=await api('/api/coverage');if(!current())return;const failed=d.latest_imports.filter(i=>i.status==='error').length;$('coverage-summary').replaceChildren(metric('Covered competitions',fmt.format(d.competitions.length),'Across all sports'),metric('Observed xG matches',fmt.format(d.xg.observed_matches),`${fmt.format(d.xg.total)} football results · source-labelled`),metric('Sources needing attention',fmt.format(failed),'Shown below; existing data retained'));$('coverage-table').replaceChildren();d.competitions.forEach(c=>{const r=el('tr');const age=c.latest_result?Math.floor((Date.now()-new Date(c.latest_result))/86400000):null;[state.names[c.competition]||c.competition,c.sport,fmt.format(c.completed),date(c.latest_result)].forEach(s=>r.append(el('td','',s)));const cell=el('td');cell.append(pill(age===null?'Unavailable':`${age} days since result`,age>45?'warn':''));r.append(cell);$('coverage-table').append(r);});$('imports-table').replaceChildren();d.imports.forEach(i=>{const row=el('tr');row.append(el('td','',i.source));const cell=el('td');cell.append(pill(i.status,i.status==='error'?'error':i.status==='empty'?'warn':''));row.append(cell,el('td','',fmt.format(i.rows)),el('td','',i.detail));$('imports-table').append(row);});}
async function switchSport(sport,push=true){
  if(state.sport!==sport){state.sport=sport;state.epoch++;state.offsets={fixtures:0,results:0};state.analysis=null;
    empty($('analysis'),'Choose a matchup or open a verified fixture to explore its forecast.');
    for(const id of ['summary-metrics','matchboard','results-list','journal-list','model-list','coverage-summary','live-matches'])loading($(id));
    for(const id of ['fixture-pages','results-pages'])$(id).replaceChildren();$('match-count').textContent='—';
    $('analyse-form').querySelector('[type="submit"]').disabled=true;state.teams=[];
    for(const side of ['home','away']){$(side+'-team-search').value='';renderTeamOptions(side+'-team','');$(side+'-team').disabled=true;$(side+'-team-search').disabled=true;}
    if(state.overview){setCompetitions();renderFreshness();}
    for(const id of ['fixture-date','fixture-search','results-date','results-search'])$(id).value='';
  }
  document.querySelectorAll('[data-sport]').forEach(b=>{b.classList.toggle('active',b.dataset.sport===sport);b.setAttribute('aria-pressed',String(b.dataset.sport===sport));});
  const hash=`#${state.page}?sport=${sport}`;if(push&&location.hash!==hash)history.pushState(null,'',hash);
  try{await loadOverview();if(state.sport===sport)await page(state.page,false,false);}catch(e){retryPanel($('matchboard'),e.message,()=>switchSport(sport,push));toast(e.message);}finally{if(state.sport===sport)$('analyse-form').querySelector('[type="submit"]').disabled=false;}
}
document.querySelectorAll('[data-page]').forEach(n=>n.addEventListener('click',()=>page(n.dataset.page)));
document.querySelectorAll('[data-go]').forEach(n=>n.addEventListener('click',()=>page(n.dataset.go)));
document.querySelectorAll('[data-sport]').forEach(n=>n.addEventListener('click',()=>switchSport(n.dataset.sport)));
for(const id of ['competition','fixture-date','fixture-status'])$(id).addEventListener('change',()=>{state.offsets.fixtures=0;loadFixtures();});
$('fixture-search').addEventListener('input',debounce(()=>{state.offsets.fixtures=0;loadFixtures();}));
for(const id of ['results-competition','results-date'])$(id).addEventListener('change',()=>{state.offsets.results=0;loadResults();});
$('results-search').addEventListener('input',debounce(()=>{state.offsets.results=0;loadResults();}));
$('reset-results').addEventListener('click',()=>{for(const id of ['results-competition','results-date','results-search'])$(id).value='';state.offsets.results=0;loadResults();});
$('analysis-competition').addEventListener('change',()=>{renderFreshness();loadTeams();});
$('clear-filters').addEventListener('click',()=>{for(const id of ['competition','fixture-date','fixture-search'])$(id).value='';$('fixture-status').value='auto';state.offsets.fixtures=0;loadFixtures();});
for(const side of ['home','away']){$(side+'-team-search').addEventListener('input',()=>renderTeamOptions(side+'-team'));$(side+'-team').addEventListener('change',()=>participantNote(side+'-team'));}
$('swap-teams').addEventListener('click',()=>{const home=$('home-team').value,away=$('away-team').value;for(const side of ['home','away'])$(side+'-team-search').value='';renderTeamOptions('home-team',away);renderTeamOptions('away-team',home);});
$('journal-status').addEventListener('change',()=>page('journal',false,false));
$('show-predictions').addEventListener('change',loadFixtures);
$('refresh-live').addEventListener('click',loadLive);
$('auto-live').addEventListener('change',()=>{clearTimeout(state.liveTimer);if($('auto-live').checked&&state.page==='live')loadLive();});
$('live-status').addEventListener('change',renderLive);$('live-search').addEventListener('input',renderLive);
document.addEventListener('visibilitychange',()=>{clearTimeout(state.liveTimer);if(!document.hidden&&state.page==='live'&&$('auto-live').checked)loadLive();});
$('analyse-form').addEventListener('submit',e=>{e.preventDefault();analyse({sport:state.sport,competition:$('analysis-competition').value,home_id:$('home-team').value,away_id:$('away-team').value,date:$('analysis-date').value,surface:$('surface').value});});
$('settle').addEventListener('click',async()=>{const b=$('settle');b.disabled=true;try{const d=await api('/api/journal/settle',{});toast(`${d.updated} predictions settled or corrected from available results.`);await loadJournal();}catch(e){toast(e.message);}finally{b.disabled=false;}});
$('refresh-view').addEventListener('click',async()=>{const b=$('refresh-view');b.disabled=true;try{state.models=(await api('/api/models')).models;await loadOverview();await page(state.page,false,false);if(state.page!=='live')toast('View refreshed from stored data. This does not download new provider data.');}catch(e){toast(e.message);}finally{b.disabled=false;}});
document.querySelector('.skip-link').addEventListener('click',e=>{e.preventDefault();$('main-content').focus();});
document.querySelector('.brand').addEventListener('click',e=>{e.preventDefault();page('overview');});
window.addEventListener('popstate',async()=>{const r=route();state.page=r.page;if(r.sport!==state.sport)await switchSport(r.sport,false);else await page(r.page,false);});
async function init(){
  $('today').textContent=new Date().toLocaleDateString('en-GB',{weekday:'short',day:'numeric',month:'short',year:'numeric'});
  $('analysis-date').value=new Date().toISOString().slice(0,10);$('analysis-date').min=$('analysis-date').value;
  const r=route();state.page=r.page;state.sport=r.sport;await page(r.page,false,false,false);
  document.querySelectorAll('[data-sport]').forEach(b=>{b.classList.toggle('active',b.dataset.sport===r.sport);b.setAttribute('aria-pressed',String(b.dataset.sport===r.sport));});
  try{state.models=(await api('/api/models')).models;await switchSport(r.sport,false);}catch(e){retryPanel($('matchboard'),e.message,init);toast(e.message);}
}init();

async function loadPerformance(){
  const current=ticket('performance');loading($('prospective-results'));
  const d=await api(`/api/performance?sport=${state.sport}&horizon=${$('tracking-horizon').value}`);
  if(!current())return;
  const target=$('prospective-results');target.replaceChildren();
  target.append(el('p','muted',`${d.tracked} tracked slots · ${d.withheld} withheld for data quality · ${d.settled} settled · ${d.void} voided. Last tracking run: ${d.last_run?new Date(d.last_run).toLocaleString():'Not run yet'}.`));
  target.append(el('p','model-caption',d.notice));
  if(d.scheduler_stale)target.append(el('p','warning','Tracking is not running regularly. Missing recording windows cannot be recovered afterward.'));
  if(!d.groups.length){target.append(el('p','','No settled forecasts yet. Results appear after pre-match recording and confirmed results; historical outcomes are never backfilled as predictions.'));return;}
  const wrap=el('div','table-scroll'),table=el('table'),head=el('thead'),hr=el('tr');
  ['Competition / model','Settled','Accuracy','Log loss','Brier'].forEach(t=>hr.append(el('th','',t)));head.append(hr);table.append(head);
  const body=el('tbody');d.groups.forEach(g=>{const r=el('tr');[`${state.names[g.competition]||g.competition} / ${g.model_version}`,g.n,pct(g.accuracy),g.log_loss.toFixed(3),g.brier.toFixed(3)].forEach(v=>r.append(el('td','',String(v))));body.append(r);});table.append(body);wrap.append(table);target.append(wrap);
}
async function loadPlayerReadiness(){
  const current=ticket('players');const target=$('player-readiness');loading(target);
  if(state.sport!=='football'){empty(target,'Player markets are being prepared for football first.');return;}
  const [d,publicData]=await Promise.all([api('/api/players/status'),api(`/api/players/public?league=${encodeURIComponent(state.playerLeague||'')}&q=${encodeURIComponent(state.playerQuery||'')}&offset=${state.playerOffset||0}`)]);if(!current())return;
  target.replaceChildren(pill(publicData.appearances?'Public player history connected':d.configured?'Provider key configured':'Awaiting provider setup',publicData.appearances?'':'warn'),el('p','',`Optional API provider: ${d.fixtures} fixtures / ${d.appearances} appearances. Public-page imports are listed below.`),el('p','muted',d.notice));
  const wrap=el('div','table-scroll'),table=el('table'),head=el('thead'),hr=el('tr');
  ['Market','Evidence needed','Forecast'].forEach(t=>hr.append(el('th','',t)));head.append(hr);table.append(head);
  const body=el('tbody');for(const m of d.markets){const r=el('tr');[m.name,m.needs,'Not available yet'].forEach(t=>r.append(el('td','',t)));body.append(r);}table.append(body);wrap.append(table);target.append(wrap);
  target.append(el('h3','','Public player match histories'),el('p','muted',`${publicData.total_players} matching players · ${publicData.appearances} appearances. No API key required.`),el('p','model-caption',publicData.notice));
  if(publicData.coverage.length){const stamps=publicData.coverage.map(c=>c.observed_at).sort();const missing=publicData.coverage.reduce((n,c)=>n+c.expected_matches-c.covered_matches,0);target.append(el('p','model-caption',`Player inventories collected ${date(stamps[0])}${stamps[0].slice(0,10)!==stamps.at(-1).slice(0,10)?' – '+date(stamps.at(-1)):''}. Browser-assisted snapshot; refresh is not automatic.`));if(missing)target.append(el('p','warning',`${missing} discovered match(es) excluded or unavailable after validation. Conflicting duplicate source rows are excluded rather than guessed. Coverage totals retain these gaps.`));}
  if(publicData.coverage.length){const box=el('div','table-scroll'),t=el('table'),h=el('thead'),hr=el('tr');['League / season','Teams','Matches imported','Players covered'].forEach(x=>hr.append(el('th','',x)));h.append(hr);t.append(h);const b=el('tbody');for(const c of publicData.coverage){const r=el('tr');[`${c.name} ${c.season}/${c.season+1}`,c.teams,`${c.covered_matches} / ${c.expected_matches}`,`${c.covered_players} / ${c.expected_players}`].forEach(x=>r.append(el('td','',String(x))));b.append(r);}t.append(b);box.append(t);target.append(box);}
  const filters=el('div','filters'),leagueLabel=el('label','','League'),leagueSelect=el('select');leagueSelect.append(new Option('All covered leagues',''));for(const c of publicData.coverage)leagueSelect.append(new Option(c.name,c.league));leagueSelect.value=state.playerLeague||'';leagueLabel.append(leagueSelect);const queryLabel=el('label','','Player or team'),queryInput=el('input');queryInput.type='search';queryInput.value=state.playerQuery||'';queryInput.placeholder='Search all collected players';queryLabel.append(queryInput);const apply=()=>{state.playerLeague=leagueSelect.value;state.playerQuery=queryInput.value.trim();state.playerOffset=0;loadPlayerReadiness().catch(e=>retryPanel(target,e.message,loadPlayerReadiness));};queryInput.addEventListener('keydown',e=>{if(e.key==='Enter')apply();});filters.append(leagueLabel,queryLabel,button('Apply filters','filter-button',apply));target.append(filters);
  target.append(el('p','model-caption',`Showing ${publicData.total_players?publicData.offset+1:0}–${publicData.offset+publicData.players.length} of ${publicData.total_players} players. Reported yellow/red card counts are separate from shots; shots on target remain unavailable.`));
  for(const p of publicData.players){const details=el('details','analysis-note');const recent=p.recent;const minutes=recent.reduce((n,r)=>n+r.minutes,0),goals=recent.reduce((n,r)=>n+r.goals,0),assists=recent.reduce((n,r)=>n+r.assists,0);
    details.append(el('summary','',`${p.name} · ${p.appearances} appearances · latest ${date(p.latest)}`),el('p','',`Last ${recent.length} appearances: ${minutes} minutes, ${goals} goals, ${assists} assists. Appearance-only sample; does not estimate the chance of starting.`));
    const scroll=el('div','table-scroll'),t=el('table'),head=el('thead'),hr=el('tr');['Date / match','Minutes','Shots','Goals','Assists','xG','xA','Yellow / red'].forEach(v=>hr.append(el('th','',v)));head.append(hr);t.append(head);const body=el('tbody');
    for(const r of recent){const tr=el('tr');[`${date(r.date)} · ${r.home} ${r.score} ${r.away}`,r.minutes,r.shots,r.goals,r.assists,r.xg.toFixed(2),r.xa.toFixed(2),r.yellow_cards===null||r.yellow_cards===undefined?'Not covered':`${r.yellow_cards} / ${r.red_cards}`].forEach(v=>tr.append(el('td','',String(v))));body.append(tr);}t.append(body);scroll.append(t);details.append(scroll);const a=el('a','text-button','View original player history');a.href=p.source;a.target='_blank';a.rel='noopener noreferrer';details.append(a);target.append(details);}
  const pager=el('nav','pagination');pager.setAttribute('aria-label','Player history pages');const move=offset=>{state.playerOffset=offset;loadPlayerReadiness().catch(e=>retryPanel(target,e.message,loadPlayerReadiness));};if(publicData.offset>0)pager.append(button('Previous players','button secondary',()=>move(Math.max(0,publicData.offset-publicData.limit))));if(publicData.has_more)pager.append(button('Next players','button secondary',()=>move(publicData.offset+publicData.limit)));target.append(pager);
}
$('tracking-horizon').addEventListener('change',()=>loadPerformance().catch(e=>retryPanel($('prospective-results'),e.message,loadPerformance)));
