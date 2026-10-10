# Audit 17 — Passo 3: richiesta unica di OK per i Passi 3-5 (nulla lanciato)

Data: 2026-10-10. Branch `revision-tnsm`. Piano: audit 14 §4 (rev. 5), GATE 2 e 3 (§3). Il documento raccoglie in un'unica richiesta tutto ciò che serve per M3/M4 e per le calibrazioni dei Passi 4-5, separando i comandi che lancio io (senza sudo) da quelli che lanci tu (sudo sul nodo). **Nessuno di questi comandi è stato eseguito.**

## 0. Decisione preliminare (blocca il braccio mTLS di M4)

**Premessa contraddetta [C].** I certificati server della PKI hanno come SAN solo l'URI SPIFFE, `DNS:<servizio>`, `DNS:localhost` e `IP:127.0.0.1` (`code/scripts/make_dist_pki.py:102-104`), e lo script non ha un'opzione per altri SAN (argomenti a `:172-177`). Il client del benchmark verifica il nome del server (`mtls.client_context`, `mtls.py:98-101`). Un generatore su questo host che si collega a `https://192.168.100.57:18100` **fallirebbe quindi la verifica** in tutte le celle mTLS.

Opzioni:
- **(b, raccomandata)** aggiungo a `make_dist_pki.py` un'opzione `--extra-san-ip` (ripetibile), test prima del codice, che aggiunge `IP:<ip>` ai soli certificati server. La modifica è in `code/scripts` (non in `code/src`) e `service.py` resta congelato. **Serve il tuo OK.**
- (a) generatore di M3/M4 sul nodo, su `localhost`: nessuna modifica al codice, ma generatore e servizi condividono la CPU del nodo, contro l'obiettivo dichiarato al Passo 3.
- (c) tunnel SSH: scartata, perché aggiunge cifratura e multiplexing e falsa M4.

## 1. Comandi che lancio io, senza sudo (dopo il tuo OK)

