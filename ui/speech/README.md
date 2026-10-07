# Local Home speech dependencies

Whisper.cpp v1.8.2, source commit 4979e04f5dcaccb36057e059bbaed8a2f5288315, is statically linked under the MIT license in whisper.LICENSE. Its ggml implementation is included under that license.

The multilingual tiny model is derived from OpenAI Whisper and distributed under the MIT license in model.LICENSE. The GGML conversion is pinned to ggerganov/whisper.cpp revision 5359861c739e955e79d9a303bcbc70fb988958b1. SHA-256: be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21.

The build downloads and verifies the model. Installed Soulu uses the bundled model and verifies it before inference. No user audio is uploaded, logged, or written to disk. The application language selects Russian or English recognition. Audio capture is limited to 15 seconds; cancellation and leaving the originating Home tab release capture.
