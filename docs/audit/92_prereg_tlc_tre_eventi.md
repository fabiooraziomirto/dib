# Audit 92 — Pre-registrazione: correzione v6 con 3 eventi dell'evidence (TLC ridotto)

Data: 2026-10-12. Branch `tnsm-fsm`. Scritto e committato **prima** di ogni esecuzione.
Il numero 91 è occupato dall'audit esplorativo dell'altra sessione: uso 92.

## Perché
- La correzione v6 è verificata solo con al più 2 eventi dell'evidence:
  - `v6/logs/v6_f2_fix_all.log:57`: 100.746.547 stati;
  - `v6/logs/v6_f3_two_split.log:174`: 476.759.280 stati.
- Il run con 3 eventi l'ho fermato io a 202.510.519 stati (`v6/logs/v6_f4_e3.log:69`): nessuna
  affermazione possibile.
- Con 3 eventi la v5 aveva un difetto invisibile con 2 (`v5/logs/v5_f4_e3.log:25`).
- B2k usa 3 eventi per fatto (`experiments_tnsm/m67_retraction/run.py:720-724`).

Secondo l'audit 90 sez. 8, B2k, lo script offline, il costo della correzione e l'integrazione di
D1/D2/D5 in un nuovo hash aspettano questo esito.

## Cosa
- Cartella `experiments_tnsm/tla_fsm/v6e3/`. Il modello è **identico** a quello di `v6/`: `cmp` senza
  differenze, eseguito.
- Riduzione: `VIEW View`. Il modello la definisce per i run di sola safety ed esclude `lastOp`
  (`v6/DIB_AE_NA.tla:647-652`): le proprietà d'azione leggono solo `lastOp'`.
- Nessun'altra modifica alle cfg: copie di `v6_f2` e `v6_f4_e3` con la riga `VIEW View` e, per e3b,
  MaxToggles 0.

| cfg | Ipotesi | Falsificata se |
|---|---|---|
| `e3a_view_check` | la VIEW è coerente: configurazione di v6_f2 (MaxEvents 2), nessuna violazione e **al più** 100.746.547 stati | violazione, o più stati |
| `e3m_nofinishapply_noparts` | non vacuità con VIEW: senza applicazione della lettura alla chiusura, MaxEvents 3, nessuna partizione → V3 violato | nessuna violazione |
| `e3b_noparts` | correzione v6, MaxEvents 3, **nessuna partizione** (MaxToggles 0): nessuna violazione | qualunque violazione; fermato da limite 3 h o watchdog = incompleto, nessuna affermazione |
| `e3c_parts` | come v6_f4_e3 (MaxEvents 3, MaxToggles 2) con VIEW: nessuna violazione | idem |

## Protezioni
Le stesse dell'audit 67 sez. 4:
- `run_tlc.sh`: heap ≤ 28 GB su 64; watchdog che uccide TLC sotto 8 GB liberi su `/`; metadir
  nello scratchpad; manifest.
- Un TLC alla volta.
- Nessuna misura di tempo in locale mentre gira (la regola concordata con l'utente).
- Ordine: e3a, e3m, e3b, e3c. Se e3a falsifica la VIEW, i run successivi senza VIEW perdono senso
  come riduzione: lo si riporta e ci si ferma.

## Cosa non dice nemmeno un esito positivo
Valgono ancora i limiti dell'audit 90 sez. 1:
- 2 siti, 1 fatto, MaxLoss 0;
- evidence irraggiungibile, crash e concorrenza nello stesso sito non modellati;
- quorum 2 non combinato con le operazioni divise.

## Risultati (eseguiti, 2026-10-12)
| cfg | Previsione | Esito | Stati distinti | Log:riga |
|---|---|---|---|---|
| `e3a_view_check` | nessuna violazione, ≤ 100.746.547 | **confermata** | 19.415.620, profondità 42, 5 min 46 s (VIEW: circa 5,2× meno stati) | `v6e3/logs/e3a_view_check.log:31,36` |
| `e3m_nofinishapply_noparts` | violazione | **confermata** | 113.182 | `v6e3/logs/e3m_nofinishapply_noparts.log` (righe "is violated" e "distinct states") |
| `e3b_noparts` | nessuna violazione | **confermata** | **37.775.741**, profondità 43, 13 min 32 s | `v6e3/logs/e3b_noparts.log:39,44` |
| `e3c_parts` | nessuna violazione | **confermata** | **402.633.492**, profondità 46, 2 h 15 min (08:22-10:38Z) | `v6e3/logs/e3c_parts.log:169,174,175` |

Lettura:
- con 3 eventi dell'evidence e senza partizioni, la correzione v6 regge;
- la riduzione VIEW non nasconde la classe di difetto trovata con 3 eventi (e3m);
- resta da vedere il caso con le partizioni (e3c).

## Deviazione dalla pre-registrazione (dichiarata prima dell'esito)
Alle 2026-10-12T08:41:57Z, con `e3c_parts` in corso e **senza esito noto**, l'utente ha deciso di completarlo
invece di fermarlo al tetto di 3 h. Il tetto era una regola di protezione delle risorse, non un
criterio scientifico. Ipotesi, proprietà e criterio di falsificazione restano invariati.

Restano le protezioni:
- heap limitato a 28 GB;
- watchdog del disco (< 8 GB liberi → TLC fermato, esito "incompleto").

Tecnica: viene terminato **solo** il processo `timeout 10800` che avvolge `run_tlc.sh` (per PID).
Lo script, con il suo watchdog e la scrittura del manifest, continua; TLC non viene toccato.

## Esito finale
**Tutte e quattro le ipotesi confermate.** La correzione v6 (= `dc3dd20`, sez. 2 dell'audit 90) non
viola nessuna proprietà (invarianti e proprietà d'azione originali e nuove) con un sito diviso e
**3 eventi dell'evidence**:
- senza partizioni: 37.775.741 stati;
- con partizioni (MaxToggles 2): 402.633.492 stati.

Il run e3c è stato completato senza il tetto di 3 h, per la deviazione dichiarata sopra prima
dell'esito. Picco della metadir circa 4-5 GB, disco libero minimo 25 GB, nessun intervento del
watchdog, nessun errore di memoria.

Conseguenze per l'audit 90:
- sez. 1: il limite "al più 2 eventi" sale a **3 eventi con un sito diviso**. Con entrambi i siti
  divisi resta 2 eventi (`v6/logs/v6_f3_two_split.log:174`);
- sez. 4 regola 4: B2k (3 eventi per fatto, `run.py:720-724`) rientra ora nella configurazione
  verificata, per un sito diviso;
- sez. 8: la condizione "aspettare TLC" per B2k, offline, costo della correzione e nuovo hash con
  D1/D2/D5 è soddisfatta.

Limiti che restano: 2 siti, 1 fatto, MaxLoss 0, quorum 1 nei run divisi; evidence irraggiungibile,
crash e concorrenza nello stesso sito non modellati.
