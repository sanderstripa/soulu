// The remoting service must outlive the first browser window.
ChromeUtils.importESModule('chrome://sona/content/remote.sys.mjs').startRemoting(Sona.backend);
