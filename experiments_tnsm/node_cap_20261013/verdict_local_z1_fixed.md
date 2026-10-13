| arm | connessioni | valide | ipotesi | verdetto | quota con la struttura attesa |
|---|---|---|---|---|---|
| D | 160 | 100 | H-P1a | **confermata** | moda 1460, valori {1460: 200} |
| D | 160 | 100 | H-P1b | **confermata** | 1.000 (100/100) |
| C | 100 | 100 | H-P1a | **confermata** | moda 1460, valori {1460: 200} |
| C | 100 | 100 | H-P1c | **falsificata** | 0.000 (0/100) |

### Arm D: firme osservate (n segmenti E→S, n segmenti S→E, n segmenti del volo del server)

- [2, 2, 0]: 100 connessioni
- lunghezze E→S (mediana per posizione): [204.0, 71.0]
- lunghezze S→E (mediana per posizione): [125.0, 16.0]

### Arm C: firme osservate (n segmenti E→S, n segmenti S→E, n segmenti del volo del server)

- [4, 4, 1]: 100 connessioni
- lunghezze E→S (mediana per posizione): [1537.0, 853.0, 226.0, 93.0]
- lunghezze S→E (mediana per posizione): [2393.0, 1502.0, 147.0, 38.0]

### Unità osservate in ingresso al sito (osservazione, audit 116)

{"D": {"valide": 100, "ingresso_uguale_all_uscita": 100, "primo_segmento_E_S_oltre_MSS": 0, "di_cui_arrivati_spezzati": 0}, "C": {"valide": 100, "ingresso_uguale_all_uscita": 100, "primo_segmento_E_S_oltre_MSS": 100, "di_cui_arrivati_spezzati": 0}}

### Addendum 1 (H-P2a, ClientHello come unità o spezzato)

{"connessioni_C": 100, "valutabili": 100, "unita": 100, "spezzate": 0, "escluse_prima_copia_fuori_finestra": 0, "quota_unita": 1.0, "H-P2a": "confermata", "lunghezze_righe_oltre_0.3s": {}}
