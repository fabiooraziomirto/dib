# Audit 84 — Risultati della replica sul nodo della validazione del modello v4 (audit 83)

Data: 2026-10-12 (04:50-05:15Z a nodo). Dati: `experiments_tnsm/netns_testbed/run_node_v4/` (420 episodi; tre container Docker con `NET_ADMIN`, `--memory 4g --cpus 4`, ~430 MB ciascuno, RAM libera del nodo ≥ 6,4 GB per tutto il run; `tc` dell'host tramite il suo loader dinamico; `service.py` del tree `50c4335`, HTTP semplice; `DATA.sha256` verificato dopo la copia: 0 discordanze; nodo `ubuntu@192.168.100.57`, CPU QEMU generica con altri carichi di fondo). Analisi `analyze_v4.py` invariata (`analysis.md`). Ipotesi, previsioni e criteri: audit 80 e 83 (committati prima dei dati).

## Verdetti
- **T-W0 (validità): superato** (mediana per sito 187/367/548 ms contro 180/360/540, 0 in ritardo su 200 per ritardo).
- **T-W1 (modello v4): VALIDATO sul nodo, 5/6 celle** (regola ≥ 5/6, nessuna oltre il doppio). Consegne in ritardo misurate (previste): 0,147 (0,150); 0,298 (0,282); 0,152 (0,149); **0,248 (0,281)**; 0,147 (0,147); 0,258 (0,277). La cella fuori è (120 ms, 8 %): −3,3 punti contro la tolleranza di 3. Episodi lenti: 0,767 (0,801), 1,000 (0,966), 0,817 (0,800), 0,917 (0,963), 0,783 (0,796), 0,917 (0,962): scarti ≤ 4,6 punti. Pending: 0 ovunque (previsto 0).
- **T-W2 (descrittivo):** il modello v3 avrebbe superato 1 cella su 6.
- **Coerenza con il banco locale (audit 81):** quote di consegne in ritardo praticamente uguali (es. 60 ms/8 %: 0,298 contro 0,290; 180 ms/4 %: 0,147 contro 0,130); nel nodo il p95 a 120 ms/4 % è sotto la previsione (1 377 contro 2 080 ms), e a 60 ms/4 % sopra (2 186 contro 1 540): la coda resta poco predicibile (stessa conclusione dell'audit 81).

## Cosa si può dire
Il modello v4 prevede la quota di consegne in ritardo entro 3,3 punti, in due ambienti indipendenti (banco locale 6/6, nodo 5/6) su condizioni mai usate per costruirlo, e il confronto retrospettivo sui dati B5 del nodo con Docker e mTLS (audit 83: D 0,178 contro 0,179; C 0,310 contro 0,251) mostra che per l'arm con mTLS manca la struttura della handshake TLS. **Limiti:** sul nodo la replica è HTTP semplice, senza mTLS e senza il bridge Docker, in container con tre banchi in parallelo che condividono la CPU del nodo (carico non controllato: il nodo ha altri servizi); la coda (p95) non è validata; 60 episodi per cella.
