import { fetchBitrate, fetchMetadata, fetchProviders, fetchVersions } from './api.js';
import { $, el } from './dom.js';
import { formatBitrate, formatRuntime, plural } from './format.js';
import { allocineUrl, badges, details, externalLink, imdbUrl, ratingContent, sendButton, siteLink } from './parts.js';

const KIND_LABELS = { movie: 'Film', tv: 'Série' };
const MAX_BITRATES = 20; // débits demandés au plus par ouverture : un appel à la source chacun
let requestId = 0; // écarte les réponses d'une fenêtre déjà refermée ou remplacée

/** Fenêtre d'un titre : sa fiche (TMDb) puis toutes ses versions disponibles, par résolution puis taille. */
export function mountVersions() {
  $('versions-close').addEventListener('click', closeVersions);
  $('versions-backdrop').addEventListener('click', closeVersions);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !$('versions').hidden) closeVersions();
  });
}

export async function openVersions(release) {
  const id = ++requestId;
  showIntro(release);
  $('versions-body').replaceChildren(el('div', { class: 'loading' },
    el('span', { class: 'spinner', 'aria-hidden': 'true' }), el('span', {}, 'Recherche de toutes les versions…')));
  $('versions').hidden = false;
  $('versions-backdrop').hidden = false;

  fetchMetadata(release).then((info) => {
    if (id === requestId) completeIntro(release, info);
  });
  try {
    const found = (await fetchVersions(release)).releases;
    if (id !== requestId) return;
    // La source n'a pas retrouvé le titre par son nom : on montre au moins la version cliquée
    const releases = found.length ? found : [release];
    $('versions-count').textContent = `${plural(releases.length, 'version')} disponible${releases.length > 1 ? 's' : ''}`;
    const bitrates = new Map(releases.map((r) => [r.id, el('span', { class: 'meta vrow__bitrate', title: 'Débit vidéo' })]));
    $('versions-body').replaceChildren(...groupByResolution(releases, bitrates));
    showBitrates(releases, bitrates, id);
  } catch (error) {
    if (id === requestId) $('versions-body').replaceChildren(el('p', { class: 'empty' }, `Versions indisponibles : ${error.message}`));
  }
}

// Débits vidéo, un par un dans l'ordre affiché, si la source sait les donner
async function showBitrates(releases, spans, id) {
  const provider = (await fetchProviders()).find((p) => p.key === releases[0]?.provider);
  if (!provider?.features.includes('video_bitrate')) return;
  for (const release of releases.slice(0, MAX_BITRATES)) {
    if (id !== requestId) return;
    const span = spans.get(release.id);
    span.textContent = '…';
    try {
      const { kbps } = await fetchBitrate(release);
      span.textContent = kbps ? formatBitrate(kbps) : 'débit ?';
    } catch {
      span.textContent = '';
      return; // source qui freine ou en erreur : on n'insiste pas
    }
  }
}

function closeVersions() {
  requestId += 1;
  $('versions').hidden = true;
  $('versions-backdrop').hidden = true;
}

// Fiche du titre : ce qui est connu tout de suite, complété ensuite par TMDb
function showIntro(release) {
  const poster = $('versions-poster');
  poster.className = 'poster';
  poster.replaceChildren(release.name.charAt(0).toUpperCase());
  $('versions-title').replaceChildren(release.name, release.year ? el('span', {}, ` ${release.year}`) : null);
  $('versions-sub').textContent = introLine(release, {});
  $('versions-rating').hidden = true;
  $('versions-overview').hidden = true;
  $('versions-count').textContent = '';
  $('versions-links').replaceChildren(externalLink(imdbUrl(release), 'IMDb ↗'), externalLink(allocineUrl(release), 'Allociné ↗'));
}

function completeIntro(release, info) {
  $('versions-sub').textContent = introLine(release, info);
  if (typeof info.rating === 'number') {
    $('versions-rating').replaceChildren(...ratingContent(info.rating));
    $('versions-rating').hidden = false;
  }
  if (info.overview) {
    $('versions-overview').textContent = info.overview;
    $('versions-overview').hidden = false;
  }
  if (info.imdb_id) $('versions-links').firstElementChild.href = imdbUrl(release, info.imdb_id);
  if (info.poster) {
    const poster = $('versions-poster');
    const image = el('img', { src: info.poster, alt: '', decoding: 'async', referrerpolicy: 'no-referrer' });
    image.addEventListener('load', () => poster.classList.add('loaded'));
    poster.append(image);
  }
}

const introLine = (release, info) => [
  KIND_LABELS[release.kind],
  release.season.split('E')[0],
  info.runtime ? formatRuntime(info.runtime) : '',
  (info.genres || []).join(', '),
].filter(Boolean).join(' · ');

// Les versions arrivent déjà triées : on les regroupe sans changer l'ordre
function groupByResolution(releases, bitrates) {
  const groups = new Map();
  for (const release of releases) {
    if (!groups.has(release.resolution)) groups.set(release.resolution, []);
    groups.get(release.resolution).push(release);
  }
  return [...groups].map(([resolution, items]) => el('section', { class: `vgroup vgroup--${resolution}` },
    el('h3', {}, el('span', {}, resolution), el('span', { class: 'vgroup__count' }, plural(items.length, 'version'))),
    items.map((release) => versionRow(release, bitrates.get(release.id)))));
}

// Badges réduits, sur une 2e ligne, sans la résolution (déjà dans la bande du groupe)
const versionRow = (release, bitrate) => el('div', { class: 'vrow' },
  el('div', { class: 'vrow__info' },
    el('p', { class: 'file' }, siteLink(release, release.title)),
    el('div', { class: 'vrow__line' }, badges(release, { small: true, withResolution: false }), details(release), bitrate)),
  sendButton(release, { compact: true }));
