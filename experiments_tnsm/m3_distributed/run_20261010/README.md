# M3/M4, run 20261010: configurazione "di default"

Questi dati sono stati misurati con la configurazione di default del prototipo, in cui ogni chiamata httpx fra servizi costruisce un contesto SSL di default (≈ 6,15 ms nell'immagine del servizio; `service.py:161,381`, audit 18 §1.3). Il braccio senza mTLS paga questa spesa per chiamata, il braccio mTLS no (riceve un contesto precostruito, `service.py:167`).

**Conseguenza:** il confronto mTLS contro plain di questo run **non misura il costo di mTLS** (a 1 e 10 writer mTLS risulta più veloce) e non va riportato come tale. Il costo di mTLS si misura nel rilancio `../run_m4_20261010/` (C contro D, stesso blocco). Questi dati restano come "configurazione di default": servono, per esempio, a quantificare quanto la spesa per chiamata pesi sul prototipo così com'è, e il braccio FANOUT 1 contro FANOUT 10 (H-M3a non informativa: nel mix non c'è fan-out nelle fasi cronometrate).
