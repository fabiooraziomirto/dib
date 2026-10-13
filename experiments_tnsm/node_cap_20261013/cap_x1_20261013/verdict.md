| arm | connessioni | valide | ipotesi | verdetto | quota con la struttura attesa |
|---|---|---|---|---|---|
| D | 243 | 160 | H-P1a | **confermata** | moda 1460, valori {1460: 320} |
| D | 243 | 160 | H-P1b | **falsificata** | 0.944 (151/160) |
| C | 144 | 144 | H-P1a | **confermata** | moda 1460, valori {1460: 288} |
| C | 144 | 144 | H-P1c | **falsificata** | 0.000 (0/144) |

### Arm D: firme osservate (n segmenti E→S, n segmenti S→E, n segmenti del volo del server)

- [2, 2, 0]: 150 connessioni
- [5, 4, 0]: 8 connessioni
- [2, 3, 0]: 1 connessioni
- [3, 2, 0]: 1 connessioni
- lunghezze E→S (mediana per posizione): [204.0, 71.0, 853, 226.0, 94.0]
- lunghezze S→E (mediana per posizione): [125.0, 16.0, 147, 38.0]

### Arm C: firme osservate (n segmenti E→S, n segmenti S→E, n segmenti del volo del server)

- [4, 4, 1]: 128 connessioni
- [4, 5, 1]: 8 connessioni
- [4, 5, 2]: 5 connessioni
- [5, 4, 0]: 1 connessioni
- [1, 1, 0]: 1 connessioni
- [3, 4, 1]: 1 connessioni
- lunghezze E→S (mediana per posizione): [1537.0, 853, 226, 93.0, 93]
- lunghezze S→E (mediana per posizione): [2393.0, 1502, 147, 38, 54]

### Unità osservate in ingresso al sito (osservazione, audit 116)

{"D": {"valide": 160, "ingresso_uguale_all_uscita": 160, "primo_segmento_E_S_oltre_MSS": 0, "di_cui_arrivati_spezzati": 0}, "C": {"valide": 144, "ingresso_uguale_all_uscita": 144, "primo_segmento_E_S_oltre_MSS": 143, "di_cui_arrivati_spezzati": 0}}

### Addendum 1 (H-P2a, ClientHello come unità o spezzato)

{"connessioni_C": 144, "valutabili": 143, "unita": 143, "spezzate": 0, "escluse_prima_copia_fuori_finestra": 1, "quota_unita": 1.0, "H-P2a": "confermata", "lunghezze_righe_oltre_0.3s": {"93": 7, "853": 2, "226": 6, "854": 2, "94": 8, "852": 1}}
