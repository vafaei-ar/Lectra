# Third-party preset voices

Lectra can use two shared preset reference clips for local Chatterbox synthesis.

| Lectra preset | CMU ARCTIC speaker | Metadata |
| --- | --- | --- |
| `us-woman` / **US Woman** | SLT | US English, female |
| `us-man` / **US Man** | BDL | US English, male |

The clips are downloaded on first use from the CMU ARCTIC corpus and cached under the local Lectra data directory. They are not copied into each Telegram user's personal voice-profile folder.

Source project:

- CMU ARCTIC Speech Synthesis Databases
- https://www.festvox.org/cmu_arctic/
- SLT reference: `cmu_us_slt_arctic/wav/arctic_a0001.wav`
- BDL reference: `cmu_us_bdl_arctic/wav/arctic_a0001.wav`
- Lectra first tries the historical Festvox individual-WAV endpoint over HTTP, because that is how CMU ARCTIC has traditionally exposed these files.
- If the individual WAV is unavailable, Lectra falls back to the official CMU ARCTIC 0.95 release ZIP from Festvox / CMU and extracts only the required reference WAV.
- HTTPS and HTTP archive variants are both attempted because network environments differ in whether they permit legacy HTTP or support the older hosts' TLS configuration.

## CMU ARCTIC license

Carnegie Mellon University  
Copyright (c) 2003  
All Rights Reserved.

Permission to use, copy, modify, and license this software and its documentation for any purpose is granted without fee, subject to these conditions:

1. The copyright notice, conditions, and disclaimer must be retained.
2. Modifications must be clearly marked as such.
3. Original authors' names must not be deleted.

The original CMU ARCTIC report also states that the voice talents signed a waiver agreeing to distribution of their recordings under these terms.

THE AUTHORS OF THIS WORK DISCLAIM ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

## Lectra use

Lectra does not present these recordings as user-cloned voices. They are shared, licensed preset references used locally as Chatterbox conditioning audio. The first-use download is stored under:

```text
~/.local/share/lectra/system-voices/
├── us-woman/reference.wav
└── us-man/reference.wav
```

The generated speech remains synthetic output from Lectra's local TTS pipeline.
