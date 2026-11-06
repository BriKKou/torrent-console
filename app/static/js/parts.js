// Éléments d'une release communs à la liste et à la fenêtre des versions
import { sendToTransmission } from './api.js';
import { el, icon } from './dom.js';
import { formatAge, formatRating, formatSize } from './format.js';
import { toast } from './toast.js';

const FOREIGN_LANGS = ['VOSTFR', 'SUBFRENCH', 'VO'];
const POOR_SOURCES = ['CAM', 'HDTV'];
const sent = new Map(); // id -> 'sent' | 'duplicate', conservé d'un affichage à l'autre

// Le codec reste lisible dans le nom de fichier : pas de badge.
// small : version réduite ; withResolution : faux quand la résolution est déjà affichée autour.
export function badges(release, { small = false, withResolution = true } = {}) {
  const tags = [
    [release.freeleech ? 'Freeleech' : '', 'free'],
    [withResolution ? release.resolution : '', release.resolution === '2160p' ? 'info' : ''],
    ...release.langs.map((lang) => [lang, FOREIGN_LANGS.includes(lang) ? 'warn' : 'ok']),
    [release.source === 'Autre' ? '' : release.source, POOR_SOURCES.includes(release.source) ? 'err' : ''],
    [release.hdr.join('·'), 'warn'],
  ];
  return el('div', { class: small ? 'badges badges--sm' : 'badges' },
    tags.filter(([text]) => text).map(([text, tone]) => el('span', { class: `badge ${tone}` }, text)));
}

// Toutes les sources ne donnent pas le nombre de seeders
export const details = (release) => el('span', { class: 'meta' }, [
  formatSize(release.size),
  release.seeders === null ? '' : `${release.seeders} seeders`,
  release.date ? formatAge(release.date) : '',
].filter(Boolean).join(' · '));

export const externalLink = (href, ...children) =>
  el('a', { href, target: '_blank', rel: 'noopener noreferrer' }, ...children);

// Titre ou nom de fichier cliquable vers la fiche du torrent sur le site
export const siteLink = (release, ...children) => (release.url ? externalLink(release.url, ...children) : children);

/** Fiche IMDb si TMDb a donné l'identifiant, sinon une recherche. */
export const imdbUrl = (release, imdbId = '') => (imdbId
  ? `https://www.imdb.com/title/${imdbId}/`
  : `https://www.imdb.com/find/?q=${encodeURIComponent(`${release.original_title || release.name} ${release.year}`.trim())}`);

export const allocineUrl = (release) => `https://www.allocine.fr/rechercher/?q=${encodeURIComponent(release.name)}`;

export const ratingContent = (rating) =>
  [el('span', { class: 'star' }, '★'), ` ${formatRating(rating)}`, el('small', {}, ' TMDb')];

export function sendButton(release, { compact = false } = {}) {
  const button = el('button', {
    type: 'button',
    class: compact ? 'btn btn--sm btn--icon' : 'btn btn--primary btn--sm',
    title: 'Envoyer à Transmission',
    'aria-label': 'Télécharger',
  });
  const show = (iconId, label) => button.replaceChildren(icon(iconId), ...(compact ? [] : [label]));

  function showStatus() {
    const status = sent.get(release.id);
    if (!status) {
      show('i-download', 'Télécharger');
      return;
    }
    button.disabled = true;
    button.classList.add('done');
    button.title = status === 'duplicate' ? 'Déjà dans Transmission' : 'Envoyé à Transmission';
    show('i-check', status === 'duplicate' ? 'Déjà présent' : 'Envoyé');
  }

  button.addEventListener('click', async () => {
    button.disabled = true;
    try {
      const { name, duplicate } = await sendToTransmission(release);
      sent.set(release.id, duplicate ? 'duplicate' : 'sent');
      showStatus();
      toast(duplicate ? 'Déjà dans Transmission' : `Envoyé à Transmission : ${name}`);
      document.dispatchEvent(new CustomEvent('torrent-added'));
    } catch (error) {
      button.disabled = false;
      toast(`Échec : ${error.message}`, { error: true });
    }
  });
  showStatus();
  return button;
}
