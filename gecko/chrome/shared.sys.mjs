// One trusted process state shared by normal and private browser windows.
export const state={config:null,initialized:false,settingsWindow:null,helper:null,helperQueue:Promise.resolve(),vpnState:{state:'disconnected',connected:false}};
