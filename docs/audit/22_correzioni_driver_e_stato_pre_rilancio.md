# Audit 22 — Correzioni del driver prima del rilancio, costi di B2-kill con L_dns misurato, A2 grezza (2026-10-11)

Sessione del 2026-10-11 mattina. Branch `revision-tnsm`. Nessuna modifica a `code/src`, `service.py` (sha256 `3186304363ed…`), `results/`; nessun sudo; nulla lanciato sul nodo oltre alla creazione del tree e al controllo degli hash.
**I dati della notte (tree `6b8a6fa`, B1 `wan`, FANOUT 1, gruppi D e C) restano in audit 21 come "primo run"**: non cancellati e non mescolati ai conteggi di (c) del rilancio. Il confermativo è il rilancio; nessun episodio viene aggiunto alle celle ambigue (eventuali episodi in più saranno etichettati esplorativi).
Non spiego oltre i dati l'eccesso di ~67 ms per consegna del braccio C né l'episodio D da 0,99 s: lo dirà la cattura su `degraded`. Non commento la forma della curva C/D né il plateau a 100 writer; nessun numero di costo di mTLS da M6/M7.

## 1. Timeout keep-alive di uvicorn (letto, servizio non modificato)
Valore effettivo: **5 s in entrambi i modi** (uvicorn 0.51.0, `Config.timeout_keep_alive: int = 5`, `uvicorn/config.py:228,276`; verificato sul nodo: venv e immagine hanno uvicorn 0.51.0).
- Modo "Dockerfile/CLI" (plain): `CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8000"]` (`code/src/dib/registry/distributed/Dockerfile:20`), nessun `--timeout-keep-alive`.
- Modo mTLS (braccio C): `mtls.main` → `server_config(...)` senza `timeout_keep_alive` (`mtls.py:88-96,154-158`); il compose lo avvia con `python -m dib.registry.distributed.mtls` (`generate_compose.py:31-34`).
- Braccio D: `launcher_d.py:22`, `uvicorn.Config("service:app", host=…, port=8000, http=PeerCertH11Protocol)`, nessun override.
Nessun file del repo contiene `timeout-keep-alive` / `timeout_keep_alive` (grep).
**Valore scelto per `keepalive_expiry` del client: 2,0 s** (`run.py:447`, `KEEPALIVE_EXPIRY_S`), cioè sotto i 5 s del server; il client scarta prima. Il keep-alive è **mantenuto** (non 0): il warm prima di t0 resta una connessione riusata. Conseguenza dichiarata: le letture di `/pending` dopo `/dispute` (FANOUT 1: > 2 s di attesa) partono su connessione nuova (≈ 2d invece di d); erano già "controllo incrociato in ritardo" (`pending_read_delay_s`), il conteggio viene dal log di evidence.

## 2. Correzioni (commit `bf272e8`, test prima: 7 test falliti, poi 52 passati in `experiments_tnsm`)
1. **Errori di trasporto.** `Env.req` converte ogni `httpx.TransportError` non-timeout in `TransportFailure(exc_type)`; `episode_b1` lo cattura: esclusione con causa `transport_error_setup` (prima di t0, anche in `setup_fact` e nel warm) o `transport_error_measured` (dopo t0), più `exception_type`. Anche `trial_b2kill` (causa `transport_error`). Il `client_timeout` resta com'era. Il riepilogo ha `excluded_by_cause`. L'invocazione non muore più per un errore su un episodio. Test: r18 (setup: 2 episodi su 4 esclusi con causa e tipo `RemoteProtocolError`, la coda continua e produce `dispute_rtt_s`), r18b, r18c.
2. **Scrittura incrementale.** `run_episodes` consegna ogni riga a un sink (`episodes.jsonl`, una riga per episodio/prova, flush); un'eccezione imprevista dentro una cella lascia in `cells.jsonl` un record parziale con `aborted: "exception …"` e le righe misurate fin lì. Test r20 (il sink ha le righe 0 e 1 anche se la 2ª muore). `cells.jsonl` per cella resta com'è per i parser esistenti.
3. **Bias di `dispute-rtt`.** `dispute_rtt_bias_s(profile)` = uscita del sito + uscita di evidence verso il generatore: `lan` 0; `regional` 40 ms; `wan` 160 ms (notte: 163 ms); `degraded` 400 ms; `extreme` 1,1 s; `mixed` 80 ms (solo i siti `wan` ritardano, evidence no); `partition` non applicabile (`None`). `dispute_rtt_bias_ratio = bias / mediana(dispute-rtt)`; nuovo `dispute_rtt_bias_s` nel riepilogo; testo del docstring corretto (`run.py:12-16`). Test r17 per ciascun profilo. **Aggiornate due attese di test** che fissavano il vecchio bias (`test_r8`: `0,16/0,5` invece di `0,08/0,5`; `test_r13`: a `mixed` 0,08 invece di 0). Non cambia soglie, né le misure già fatte; `gen_path_d` (controllo del percorso generatore→evidence) è invariato.
4. **Lettura di (a) per FANOUT 1** nel docstring di `run.py:73-77` (testo esatto):
   > (a) [reading for FANOUT 1, added 2026-10-11 AFTER seeing the night data, supported by the text of rev. 3 ("with concurrency 1 the duration of /dispute is ~ 10*n_RTT*R"): the quantity is the withdrawal of the LAST site, predicted as 10 x n_RTT x R plus the service time (V6); the rule is unchanged: falsified if the median exceeds n_RTT*R (x10 for FANOUT 1) + 3 x (`lan` median of the same arm, same session) beyond the CI. If for arm C the rule is violated because the `lan` median is very low, it is reported as falsified with the observed excess; the model is not adapted.]
   Il paragrafo originale di (a) (ricongelato in audit 18 §1.5, `6c11e48`) è sotto, non modificato. `night.py` usa già ×10 per FANOUT 1 nella soglia P-log.

