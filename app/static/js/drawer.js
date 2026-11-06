import { fetchTorrents, fetchWatches, removeWatch, torrentAction } from './api.js';
import { LANGS, RESOLUTIONS, TYPES } from './constants.js';
import { $, el, icon, setPressed } from './dom.js';
import { formatAge, formatEta, formatPercent, formatRatio, formatSize, formatSpeed } from './format.js';
import { toast } from './toast.js';

const REFRESH_OPEN_MS = 3000;     // volet ouvert : suivi en direct
const REFRESH_CLOSED_MS = 30000;  // volet fermé : seulement le compteur de l'en-tête
const STATE_LABELS = { downloading: 'Téléchargement', seeding: 'Partage', paused: 'En pause', queued: 'En attente', checking: 'Vérification' };
const ACTIVE_STATES = ['downloading', 'queued', 'checking'];
const STATE_ORDER = ['downloading', 'checking', 'queued', 'paused', 'seeding'];

let currentTab = 'downloads';
let timer;
let torrents = [];
const confirming = new Set(); // torrents dont la suppression attend une confirmation

/** Volet latéral : téléchargements de Transmission et surveillances de recherches. */
export function mountDrawer() {
  $('open-drawer').addEventListener('click', () => openDrawer());
  $('close-drawer').addEventListener('click', closeDrawer);
  $('drawer-backdrop').addEventListener('click', closeDrawer);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isOpen()) closeDrawer();
  });
  for (const button of $('drawer-tabs').children) {
    button.addEventListener('click', () => showTab(button.dataset.tab));
  }
  document.addEventListener('torrent-added', refreshTorrents);
  refreshTorrents();
}

export function openDrawer(tab = currentTab) {
  $('drawer').hidden = false;
  $('drawer-backdrop').hidden = false;
  $('open-drawer').setAttribute('aria-expanded', 'true');
  showTab(tab);
}

const isOpen = () => !$('drawer').hidden;

function closeDrawer() {
  $('drawer').hidden = true;
  $('drawer-backdrop').hidden = true;
  $('open-drawer').setAttribute('aria-expanded', 'false');
  confirming.clear();
}

function showTab(tab) {
  currentTab = tab;
  for (const button of $('drawer-tabs').children) setPressed(button, button.dataset.tab === tab);
  $('drawer-downloads').hidden = tab !== 'downloads';
  $('drawer-watches').hidden = tab !== 'watches';
  if (tab === 'downloads') refreshTorrents();
  else refreshWatches();
}

// Téléchargements

async function refreshTorrents() {
  clearTimeout(timer);
  try {
    torrents = (await fetchTorrents()).torrents;
    updateCount();
    if (isOpen() && currentTab === 'downloads') renderTorrents();
  } catch (error) {
    if (isOpen()) $('drawer-downloads').replaceChildren(el('p', { class: 'empty' }, `Transmission indisponible : ${error.message}`));
  }
  timer = setTimeout(refreshTorrents, isOpen() ? REFRESH_OPEN_MS : REFRESH_CLOSED_MS);
}

function updateCount() {
  const active = torrents.filter((t) => ACTIVE_STATES.includes(t.state)).length;
  $('active-count').hidden = !active;
  $('active-count').textContent = active;
}

function renderTorrents() {
  const sorted = [...torrents].sort((a, b) =>
    STATE_ORDER.indexOf(a.state) - STATE_ORDER.indexOf(b.state) || b.added - a.added);
  $('drawer-downloads').replaceChildren(...(sorted.length
    ? sorted.map(torrentItem)
    : [el('p', { class: 'empty' }, 'Aucun torrent dans Transmission')]));
}

