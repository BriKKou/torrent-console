import { LANGS, RESOLUTIONS, SIZE_MAX_GB, SORTS, SOURCES, TYPES, VIEWS } from './constants.js';
import { $, el, icon, setPressed } from './dom.js';
import { activeFilters, clearFilters, saveSettings } from './settings.js';

const DEBOUNCE_MS = 300; // clics enchaînés, curseur en mouvement

/**
 * Sélecteurs (type, vue, tri) et barre de filtres.
 * onQueryChange : relancer la recherche ; onViewChange : seulement réafficher.
 */
export function mountControls(settings, { onQueryChange, onViewChange }) {
  let expanded = false;
  let timer;

  function queryChanged({ debounce = false } = {}) {
    saveSettings(settings);
    updateReset();
    clearTimeout(timer);
    timer = setTimeout(onQueryChange, debounce ? DEBOUNCE_MS : 0);
  }

  function segment(container, key, entries, onSelect) {
    container.replaceChildren(...entries.map(([value, content, label]) => {
      const button = el('button', { type: 'button', ...(label && { 'aria-label': label }) }, content);
      setPressed(button, settings[key] === value);
      button.addEventListener('click', () => {
        settings[key] = value;
        [...container.children].forEach((other) => setPressed(other, other === button));
        onSelect();
      });
      return button;
    }));
  }

  function chips(key, values) {
    return values.map((value) => {
      const button = el('button', { type: 'button', class: 'chip' }, value);
      setPressed(button, settings[key].includes(value));
      button.addEventListener('click', () => {
        const selected = settings[key];
        if (selected.includes(value)) selected.splice(selected.indexOf(value), 1);
        else selected.push(value);
        setPressed(button, selected.includes(value));
        queryChanged({ debounce: true });
      });
      return button;
    });
  }

  function sizeSlider() {
    const label = (gb) => (gb >= SIZE_MAX_GB ? 'Toutes' : `≤ ${gb} Go`);
    const input = el('input', {
      type: 'range', min: 1, max: SIZE_MAX_GB, step: 1, value: settings.maxSize || SIZE_MAX_GB, 'aria-label': 'Taille max',
    });
    const output = el('output', {}, label(Number(input.value)));
    input.addEventListener('input', () => {
      const gb = Number(input.value);
      settings.maxSize = gb >= SIZE_MAX_GB ? 0 : gb;
      output.textContent = label(gb);
      queryChanged({ debounce: true });
    });
    return el('span', { class: 'size' }, input, output);
  }

  const group = (label, items) =>
    el('div', { class: 'fgroup' }, el('span', { class: 'flabel' }, label), el('div', { class: 'fitems' }, items));

  function buildFilters() {
    $('filter-line').replaceChildren(
      group('Résolution', chips('res', RESOLUTIONS)),
      group('Taille', sizeSlider()),
      group('Langue', chips('langs', LANGS)),
      group('Source', chips('sources', SOURCES)),
    );
    updateMore();
    updateReset();
  }

  // Replié, les filtres tiennent sur une ligne ; « + » n'apparaît que s'ils dépassent
  function updateMore() {
    const line = $('filter-line');
    const button = $('more');
    line.classList.toggle('open', expanded);
    button.hidden = !expanded && line.scrollHeight <= line.clientHeight + 2;
    button.setAttribute('aria-expanded', String(expanded));
    button.title = expanded ? 'Moins de filtres' : 'Plus de filtres';
    button.replaceChildren(icon(expanded ? 'i-minus' : 'i-plus'));
  }

  function updateReset() {
    const count = activeFilters(settings);
    $('reset').hidden = !count;
    $('reset').textContent = `Effacer les filtres (${count})`;
  }

  segment($('type'), 'type', Object.entries(TYPES), () => queryChanged());
  segment($('view'), 'view', Object.entries(VIEWS).map(([value, view]) => [
    value, [icon(view.icon), el('span', { class: 'seg__label' }, view.label)], view.label,
  ]), () => {
    saveSettings(settings);
    onViewChange();
  });

  const sort = $('sort');
  sort.replaceChildren(...Object.entries(SORTS).map(([value, label]) => el('option', { value }, label)));
  sort.value = settings.sort;
  sort.addEventListener('change', () => {
    settings.sort = sort.value;
    queryChanged();
  });

  $('more').addEventListener('click', () => {
    expanded = !expanded;
    updateMore();
  });
  $('reset').addEventListener('click', () => {
    clearFilters(settings);
    buildFilters();
    queryChanged();
  });
  window.addEventListener('resize', updateMore);
  buildFilters();
}

/** Choix de la source, affiché seulement s'il y en a plusieurs. */
export function mountProviders(settings, providers, onChange) {
  const select = $('provider');
  select.replaceChildren(...providers.map(({ key, label }) => el('option', { value: key }, label)));
  select.value = settings.provider;
  $('provider-box').hidden = providers.length < 2;
  select.addEventListener('change', () => {
    settings.provider = select.value;
    saveSettings(settings);
    onChange();
  });
}
