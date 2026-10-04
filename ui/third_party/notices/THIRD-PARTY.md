# Soulu local translation and QR notices

Bergamot translator: Mozilla Public License 2.0 (full text ../bergamot.LICENSE).
Official npm package @browsermt/bergamot-translator 0.4.9:
https://www.npmjs.com/package/@browsermt/bergamot-translator/v/0.4.9
Package JavaScript source revision: 8cc5d0495479c9ec56eafafd6bcd7fb5b929ca98.
Embedded binary identifies itself as v0.4.5+4917c11; full source revision:
https://github.com/browsermt/bergamot-translator/tree/4917c1124e394acd8deb78100b7c81a69999ffe8
Marian source: e88c1aa5d5c5622cb52c7df09fbb7c3d7f4b5b5a (MIT).
Sentence splitter: 49fde6df7ee9199aedb9571be800448192e3515c (Apache-2.0 C++ code; LGPL-2.1 prefix data).
SentencePiece: 3ffdc0065a03cadd9d0e5e123aaf9b6ea7ffb05d (Apache-2.0).
intgemm: be3053515a8a04d19c6959a370eaf8b5a6eab686 (MIT).
Other upstream notices in this directory retain their original authors.

Soulu modifications: scripts/build-translation-runtime.py wraps upstream
JavaScript as a classic script, embeds WASM in a Blob worker, substitutes a
local WASM fetch response, includes Emscripten glue without indirect eval,
and uses self rather than strict-mode this for glue export registration.
No neural weights or native/WASM inference code were modified.
The exact reproducible packaging recipe and modified source are available:
https://github.com/sanderstripa/soulu/blob/codex/menu-translate/scripts/build-translation-runtime.py
Package archive SHA-512 is enforced by that script before extracting files.

Mozilla language models: MPL-2.0; integrity and exact URLs are listed in
ui/translation-models.json. Source registry:
https://storage.googleapis.com/moz-fx-translations-data--303e-prod-translations-data/db/models.json
Model licensing documentation:
https://github.com/mozilla/translations/blob/69455acaecbe8650cdba988dbcf7c10ca20e7c48/README.md
Models are optional downloads from the official Mozilla public bucket.

Language detection: tinyld 1.3.4, MIT (full text ../tinyld.LICENSE).
https://github.com/komodojp/tinyld
QR generation: qrcode-generator 2.0.4, Kazuhiko Arase, MIT (qrcode.LICENSE).
https://github.com/kazuhikoarase/qrcode-generator
QR Code is a registered trademark of DENSO WAVE INCORPORATED.
