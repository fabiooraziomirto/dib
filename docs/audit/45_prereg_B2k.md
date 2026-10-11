# Audit 45 — PRE-REGISTRAZIONE — B2-kill (ipotesi, regole di stop, decisioni Q9)

Data: 2026-10-11. **Nessun dato raccolto.** Pre-registrazione committata **prima** del blocco sul nodo (via dell'utente, 2026-10-11). Fonte: `docs/audit/43_piano_esperimenti_DRAFT.md` B1a/B2k; a14:250-263, 281-288; a33:19-21, 38; `experiments_tnsm/m67_retraction/run.py:90-92, 154-155, 312`. Ogni ssh **[SSH-U]**, ogni sudo **[SUDO-U]**, uno per volta, autorizzati dall'utente. Questo file non autorizza ssh, sudo né lanci: ognuno resta da chiedere.

## 1. Domanda
Dopo la morte e il riavvio di un sito (`start`), quanto tempo serve perché il sito converga, ed è entro un limite? Misura la convergenza **dopo la riconnessione**: serve sia con lease sia senza (Q2); non dice nulla sul tempo durante la disconnessione.

## 2. Ipotesi (da a14:254-261)
- **(d-kill):** convergenza dopo `start` ≈ 0,45 s + U(0; 0,1·T) + D_run, con **bound 1,5 s + 0,1·T + max(5 s, D_run_max)**. **Falsificata se** l'estremo inferiore dell'IC bootstrap 95% della mediana di una cella supera il bound della cella.
- **(e) correttezza:** nessuna violazione di I1-I3 e nessuna regola disputata esportabile oltre il bound della variante e del profilo. **Falsificata da una sola violazione.**
- **T15 − T5: DESCRITTIVA** (decisione Q9, §4): differenza delle mediane con IC, atteso in [0; 1,5] s (a14:254-257) come riferimento, **nessun criterio di falsificazione** su quel termine.

## 3. Configurazione (fissata ora)
Versione **completa**: profili `lan`, `degraded`, `wan` × k ∈ {1, 10} + `lan` con k = 50; FANOUT 10; arm C e D; T ∈ {5, 15} s (`run.py:154-155`); **10 prove per cella** (`run.py:312`). Durata dichiarata 2,36 h con L_dns veloce (a14:288; minima 1,69 h + 0,67 h); con L_dns = 186 ms 3,06 h (a22:49-69). n = vincolo di tempo, non di potere. Seed, versione Python, hardware (CPU QEMU senza AVX2, a04:154), hash dei dati e PKI (`pki_record.json`, validità 336 h) nel manifest.

## 4. Decisione Q9 (registrata)
10 ripetizioni per cella; T15 − T5 descrittiva. Motivo (a14:37): con 10 ripetizioni la differenza attesa ≈ 0,5 s può non distinguersi dal jitter U(0; 0,1·T); 30 ripetizioni non si fanno prima del 16.

## 5. Regola di stop su L_dns (prerequisito, B1a; da a14:263, a43 B1 voce 8)
- Si misura L_dns (sito morto) a `lan` e `degraded` nello stesso blocco di B2k; **p95 ≤ 50 ms** e poll del watcher ≤ 0,1 s ⇒ B2k nello stesso blocco (`ldns_decision`, `M67/night.py:38, 45-54`).
- p95 > 50 ms ⇒ B2k **non** parte; **al massimo 2 tentativi di calibrazione, in giorni diversi** (previsti lun 12 e mar 13); se entrambi > 50 ms, B2k non si esegue, lo si dichiara nel paper e in un audit. **Nessun terzo tentativo, nessuna modifica della soglia.** (A14:263 prevede per ≥ 0,5 s anche la variante solo-partition e per valori intermedi una nuova decisione dell'utente: **non applicabile**, B2p non è in questo piano; i casi intermedi 50 ms < p95 < 0,5 s si trattano come sopra.)
- Altre stop: battito > 10 s prima del lancio (a32:117), incoerenza del monitor (a32 §15), df < 2 GB, PKI scaduta (a33:38; il blocco si ferma da solo).

## 6. Esclusioni (come i blocchi precedenti)
`client_timeout` escluso e contato (a14:167); `transport_error_setup` escluso per episodio (a20:18); un solo nuovo tentativo e solo per un gruppo senza dati (a33:19-20); celle di riscaldamento o ordine randomizzato per lo stallo fsync iniziale (a38:95). Nessun numero di costo mTLS da questi dati (a33:21).

## 7. Cosa non si fa
Nessuna analisi prima del commit di questo file; nessuna modifica di ipotesi, bound o regole dopo i dati (analisi successive = POST-HOC); nessuna scrittura in `results/`; fine blocco: file `STOP`, `netem_show.sh` [SUDO-U], `docker ps` senza container `dibtnsm`. Dati in `experiments_tnsm/`, solo aggregati e `cells.jsonl`/`episodes.jsonl` (MB), nessun pcap.
