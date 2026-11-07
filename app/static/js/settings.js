import { LANGS, RESOLUTIONS, SIZE_MAX_GB, SORTS, SOURCES, TYPES, VIEWS } from './constants.js';

const STORAGE_KEY = 'recherche:settings';

const pick = (value, allowed, fallback) => (Object.hasOwn(allowed, value) ? value : fallback);
const keep = (values, allowed) => (Array.isArray(values) ? values.filter((v) => allowed.includes(v)) : []);

/** Réglages de la page (source, type, vue, tri, filtres), mémorisés dans le navigateur. */
export function loadSettings() {
  let stored = {};
  try {
    stored = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    // stockage indisponible : réglages par défaut
  }
  return {
    provider: typeof stored.provider === 'string' ? stored.provider : '', // vérifiée au démarrage
    type: pick(stored.type, TYPES, 'all'),
    view: pick(stored.view, VIEWS, 'detailed'),
    sort: pick(stored.sort, SORTS, 'seeders'),
    langs: keep(stored.langs, LANGS),
    res: keep(stored.res, RESOLUTIONS),
    sources: keep(stored.sources, SOURCES),
    maxSize: Number.isInteger(stored.maxSize) ? stored.maxSize : 0,
  };
}

/**
 * Recherche donnée par l'adresse de la page (lien d'une notification, onglet rechargé) :
 * elle prend la place des réglages mémorisés, sauf la vue. Renvoie le texte cherché.
 */
export function applyUrl(settings) {
  const params = new URLSearchParams(location.search);
  if (!params.has('provider')) return '';
  const list = (name) => (params.get(name) || '').split(',');
  const gb = Number.parseInt(params.get('max'), 10);
  Object.assign(settings, {
    provider: params.get('provider'), // vérifiée au démarrage
    type: pick(params.get('type'), TYPES, 'all'),
    sort: pick(params.get('sort'), SORTS, 'seeders'),
    langs: keep(list('langs'), LANGS),
    res: keep(list('res'), RESOLUTIONS),
    sources: keep(list('sources'), SOURCES),
    maxSize: gb > 0 && gb < SIZE_MAX_GB ? gb : 0, // comme le curseur : tout à droite = pas de limite
  });
  return (params.get('q') || '').trim();
}

export function saveSettings(settings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // stockage indisponible : réglages non mémorisés
  }
}

export function clearFilters(settings) {
  Object.assign(settings, { langs: [], res: [], sources: [], maxSize: 0 });
}

export const activeFilters = (settings) =>
  settings.langs.length + settings.res.length + settings.sources.length + (settings.maxSize ? 1 : 0);
