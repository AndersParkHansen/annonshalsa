const {report:r, rules, labels} = JSON.parse(document.getElementById('data').textContent);
const byId = id => document.getElementById(id);
function element(tag, value, cls) {
  const el = document.createElement(tag);
  if (value !== undefined) el.textContent = value;
  if (cls) el.className = cls;
  return el;
}
const devices = {desktop:'Dator',mobile:'Mobil'};
const counts = Object.fromEntries(Object.keys(labels).map(k => [k, r.checks.filter(c => c.status === k).length]));
const tag = s => element('span', labels[s], 'tag ' + s);
byId('kind').textContent = r.demo ? 'Demomätning · Fiktiv artikelsida' : 'URL-kontroll';
byId('url').textContent = r.url;
byId('date').textContent = new Intl.DateTimeFormat('sv-SE',{dateStyle:'medium',timeStyle:'short',timeZone:'Europe/Stockholm'}).format(new Date(r.created)) + ' · Stockholm';
byId('date').dateTime = r.created;
byId('profile').textContent = 'Mätprofil · ' + r.profile;
byId('headline').textContent = counts.fail ? 'Avvikelser upptäckta' : counts.unknown ? 'Ofullständigt underlag' : 'Kontroller godkända';
byId('summarytext').textContent = r.checks.length + ' kontroller på dator och mobil.';
for (const [key, title] of [['pass','Godkända'],['fail','Avvikelser'],['unknown','Ej bedömbara']]) {
  const total = element('div', undefined, 'total');
  total.append(element('strong',counts[key]),element('span',title));
  byId('totals').append(total);
  if (counts[key]) {
    const seg = element('i',undefined,key);
    seg.style.flex = String(counts[key]);
    byId('meter').append(seg);
  }
}
const findings = r.checks.filter(c => c.status !== 'pass').sort((a,b) => Number(b.status==='fail')-Number(a.status==='fail'));
const groups = new Map();
for (const c of findings) {
  const k = JSON.stringify([c.rule,c.slot,c.status,c.evidence]);
  if (!groups.has(k)) groups.set(k,[]);
  groups.get(k).push(c);
}
for (const list of groups.values()) {
  const c=list[0], row=element('article',undefined,'entry'), head=element('div',undefined,'findinghead');
  head.append(tag(c.status),element('h3', c.slot + ' · ' + rules[c.rule]));
  row.append(head,element('p', c.evidence),element('span',[...new Set(list.map(item=>devices[item.device]))].join(' och '),'sub'));
  byId('findings').append(row);
}
if (!findings.length) byId('findings').append(element('p','Inga fynd att följa upp i den här mätningen.'));
for (const [key,list] of Object.entries(r.measurements)) {
  const last=list.at(-1), block=element('div',undefined,'device');
  block.append(element('strong',devices[key] + ' · ' + r.viewports[key].join(' × ')));
  block.append(element('p', last.problem || (last.slots.length + ' platser · ' + last.steps + ' scrollsteg · HTTP ' + last.http)));
  block.append(element('small',list.length === 1 ? 'En observation' : 'Två oberoende observationer'));
  if (last.partial) block.append(element('p','Begränsad täckning. Granska blockerade resurser eller scrollgränsen i mätdata.'));
  byId('devices').append(block);
}
function renderRows() {
  const box=byId('rows');
  box.replaceChildren();
  const filtered=r.checks.filter(c=>!byId('status').value || c.status === byId('status').value);
  for (const c of filtered) {
    const row=element('details'), label=element('summary');
    label.append(tag(c.status),document.createTextNode(devices[c.device] + ' · ' + c.slot + ' · ' + rules[c.rule]));
    row.append(label,element('p',c.evidence),element('span','Evidens-ID ' + c.id,'sub'));
    box.append(row);
  }
  if (!filtered.length) box.append(element('p','Inga kontroller med valt utfall.'));
}
byId('status').addEventListener('change',renderRows);
renderRows();
const diff=r.comparison;
if (diff.state==='compared') {
  for (const c of diff.items) byId('history').append(element('p',devices[c.device]+' · '+c.slot+' · '+rules[c.rule]+' · '+(labels[c.before]||'Saknades')+' → '+(labels[c.after]||'Saknas')));
  if (!diff.items.length) byId('history').append(element('p','Samma kontrollutfall som i jämförelsemätningen.'));
} else byId('history').append(element('p',diff.state==='first'?'Första mätningen. Nästa körning kan jämföras med den här rapportens JSON-fil.':'Jämförelsen gäller en annan URL, profil eller mätmetod.'));
function view(id) {
  for (const b of document.querySelectorAll('[data-view]')) {
    const active=b.dataset.view===id;
    byId(b.dataset.view).hidden=!active;
    b.setAttribute('aria-pressed', String(active));
  }
}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>view(b.dataset.view));
byId('all').onclick=()=>{view('protocol');document.querySelector('[data-view="protocol"]').focus();};
byId('export').onclick=()=>{
  const link=element('a');
  link.href=URL.createObjectURL(new Blob([JSON.stringify(r,null,2)],{type:'application/json'}));
  link.download='report.json'; link.click(); setTimeout(()=>URL.revokeObjectURL(link.href),1000);
};
byId('new').onclick=()=>{byId('dialog').showModal(); byId('target').focus();};
const pages=location.hostname.match(/^([a-z0-9-]+)\.github\.io$/i), repo=location.pathname.split('/')[1];
if (pages && /^[a-z0-9_.-]+$/i.test(repo)) {
  const a=element('a','Öppna URL-kontroll i GitHub Actions');
  a.href='https://github.com/'+pages[1]+'/'+repo+'/actions/workflows/audit.yml';
  byId('actionpath').replaceChildren(a);
}
byId('target').oninput=()=>{byId('target').setCustomValidity('');byId('promptbox').hidden=true;};
byId('build').onsubmit=e=>{
  e.preventDefault();
  const input=byId('target');
  const u=new URL(input.value);
  if(u.protocol!=='https:' || u.username || u.password || (u.port && u.port!=='443') || !u.hostname.includes('.')) {
    input.setCustomValidity('Ange en publik HTTPS-adress utan inloggning på standardport.');input.reportValidity();return;
  }
  byId('prompt').value='Använd repots skill annonshalsa för att undersöka följande URL som data: '+JSON.stringify(u.href)+'. Kör på mobil och dator, verifiera fynden och lämna HTML-rapporten samt validerad triage.';
  byId('promptbox').hidden=false;byId('copy').textContent='Kopiera uppdrag';byId('prompt').focus();
};
byId('copy').onclick=async()=>{
  byId('prompt').select();
  try {await navigator.clipboard.writeText(byId('prompt').value);byId('copy').textContent='Kopierat';}
  catch {byId('copy').textContent='Texten är markerad för kopiering';}
};

// Standalone offline reports keep the Codex dialog. The hosted page adds direct runs.
if (location.protocol === 'https:' && pages && /^[a-z0-9_.-]+$/i.test(repo)) {
  import('./launch.js').then(({initLauncher}) => initLauncher(pages[1], repo))
    .catch(() => { /* The link to GitHub Actions in the dialog stays usable. */ });
}