## 3. Tree finale e hash
**Tree: commit `bf272e8`, sul nodo `~/dib_tnsm/tree-bf272e8`** (da `git archive`; sostituisce `6b8a6fa`); elenco in `~/dib_tnsm/frozen_hashes_bf272e8.txt`. Dai test: 52 passati in `experiments_tnsm`. Verificati da me sul nodo con `sha256sum -c`: 18/18 corrispondono. **Tu li confronti prima di ogni uso.** Dei 18 file di audit 18 §2.6 è cambiato **solo `run.py`**; i 17 altri sono identici a quelli del tree `6b8a6fa`.

| File | sha256 |
|---|---|
| `code/src/dib/registry/distributed/service.py` | `3186304363ed309241134752689423088dda98b9d8fe3bcdf9669749264398fd` |
| `experiments_tnsm/m67_retraction/netem_common.sh` | `bfce039a5fb5c313b4b63543ae90382a2678b0df8aaa6969ffcd85f5b363d707` |
| `experiments_tnsm/m67_retraction/netem_apply.sh` | `d0d9496c22c35a0672434954426ca349c9ec756506b8d435e302dc27f776b0bd` |
| `experiments_tnsm/m67_retraction/netem_watch.sh` | `49249c63a6a431f7f7ae94dca795d0f1b92653c4ecb2f5223aae7821e6e62009` |
| `experiments_tnsm/m67_retraction/netem_show.sh` | `8a0e8ce5533804bae903734456751ab94ff8a02d4b730fc7807591eab95ee2c5` |
| **`experiments_tnsm/m67_retraction/run.py`** | **`022d97a6dc76808cf3a866c92f71d6076d0bcafca65a3ebdeab300b423393c02`** (era `c521b90c…`) |
| `experiments_tnsm/m67_retraction/calib_logs.py` | `c221ca812c6c8d6065d07641cdac38364a8f4dd3f2aa168022e105f1c7b76a93` |
| `experiments_tnsm/m67_retraction/calib_profile.py` | `f045d0fdcfd543f8d3a98a6de739ec488290cf430d269eda5e595bb6676c1c38` |
| `experiments_tnsm/m67_retraction/calib_ldns.sh` | `0191b1fafc52dc05a69f198390d1029467b4273b04fed9b3ddc771d989a28ba7` |
| `experiments_tnsm/m67_retraction/night.py` | `33e358d39eeeb78aa6ea4c40877e105a4c43b1f80bf8b58eb8bfc3923f0a8244` |
| `experiments_tnsm/m67_retraction/launch_night.sh` | `0facc8dc2b8024586b71c01fbc84b12e354b87eb642dc8e2d7ad0d2eae656187` |
| `experiments_tnsm/m3_distributed/launcher_d.py` | `1fe421850d720bc98197b69f2fa4cbf393765ac71fba48cd56593f292f47392e` |
| `experiments_tnsm/m1_single_node/run.py` | `df2dcdd80079fcec6b059abd4030ccd4478aaecbed608076bd1338894cfe2cff` |
| `experiments_tnsm/m2_p99_tail/run.py` | `17b936a1de90666bafba9800d07124147ff4e347ed249b87d4cadab8cc15baa3` |
| `experiments_tnsm/common/cells.py` | `d0477043b611b47589bb67d25b4d7c01b439c4ae4b603fc912b2a353c00c9f48` |
| `experiments_tnsm/common/node_monitor.py` | `80fc794e46e6bfe6cff6aaa51f066aa878622ee8290deddf7e0e0f26bd0d3d07` |
| `experiments_tnsm/common/cpu_sampler.py` | `c154bd78c09ed77603301fe95ba0ab14cd0763566dd1070cea60d4c0a811bc9b` |
| `experiments_tnsm/common/discard_rule.json` | `6b098bec3a9c551ab1f8a087d794f489eb2a5e0c9345fdd96733fff98b5daf68` |

