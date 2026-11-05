// The remoting service must outlive the first browser window.
ChromeUtils.importESModule('chrome://soulu/content/remote.sys.mjs').startRemoting(Soulu.backend);
