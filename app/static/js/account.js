import { fetchAccount } from './api.js';
import { $, el } from './dom.js';
import { formatRatio, formatSize } from './format.js';

let requestId = 0; // écarte la réponse d'une source qu'on vient de quitter

/** Ratio et volumes du compte, en haut de page ; rien si la source ne les fournit pas. */
export async function showAccount(provider) {
  const id = ++requestId;
  const box = $('account');
  box.hidden = true;
  if (!provider.features.includes('account')) return;
  try {
    const account = await fetchAccount(provider.key);
    if (id !== requestId || !account.username) return;
    const ratio = account.ratio === null ? '∞' : formatRatio(account.ratio);
    box.title = `${account.username} · envoyé ${formatSize(account.uploaded)} (dont ${formatSize(account.bonus)} de bonus) · reçu ${formatSize(account.downloaded)}`;
    box.replaceChildren(
      el('span', { class: 'account__up' }, `↑ ${formatSize(account.uploaded)}`),
      el('span', { class: 'account__down' }, `↓ ${formatSize(account.downloaded)}`),
      el('span', { class: account.ratio === null || account.ratio >= 1 ? 'account__ratio ok' : 'account__ratio err' }, `Ratio ${ratio}`),
    );
    box.hidden = false;
  } catch {
    // statistiques indisponibles : l'encart reste masqué
  }
}
