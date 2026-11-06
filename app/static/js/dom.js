export const $ = (id) => document.getElementById(id);

/** Crée un élément ; les textes sont insérés comme texte, jamais comme HTML. */
export function el(tag, attributes = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (name === 'class') node.className = value;
    else node.setAttribute(name, value);
  }
  node.append(...children.flat().filter((child) => child !== null && child !== undefined && child !== ''));
  return node;
}

/** Icône du sprite SVG de la page. */
export function icon(id) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  svg.setAttribute('class', 'ic');
  use.setAttribute('href', `#${id}`);
  svg.append(use);
  return svg;
}

export const setPressed = (button, pressed) => button.setAttribute('aria-pressed', String(pressed));
