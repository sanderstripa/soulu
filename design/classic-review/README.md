# Classic toolbar — visual review

Status: interactive visual prototype for owner approval. Not integrated into the
native application, not on main, and not released. Baseline: Soulu Beta 1.0.62,
3c13018cf64e8a0f65c5546e7fa14aceb72a07b6.

Reference: owner-supplied Safari screenshot. The proposal retains Soulu branding
and Windows controls, with address/search above a dedicated capsule tab row.
Pinned tabs are circles at the left, separate from normal tabs. Desktop chrome
retains the current 82 px geometry (excluding the preview frame border).

`preview.html` is an in-conversation HTML fragment using the host-provided Lucide
runtime. It references the repository's Onest font and Soulu logo and embeds public site
favicons. The in-conversation copy embeds those repository assets too. Existing font and branding licenses remain in the repository.

Local interactions: tab switching, create/close, pin/unpin via the tab sidebar or
context menu, reorder regular tabs by drag, local address/search demonstration,
back/forward, favorites, tab overview, theme switching. Website content is mock
content; no browsing or network requests are performed by the prototype.

Checks passed in headless Chromium: initial pinned/regular groups, switching and
address synchronization, pin/unpin, create/close, navigation history, theme toggle,
overview, no outer overflow at 1440/1280/1024/736/390/320 px, no JavaScript errors.
Light and dark screenshots were visually inspected.

After approval: implement approved geometry in the production classic renderer;
add native pinned-tab state, ordering and persistence; verify native drag regions,
content insets, caption hit-testing, tab overflow, keyboard behavior, both themes
and the compact-layout regression suite. Publish only after owner approval and
successful native Windows verification.
