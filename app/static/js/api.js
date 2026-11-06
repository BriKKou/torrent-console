async function request(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Erreur ${response.status}`);
  return data;
}

const post = (url, body) => request(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

/** Paramètres d'une recherche, partagés par la recherche et les surveillances. */
function queryParams(settings, text) {
  return {
    q: text,
    type: settings.type,
    sort: settings.sort,
    langs: settings.langs.join(','),
    res: settings.res.join(','),
    sources: settings.sources.join(','),
    max: settings.maxSize,
  };
}

let providers;

/** Sources configurées : clé, nom et fonctions facultatives fournies (account, video_bitrate). */
export function fetchProviders() {
  providers ??= request('/api/providers').then((data) => data.providers);
  return providers;
}

/** Lot de résultats qui suit les `after` déjà affichés. */
export function searchReleases(settings, text, { after = 0, refresh = false } = {}) {
  const params = new URLSearchParams({
    provider: settings.provider, ...queryParams(settings, text), after, refresh: refresh ? 1 : 0,
  });
  return request(`/api/search?${params}`);
}

/** Toutes les versions disponibles du titre d'une release. */
export function fetchVersions(release) {
  const params = new URLSearchParams({
    provider: release.provider,
    kind: release.kind,
    title: release.title,
    name: release.name,
    year: release.year,
    season: release.season,
  });
  return request(`/api/versions?${params}`);
}

const metadataCache = new Map();

/** Jaquette, note et IMDb (TMDb) ; un seul appel par titre. */
export function fetchMetadata(release) {
  const params = new URLSearchParams({
    kind: release.kind,
    title: release.name,
    original: release.original_title,
    year: release.year,
  });
  const key = params.toString();
  if (!metadataCache.has(key)) {
    metadataCache.set(key, request(`/api/meta?${params}`).catch(() => ({})));
  }
  return metadataCache.get(key);
}

/** Statistiques du compte sur la source ({} si elle ne les fournit pas). */
export const fetchAccount = (provider) => request(`/api/account?${new URLSearchParams({ provider })}`);

/** Débit vidéo en kb/s ({ kbps: null } s'il est inconnu). */
export const fetchBitrate = (release) =>
  request(`/api/bitrate?${new URLSearchParams({ provider: release.provider, id: release.id })}`);

export const sendToTransmission = (release) => post('/api/add', { provider: release.provider, id: release.id });

export const fetchTorrents = () => request('/api/torrents');

/** action : start, stop, remove (garde les fichiers) ou delete (supprime aussi les fichiers). */
export const torrentAction = (action, ids) => post('/api/torrents/action', { action, ids });

export const fetchWatches = () => request('/api/watches');

export const addWatch = (settings, text, label) =>
  post('/api/watches', { provider: settings.provider, label, params: queryParams(settings, text) });

export const removeWatch = (id) => post('/api/watches/remove', { id });
