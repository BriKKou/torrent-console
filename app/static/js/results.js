import { fetchMetadata } from './api.js';
import { el, icon } from './dom.js';
import { allocineUrl, badges, details, externalLink, imdbUrl, ratingContent, sendButton, siteLink } from './parts.js';
import { openVersions } from './versions.js';

const KIND_LABELS = { movie: 'Film', tv: 'Série' };
const titleCards = new WeakMap(); // conteneur -> Map(clé du titre -> { releases, node }), vue détaillée

/** Remplace la liste affichée. */
export function renderReleases(container, releases, view) {
  container.replaceChildren();
  container.className = view === 'compact' ? '' : 'cards';
  titleCards.set(container, new Map());
  appendReleases(container, releases, view, { animate: false });
}

/**
 * Ajoute à la suite, sans toucher à ce qui est déjà affiché.
 * Vue détaillée : une seule carte par titre, qui montre sa version la plus récente.
 */
export function appendReleases(container, releases, view, { animate = true } = {}) {
  if (view === 'compact') {
    if (releases.length) container.className = 'rows panel';
    container.append(...releases.map((release) => withAnimation(row(release), animate)));
    return;
  }
  const cards = titleCards.get(container);
  for (const release of releases) {
    const key = titleKey(release);
    const entry = cards.get(key);
    if (!entry) {
      const node = withAnimation(titleCard(release, 1), animate);
      cards.set(key, { releases: [release], node });
      container.append(node);
      continue;
    }
    entry.releases.push(release);
    const latest = entry.releases.reduce((a, b) => (b.date > a.date ? b : a));
    const node = titleCard(latest, entry.releases.length);
    entry.node.replaceWith(node);
    entry.node = node;
  }
}

const withAnimation = (node, animate) => {
  if (animate) node.classList.add('new');
  return node;
};

// Même titre : même type, nom, année et saison (S03E05 et S03E06 vont ensemble)
const titleKey = (release) =>
  [release.kind, release.name.toLowerCase(), release.year, release.season.split('E')[0]].join('|');

function row(release) {
  return el('div', { class: 'row' },
    el('div', { class: 'row__info' },
      el('p', { class: 'file' }, siteLink(release, release.title)),
      el('div', { class: 'row__line' }, badges(release), details(release))),
    sendButton(release, { compact: true }));
}

function titleCard(release, versionCount) {
  const poster = el('div', { class: 'poster' }, release.name.charAt(0).toUpperCase());
  const rating = el('span', { class: 'rating', hidden: '' });
  const imdb = externalLink(imdbUrl(release), 'IMDb ↗');
  const versions = versionCount > 1 ? versionsButton(release, versionCount) : null;
  const node = el('article', { class: 'card card--clickable panel', title: 'Voir toutes les versions' },
    poster,
    el('div', { class: 'card__body' },
      el('div', { class: 'card__head' },
        el('h2', {}, siteLink(release, release.name, release.year ? el('span', {}, ` ${release.year}`) : null)),
        el('span', { class: 'card__tags' },
          el('span', { class: 'kind' }, [KIND_LABELS[release.kind], release.season].filter(Boolean).join(' · ')),
          versions)),
      badges(release),
      details(release),
      el('p', { class: 'file' }, release.title),
      el('div', { class: 'card__foot' },
        el('nav', { class: 'links' }, imdb, externalLink(allocineUrl(release), 'Allociné ↗')),
        el('div', { class: 'card__actions' }, rating, sendButton(release)))));

  // Un clic sur la carte (hors liens et boutons) ouvre toutes les versions du titre
  node.addEventListener('click', (event) => {
    if (!event.target.closest('a, button')) openVersions(release);
  });

  whenVisible(node, async () => {
    const info = await fetchMetadata(release);
    if (info.imdb_id) imdb.href = imdbUrl(release, info.imdb_id);
    if (typeof info.rating === 'number') {
      rating.replaceChildren(...ratingContent(info.rating));
      rating.hidden = false;
    }
    if (info.poster) {
      const image = el('img', { src: info.poster, alt: '', decoding: 'async', referrerpolicy: 'no-referrer' });
      image.addEventListener('load', () => poster.classList.add('loaded'));
      poster.append(image);
    }
  });
  return node;
}

function versionsButton(release, count) {
  const button = el('button', { type: 'button', class: 'versions-pill', title: 'Voir toutes les versions disponibles' },
    icon('i-layers'), `${count} versions`);
  button.addEventListener('click', () => openVersions(release));
  return button;
}

// Jaquettes et notes chargées quand la carte approche de l'écran
const onVisible = new WeakMap();
const observer = new IntersectionObserver((entries) => {
  for (const entry of entries.filter((e) => e.isIntersecting)) {
    observer.unobserve(entry.target);
    onVisible.get(entry.target)();
  }
}, { rootMargin: '400px' });

function whenVisible(node, callback) {
  onVisible.set(node, callback);
  observer.observe(node);
}