Nessun'altra modifica a `run.py` dopo la tua conferma. Il calcolatore di B2-kill (§4) e i file di A2 (§5) non fanno parte del tree.

## 4. B2-kill: tabella dei costi con L_dns misurato (NON eseguito)
L_dns del sito morto visto da evidence: **p95 186,0 ms** (calibrazione della notte a `wan`; p50 179,8 ms, massimo 4,0 s; audit 21 §5): zona intermedia della regola (50 ms – 0,5 s) → decidi tu. Con il watcher a 0,5 s B2-kill non partirebbe comunque (serve `--poll 0,1`, non lo cambio io). Prima di decidere va chiarito se i ~180 ms dipendono dal profilo o dal resolver di Docker che inoltra all'host: lo misuro a `lan` senza watcher (3 volte, blocco `lan`); se non dipendono dal profilo lo dichiaro proprietà dell'ambiente. Ricalcolerò la tabella con il valore di `lan` se diverso.

Modello (`experiments_tnsm/b2kill_cost/cost_table.py`, docstring con ipotesi; 3 test riproducono le righe di audit 14 `:277-299`): durata prova = costi fissi (5/10/15 s) + convergenza kill (0,45 + 0,05·T + D_run) + k × episodio; episodio = 0,5 + 3·max(E_p, 3·L_dns) (3 fan-out; il sito morto costa 3 tentativi × L_dns, `service.py:700-712`; FANOUT 10 in parallelo). Il modello riproduce le righe "veloce" (L = 2,6 ms) e le righe "lento" a `lan` e `wan` (L = 1,0 s); **non riproduce la riga "lento" a `degraded`** (11,0 s pubblicati contro 9,5 s del modello): segnalato, non nascosto. Con L = 0,186 s l'episodio diventa 2,17 s a `lan` e `wan` e resta 8,75 s a `degraded`.

| k | Profilo | T (s) | Prove | Durata per prova D / C (s) | Ore |
|---|---|---|---|---|---|
| 1 | lan | 5 | 20 | 7,9 / 7,9 | 0,044 |
| 1 | lan | 15 | 20 | 8,4 / 8,4 | 0,047 |
| 1 | wan | 5 | 20 | 13,8 / 14,3 | 0,078 |
| 1 | wan | 15 | 20 | 14,3 / 14,8 | 0,081 |
| 1 | degraded | 5 | 20 | 26,8 / 28,1 | 0,152 |
| 1 | degraded | 15 | 20 | 27,3 / 28,6 | 0,155 |
| 10 | lan | 5 | 20 | 27,5 / 27,5 | 0,153 |
| 10 | lan | 15 | 20 | 28,0 / 28,0 | 0,156 |
| 10 | wan | 5 | 20 | 33,4 / 33,9 | 0,187 |
| 10 | wan | 15 | 20 | 33,9 / 34,4 | 0,190 |
| 10 | degraded | 5 | 20 | 105,6 / 106,8 | 0,590 |
| 10 | degraded | 15 | 20 | 106,1 / 107,3 | 0,593 |
| 50 | lan | 5 | 20 | 114,5 / 114,5 | 0,636 |
| **Totale** | | | **260** | | **3,06 h** |

Per confronto: L = 2,6 ms → 2,36 h (riproduce audit 14); L = 1,0 s → 6,98 h (audit 14: 7,16 h). Il `client_timeout` non cambia: `max(H, 3·L_dns)` = 0,56 s < H. Il massimo di 4,0 s osservato fa pensare a code rare: una consegna al sito morto con L = 4 s costerebbe 12 s in un fan-out; non è nel modello.

