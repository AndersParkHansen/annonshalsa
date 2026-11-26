// Loaded only by the GitHub Pages report. All authenticated requests go to GitHub's API.
export function initLauncher(owner, repo) {
  const el = id => document.getElementById(id);
  const repoName = owner + '/' + repo;
  const base = 'https://api.github.com/repos/' + repoName;
  const runs = 'https://github.com/' + repoName + '/actions/runs/';
  const form = el('launch-form');
  const input = el('launch-url');
  const submit = el('launch-submit');
  const dialog = el('auth-dialog');
  const tokenInput = el('github-credential');
  const feedback = el('launch-feedback');
  const links = el('launch-links');
  let token = '';
  let generation = 0;
  let timer;
  let dispatching = false;

  function forget() {
    token = '';
    tokenInput.value = '';
    el('forget-token').hidden = true;
  }

  function addLink(text, href) {
    const link = document.createElement('a');
    link.href = href;
    link.textContent = text;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    links.append(link);
  }

  async function github(path, body) {
    const headers = {Accept:'application/vnd.github+json', 'X-GitHub-Api-Version':'2026-03-10'};
    if (token) headers.Authorization = 'Bearer ' + token;
    if (body) headers['Content-Type'] = 'application/json';
    const res = await fetch(base + path, {
      method:body ? 'POST' : 'GET', headers, body:body ? JSON.stringify(body) : undefined,
      cache:'no-store', credentials:'omit', redirect:'error', referrerPolicy:'no-referrer',
      signal:AbortSignal.timeout(20000)
    });
    if (!res.ok) throw Object.assign(new Error('GitHub svarade med HTTP ' + res.status), {status:res.status});
    return res.status === 204 ? null : res.json();
  }

  async function follow(runId, current) {
    const runUrl = runs + runId;
    links.replaceChildren();
    addLink('Öppna körningen på GitHub', runUrl);
    const deadline = Date.now() + 16 * 60 * 1000;
    let failures = 0;
    async function poll() {
      if (current !== generation) return;
      try {
        const run = await github('/actions/runs/' + runId);
        if (current !== generation) return;
        failures = 0;
        if (run.status === 'completed') {
          if (run.conclusion !== 'success') {
            const conclusion = {failure:'misslyckades', cancelled:'avbröts', timed_out:'överskred tidsgränsen', skipped:'hoppades över'};
            feedback.textContent = 'Kontrollen ' + (conclusion[run.conclusion] || 'avslutades utan rapport') + '. Se körningen för detaljer.';
            return;
          }
          feedback.textContent = 'Kontrollen är klar. Rapporten finns bland körningens artefakter.';
          const data = await github('/actions/runs/' + runId + '/artifacts').catch(() => null);
          if (current !== generation) return;
          const artifact = data?.artifacts?.find(a => !a.expired && a.name === 'annonsrapport-' + runId);
          if (artifact && Number.isSafeInteger(artifact.id)) {
            addLink('Hämta rapport (ZIP)', runUrl + '/artifacts/' + artifact.id);
            feedback.textContent = 'Kontrollen är klar. Öppna index.html i den hämtade rapporten.';
          }
          return;
        }
        feedback.textContent = run.status === 'in_progress' ? 'Kontrollen pågår i GitHub Actions…' : 'Kontrollen ligger i kö hos GitHub…';
      } catch (err) {
        if (current !== generation) return;
        failures++;
        feedback.textContent = 'Körningen har startat. Status kunde inte hämtas just nu.';
        if (failures >= 3 || [401,403,429].includes(err.status)) return;
      }
      if (Date.now() < deadline) timer = setTimeout(poll, failures ? 15000 : 8000);
      else feedback.textContent = 'Följ den fortsatta körningen på GitHub.';
    }
    await poll();
  }

  function targetUrl() {
    const value = input.value.trim();
    if (!value) throw new Error();
    const url = new URL(value.includes('://') ? value : 'https://' + value);
    const host = url.hostname;
    if (url.protocol !== 'https:' || url.username || url.password || url.port ||
        !host.includes('.') || /\s|\\/.test(value) || host.endsWith('.localhost')) throw new Error();
    return url.href;
  }

  async function start() {
    if (dispatching) return;
    let url;
    try { url = targetUrl(); }
    catch {
      input.setCustomValidity('Ange en publik HTTPS-adress utan inloggningsuppgifter på standardport.');
      input.reportValidity();
      return;
    }
    if (!token) { dialog.showModal(); tokenInput.focus(); return; }
    dispatching = true;
    submit.disabled = true;
    const current = ++generation;
    clearTimeout(timer);
    links.replaceChildren();
    feedback.textContent = 'Skickar kontrollen till GitHub…';
    try {
      const run = await github('/actions/workflows/audit.yml/dispatches', {ref:'main', inputs:{url}});
      if (!Number.isSafeInteger(run?.workflow_run_id)) {
        feedback.textContent = 'GitHub tog emot kontrollen. Öppna arbetsflödet för att följa den.';
        addLink('Öppna URL-kontroll', 'https://github.com/' + repoName + '/actions/workflows/audit.yml');
      } else {
        feedback.textContent = 'Kontrollen har startat.';
        history.replaceState(null, '', '#korning=' + run.workflow_run_id);
        void follow(run.workflow_run_id, current);
      }
    } catch (err) {
      if ([401,403,404].includes(err.status)) {
        forget();
        feedback.textContent = 'GitHub nekade starten. Kontrollera att din token gäller för repot med Actions → Read and write och att ditt konto har skrivåtkomst.';
      } else if (err.status) {
        feedback.textContent = err.message + '. Kontrollera att arbetsflödet URL-kontroll är aktiverat.';
      } else {
        feedback.textContent = 'GitHubs svar uteblev. Kontrollera körningslistan innan du försöker igen.';
        addLink('Visa körningslistan', 'https://github.com/' + repoName + '/actions/workflows/audit.yml');
      }
    } finally {
      dispatching = false;
      submit.disabled = false;
    }
  }

  el('auth-repo').textContent = repoName;
  const tokenHelp = new URL('https://github.com/settings/personal-access-tokens/new');
  tokenHelp.search = new URLSearchParams({name:'Annonshälsa',target_name:owner,actions:'write'}).toString();
  el('token-help').href = tokenHelp.href;
  form.addEventListener('submit', e => { e.preventDefault(); void start(); });
  input.addEventListener('input', () => input.setCustomValidity(''));
  el('auth-form').addEventListener('submit', e => {
    e.preventDefault();
    token = tokenInput.value.trim();
    tokenInput.value = '';
    if (!token) { tokenInput.focus(); return; }
    el('forget-token').hidden = false;
    dialog.close();
    void start();
  });
  dialog.addEventListener('close', () => { tokenInput.value = ''; });
  window.addEventListener('pagehide', forget);
  el('forget-token').onclick = forget;
  el('launch').hidden = false;
  // The header shortcut now focuses the live form; the offline report keeps its Codex shortcut.
  el('new').onclick = () => { el('launch').scrollIntoView({block:'center'}); input.focus(); };
  const resumed = location.hash.match(/^#korning=([1-9]\d{0,15})$/);
  if (resumed && Number.isSafeInteger(Number(resumed[1]))) void follow(Number(resumed[1]), ++generation);
}
