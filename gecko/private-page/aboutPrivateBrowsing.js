const en = !navigator.language.toLowerCase().startsWith('ru');
const isPrivate = RPMIsWindowPrivate();
const mode = isPrivate ? (en ? 'Incognito' : 'Инкогнито') : (en ? 'Regular window' : 'Обычное окно');
document.documentElement.lang = en ? 'en' : 'ru';
document.title = mode + ' — Soulu';
document.querySelector('#mode').textContent = mode;
if (!isPrivate) {
  const button = document.querySelector('#open');
  button.textContent = en ? 'Open incognito window' : 'Открыть окно инкогнито';
  button.hidden = false;
  button.onclick = () => RPMSendAsyncMessage('OpenPrivateWindow');
}
