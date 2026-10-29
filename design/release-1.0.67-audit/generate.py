"""Render a minute-by-minute audit from public GitHub event timestamps."""
import csv, json
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

root=Path(__file__).parent
data=json.loads((root/'source-events.json').read_text())
def dt(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')) if value else None
zone=ZoneInfo(data['timezone'])
start=dt(data['coverageStart']).replace(second=0,microsecond=0)
end=dt(data['coverageEnd'])
commits=data['commits'];jobs=data['jobs']
rows=[];minute=start
while minute<=end:
    stop=minute+timedelta(minutes=1)
    notes=[];links=[];categories=[]
    for c in commits:
        if minute<=dt(c['time'])<stop:
            notes.append('Коммит '+c['sha'][:7]+': '+c['title']);links.append(c['url']);categories.append('commit')
    for j in jobs:
        for s in j['steps']:
            a,b=dt(s.get('start')),dt(s.get('end'))
            if not a or s.get('result')=='skipped':continue
            if b is None:continue
            if a<stop and b>=minute:
                previous=j['runId']==40744046357
                notes.append(('Предыдущий выпуск 1.0.66, не работа над матовостью: ' if previous else 'GitHub Actions: ')+s['name']+'; результат шага: '+str(s.get('result')))
                links.append('https://github.com/sanderstripa/soulu/actions/runs/'+str(j['runId']))
                categories.append('previous_release' if previous else 'ci')
    if not notes:
        notes=['В доступном журнале GitHub нет событий за эту минуту. Чем именно был занят ассистент, подтвердить нельзя.']
        categories=['no_record']
    rows.append([minute.astimezone(zone).isoformat(timespec='minutes'),', '.join(sorted(set(categories))), ' | '.join(notes),' | '.join(dict.fromkeys(links))])
    minute=stop
with (root/'minutes.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f,delimiter=';');w.writerow(['Минута, Екатеринбург UTC+5','Тип подтверждения','Подтверждённые события или отсутствие данных','Источники']);w.writerows(rows)
lines=['# Хронология выпуска Soulu 1.0.67','',
'Все времена — Екатеринбург, UTC+5. Это реконструкция по публичным записям GitHub, а не запись каждой минуты работы ассистента.', '',
'Поминутная таблица: [minutes.csv](minutes.csv). Исходные даты и шаги: [source-events.json](source-events.json).', '',
'Диапазон: с первого сохранённого коммита матового режима 29.10.2026 в 01:12 до завершения выпуска в 11:38, то есть более десяти часов. Точное время начала обсуждения и подготовки макета до первого коммита в доступных данных не установлено; эти действия нельзя честно разложить по минутам.', '',
'Коммит подтверждает сохранённое изменение в указанное время, но не длительность редактирования перед ним. Активный шаг CI подтверждает работу сервера сборки, но не непрерывную работу ассистента. Отсутствие событий означает отсутствие подтверждения: придумывать для этих минут действия нельзя.', '',
'## Сохранённые изменения','', '| Время | Изменение |','|---|---|']
for c in sorted(commits,key=lambda c:c['time']):
    lines.append('| '+dt(c['time']).astimezone(zone).strftime('%d.%m %H:%M:%S')+' | ['+c['title'].replace('|','/')+']('+c['url']+') |')
lines+=['','## Запуски сборок и проверок','', '| Начало | Конец | Результат | Запуск |','|---|---|---|---|']
for r in sorted(data['runs'],key=lambda r:r['start']):
    lines.append('| '+dt(r['start']).astimezone(zone).strftime('%d.%m %H:%M:%S')+' | '+(dt(r['end']).astimezone(zone).strftime('%d.%m %H:%M:%S') if r.get('end') else '—')+' | '+str(r.get('result'))+' | ['+r['name']+']('+r['url']+') |')
lines+=['','## Промежутки без записей','', 'Ниже перечислены непрерывные отрезки от пяти минут, в которых не обнаружено ни коммитов, ни шагов CI. Это не заявленное время работы.','']
gaps=[];a=None
for row in rows+[[None,'end']]:
    if row[1]=='no_record' and a is None:a=dt(row[0])
    if row[1]!='no_record' and a is not None:
        b=dt(row[0]) if row[0] else end
        if (b-a).total_seconds()>=300:gaps.append((a,b))
        a=None
for a,b in gaps:lines.append('- '+a.strftime('%d.%m %H:%M')+'–'+b.strftime('%d.%m %H:%M')+': '+str(int((b-a).total_seconds()/60))+' мин без подтверждённых записей.')
lines+=['','## Что задержало выпуск','',
'Несколько ранних сборок завершились ошибками Windows/WinRT, затем были сбои запуска прототипа. После исправления создания графического слоя браузер начал запускаться. Один последующий провал был ошибкой тестовой страницы: селектор CSS учитывал добавленную шапку и менял ожидаемый цвет первого блока.', '',
'После успешной проверки прототип оставался в отдельной ветке; выпуск не был запущен сразу. Затем были дополнены проверки тёмной темы, вкладок и сайтов, оформлен PR. Релизный процесс был запущен только после последующего прямого требования пользователя опубликовать результат. Длинные интервалы без записей не объясняются непрерывной сборкой.', '',
'## Публикация','', data.get('releaseSummary','Публикация ещё не подтверждена.'),'']
(root/'README.md').write_text('\n'.join(lines),encoding='utf-8')
print('Minute rows:',len(rows),'Unrecorded minutes:',sum(r[1]=='no_record' for r in rows))
