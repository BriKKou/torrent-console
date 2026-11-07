import { showAccount } from './account.js';
import { addWatch, fetchProviders, searchLink, searchReleases } from './api.js';
import { mountControls, mountProviders } from './controls.js';
import { $, el } from './dom.js';
import { mountDrawer, openDrawer } from './drawer.js';
import { mountVersions } from './versions.js';
import { plural } from './format.js';
import { appendReleases, renderReleases } from './results.js';
import { applyUrl, loadSettings } from './settings.js';
import { toast } from './toast.js';

const settings = loadSettings();
// `id` écarte les réponses d'une recherche dépassée
const session = { id: 0, text: applyUrl(settings), releases: [], batch: null };

function updateStatus(added = null) {
  const { batch, releases } = session;
  const shown = releases.length;
  const count = batch.exact && batch.total !== null ? plural(batch.total, 'résultat') : `${plural(shown, 'résultat')} affiché${shown > 1 ? 's' : ''}`;
  $('status').textContent = shown ? count : 'Aucun résultat';

  const notes = [];
  if (added !== null) notes.push(added ? `+${plural(added, 'résultat')}` : 'aucun nouveau résultat');
  if (batch.limited) notes.push('le site freine les requêtes : réessaie dans une minute');
  else if (!batch.exact) notes.push('filtres taille et source appliqués au fil du chargement');
  else if (batch.total) notes.push(`${shown.toLocaleString('fr-FR')} sur ${batch.total.toLocaleString('fr-FR')}`);
  $('load-note').textContent = notes.join(' · ');
  $('load-btn').hidden = !batch.more;
  $('load-more').hidden = !batch.more && !batch.limited;
}

async function search({ refresh = false } = {}) {
  const id = ++session.id;
  Object.assign(session, { releases: [], batch: null });
  // L'adresse suit la recherche affichée : un onglet rechargé la retrouve
  history.replaceState(null, '', searchLink(settings, session.text));
  $('status').textContent = '';
  $('results').replaceChildren();
  $('results').className = '';
  $('load-more').hidden = true;
  $('loading').hidden = false;
  try {
    const batch = await searchReleases(settings, session.text, { refresh });
    if (id !== session.id) return;
    Object.assign(session, { batch, releases: batch.releases });
    renderReleases($('results'), session.releases, settings.view);
    updateStatus();
  } catch (error) {
    if (id === session.id) $('status').textContent = `Recherche impossible : ${error.message}`;
  } finally {
    if (id === session.id) $('loading').hidden = true;
  }
}

// Ajoute le lot suivant sous la liste, sans recharger la page
async function loadMore() {
  const id = session.id;
  const button = $('load-btn');
  button.disabled = true;
  button.replaceChildren(el('span', { class: 'spinner spinner--sm', 'aria-hidden': 'true' }), 'Chargement…');
  try {
    const batch = await searchReleases(settings, session.text, { after: session.releases.length });
    if (id !== session.id) return;
    const known = new Set(session.releases.map((release) => release.id));
    const added = batch.releases.filter((release) => !known.has(release.id) && known.add(release.id));
    session.releases.push(...added);
    session.batch = batch;
    appendReleases($('results'), added, settings.view);
    updateStatus(added.length);
  } catch (error) {
    if (id === session.id) toast(`Échec : ${error.message}`, { error: true });
  } finally {
    button.disabled = false;
    button.replaceChildren('Charger plus');
  }
}

// Prévient des nouvelles releases de la recherche affichée (sans rien télécharger)
async function watchSearch() {
  try {
    const watch = await addWatch(settings, session.text, session.text || 'Derniers ajouts');
    toast(`Surveillance ajoutée : ${watch.label}`);
    openDrawer('watches');
  } catch (error) {
    toast(`Échec : ${error.message}`, { error: true });
  }
}

$('q').value = session.text;
mountControls(settings, {
  onQueryChange: () => search(),
  onViewChange: () => renderReleases($('results'), session.releases, settings.view),
});
mountDrawer();
mountVersions();
$('search').addEventListener('submit', (event) => {
  event.preventDefault();
  $('q').blur();
  session.text = $('q').value.trim();
  search({ refresh: true });
});
$('refresh').addEventListener('click', () => search({ refresh: true }));
$('watch').addEventListener('click', watchSearch);
$('load-btn').addEventListener('click', loadMore);

// La source choisie la dernière fois, si elle est toujours configurée, sinon la première
async function start() {
  let providers;
  try {
    providers = await fetchProviders();
  } catch (error) {
    $('status').textContent = `Page indisponible : ${error.message}`;
    return;
  }
  if (!providers.some((provider) => provider.key === settings.provider)) settings.provider = providers[0].key;
  const current = () => providers.find((provider) => provider.key === settings.provider);
  mountProviders(settings, providers, () => {
    search();
    showAccount(current());
  });
  search();
  showAccount(current());
}

start();
