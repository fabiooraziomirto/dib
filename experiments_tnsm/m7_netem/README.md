# M7 — rete emulata con netem (preparato, NON eseguito)

Script da rivedere e lanciare **solo dall'utente**, con `sudo`, **solo sul nodo libero** (192.168.100.57). Decisione utente: netem solo in un network namespace dedicato con una coppia veth, mai su `lo` né su un'interfaccia condivisa.

- `netem_apply.sh [--dry-run] <profilo>`: crea, se mancano, il namespace `dibnet` e la coppia `veth-dib-h` (10.203.0.1/30, namespace radice) ↔ `veth-dib-n` (10.203.0.2/30, dentro `dibnet`), poi applica il profilo. Profili (piano §7.5):
  - `lan`: nessun qdisc;
  - `regional`: 20 ms e 0,1% per direzione;
  - `wan`: 80 ms e 1%;
  - `degraded`: 200 ms e 5%;
  - `partition-to-ns` e `partition-from-ns`: partizioni asimmetriche (100% di perdita in una sola direzione).
- `netem_clear.sh [--dry-run] [--teardown]`: rimuove i qdisc. Con `--teardown` rimuove anche la coppia veth e il namespace.
- Una guardia (`guard_dev`) rifiuta qualsiasi interfaccia diversa da `veth-dib-h` e `veth-dib-n`. `lo` dentro il namespace viene solo portata up, senza qdisc.
- Provati solo con `--dry-run` su questo host (2026-10-10). Niente è stato eseguito sul nodo.

**Punto aperto da decidere prima di M7.** I servizi DIB girerebbero dentro `dibnet` (`ip netns exec dibnet ...`). Il generatore di carico sta su questo host, e per raggiungere 10.203.0.2 serve uno di questi:
- (a) sul nodo, `net.ipv4.ip_forward=1` più una rotta su questo host verso 10.203.0.0/30 via 192.168.100.57: cambia la configurazione di rete di **entrambi** gli host;
- (b) un inoltro TCP sul nodo (es. `socat TCP-LISTEN:<p>,fork TCP:10.203.0.2:<p>`), che aggiunge un hop nel namespace radice, fuori dal link emulato;
- (c) il generatore dentro il nodo, nel namespace radice: co-locazione, ma tutto il traffico dell'esperimento passa dal link emulato.

Raccomandazione: (b) per M7 (nessuna modifica di routing; il ritardo dell'hop locale si misura nel profilo `lan`). Oppure (c) se si vuole il caso più pulito per la rete. Da decidere insieme.
