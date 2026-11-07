/* VELIO — browser-only task manager. Dates use the user's local timezone. */
(() => {
  'use strict';
  const KEY = 'velio-tasks-v1';
  const $ = s => document.querySelector(s);
  const day = (date = new Date()) => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
  const shiftedDay = n => { const d = new Date(); d.setDate(d.getDate()+n); return day(d); };
  const parseDay = s => new Date(`${s}T12:00:00`);
  const validDate = s => typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s) && !isNaN(parseDay(s)) && day(parseDay(s)) === s;
  const id = () => crypto.randomUUID();
  const icon = name => feather.icons[name].toSvg({'aria-hidden':'true'});
  let today = day(), view = ['today','upcoming','completed'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'today';
  let tasks = [], removed = null, toastTimer;
  const examples = () => [
    ['Подготовить презентацию',0,'11:00',false], ['Ответить на письма',0,'13:00',true],
    ['Созвон с командой',0,'15:00',false],['Купить продукты',0,'',true],['Провести тренировку',0,'19:00',false],
    ['Встреча с командой',1,'10:00',false],['Оплатить подписку',1,'18:00',false],['Запланировать поездку',3,'',false]
  ].map(([text,offset,time,done]) => ({id:id(),text,date:shiftedDay(offset),time,done}));
  function load() {
    try {
      const stored = localStorage.getItem(KEY);
      if (stored === null) {
        const legacy = JSON.parse(localStorage.getItem('focus-todo-tasks-v1') || 'null');
        tasks = Array.isArray(legacy) ? legacy.filter(t => t && typeof t.text === 'string').map(t => ({id:id(),text:t.text.slice(0,300),done:!!t.done,date:today,time:''})) : examples();
        save();
      } else {
        const data = JSON.parse(stored);
        if (!Array.isArray(data)) throw new Error('Invalid task data');
        tasks = data.filter(t => t && typeof t.id === 'string' && typeof t.text === 'string' && typeof t.done === 'boolean' && validDate(t.date)).map(t=>({...t,time:/^([01]\d|2[0-3]):[0-5]\d$/.test(t.time)?t.time:''}));
      }
    } catch { $('#storage-error').hidden = false; }
  }
  function save() { try { localStorage.setItem(KEY,JSON.stringify(tasks)); $('#storage-error').hidden = true; } catch { $('#storage-error').hidden = false; } }
  function dateLabel(value) {
    const d = parseDay(value);
    const prefix = value === today ? 'Сегодня' : value === shiftedDay(1) ? 'Завтра' : new Intl.DateTimeFormat('ru',{weekday:'long'}).format(d);
    return `${prefix[0].toUpperCase()+prefix.slice(1)}, ${new Intl.DateTimeFormat('ru',{day:'numeric',month:'long',...(d.getFullYear()!==new Date().getFullYear()?{year:'numeric'}:{})}).format(d)}`;
  }
  function countLabel(n) { return n%10===1 && n%100!==11?'задача':n%10>=2 && n%10<=4 && (n%100<12 || n%100>14)?'задачи':'задач'; }
  function notify(message, undo = false) {
    clearTimeout(toastTimer); $('#toast span').textContent = message; $('#toast button').hidden = !undo; $('#toast').hidden = false;
    toastTimer = setTimeout(()=>{$('#toast').hidden = true; removed = null;},5000);
  }
  function row(task) {
    const li = document.createElement('li'); li.className = `task-row${task.done?' done':''}`; li.dataset.id = task.id;
    const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.className = 'task-check'; checkbox.checked = task.done; checkbox.setAttribute('aria-label',`${task.done?'Вернуть в активные':'Выполнить'}: ${task.text}`);
    checkbox.addEventListener('change',()=>{task.done=checkbox.checked; save(); render();});
    const body = document.createElement('div'); body.className='task-body';
    const title = document.createElement('div'); title.className='task-title'; title.textContent=task.text;
    const meta = document.createElement('div'); meta.className='task-meta'; meta.innerHTML=icon(view==='completed'?'calendar':'clock');
    const metaText = document.createElement('span'); metaText.textContent=view==='completed'?new Intl.DateTimeFormat('ru',{day:'numeric',month:'long'}).format(parseDay(task.date)):(task.time||'Весь день');
    if (task.date < today && !task.done) metaText.textContent = `${dateLabel(task.date)} · ${task.time || 'Весь день'}`;
    meta.append(metaText); body.append(title,meta); li.append(checkbox,body);
    if(task.time) { const time=document.createElement('span');time.className='time-chip';time.innerHTML=icon('clock');time.append(document.createTextNode(task.time));li.append(time); }
    const del=document.createElement('button');del.type='button';del.className='delete-button';del.setAttribute('aria-label',`Удалить: ${task.text}`);del.title='Удалить задачу';del.innerHTML=icon('trash-2');
    del.addEventListener('click',()=>{removed={task,index:tasks.indexOf(task)};tasks=tasks.filter(t=>t.id!==task.id);save();render();notify('Задача удалена',true);});li.append(del);return li;
  }
  function render() {
    today=day();
    const daily=tasks.filter(t=>t.date===today), done=daily.filter(t=>t.done).length;
    const percentage=daily.length?Math.round(done/daily.length*100):0;
    const upcoming=tasks.filter(t=>!t.done && t.date>today), completed=tasks.filter(t=>t.done);
    document.querySelectorAll('[data-progress]').forEach(el=>el.textContent=`${percentage}%`);
    document.querySelectorAll('.ring').forEach(el=>el.style.setProperty('--value',`${percentage}%`));
    $('[data-progress-label]').textContent=`${done} из ${daily.length} ${countLabel(daily.length)}`;
    $('#stat-done').textContent=done;$('#stat-left').textContent=daily.length-done;
    const counts={today:tasks.filter(t=>t.date===today || (!t.done && t.date<today)).length,upcoming:upcoming.length,completed:completed.length};
    document.querySelectorAll('[data-count]').forEach(el=>el.textContent=counts[el.dataset.count]);
    document.querySelectorAll('[data-view]').forEach(button=>{const selected=button.dataset.view===view;button.classList.toggle('active',selected);if(selected)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');});
    document.body.className=`${view}-view`;
    const titles={today:['Сегодня','Ваши задачи на сегодня','sun'],upcoming:['Предстоящие','Запланированные задачи','calendar'],completed:['Завершено','Выполненные задачи','check-circle']};
    $('#page-title').textContent=titles[view][0];$('#page-subtitle').textContent=innerWidth<=760 && view==='today'?new Intl.DateTimeFormat('ru',{weekday:'long',day:'numeric',month:'long'}).format(new Date()):titles[view][1];
    $('.heading-icon').innerHTML=icon(titles[view][2]);
    $('#current-date').textContent=new Intl.DateTimeFormat('ru',{weekday:'short',day:'numeric',month:'short'}).format(new Date());
    $('#task-form').hidden=view==='completed';$('#completed-banner').hidden=view!=='completed'||!completed.length;
    $('#completed-summary').textContent=`${completed.length} ${countLabel(completed.length)} выполнено`;
    const groups=$('#task-groups');groups.replaceChildren();
    let selected=view==='upcoming'?upcoming:view==='completed'?completed:tasks.filter(t=>t.date===today || (!t.done && t.date<today));
    selected=[...selected].sort((a,b)=>view==='completed'?b.date.localeCompare(a.date):a.date.localeCompare(b.date)||(a.time||'99').localeCompare(b.time||'99'));
    const grouped=new Map();selected.forEach(t=>{const key=view==='today'?(t.date<today?'overdue':today):t.date;if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(t);});
    for(const [key,items] of grouped){
      if(view!=='today'||key==='overdue'){const heading=document.createElement('h2');heading.className='group-title';heading.append(document.createTextNode(key==='overdue'?'Просроченные':dateLabel(key)));const n=document.createElement('b');n.textContent=items.length;heading.append(n);groups.append(heading);}
      const list=document.createElement('ul');list.className='task-list';items.forEach(t=>list.append(row(t)));groups.append(list);
    }
    $('#empty-state').hidden=selected.length>0;
    const empty={today:['Сегодня всё спокойно','Добавьте первую задачу и освободите мысли.'],upcoming:['Планы начинаются здесь','Выберите будущую дату и добавьте задачу.'],completed:['Всё ещё впереди','Выполненные задачи появятся здесь.']};
    $('#empty-title').textContent=empty[view][0];$('#empty-description').textContent=empty[view][1];
  }
  function setView(next) { if(!['today','upcoming','completed'].includes(next))return;view=next;location.hash=next;$('#task-date').value=view==='upcoming'?shiftedDay(1):day();render(); }
  $('#task-form').addEventListener('submit',event=>{
    event.preventDefault();const text=$('#task-input').value.trim(), date=$('#task-date').value;
    if(!text){$('#task-input').setCustomValidity('Введите название задачи');$('#task-input').reportValidity();return;}
    if(!validDate(date))return;
    tasks.push({id:id(),text,date,time:$('#task-time').value,done:false});save();$('#task-input').value='';$('#task-time').value='';
    setView(date>today?'upcoming':'today');notify('Задача добавлена');$('#task-input').focus();
  });
  $('#task-input').addEventListener('input',()=>$('#task-input').setCustomValidity(''));
  document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>setView(button.dataset.view)));
  window.addEventListener('hashchange',()=>{const next=location.hash.slice(1);if(next!==view)setView(next);});
  $('.theme-toggle').addEventListener('click',()=>{const theme=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=theme;try{localStorage.setItem('velio-theme',theme);}catch{}renderTheme();});
  function renderTheme(){const dark=document.documentElement.dataset.theme==='dark';$('.theme-toggle').innerHTML=icon(dark?'moon':'sun');$('.theme-toggle').title=dark?'Тёмная тема — переключить на светлую':'Светлая тема — переключить на тёмную';$('.theme-toggle').setAttribute('aria-label',`Включить ${dark?'светлую':'тёмную'} тему`);$('meta[name="theme-color"]').content=dark?'#050e18':'#f5f7fc';}
  $('#toast button').addEventListener('click',()=>{if(removed){tasks.splice(removed.index,0,removed.task);removed=null;save();render();}$('#toast').hidden=true;});
  window.addEventListener('storage',event=>{if(event.key===KEY){load();render();}});
  window.addEventListener('focus',()=>{if(day()!==today)render();});
  load();feather.replace({'aria-hidden':'true'});renderTheme();$('#task-date').value=view==='upcoming'?shiftedDay(1):day();render();
})();
