| arm | FANOUT | episodes | site-episodes with P-log apply | missing | fields with 10 sites (every episode) | per-site median ms (site 0..9) |
|---|---|---|---|---|---|---|
| C | 10 | 10 | 100 / 100 | 0 | 6/6 | 418 419 420 419 419 420 420 420 420 420 |
| D | 1 | 10 | 100 / 100 | 0 | 6/6 | 249 576 902 1228 1556 1880 2205 2544 2868 3192 |
| C | 1 | 10 | 100 / 100 | 0 | 6/6 | 414 902 1391 1881 2371 2860 3347 3841 4339 4828 |
| D | 10 | 10 | 100 / 100 | 0 | 6/6 | 255 254 254 256 256 257 256 256 258 258 |

episodes.jsonl: 40 lines, keys of a row: ['dispute_rtt_s', 'episode', 'excluded', 'pending_after_response', 'pending_left', 'pending_read_delay_s', 'plog_ack_count', 'plog_ack_ts', 'plog_apply_ts', 'queue_wait_before_s', 'score_id', 'status', 't0', 't_resp', 'withdrawn_plog_s']