**1.1 Preparazione** (regola G: `df -h /` all'inizio, stop sotto 2 GB; oggi 3,7 GB sul nodo).
1. Nuovo albero sul nodo dal commit corrente (`git archive HEAD code experiments_tnsm | ssh … tar -x -C ~/dib_tnsm/tree-<commit>`). Si verifica che lo sha256 di `service.py` sia `3186304363ed…`.
2. PKI fuori dalla repo: `python scripts/make_dist_pki.py --out ~/dib_tnsm/pki --n-sites 10 --not-before <ora UTC> --valid-hours 24 [--extra-san-ip 192.168.100.57]`.
3. Quattro file compose generati con `generate_compose.py` (`DIB_DIST_FANOUT_CONCURRENCY` ∈ {1, 10} × `DIB_DIST_MTLS` ∈ {0, 1}, `DIB_DIST_PKI_DIR=~/dib_tnsm/pki`), scritti in `~/dib_tnsm/m3/`. Si usano con `docker compose -p dibtnsm -f <file> --project-directory <tree>/code/src/dib/registry/distributed up -d --build`, con `PATH=/snap/bin:$PATH` (audit 15 §1).

**1.2 M3/M4.** Driver nuovo `experiments_tnsm/m3_distributed/run.py`, con le ipotesi di audit 04 §2 (M3: costo di N = 10 contro N = 1 a 1 writer < 10% con il fan-out parallelo; M4: mTLS ≤ 20% di throughput a 100 writer e ≤ 5 ms di p50 a 1 writer, limite superiore senza pool) nel docstring e committate prima del lancio.
- 4 bracci alternati per ripetizione, 10 ripetizioni.
- Writer 1, 10, 50, 100; 200 operazioni per worker; warm-up 20.
- Cluster ricreato a ogni cambio di braccio, con database nuovo.
- Monitoraggio del nodo e regola di scarto come in M1/M2 (`experiments_tnsm/common/`).
- Generatore su questo host (opzione b) e output in `experiments_tnsm/m3_distributed/`.
- **Stima: ~1 h 10 min** (40 celle × ~65 s più ~40 riavvii × ~30 s).
- Fine passo: `docker compose -p dibtnsm down -v --remove-orphans`.

**1.3 Calibrazioni dei Passi 4-5 senza sudo** (cluster `dibtnsm` attivo, profilo `lan`):
1. **Pipeline dei log (GATE 2):** 100 richieste `/health` a tempi noti (`time.time()` sul nodo) verso evidence da sola, poi verso evidence e `site-0` **in parallelo**. Per ogni richiesta, il timestamp di `docker logs -t` meno il tempo di invio. Si riportano la distribuzione (p50, p95, max), l'ordine relativo delle righe dei due container e il loro scarto. La soglia della regola per profilo (p95 < 10% della mediana del ritiro diretto del profilo) si committa dopo questa calibrazione.
2. **L_dns a `lan`:** `docker compose kill site-3`, poi dentro evidence 50 volte `docker exec dibtnsm-evidence-1 python -c "<cronometro di socket.getaddrinfo('site-3', 8000)>"`, e lo stesso con il sito vivo come controllo. Dal valore misurato si decide la variante (B2-kill e B2-partition oppure solo B2-partition più `kill-min`, audit 14 §4).
3. **Dry-run netem:** `experiments_tnsm/m67_retraction/netem_apply.sh --dry-run <profilo>` per i 7 profili. Elenca i comandi `nsenter … tc` che verrebbero eseguiti, con la guardia sul progetto `dibtnsm`.

## 2. Comandi che lanci tu, con sudo sul nodo

1. **Netem disponibile (G3):** `sudo modprobe sch_netem && lsmod | grep sch_netem`.
2. **Profili netem:**
   - comando: `sudo ~/dib_tnsm/tree-<commit>/experiments_tnsm/m67_retraction/netem_apply.sh <profilo> [indice-sito]`, con i profili `lan | regional | wan | degraded | extreme | mixed | partition <i>`; `lan` rimuove i qdisc. Verifica: `sudo nsenter -t <pid> -n tc qdisc show dev eth0`;
   - **decisione:** M6/M7 cambiano profilo molte volte (B1 6 profili; B2 3 profili × 2 T × 2 mTLS, più la partizione a ogni prova di B2-partition, cioè centinaia di applicazioni in 10-16 h). Due modi:
     - **(i)** una regola sudoers ristretta a quel solo script, `ubuntu ALL=(root) NOPASSWD: /opt/dib_tnsm/netem_apply.sh`, con lo script copiato in `/opt/dib_tnsm/`, di proprietà di root e non scrivibile da `ubuntu`. Così `run.py` cambia profilo da solo. È la soluzione più pratica, ma è una modifica della configurazione di sicurezza del nodo, che decidi tu;
     - **(ii)** lanci tu ogni blocco a mano, e io preparo l'elenco ordinato con i tempi.
3. **Cattura `tcpdump` (calibrazione delle assunzioni a1-a4):** con il profilo `degraded` applicato, mentre io invio 20 tentativi per braccio (mTLS off/on):
   `sudo nsenter -t $(docker inspect -f '{{.State.Pid}}' dibtnsm-evidence-1) -n timeout 300 tcpdump -i eth0 -w /tmp/dib_degraded_<braccio>.pcap 'tcp port 8000'`
   poi `sudo chown ubuntu /tmp/dib_degraded_*.pcap`. Ne ricavo n_c per fase, RTO e PTO effettivi e il NewSessionTicket. Gli intervalli della predizione (c) si ricalcolano e si committano **prima** del lancio di M6/M7.
4. **L_dns sotto netem:** applichi `wan` e poi `degraded` (punto 2) mentre ripeto la misura 1.3.2.

## 3. Ordine e durate

| Fase | Chi | Durata |
|---|---|---|
| OK sulla decisione 0 e, se (b), modifica di `make_dist_pki.py` con test | io | ~30 min |
| 1.1 preparazione | io | ~10 min |
| 1.2 M3/M4 | io | ~1 h 10 min |
| 1.3 calibrazioni senza sudo | io | ~15 min |
| 2.1 e 2.3-2.4 (sudo) | tu, con me che guido il traffico | ~20 min |
| Congelamento delle soglie e degli intervalli (commit) | io | — |
| Decisione 2.2 (i oppure ii), poi lancio di M6/M7 (11,9 / 16,7 / 9,7 h secondo L_dns) | tu e io | — |

GATE 3 (potenza di d-kill) si valuta dopo la calibrazione di L_dns e prima di qualsiasi prova B2-kill.

## 4. GATE 3: potenza di (d-kill), calcolo preliminare (simulazione, nessun lancio)

- Modello: convergenza = avvio 0,45 s (sd 0,02 s, dalla dispersione di `results/fault_injection`) + U(0; 0,1·T) + riconciliazione 0,07 s (sd 0,01 s).
- Confronto fra T = 15 e T = 5: differenza attesa delle mediane ≈ 0,5 s.
- 4000 simulazioni per riga.

| Ripetizioni per T | Potenza di Mann-Whitney unilaterale (α = 0,05) | P(differenza delle mediane in [0; 1,5] s) |
|---|---|---|
| 10 (un braccio mTLS) | **0,855** | 0,991 |
| 20 (i due bracci mTLS insieme, come nel piano) | **0,988** | 0,999 |
| 30 | 1,000 | 1,000 |

**Lettura [D].**
- Il criterio a intervallo [0; 1,5] s del piano è soddisfatto quasi sempre e quindi **discrimina poco**.
- Un test di Mann-Whitney sulla differenza ha potenza 0,86 con 10 ripetizioni per braccio, e 0,99 mettendo insieme i due bracci mTLS (20 per T), senza costo aggiuntivo. Questo assume che mTLS non cambi la dispersione della convergenza a `lan`; lo si controlla con un test sulle varianze dei due bracci.
- Con 30 ripetizioni per braccio il costo di `kill-min` passa da 0,17 a 0,52 h (caso L_dns lento).

**Decisione tua (GATE 3), una fra:**
- (i) 10 per braccio, con test Mann-Whitney sui due bracci insieme (potenza 0,99) più il criterio a intervallo [raccomandata, nessun costo];
- (ii) 30 ripetizioni per braccio;
- (iii) (d-kill) solo descrittiva.

Da rifare con L_dns e con la dispersione misurata prima del lancio.
