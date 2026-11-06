import { LANGS, RESOLUTIONS, SORTS, SOURCES, TYPES, VIEWS } from './constants.js';

const STORAGE_KEY = 'recherche:settings';

/** Réglages de la page (source, type, vue, tri, filtres), mémorisés dans le navigateur. */
export function loadSettings() {
  let stored = {};
  try {
    stored = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    // stockage indisponible : réglages par défaut
  }
  const pick = (value, allowed, fallback) => (Object.hasOwn(allowed, value) ? value : fallback);
  const keep = (values, allowed) => (Array.isArray(values) ? values.filter((v) => allowed.includes(v)) : []);
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
