import { $ } from './dom.js';

let timer;

export function toast(message, { error = false } = {}) {
  const box = $('toast');
  box.textContent = message;
  box.className = error ? 'toast show err' : 'toast show';
  clearTimeout(timer);
  timer = setTimeout(() => { box.className = 'toast'; }, 4000);
}
