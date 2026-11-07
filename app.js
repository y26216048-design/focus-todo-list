/* Focus To-Do List — задачи, фильтры и сохранение в браузере */
(() => {
  'use strict';
  const KEY = 'focus-todo-tasks-v1';
  const form = document.getElementById('task-form');
  const input = document.getElementById('task-input');
  const list = document.getElementById('tasks');
  const count = document.getElementById('count');
  const remaining = document.getElementById('remaining');
  const progress = document.getElementById('progress');
  const fill = document.getElementById('progress-fill');
  const clear = document.getElementById('clear');
  const filters = [...document.querySelectorAll('[data-filter]')];

  let filter = 'all';
  let tasks = [];
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || '[]');
    if (Array.isArray(saved)) {
      tasks = saved.filter(t => t && typeof t.id === 'string' &&
        typeof t.text === 'string' && typeof t.done === 'boolean').slice(0, 2000);
    }
  } catch (error) {
    console.warn('Не удалось прочитать сохранённые задачи:', error);
  }

  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(tasks));
    } catch (error) {
      console.warn('Не удалось сохранить задачи:', error);
    }
  }
  function makeId() {
    return typeof crypto !== 'undefined' && crypto.randomUUID ?
      crypto.randomUUID() : Date.now() + '-' + Math.random().toString(36).slice(2);
  }
  function render() {
    const completed = tasks.filter(t => t.done).length;
    const active = tasks.length - completed;
    count.textContent = completed + ' из ' + tasks.length + ' выполнено';
    remaining.textContent = active ? 'Осталось задач: ' + active :
      (tasks.length ? 'Всё выполнено!' : 'Нет активных задач');
    const pct = tasks.length ? Math.round(completed / tasks.length * 100) : 0;
    fill.style.width = pct + '%';
    progress.setAttribute('aria-valuenow', String(pct));
    clear.disabled = completed === 0;

    filters.forEach(button =>
      button.setAttribute('aria-pressed', String(button.dataset.filter === filter)));

    const visible = tasks.filter(t => filter === 'all' ||
      (filter === 'active' ? !t.done : t.done));

    list.replaceChildren();
    if (!visible.length) {
      const empty = document.createElement('li');
      empty.className = 'empty';
      const symbol = document.createElement('div');
      symbol.className = 'symbol';
      symbol.textContent = '☑';
      symbol.setAttribute('aria-hidden', 'true');
      const title = document.createElement('strong');
      title.textContent = filter === 'active' ? 'Активных задач нет' :
        filter === 'done' ? 'Выполненных задач пока нет' : 'Пока здесь пусто';
      const hint = document.createElement('p');
      hint.textContent = filter === 'all' ?
        'Добавьте первую задачу, чтобы начать.' :
        'Выберите другой фильтр или добавьте задачу.';
      empty.append(symbol, title, hint);
      list.append(empty);
      return;
    }
    for (const task of visible) {
      const li = document.createElement('li');
      li.className = 'task' + (task.done ? ' done' : '');
      const toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'check';
      toggle.textContent = task.done ? '✓' : '';
      toggle.setAttribute('aria-label',
        (task.done ? 'Отметить невыполненной: ' : 'Отметить выполненной: ') + task.text);
      toggle.setAttribute('aria-pressed', String(task.done));
      toggle.addEventListener('click', () => {
        task.done = !task.done;
        save();
        render();
      });
      const label = document.createElement('span');
      label.className = 'label';
      label.textContent = task.text;
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'remove';
      remove.textContent = '×';
      remove.setAttribute('aria-label', 'Удалить задачу: ' + task.text);
      remove.addEventListener('click', () => {
        tasks = tasks.filter(t => t.id !== task.id);
        save();
        render();
      });
      li.append(toggle, label, remove);
      list.append(li);
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    tasks.unshift({ id: makeId(), text, done: false });
    save();
    input.value = '';
    render();
    input.focus();
  });
  filters.forEach(button => button.addEventListener('click', () => {
    filter = button.dataset.filter;
    render();
  }));
  clear.addEventListener('click', () => {
    tasks = tasks.filter(t => !t.done);
    save();
    render();
  });
  render();
})();