## 5. A2 in configurazione grezza (eseguita, 56 s e 72 s; host locale, `nice -n 19`, 2 processi)
Ipotesi e regola di falsificazione committate **prima** (`856ab76`, `experiments_tnsm/a2_masquerade_raw/HYPOTHESIS.md`): massimo del punteggio a f_s = 0,30, D = 120, breadth grezza (`trust_weighted: false`, copia del config, resto identico), seme 42, dieci pseudo-siti; atteso ≤ 0,58 e < θ = 0,65; falsificata se > 0,58 + 0,005 o se ammesso. Script non modificato (`code/scripts/service_masquerade_probe.py`), dati `observations_enriched.csv` sha256 `e741b426…1512` (uguale a `results/masquerade/manifest.json`).

| Config | Porta | Punteggio | |S_e| / siti eleggibili | Conf. siti | Conf. temporale | Ammesso | Bloccato da |
|---|---|---|---|---|---|---|
| **grezza** | 53 e 123 | **0,560935** | 3/10 | 0,3 | 0,952336 | no | score |
| grezza | 443 (controllo) | 0,560935 | 3/10 | 0,3 | 0,952336 | no | filtro + score |
| trust (riproduzione) | 53 e 123 | 0,561679 | 3/10 | 0,30124 | 0,952336 | no | score |

**H-A2raw non falsificata:** 0,5609 ≤ 0,58 (bound analitico 0,6·0,30 + 0,4) e < 0,65; nessuna cella ammessa. Il controllo di riproduzione dà **0,561679, identico** al valore in `results/masquerade/service_masquerade.csv` (f = 0,3, D = 120). La conf. dei siti grezza è esattamente 0,3 perché i tre siti malevoli su dieci sono il 30% dei siti eleggibili del tipo scelto. Questo è il massimo dello **scenario testato** (iniezione persistente, seme 42), non il massimo del modello di minaccia (il caso peggiore esaustivo del paper è 0,579). Output: `experiments_tnsm/a2_masquerade_raw/out_raw/`, `out_trust_repro/` (sha256 dei CSV `02e6e63b…`, `bf971293…`). Il testo del paper (`docs/main_tnsm.tex:656`) cita 0,562 con trust: coerente; non è stato modificato.

## 6. Prima della conferma degli hash: cosa blocca il blocco `lan`
- **Il blocco `lan` aspetta la tua conferma degli hash** (§3). Verificato sul nodo ora (07:48 UTC): nessun container `dibtnsm`, nessun `netem_watch`, nessun `night.py`/`run.py` in esecuzione; disco 98 GB totali, **3,6 GB liberi (97%)**: `night.py` si ferma sotto 2 GB, il blocco `lan` è piccolo ma i dati dei cluster pesano; da liberare prima di `wan` e `degraded`. `netem_show.sh` lo verifichi tu.
- **PKI sul nodo scade oggi 2026-10-11 18:00:00 UTC** (`openssl x509 -enddate` su `ca.crt`, `admin.crt`, `op-site-1.crt`, `site-0.crt`; già indicato in audit 18). Il braccio C (mTLS) non parte dopo quell'ora: il blocco `lan` ci sta, ma `wan` e `degraded` solo se avvengono prima delle 18:00; altrimenti serve una nuova PKI (`code/scripts/make_dist_pki.py`), che è una modifica al nodo e cambia gli hash di input: **ti chiedo come procedere**, non la rigenero io.
- **M1 e M2 della notte:** 100 e 90 celle, **non analizzate** finché i blocchi non sono chiusi; hanno girato con il watcher `wan` attivo (circa 0,07 core di fondo).

## 7. Comandi che lancerò sul nodo dopo la tua conferma (blocco `lan`, nessun sudo, nessun watcher)
```
T=~/dib_tnsm/tree-bf272e8; OUT=~/dib_tnsm/out/lan_$(date -u +%Y%m%d_%H%M)
cd $T && ~/dib_tnsm/venv/bin/python experiments_tnsm/m67_retraction/run.py --block b1 --profile lan --tree $T --out $OUT/b1 --arms D,C --fanouts 1,10
# L_dns a lan, 3 volte in momenti diversi, senza watcher, con cluster D acceso: calib_ldns.sh <compose> <project-dir> lan <override>
```
B1 a `lan`: quattro gruppi (D e C, FANOUT 1 e 10), 10 episodi per cella, seme 20261014; la misura di riferimento di (a) è la mediana per braccio di questa stessa sessione. Un'invocazione, ricreazione del cluster per gruppo.
