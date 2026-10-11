# A2, service masquerading in raw-breadth configuration (esperimento 22, ripetuto con breadth grezza)

Scritto e committato PRIMA di eseguire. Script: `code/scripts/service_masquerade_probe.py`, non modificato
(lines 94-103 il config; 117-135 l'iniezione; 151-154 la scelta del miglior caso che supera il quorum).
Precedente con trust weighting: `results/masquerade/README.md:52-55,67` (0,562 a f=0,30, D=120).

## Setup
- Config: `graph_free_raw.yaml` = copia di `configs/graph_free_selected.yaml` con la sola riga `trust_weighted: false`
  (alpha 0,6, beta 0,4, gamma 0, theta 0,65, m = 2). Originale intatto.
- Dati: `/root/Desktop/DIB/data/processed/observations_enriched.csv` (sha256 e741b426...1512, lo stesso di
  `results/masquerade/manifest.json`). Seme 42, dieci pseudo-siti, partizione random come nello script.
- Celle: porte 53, 123 e controllo 443; f_s = 0,30 (3 siti malevoli su 10), D = 120 giorni. Un secondo run con il
  config con trust weighting, stesse celle, come controllo di riproduzione (atteso 0,562 per 53/123, `results/masquerade/service_masquerade.csv`).
- Interprete: `/opt/conda/envs/dib312/bin/python`. Al massimo 8 processi, `nice -n 19`. Output in `experiments_tnsm/a2_masquerade_raw/`.

## Ipotesi (H-A2raw)
Con breadth grezza, f_s = 0,30 e D = 120, il massimo punteggio di un fatto inventato fra le istanze che superano il quorum
e` <= 0,58 (bound analitico del Criterio 1: 0,6 x 0,30 + 0,4 x 1) e quindi < theta = 0,65; il fatto non e` ammesso.
Il controllo 443 ha lo stesso punteggio ed e` fermato dal filtro di eleggibilita`.

## Regola di falsificazione (dichiarata prima)
H-A2raw e` falsificata se, per la porta 53 o 123, (i) score > 0,58 + 0,005 (tolleranza 0,005: l'arrotondamento a 6 decimali
e` trascurabile, la tolleranza copre solo il fatto che il bound e` scritto a due cifre), oppure (ii) `accepted` e` vero.
Se il punteggio e` fra 0,58 e 0,585 lo riporto come "entro tolleranza" con il valore esatto. Il controllo di riproduzione e`
falsificato (ambiente diverso dall'originale) se il run con trust weighting non da` 0,562 a 6 decimali per 53/123.
Nota dichiarata: la breadth per tipo di dispositivo e` |S_e| / (siti che ospitano il tipo); se un tipo e` ospitato da pochi siti
la breadth puo` superare f_s: e` esattamente quello che il test puo` rivelare, e se succede la ipotesi e` falsificata e il valore si riporta.

## Costo
Il run originale a 18 celle e` durato 122,4 s (picco 1,73 GiB, `results/masquerade/manifest.json`); qui 3 celle per config: ~20-30 s ciascuno. Sotto l'ora: si esegue per intero.
