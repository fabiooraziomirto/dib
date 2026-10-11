# Audit 26 — Riferimento `lan` adiacente per (a), deriva fra due sessioni, note su P-a1/P-a2, comandi prima di `wan` (2026-10-11)

Scritto e committato PRIMA di qualunque dato di `wan` del rilancio. Nulla eseguito sul nodo in questa fase.

## A. Riferimento `lan` per (a) (decisione dell'utente)
Le due sessioni a `lan` di oggi hanno dato valori diversi per D nello stesso giorno (FANOUT 1, P-log ultimo sito: **67,3 [62,8; 82,1] ms** alle 07:52 UTC contro **48,4 [45,4; 51,9] ms** alle 08:27, IC non sovrapposti). Una deriva del nodo nel tempo è dello stesso ordine del segnale cercato: **nessuna delle due è il riferimento.** Regola (scritta nel docstring di `analyze_b1.py` con la nota "scelta dopo aver visto la differenza fra le due sessioni a `lan` del giorno 11"; implementata con `--lan-ref`, test `test_analyze_b1.py`):
- riferimento = celle `lan` **adiacenti** al blocco `wan`, stessa sessione: D e C, FANOUT 1 e 10, 10 episodi, ordine mescolato, subito **prima** di `wan` (watcher fermo, `netem_show.sh` pulito verificato dall'utente) e, se il tempo lo permette, subito **dopo**; stesso braccio e stesso FANOUT;
- se prima e dopo differiscono, si usa la mediana **più alta** (riferimento più favorevole alla predizione: se è violata comunque, la conclusione è robusta);
- soglia = n_RTT·R·(10 se FANOUT 1) + 3 × mediana di riferimento; "falsificata" se la mediana la supera con il limite inferiore dell'IC sopra la soglia, "inconclusiva" se la mediana la supera ma l'IC la attraversa, "non falsificata" altrimenti; si riporta sempre l'eccesso osservato; il modello non si adatta.
**Smoke del codice, non un risultato:** il percorso `--lan-ref` è stato provato sui dati della notte (primo run, C FANOUT 1) con un riferimento NON adiacente (la sessione `lan` delle 07:52): ha prodotto "inconclusiva", eccesso 352,8 ms sopra 5117,9 ms; vale solo come prova che il codice gira (ha rivelato un `KeyError` su `excluded_by_cause`, assente nei riepiloghi del tree `6b8a6fa`, corretto con `.get`). I due run di oggi restano nel rapporto come "due sessioni a `lan`", non scartati.

## A.4 Deriva fra le due sessioni (documentata, non spiegata)
Dati: `experiments_tnsm/m67_retraction/lan_20261011/sessions_compare.md` (script `lan_sessions_compare.py`). Mediana dell'ultimo sito, ms; `other_cores` / `steal_pct` del fondo prima di ogni cella.

| Sessione | Ordine | Cella | Ora UTC | other_cores | steal_pct | Mediana | 1ª metà / 2ª metà |
|---|---|---|---|---|---|---|---|
| b1 (07:51:49) | 1 | C f10 | 07:52:12 | 0,169 | 0,229 | 30,6 | 30,6 / 30,6 |
| b1 | 2 | D f1 | 07:53:32 | 0,274 | 0,313 | 67,3 | 67,2 / 67,4 |
| b1 | 3 | C f1 | 07:54:32 | 0,216 | 0,401 | 106,0 | 99,3 / 110,3 |
| b1 | 4 | D f10 | 07:55:53 | 0,148 | 0,359 | 25,9 | 26,6 / 25,2 |
| b1_default (08:26:46) | 1 | D f10 | 08:27:09 | 0,147 | 0,317 | 22,0 | 27,6 / 17,1 |
| b1_default | 2 | default f1 | 08:28:00 | 0,112 | 0,031 | 128,3 | 138,7 / 124,6 |
| b1_default | 3 | D f1 | 08:28:51 | 0,133 | 0,021 | 48,4 | 50,5 / 45,7 |
| b1_default | 4 | default f10 | 08:29:40 | 0,137 | 0,010 | 27,4 | 28,6 / 25,1 |

Osservazioni (solo dati): D è più basso nella seconda sessione (FANOUT 1: 67,3 → 48,4; FANOUT 10: 25,9 → 22,0); nella sessione 1 le mezze metà di D f1 sono stabili (67,2 / 67,4), nella 2 scendono un poco (50,5 / 45,7); `steal_pct` è 0,23-0,40 in tutta la sessione 1 e nella prima cella della 2 (0,317), poi 0,01-0,03; `other_cores` è 0,15-0,27 contro 0,11-0,15. Con **due sole sessioni** non si può dire se la differenza sia **monotona** nel tempo (due punti per cella di D; nessun D a metà). Ipotesi possibili, **senza sceglierne una:** cache a freddo dopo la ripubblicazione del tree; stato della cache del disco; frequenza della CPU; attività di k3s (`k3s-server` è il primo processo nel fondo di ogni cella). Il primo episodio di ogni cella è più lento della mediana (effetto già noto: audit 18 §1.9).

## A.5 D FANOUT 10 a `lan`: P-log non accettato
Rapporto 0,114 (soglia 0,10) nella sessione 2, 0,096 nella 1: la regola per cella funziona come previsto; a `lan` vale `dispute-rtt` (d = 0, bias nullo). Nessuna azione.

## B. Note per il rapporto su P-a1 e P-a2 (nessun nuovo dato, nessuna spiegazione)
- P-a1: stima puntuale 79,85 ms [69,60; 96,73] contro l'intervallo previsto [46, 77]: eccesso sopra l'estremo di circa 2,9 ms su 10 consegne (circa 0,3 ms per consegna); classificazione invariata, **non conclusivo**.
- P-a2: l'IC di D FANOUT 10 su `dispute-rtt` è molto largo, [20,5; 45,5], con una sola cella da 10 episodi; classificazione invariata, **non conclusivo**.
- **Limite dichiarato:** nelle quattro celle `b1_default` i bracci `default` e D usano per costruzione cluster in due configurazioni diverse (D: lanciatore di B con contesto SSL precostruito e override del compose; `default`: `CMD` dell'immagine come spedito), per cui la differenza default − D include anche l'effetto di questa configurazione, non solo del contesto SSL.

## C. Comandi da autorizzare prima di `wan` (uno per volta; nulla lanciato)
Prima di ognuno verifichi tu `netem_show.sh` pulito. Ogni comando si ferma da solo (`set -e`, con `if … exit 1`; i nomi dei percorsi sono spezzati per non trovarli nella propria riga di comando) se c'è un container `dibtnsm`, un `run.py`, un watcher, meno di 2 GB liberi, o se la PKI scade fra meno di 2 ore (`openssl x509 -checkend 7200`; scadenza attuale 2026-10-13 08:22:10Z).

**C.1 — controllo di stato (sola lettura):**
```
ssh -i ~/.ssh/id_ed25519_lab ubuntu@192.168.100.57 'export PATH=/snap/bin:$PATH; date -u +%FT%TZ; echo "containers dibtnsm: $(docker ps -a -q --filter label=com.docker.compose.project=dibtnsm | wc -l)"; P="m67_retr""action/run.py"; W="netem_wa""tch"; echo "run.py: $(pgrep -f "$P" | wc -l)"; echo "watcher: $(pgrep -f "$W" | wc -l)"; df -h / | tail -1; openssl x509 -in ~/dib_tnsm/pki/ca.crt -noout -enddate; openssl x509 -in ~/dib_tnsm/pki/evidence.crt -noout -enddate'
```
(i conteggi di `pgrep` possono includere la shell remota solo se il nome del percorso compare contiguo nella riga di comando: qui è spezzato.)

**C.2 — celle `lan` di riferimento "prima"** (D e C, FANOUT 1 e 10, 10 episodi, ordine seme 20261014, senza watcher né netem; ~5 min):
```
ssh -i ~/.ssh/id_ed25519_lab ubuntu@192.168.100.57 'set -e; export PATH=/snap/bin:$PATH; P="m67_retr""action/run.py"; W="netem_wa""tch"; [ -z "$(docker ps -a -q --filter label=com.docker.compose.project=dibtnsm)" ]; if pgrep -f "$P" >/dev/null; then echo "run.py in esecuzione"; exit 1; fi; if pgrep -f "$W" >/dev/null; then echo "watcher attivo"; exit 1; fi; df -h / | tail -1; [ "$(df --output=avail -B1 / | tail -1)" -gt 2000000000 ]; openssl x509 -in ~/dib_tnsm/pki/ca.crt -noout -checkend 7200; T=$HOME/dib_tnsm/tree-bf272e8; OUT=$HOME/dib_tnsm/out/lan_ref_20261011; mkdir -p $OUT; cd $T; date -u +%FT%TZ; set +e; timeout 900 $HOME/dib_tnsm/venv/bin/python "experiments_tnsm/m67_retr""action/run.py" --block b1 --profile lan --tree $T --out $OUT/before --arms D,C --fanouts 1,10 > $OUT/before.stdout 2>&1; echo "run.py rc=$?"; tail -12 $OUT/before.stdout; date -u +%FT%TZ; df -h / | tail -1'
```
**C.3 — L_dns a `lan` subito dopo** (50 campioni, sito ucciso `site-3` come la notte, stesso metodo `calib_profile.py --profile lan`), stesso guard del C.2 con output in `$OUT/ldns_before`; da lanciare solo dopo il tuo OK, con `lan` verificato pulito da te:
```
ssh -i ~/.ssh/id_ed25519_lab ubuntu@192.168.100.57 'set -e; export PATH=/snap/bin:$PATH; P="m67_retr""action/run.py"; W="netem_wa""tch"; [ -z "$(docker ps -a -q --filter label=com.docker.compose.project=dibtnsm)" ]; if pgrep -f "$P" >/dev/null; then echo "run.py in esecuzione"; exit 1; fi; if pgrep -f "$W" >/dev/null; then echo "watcher attivo"; exit 1; fi; df -h / | tail -1; [ "$(df --output=avail -B1 / | tail -1)" -gt 2000000000 ]; T=$HOME/dib_tnsm/tree-bf272e8; OUT=$HOME/dib_tnsm/out/lan_ref_20261011; mkdir -p $OUT; date -u +%FT%TZ; set +e; timeout 600 $HOME/dib_tnsm/venv/bin/python $T/experiments_tnsm/m67_retraction/calib_profile.py --tree $T --out $OUT/ldns_before --profile lan > $OUT/ldns_before.stdout 2>&1; echo "rc=$?"; date -u +%FT%TZ; cat $OUT/ldns_before/calib_ldns_lan.txt'
```
**C.4 — copia in locale con sha256** (dopo la tua conferma che le celle sono finite): `ssh … 'cd ~/dib_tnsm/out/lan_ref_20261011 && sha256sum before/cells.jsonl ldns_before/calib_ldns_lan.txt'` e `scp -r … lan_ref_20261011 experiments_tnsm/m67_retraction/`. Dopo, mi fermo; aspetto il tuo "wan attivo".

## D. Piano `wan` (dopo il "wan attivo")
Come da istruzioni dell'utente: `calib_profile.py --profile wan --hold 60`; L_dns subito dopo l'applicazione (riporto i due valori adiacenti, `lan` e `wan`, senza etichette); **soglie P-log nuove** da ricalcolare con la nuova calibrazione (regola per cella: p95 < 10% del ritiro previsto da (a), per braccio e FANOUT: 10% di `n_RTT·R·(10 se f=1)`), file nuovo con sha256 e commit PRIMA del primo dato di B1; confronto con la notte (320 / 32 / 480 / 48 ms) solo come coerenza; poi i quattro gruppi B1 (seme 20261014), nessun episodio in più, a fine blocco eventualmente le celle `lan` "dopo" (decide l'utente).

## C.3 eseguito (2026-10-11 08:45:29-08:46:22 UTC; `lan` pulito, nessun watcher, nessun container secondo l'utente; ora del controllo di `netem_show.sh` non indicata, il messaggio riportava il segnaposto "HH:MM")
L_dns a `lan` "prima" (50 campioni, cluster D, `site-3` ucciso, `calib_profile.py --profile lan`): sito vivo p50 0,188 / p95 0,338 / max 2,09 ms; **sito morto p50 3,05 / p95 4,02 / max 7,84 ms**, errore `gaierror(-3, 'Temporary failure in name resolution')`. Dati sul nodo in `~/dib_tnsm/out/lan_ref_20261011/ldns_before/calib_ldns_lan.txt`; copia con sha256 in C.4. Valore adiacente a `lan` per il confronto con `wan`, da riportare accanto a quello di `wan` senza etichette.
