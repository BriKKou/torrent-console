// Étiquettes des releases françaises (langue) et résolutions
export const LANGS = ['MULTI', 'VFF', 'VFQ', 'VF2', 'VFI', 'VOF', 'TRUEFRENCH', 'VF', 'VOSTFR', 'VO'];
export const RESOLUTIONS = ['2160p', '1080p', '720p', 'SD'];
// Sources utiles d'abord, les mauvaises (ou inutiles) à la fin
export const SOURCES = ['WEB-DL', 'BluRay', 'HDLight', 'WEBRip', 'HDTV', 'DVD', 'Remux', 'CAM', 'Autre'];
export const SIZE_MAX_GB = 30; // curseur tout à droite = pas de limite

export const TYPES = { all: 'Tout', movie: 'Films', tv: 'Séries' };
export const SORTS = { seeders: 'Seeders', date: 'Plus récents', size_desc: 'Taille ↓', size_asc: 'Taille ↑' };
export const VIEWS = {
  compact: { label: 'Compacte', icon: 'i-rows' },
  detailed: { label: 'Détaillée', icon: 'i-image' },
};
