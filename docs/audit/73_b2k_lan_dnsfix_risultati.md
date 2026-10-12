# Audit 73 — B2-kill a `lan` con il DNS corretto: primo blocco senza censura (H-N1..N3 di audit 72)

Data: 2026-10-12 (01:54-02:09Z a nodo). Dati: `experiments_tnsm/b2k_dnsfix_20261012/b2k_lan/` (tree `3a45868` = `50c4335` con solo `run.py` cambiato; `DIB_M67_DNS_NOSEARCH=1`, registrato nei manifest come `dns_nosearch: true`; keep-alive spento; correzione del driver di audit 60; L_dns calibrato a `lan` nel blocco; seme 20261014; PKI 336 h; nessun watcher; `DATA.sha256` verificato dopo la copia: 0 discordanze; nessun pcap). Protocollo di B2k dell'audit 45 invariato. Script `lan_b2k_dnsfix.sh`, analisi `analyze_b2k.py` (output `analysis_b2k.md`). Ipotesi: audit 72 (committato prima dei dati).

## Verdetti
- **H-N1 non falsificata:** **120 prove su 120 utilizzabili**, 0 escluse (nessun `client_timeout`, nessuna coda non vuota, nessun `transport_error`); massimo di esclusioni in una cella k = 10/50: 0 (limite 3). Nello stesso protocollo senza la correzione DNS: 61 esclusioni (audit 57), 19 con la correzione del driver (audit 69), 18 con keep-alive (audit 71).
- **H-N2 non falsificata:** (d-kill) non falsificata in 12/12 celle (mediana massima 1,69 s, estremo superiore massimo dell'IC 1,96 s, contro bound 7-8 s); (e) non falsificata (0 violazioni su 120 prove; I1-I3 solo tramite `final_all_monitor_only`).
- **H-N3 (descrittiva):** mediane 0,60-1,69 s, nello stesso ordine di grandezza di audit 69 (0,6-1,9 s).
- **Durata:** il blocco è durato 15 minuti (due bracci da ~7 min) contro ~50 min degli audit 69 e 71: il resto era attesa su stalli del DNS.

## Tabella (mediana della convergenza dopo `start`, IC bootstrap 95%; bound 7,0 s a T = 5, 8,0 s a T = 15)
| arm | T | k | n | mediana s [IC] |
|---|---|---|---|---|
| C | 5 | 1 | 10 | 0,60 [0,51; 0,70] |
| C | 15 | 1 | 10 | 0,91 [0,63; 1,70] |
| C | 5 | 10 | 10 | 0,65 [0,52; 0,84] |
| C | 15 | 10 | 10 | 1,05 [0,78; 1,53] |
| C | 5 | 50 | 10 | 0,81 [0,72; 0,90] |
| C | 15 | 50 | 10 | 1,47 [1,11; 1,81] |
| D | 5 | 1 | 10 | 0,74 [0,62; 0,80] |
| D | 15 | 1 | 10 | 1,12 [0,67; 1,72] |
| D | 5 | 10 | 10 | 0,64 [0,59; 0,84] |
| D | 15 | 10 | 10 | 0,81 [0,63; 1,06] |
| D | 5 | 50 | 10 | 0,81 [0,76; 0,96] |
| D | 15 | 50 | 10 | 1,69 [1,06; 1,96] |
T15 − T5 resta descrittiva (decisione Q9).

## Cosa si può dire (e cosa no)
- A `lan`, con il sito ucciso che risponde NXDOMAIN subito, la convergenza dopo il riavvio è misurata fino a **k = 50 in entrambi i bracci**: mediana ≤ 1,7 s, senza violazioni, 10 prove per cella. **Sostituisce** i blocchi `lan` degli audit 57, 69 e 71 per k = 10 e 50.
- **Limiti:** un solo nodo, 10 prove per cella, coda non stimata; il modello di guasto è "sito ucciso con nome non risolvibile", non "sito muto" (silenzio di rete): non misurato qui; la regola L_dns (audit 45 §5) calibrata a bassa frequenza non intercetta stalli del DNS sotto raffica (audit 72): per B2k a `degraded` e `wan` (audit 57) la stessa censura non è stata verificata; per k = 1 nei due profili non ci sono state esclusioni per timeout, per k = 10 a `degraded` 1-2 esclusioni per cella (audit 57), compatibili con la stessa causa ma **non attribuite**.