function torrentItem(torrent) {
  const paused = torrent.state === 'paused';
  const progress = el('i');
  progress.style.width = `${Math.round(torrent.progress * 100)}%`;
  return el('div', { class: 'torrent' },
    el('p', { class: 'torrent__name' }, torrent.name),
    el('div', { class: torrent.progress >= 1 ? 'progress done' : 'progress' }, progress),
    el('div', { class: 'torrent__line' },
      el('span', {}, torrentStatus(torrent)),
      el('span', { class: 'torrent__actions' },
        actionButton(paused ? 'i-play' : 'i-pause', paused ? 'Reprendre' : 'Mettre en pause', () => act(paused ? 'start' : 'stop', torrent)),
        actionButton('i-trash', 'Retirer', () => {
          confirming.add(torrent.id);
          renderTorrents();
        }))),
    torrent.error ? el('p', { class: 'torrent__error' }, torrent.error) : null,
    confirming.has(torrent.id) ? removalConfirm(torrent) : null);
}

function torrentStatus(torrent) {
  const parts = [STATE_LABELS[torrent.state] || torrent.state];
  if (torrent.state === 'downloading') {
    parts.push(formatPercent(torrent.progress), `↓ ${formatSpeed(torrent.down_rate)}`, formatEta(torrent.eta));
  } else if (torrent.state === 'seeding') {
    parts.push(`↑ ${formatSpeed(torrent.up_rate)}`, `ratio ${formatRatio(torrent.ratio)}`);
  } else if (torrent.progress < 1) {
    parts.push(formatPercent(torrent.progress));
  }
  parts.push(formatSize(torrent.size));
  return parts.filter(Boolean).join(' · ');
}

function removalConfirm(torrent) {
  const choice = (label, className, onClick) => {
    const button = el('button', { type: 'button', class: `btn btn--sm ${className}` }, label);
    button.addEventListener('click', onClick);
    return button;
  };
  const cancel = () => {
    confirming.delete(torrent.id);
    renderTorrents();
  };
  return el('div', { class: 'confirm' },
    el('span', {}, 'Retirer ce torrent ?'),
    choice('Garder les fichiers', '', () => act('remove', torrent)),
    choice('Supprimer les fichiers', 'btn--danger', () => act('delete', torrent)),
    choice('Annuler', 'btn--ghost', cancel));
}

function actionButton(iconId, label, onClick) {
  const button = el('button', { type: 'button', class: 'btn btn--sm btn--icon', title: label, 'aria-label': label }, icon(iconId));
  button.addEventListener('click', onClick);
  return button;
}

async function act(action, torrent) {
  confirming.delete(torrent.id);
  try {
    await torrentAction(action, [torrent.id]);
  } catch (error) {
    toast(`Échec : ${error.message}`, { error: true });
  }
  refreshTorrents();
}

// Surveillances

export async function refreshWatches() {
  try {
    const { watches } = await fetchWatches();
    $('drawer-watches').replaceChildren(...(watches.length
      ? watches.map(watchItem)
      : [el('p', { class: 'empty' }, 'Aucune surveillance. Lance une recherche puis « Surveiller » : tu seras prévenu sur ton téléphone des nouvelles releases.')]));
  } catch (error) {
    $('drawer-watches').replaceChildren(el('p', { class: 'empty' }, `Surveillances indisponibles : ${error.message}`));
  }
}

function watchItem(watch) {
  const remove = actionButton('i-trash', 'Supprimer la surveillance', async () => {
    try {
      await removeWatch(watch.id);
      toast(`Surveillance supprimée : ${watch.label}`);
    } catch (error) {
      toast(`Échec : ${error.message}`, { error: true });
    }
    refreshWatches();
  });
  return el('div', { class: 'watch' },
    el('div', { class: 'watch__info' },
      el('p', { class: 'watch__label' }, watch.label),
      el('p', { class: 'watch__meta' }, [describeQuery(watch.query), `vérifiée il y a ${formatAge(watch.checked * 1000)}`].join(' · '))),
    remove);
}

/** Résumé lisible des filtres d'une surveillance. */
export function describeQuery(query) {
  const parts = [TYPES[query.kind] || ''];
  parts.push(...query.resolutions.filter((r) => RESOLUTIONS.includes(r)));
  parts.push(...query.langs.filter((l) => LANGS.includes(l)));
  parts.push(...query.sources);
  if (query.max_gb) parts.push(`≤ ${query.max_gb} Go`);
  return parts.filter(Boolean).join(' · ');
}
