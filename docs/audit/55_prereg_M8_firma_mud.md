# Audit 55 — Pre-registrazione: M8, costo della firma MUD (sign + verify con `openssl cms`) sul nodo (B7 di audit 43)

Data: 2026-10-11. Nessuna ipotesi è nuova: è quella di audit 04 (M8: "Sign + verify costa < 10 ms per file MUD. Falsificata se il p95 supera 10 ms", a04:78), con le regole di decisione sotto, scritte prima dei dati. Il paper dice che le esportazioni non sono firmate (`wip:503`, `wip:782`): la misura dà un costo, **non integra la firma nel percorso di export** e non dice nulla sulla sicurezza.

## Cosa si misura
- **File:** MUD RFC 8520 esportati dal codice di produzione `export_mud_file` (`code/src/dib/evaluation/mud_export.py:61`) su `EndpointScore` sintetici, 3 taglie: **5, 20, 100 endpoint** (FQDN di classe eleggibile, https/443; ACE from-device). Generati in locale, sha256 in manifest, copiati sul nodo (`~/dib_tnsm/m8/`). Nessun dato terzo.
- **Operazioni (CLI, come da piano):** `openssl cms -sign -binary -in <file> -signer <cert> -inkey <key> -md sha256 -outform DER -out <sig>` (firma staccata, default senza `-nodetach`) e `openssl cms -verify -binary -inform DER -in <sig> -content <file> -CAfile <cert> -purpose any -no_check_time -out /dev/null`. Due algoritmi, chiave e certificato autofirmato generati con `openssl` (validità 2 giorni): **ECDSA P-256** e **RSA-2048**.
- **Unità = una coppia sign + verify** su un file; tempo = `time.perf_counter()` attorno a `subprocess.run` (somma dei due processi). **Riferimento di spawn (descrittivo):** `openssl version`, misurato intercalato, perché il processo CLI domina a questi costi; il criterio sotto si applica al **totale con spawn**, come scritto in a04:78; la differenza si riporta, senza criterio.
- **Celle:** 3 taglie × 2 algoritmi = 6; **10 ripetizioni** per cella, **20 coppie** per ripetizione (200 coppie per cella), 5 coppie di riscaldamento scartate all'inizio di ogni ripetizione; ordine di celle e di ripetizioni randomizzato con seme **20261011**.

## Ipotesi e criteri (fissati ora)
- **H-M8:** sign + verify < 10 ms per file. **Falsificata** (per cella) se l'estremo inferiore dell'IC bootstrap percentile 95% (10 000 ricampionamenti, seme 20261011, unità = coppia) del **p95** supera 10 ms; "inconclusiva" se il p95 > 10 ms ma l'IC lo attraversa; "non falsificata" altrimenti. **Globale:** falsificata se almeno una cella è falsificata; riportata come k/6.
- **Validità (asserzione):** ogni verify di una firma corretta deve riuscire e **un verify su file alterato di un byte deve fallire** (controllo negativo, 5 per cella fuori dal campione): se una delle due condizioni non regge, la cella non vale e lo si dice.
- **Descrittivo, senza criterio:** mediana e p95 con IC per operazione separata (sign, verify), riferimento di spawn, dimensione della firma.

## Condizioni sul nodo (non si lancia se non reggono)
Nessun container `dibtnsm`, nessun `run.py`/`auto_block.py`/`auto_b2k.py` in esecuzione (la misura parte **dopo B5 e B2k**, che occupano la CPU); loadavg a 1 min e quota di steal da `/proc/stat` registrati prima e dopo; il nodo ha altri carichi (k3s, `wasmbed-registry`, a04:164-167) e una CPU QEMU generica (`QEMU Virtual CPU version 2.5+`, senza AVX2): **i tempi non sono confrontabili con altre macchine** (CLAUDE.md). Python 3.12.3 del venv del nodo, OpenSSL 3.0.13. Nessuna dipendenza installata (`cryptography` non c'è sul nodo; non si installa).

## Cosa non si fa
Nessuna modifica del criterio dopo i dati; nessuna misura in-process (richiederebbe una dipendenza non installata); nessun numero di costo mTLS. Dati: `experiments_tnsm/m8_mud_sig/run_<data>/` (aggregati, manifest, sha256 dei file); nessuna scrittura in `results/`.
