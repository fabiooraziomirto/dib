## Arm D: evidence 172.19.0.2, site-0 172.19.0.11
packets: evidence capture 17003, site-0 capture 1056; time span evidence 1791712134.704-1791712525.713, site-0 1791712148.539-1791712520.965

### Q1 tap side (matched header keys between the two namespaces)
- evidence -> site-0: sent-seen 485, recv-seen 490, matched 485, unmatched at receiver 0 (0.0000, CP95 (0.0, 0.0076)), recv-seen not sent-seen 5, delta median 0.02 ms (p05/p95 0.01/0.08) -> **tap AFTER the qdisc**
- site-0 -> evidence: sent-seen 561, recv-seen 584, matched 561, unmatched at receiver 0 (0.0000, CP95 (0.0, 0.0066)), recv-seen not sent-seen 23, delta median 0.03 ms (p05/p95 0.01/0.09) -> **tap AFTER the qdisc**

### Q3 SYN retransmission intervals (s), client = evidence
- n = 0; quantiles 5/50/95%: - / - / -; sorted: []

### Q4 data-segment retransmission delays (s), seen in the evidence capture (same seq+len repeated)
- n = 2; sorted (first 40): [1.428, 1.452]

### Q4 data-segment retransmission delays (s), seen in the site-0 capture (same seq+len repeated)
- n = 0; sorted (first 40): []

### Q5 flights per evidence->site connection (non-pure-ACK, non-FIN/RST packets, direction changes)
- connections evidence->site (with SYN): 233; completed (server payload seen): 213; flights per completed connection: median 4, distribution {4: 193, 5: 20}; connections per delivery cannot be derived from headers alone (see Q7)

### Q6 phase timeouts (evidence->site)
- SYN count per connection: {1: 233} (connect phase not completed within the first RTO: 0/233)
- connections with no server payload and a client FIN/RST (aborted by the client): 20/233; connections with no server payload at all: 20/233
- duration (s) of completed connections: 5/50/95% 1.203 / 1.204 / 2.257

### Repeated transmissions by evidence toward sites (data/SYN/FIN segments seen twice or more at the sender tap): 18/920

### Q7 coverage
- evidence->site connections in the evidence capture: 233 (expected deliveries: 20 episodes x 10 sites = 200, plus retries)

### Q8 capture-gap indicator, evidence: ACKs acknowledging bytes not seen: 0/15669

### Q8 capture-gap indicator, site-0: ACKs acknowledging bytes not seen: 0/963
