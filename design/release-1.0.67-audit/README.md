# Хронология выпуска Soulu 1.0.67

Все времена — Екатеринбург, UTC+5. Это реконструкция по публичным записям GitHub, а не запись каждой минуты работы ассистента.

Поминутная таблица: [minutes.csv](minutes.csv). Исходные даты и шаги: [source-events.json](source-events.json).

Диапазон: с первого сохранённого коммита матового режима 29.10.2026 в 01:12 до завершения выпуска в 11:38, то есть более десяти часов. Точное время начала обсуждения и подготовки макета до первого коммита в доступных данных не установлено; эти действия нельзя честно разложить по минутам.

Коммит подтверждает сохранённое изменение в указанное время, но не длительность редактирования перед ним. Активный шаг CI подтверждает работу сервера сборки, но не непрерывную работу ассистента. Отсутствие событий означает отсутствие подтверждения: придумывать для этих минут действия нельзя.

## Сохранённые изменения

| Время | Изменение |
|---|---|
| 29.10 01:12:14 | [Prototype live page-content glass with an opaque off state](https://github.com/sanderstripa/soulu/commit/f84995a573069ced36817c2709f78c59060ee4bc) |
| 29.10 01:24:57 | [Correct Windows effect interop and feather the page-glass edge](https://github.com/sanderstripa/soulu/commit/ffb3c68f242ea5d15ebe4f1935463a77ba68d0ea) |
| 29.10 01:27:06 | [Include WinRT collection definitions and report effect initialization errors](https://github.com/sanderstripa/soulu/commit/08dd1cec36e322db9ee944f9cc5c47265f9af13d) |
| 29.10 01:38:03 | [Initialize classic COM before WinRT and preserve toolbar hit testing](https://github.com/sanderstripa/soulu/commit/90d2a1f202d28d5259b896a94b646fff33bcdd3c) |
| 29.10 01:55:29 | [Make glass initialization fail safely and preserve fixed site controls](https://github.com/sanderstripa/soulu/commit/f26cdb91ffc506d437e212e07d8e829c924ecbde) |
| 29.10 02:08:50 | [Defer backdrop creation until the browser is visible and probe live sampling](https://github.com/sanderstripa/soulu/commit/086fb12a2eac4e3652febb1291c7a91d252a3cda) |
| 29.10 02:21:59 | [Measure the initial page inset and record native glass screenshots](https://github.com/sanderstripa/soulu/commit/1c44e7b1772dd2061593c9761da25d8563663ce3) |
| 29.10 02:23:30 | [Recheck the unchanged compiled prototype against corrected visual fixtures](https://github.com/sanderstripa/soulu/commit/15b722c1bd8a109dd6595dc3c90fea3c9bae49ad) |
| 29.10 02:26:15 | [Record native page glass preview and focused Windows verification [skip ci]](https://github.com/sanderstripa/soulu/commit/2e8487d83081a5fa7afbc75679fc517d30299cae) |
| 29.10 08:13:30 | [Exercise page glass in dark theme, resized windows, tabs and external HTTPS pages](https://github.com/sanderstripa/soulu/commit/92cc0555bd65a6889aa69fa6ca879d8858638b36) |
| 29.10 08:15:57 | [Run existing toolbar, adaptive layout and storage regressions on page glass prototype](https://github.com/sanderstripa/soulu/commit/d12a0e8d52eb72775567db6b3ed8d5eb2251ac35) |
| 29.10 08:18:52 | [Document successful Windows regression checks and real-site glass screenshots [skip ci]](https://github.com/sanderstripa/soulu/commit/9f0257a14c072634265ba132a6bbce5b19f030ca) |
| 29.10 11:02:17 | [Prepare Soulu 1.0.67 matte page glass release and mandatory visual regression gate](https://github.com/sanderstripa/soulu/commit/e0c37c3d41ca8f61d467c6fbde06d6c5deaea986) |
| 29.10 11:02:23 | [Release Soulu 1.0.67 with live page glass [release 1.0.67]](https://github.com/sanderstripa/soulu/commit/acdb0bcf0cc5910acdd51bbc82e78a5c7dc078f9) |

## Запуски сборок и проверок

| Начало | Конец | Результат | Запуск |
|---|---|---|---|
| 29.10 01:12:17 | 29.10 01:22:12 | failure | [Test page-content glass prototype](https://github.com/sanderstripa/soulu/actions/runs/40761152159) |
| 29.10 01:25:00 | 29.10 01:26:23 | failure | [Test page-content glass prototype](https://github.com/sanderstripa/soulu/actions/runs/40763077454) |
| 29.10 01:27:10 | 29.10 01:36:38 | failure | [Test page-content glass prototype](https://github.com/sanderstripa/soulu/actions/runs/40763405891) |
| 29.10 01:38:07 | 29.10 01:49:21 | failure | [Test page-content glass prototype](https://github.com/sanderstripa/soulu/actions/runs/40765028830) |
| 29.10 01:55:32 | 29.10 02:04:00 | failure | [Test page-content glass prototype](https://github.com/sanderstripa/soulu/actions/runs/40767561416) |
| 29.10 02:08:53 | 29.10 02:19:17 | failure | [Test page-content glass prototype](https://github.com/sanderstripa/soulu/actions/runs/40769480160) |
| 29.10 02:22:02 | 29.10 02:32:24 | success | [Test page-content glass prototype](https://github.com/sanderstripa/soulu/actions/runs/40771343188) |
| 29.10 02:23:32 | 29.10 02:24:20 | success | [Recheck compiled page glass](https://github.com/sanderstripa/soulu/actions/runs/40771552082) |
| 29.10 08:13:33 | 29.10 08:14:31 | success | [Recheck compiled page glass](https://github.com/sanderstripa/soulu/actions/runs/40810921922) |
| 29.10 08:16:00 | 29.10 08:17:31 | success | [Recheck compiled page glass](https://github.com/sanderstripa/soulu/actions/runs/40811164252) |
| 29.10 11:02:25 | 29.10 11:38:49 | success | [Build Soulu Beta](https://github.com/sanderstripa/soulu/actions/runs/40826822181) |

## Промежутки без записей

Ниже перечислены непрерывные отрезки от пяти минут, в которых не обнаружено ни коммитов, ни шагов CI. Это не заявленное время работы.

- 29.10 01:50–29.10 01:55: 5 мин без подтверждённых записей.
- 29.10 02:33–29.10 08:13: 340 мин без подтверждённых записей.
- 29.10 08:19–29.10 11:02: 163 мин без подтверждённых записей.

## Что задержало выпуск

Несколько ранних сборок завершились ошибками Windows/WinRT, затем были сбои запуска прототипа. После исправления создания графического слоя браузер начал запускаться. Один последующий провал был ошибкой тестовой страницы: селектор CSS учитывал добавленную шапку и менял ожидаемый цвет первого блока.

После успешной проверки прототип оставался в отдельной ветке; выпуск не был запущен сразу. Затем были дополнены проверки тёмной темы, вкладок и сайтов, оформлен PR. Релизный процесс был запущен только после последующего прямого требования пользователя опубликовать результат. Длинные интервалы без записей не объясняются непрерывной сборкой.

## Публикация

Soulu 1.0.67 опубликован 29.10.2026 в 11:38:38 UTC+5: https://github.com/sanderstripa/soulu/releases/tag/beta-1.0.67 . Установщик и ZIP имеют статус uploaded. Тег, исходный коммит сборки и main совпадают: acdb0bcf0cc5910acdd51bbc82e78a5c7dc078f9. Финальный запуск 40826822181 завершился success. Это был свежий выпуск из исходников, а не переименование старой сборки.
