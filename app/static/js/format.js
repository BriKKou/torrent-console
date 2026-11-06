export const plural = (count, word) => `${count.toLocaleString('fr-FR')} ${word}${count > 1 ? 's' : ''}`;

export function formatSize(bytes) {
  const gb = bytes / 1e9;
  return `${gb.toLocaleString('fr-FR', { maximumFractionDigits: gb < 10 ? 1 : 0 })} Go`;
}

export function formatSpeed(bytesPerSecond) {
  if (bytesPerSecond >= 1e6) return `${(bytesPerSecond / 1e6).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} Mo/s`;
  return `${Math.round(bytesPerSecond / 1e3)} Ko/s`;
}

/** Temps écoulé depuis une date (ISO 8601 ou millisecondes). */
export function formatAge(date) {
  const minutes = Math.floor((Date.now() - new Date(date)) / 6e4);
  if (minutes < 60) return `${Math.max(minutes, 1)} min`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)} h`;
  const days = Math.floor(minutes / 1440);
  if (days < 31) return `${days} j`;
  if (days < 365) return `${Math.floor(days / 30)} mois`;
  return plural(Math.floor(days / 365), 'an');
}

/** Temps restant, en secondes ; vide si inconnu. */
export function formatEta(seconds) {
  if (seconds < 0) return '';
  if (seconds < 60) return '< 1 min';
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  const hours = Math.floor(seconds / 3600);
  return hours < 48 ? `${hours} h ${String(Math.round((seconds % 3600) / 60)).padStart(2, '0')}` : `${Math.round(hours / 24)} j`;
}

export const formatPercent = (fraction) => `${Math.floor(fraction * 100)} %`;

/** Durée en minutes : « 2 h 46 » ou « 46 min ». */
export function formatRuntime(minutes) {
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, '0')}`;
}

/** Débit en kb/s : « 5,3 Mb/s » ou « 850 kb/s ». */
export function formatBitrate(kbps) {
  if (kbps < 1000) return `${kbps} kb/s`;
  return `${(kbps / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} Mb/s`;
}

export const formatRating = (rating) =>
  rating.toLocaleString('fr-FR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const formatRatio = (ratio) =>
  ratio.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
