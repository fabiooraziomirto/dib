## Arm C: evidence 172.19.0.2, site-0 172.19.0.8
packets: evidence capture 29361, site-0 capture 1828; time span evidence 1791712691.017-1791713270.435, site-0 1791712707.562-1791713266.590

### Q1 tap side (matched header keys between the two namespaces)
- evidence -> site-0: sent-seen 843, recv-seen 845, matched 843, unmatched at receiver 0 (0.0000, CP95 (0.0, 0.0044)), recv-seen not sent-seen 2, delta median 0.02 ms (p05/p95 0.01/0.06) -> **tap AFTER the qdisc**
- site-0 -> evidence: sent-seen 979, recv-seen 1009, matched 979, unmatched at receiver 0 (0.0000, CP95 (0.0, 0.0038)), recv-seen not sent-seen 30, delta median 0.02 ms (p05/p95 0.01/0.09) -> **tap AFTER the qdisc**

### Q3 SYN retransmission intervals (s), client = evidence
- n = 1; quantiles 5/50/95%: 1.001 / 1.001 / 1.001; sorted: [1.001]

### Q4 data-segment retransmission delays (s), seen in the evidence capture (same seq+len repeated)
- n = 13; sorted (first 40): [0.397, 0.399, 0.404, 0.62, 1.02, 1.053, 1.054, 1.054, 1.12, 1.215, 1.226, 1.23, 2.415]

### Q4 data-segment retransmission delays (s), seen in the site-0 capture (same seq+len repeated)
- n = 1; sorted (first 40): [1.02]

### Q5 flights per evidence->site connection (non-pure-ACK, non-FIN/RST packets, direction changes)
- connections evidence->site (with SYN): 273; completed (server payload seen): 255; flights per completed connection: median 6, distribution {4: 12, 5: 16, 6: 172, 7: 41, 8: 11, 9: 3}; connections per delivery cannot be derived from headers alone (see Q7)

### Q6 phase timeouts (evidence->site)
- SYN count per connection: {1: 271, 2: 2} (connect phase not completed within the first RTO: 2/273)
- connections with no server payload and a client FIN/RST (aborted by the client): 18/273; connections with no server payload at all: 18/273
- duration (s) of completed connections: 5/50/95% 1.606 / 1.609 / 3.005

### Repeated transmissions by evidence toward sites (data/SYN/FIN segments seen twice or more at the sender tap): 7/1482

### Q7 coverage
- evidence->site connections in the evidence capture: 273 (expected deliveries: 20 episodes x 10 sites = 200, plus retries)

### Q8 capture-gap indicator, evidence: ACKs acknowledging bytes not seen: 0/27604

### Q8 capture-gap indicator, site-0: ACKs acknowledging bytes not seen: 0/1704
