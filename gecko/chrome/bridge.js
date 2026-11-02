/* This file is packaged ONLY in a non-content-accessible chrome resource. */
(() => {
  const host = window.opener?.Soulu;
  if (!host || location.protocol !== 'chrome:') throw Error('Soulu trusted settings host required');
  window.cefQuery = ({request,onSuccess,onFailure}) => {
    Promise.resolve().then(() => {
      const {action,payload} = JSON.parse(request);
      return host.dispatch(action,payload,window);
    }).then(result=>onSuccess(JSON.stringify(result??null)),error=>onFailure(1,error.message));
  };
  window.addEventListener('load',()=>document.documentElement.classList.add('gecko-runtime'),{once:true});
})();
