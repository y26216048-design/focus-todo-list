// Lightweight smoke tests for To-Do List logic (Node.js, no packages).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');

class Element {
  constructor() {
    this.handlers = {};
    this.children = [];
    this.dataset = {};
    this.style = {};
    this.textContent = '';
    this.value = '';
    this.disabled = false;
    this.attributes = {};
  }
  addEventListener(type, handler) { this.handlers[type] = handler; }
  click() { this.handlers.click?.(); }
  focus() {}
  setAttribute(name, value) { this.attributes[name] = value; }
  replaceChildren(...children) { this.children = children; }
  append(...children) { this.children.push(...children); }
}
const saved = new Map();
const storage = {
  getItem: key => saved.has(key) ? saved.get(key) : null,
  setItem: (key, value) => saved.set(key, value),
};
function mount() {
  const keys = ['task-form', 'task-input', 'tasks', 'count', 'remaining',
    'progress', 'progress-fill', 'clear'];
  const elements = Object.fromEntries(keys.map(key => [key, new Element()]));
  const filters = ['all', 'active', 'done'].map(name => {
    const item = new Element();
    item.dataset.filter = name;
    return item;
  });
  const doc = {
    getElementById: id => elements[id],
    querySelectorAll: query => query === '[data-filter]' ? filters : [],
    createElement: () => new Element(),
  };
  vm.runInNewContext(source, {
    document: doc,
    localStorage: storage,
    console,
    crypto: require('node:crypto'),
  });
  return { elements, filters };
}
function add(ui, text) {
  ui.elements['task-input'].value = text;
  ui.elements['task-form'].handlers.submit({ preventDefault() {} });
}

let ui = mount();
assert.equal(ui.elements.tasks.children.length, 1, 'Empty state shown');
add(ui, 'Сдать тестовое задание');
assert.equal(ui.elements.tasks.children.length, 1, 'Adds task');
assert.equal(ui.elements.tasks.children[0].children[1].textContent,
  'Сдать тестовое задание', 'Correct task text');
ui.elements.tasks.children[0].children[0].click();
assert.equal(ui.elements.count.textContent, '1 из 1 выполнено');
assert.equal(ui.elements.progress.attributes['aria-valuenow'], '100');
ui = mount();
assert.equal(ui.elements.count.textContent, '1 из 1 выполнено',
  'Completion persists after reload');
ui.filters.find(x => x.dataset.filter === 'active').click();
assert.equal(ui.elements.tasks.children[0].className, 'empty',
  'Completed task hidden in active filter');
ui.filters.find(x => x.dataset.filter === 'all').click();
ui.elements.tasks.children[0].children[2].click();
ui = mount();
assert.equal(ui.elements.count.textContent, '0 из 0 выполнено',
  'Deletion persists after reload');
add(ui, 'Дополнительная задача');
ui.elements.tasks.children[0].children[0].click();
ui.elements.clear.click();
assert.equal(ui.elements.count.textContent, '0 из 0 выполнено',
  'Clears completed tasks');
add(ui, '    ');
assert.equal(ui.elements.count.textContent, '0 из 0 выполнено',
  'Rejects blank input');
console.log('PASS: add / complete / persist / filter / delete / clear / blank input');