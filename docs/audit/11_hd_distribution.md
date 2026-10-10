# Audit 11 — Forma in conteggi di Criterion 1 sul DIBScorer e distribuzione di h_d

Data: 2026-10-10. Branch `revision-tnsm`, worktree `/root/Desktop/DIB_tnsm`. Nessun file di produzione modificato. Notazione: [C] = verificato nel codice o nei dati (file:riga); [D] = deduzione.

## 1. Forma in conteggi sul DIBScorer reale (Fase 2)

Test: `analysis_fs/test_fstar_scorer.py`. Ipotesi, previsione e criterio di falsificazione sono nel docstring, scritti prima dell'esecuzione.

**Ipotesi H (utente).** Con (α, θ) = (0.6, 0.65), un fatto riportato solo da K siti avversari e mai dagli h siti onesti che osservano il tipo è ammesso se e solo se K > 5h/7 (pareggio escluso), anche con volume avversario ρ = 100. Per altre coppie il rapporto 5/7 diventa r = (θ+α−1)/(1−θ).

**Griglia.** K = 1..8, h = 0..20. Quattro coppie (α, θ): (0.6, 0.65) con r = 5/7, (0.7, 0.65) con r = 1, (0.6, 0.7) con r = 1, (0.55, 0.6) con r = 3/8. Due costruzioni, entrambe riusate:
- `bound_grid.population`: un giorno, volume avversario di almeno 100 volte quello onesto;
- `test_followup._flood`: tre giorni, l'avversario copre ogni giorno con `ceil(100h/K)` report per sito.

**Codice [C].** C_s = |S_e|/|ES_d| (`code/src/dib/evaluation/dib.py:276`). C_t = min(1, 0.7·giorni + 0.3·volume) (`:277-279`). score = α·C_s + β·C_t (`:281-285`). Ammissione in `admit_auto` (`:22-47`), con il quorum `min_reporting_sites` a `:45-46`.

**Esito.** 18 test: 10 passed, 8 failed. I fallimenti erano previsti e l'asserzione non è stata indebolita.

| Test | Esito | Contraddizioni di H |
|---|---|---|
| `test_h_score_only_m1` (quorum m = 1, solo score), 4 coppie × 2 costruzioni | 8 passed | nessuna su 168 celle per combinazione |
| `test_supremum_never_attained` (h ≥ 1: score < αK/(K+h)+β; volume avversario ≥ 100× onesto), 2 costruzioni | 2 passed | — |
| `test_h_operating_quorum_m2` (quorum operativo m = 2), 4 coppie × 2 costruzioni | **8 failed** | solo celle con K = 1, uguali nelle due costruzioni: |
| — (0.6, 0.65) | | (K,h) = (1,0) score 1.0; (1,1) score 0.6988 |
| — (0.7, 0.65) e (0.6, 0.7) | | (1,0) score 1.0 |
| — (0.55, 0.6) | | (1,0) 1.0; (1,1) 0.7237; (1,2) 0.6320 |

In tutte le contraddizioni lo score supera θ, |S_e| = 1, e il fatto è rifiutato dal quorum m = 2 (`dib.py:45-46`), non dallo score. Le celle coincidono con la previsione calcolata prima in aritmetica esatta. Coerente con `analysis_fs/test_followup.py::test_p0_5` (con due fonti, solo il quorum rifiuta).

**Lettura [D].**
1. Il solo score realizza esattamente "ammesso ⇔ K > r·h" sulla griglia, per tutte e quattro le coppie. H vale come proprietà dello score. Con il quorum operativo, la condizione corretta è "ammesso ⇔ K > r·h e K ≥ m". Per K ≥ 2 il quorum non cambia nulla nella griglia.
2. **Pareggio (0.6, 0.65), K = 5, h = 7: rifiutato con margine 0.00119 = 0.3β/101.** È lo scarto dovuto al volume finito (ρ = 100). Per ρ → ∞ lo score tende a θ dal basso: il supremum non è raggiunto e il fatto resta rifiutato, ma con un margine che tende a 0. [?] In virgola mobile, con ρ molto grande, l'arrotondamento potrebbe portare lo score a ≥ θ. Non testato.
3. **La direzione "se" dipende da ρ.** Il caso ammesso più vicino alla soglia, a (0.6, 0.65), è K = 8, h = 11 (share 0.421), con margine 0.00145. In aritmetica esatta servono ρ ≳ 45 perché sia ammesso. Con ρ più piccolo, K > 5h/7 non basta. La direzione "solo se" (K ≤ r·h ⇒ rifiutato) non dipende da ρ: è il Criterion 1.
4. Margini minimi dalla soglia nella griglia (costruzione a un giorno, K ≥ 2):

| (α, θ) | r | ammesso più vicino (score−θ; K, h) | rifiutato più vicino (θ−score; K, h) |
|---|---|---|---|
| (0.6, 0.65) | 5/7 | 0.00145; 8, 11 | 0.00119; 5, 7 |
| (0.7, 0.65) | 1 | 0.02245; 8, 7 | 0.00089; 2, 2 |
| (0.6, 0.7) | 1 | 0.01882; 8, 7 | 0.00119; 8, 8 |
| (0.55, 0.6) | 3/8 | 0.00144; 5, 13 | 0.00133; 3, 8 |

**Aggiornamento (decisione utente).** `test_h_operating_quorum_m2` è invariato e marcato `xfail(strict=True)` con motivazione "ipotesi H falsificata: il quorum respinge K = 1". Nuovo test `test_h_prime_with_quorum`, sulla stessa griglia e sul DIBScorer reale, con H' = "ammesso ⇔ K > r·h e K ≥ m" per m ∈ {1, 2}: **16 passed**. Stato del file: 26 passed, 8 xfailed. Formulazione corretta riportata in `docs/audit/09_f_s_derivazione_e_letteratura.md` (punto 4).

Riprodurre: `PYTHONPATH=code/src PYTHONDONTWRITEBYTECODE=1 timeout 300 python3 -m pytest analysis_fs/test_fstar_scorer.py -q -p no:cacheprovider` (~10 s).

## 2. Distribuzione di h_d (Fase 3)

Solo dati già sul disco, niente scaricato. Script nuovo `analysis_fs/hd_union.py`; riusati `analysis_fs/hd_heterogeneity.py` (output per corpus) e `dib.adapters.real_federation.find_overlap_devices` (`code/src/dib/adapters/real_federation.py:65-112`).

### 2.1 Cosa c'è sul disco e cosa manca

| Corpus | Sul disco | Forma | Siti | Tipi | Finestra | sha256 (16) |
|---|---|---|---|---|---|---|
| UNSW-IoTraffic | sì, solo processato: `/root/Desktop/DIB/data/processed/observations_enriched.csv` (e `_item1fixed`) | osservazioni normalizzate | 1 | 27 | set 2016 – apr 2017 (+ righe spurie del 1970, audit 08 §11) | `e741b426…` (`_item1fixed`: `4de5423c…`) |
| Mon(IoT)r IMC19 | sì, solo processato: `moniotr_full_observations.csv` | osservazioni normalizzate | 4 capture tree = 2 laboratori (US, UK) | 59 | 29 mar – 8 mag 2019 | `6d2f0080…` |
| YourThings | sì, solo processato: `yourthings_observations.csv` | osservazioni normalizzate | 1 | 46 | **un solo giorno** (21 mar 2018) | `b6db4884…` |
| Federazione reale (derivata) | sì: `real_federation_observations.csv` | 6 org label, 10 tipi condivisi | 6 (4 indipendenti) | 10 | — | `ce6d37fb…` |
| UNSW attack 2018 | sì: `data/unsw_attack_2018/{flowdata,annotations}` (14 MB) | flowstats + annotazioni | — | — | — | — |
| UNSW MUD profiles | sì: `data/unsw/profiles/{ground_truth,normalized}` | 28 profili | — | 28 | — | — |

**Mancano** (ricerca su tutto il filesystem di `.pcap`, `.pcapng`, archivi e nomi dei dataset; nessuna cattura grezza IoT trovata):
- PCAP o CSV grezzi di UNSW-IoTraffic (`data/unsw_iotraffic_2025/{flows,protocols}_extracted`), Mon(IoT)r (`iot-data.tar`, `iot-idle.tgz`) e YourThings (`iot_traffic*.tgz`). Gli script `prepare_*.py` non si possono rieseguire. Lo conferma anche `/root/Desktop/DIB/outputs/dataset_inventory.json` ("flows directory missing").
- Tutti i candidati di `10_dataset_survey.md`: raccolta Ahmed et al. (PETS 2022), NCSU IoT-Lab 2020/2021, PingPong, HomeSnitch, IoT Inspector (nessun CSV per `code/scripts/prepare_iot_inspector_conditional.py`, che richiede `--input`), IoT-23, CICIoT2023, GothX/Gotham.
- Disco: 35 GB liberi su 540 (94% occupato).

### 2.2 Come si identifica "lo stesso tipo" tra siti

Nel codice ci sono due meccanismi, e **non coincidono** [C]:
1. `dib.evaluation.profiles.canonical_device_name` (`profiles.py:142-194`): minuscole, caratteri non alfanumerici → `-`, più una tabella di alias, quasi tutti UNSW → nome canonico (es. `SamsungSmartThings` → `smartthings`, `TPLinkSmartPlug` → `tp-link-plug`). Lo usano `real_federation.py:86-99` e quindi i corpora `real_federation_*` e `union_canonical_*`.
2. `docs/label_mapping_v16.csv`: 6 tipi allineati YourThings ↔ Mon(IoT)r, usato da `hd_heterogeneity.py` per `three_lab_US_UK_YT`. Tre righe (`googlehomemini`, `insteonhub`, `rokutv`, "hyphen-only normalization") **non** sono unite da `canonical_device_name`: per il codice sono tipi diversi da `google-home-mini`, `insteon-hub`, `roku-tv`.

Per questo la tabella riporta l'unione sia con il solo mapping canonico sia con "canonico + v16". Restano quasi-duplicati che nessuno dei due mapping unisce e che non ho unito io: `googlehome` (YT) / `google-home` (Mon(IoT)r UK); `augustdoorbellcam` (YT) / `august-doorbell` (UNSW); `nestcamera` (YT) / `dropcam` (UNSW; `nest-cam` → `dropcam` è un alias, `nestcamera` no); `t-echodot` / `echodot` (stesso laboratorio). Il mapping è per nome commerciale, non per make-and-model o firmware. Alcuni alias uniscono già dispositivi diversi (`philips-bulb` → `philips-hue`, `nest-cam` → `dropcam`: `profiles.py:163-173`). Unire anche questi quasi-duplicati porterebbe al massimo 3 tipi da h = 1 a h = 2 e non cambierebbe le conclusioni sotto.

**Sito.** `real_federation.ORG_LABELS` (`real_federation.py:46-53`). "Indipendente" fonde us/us-vpn e uk/uk-vpn (`NON_INDEPENDENT_PAIRS`, `:59-62`: stessa popolazione di dispositivi, due percorsi di rete). Con i dati sul disco esistono quindi **al più 4 siti indipendenti** (UNSW, Mon(IoT)r US, Mon(IoT)r UK, YourThings). Un sito osserva un tipo se ha almeno una riga di quel tipo. La variante "solo righe con endpoint" (regola di `dib.py:198` e di `hd_heterogeneity.py`) dà gli stessi h per tutti i 119 tipi (0 differenze).

### 2.3 Risultati

**Ipotesi (nel docstring di `hd_union.py`, scritta prima dell'esecuzione).** Nessun tipo ha h ≥ 5. K = 3 non è mai coperto al margine e K = 2 non è mai coperto a f_s. La mediana di h è 1. Falsificata se h_indep ≥ 5 per qualche tipo o se più di metà dei tipi ha h_indep ≥ 2. **Esito: non falsificata.** 0 tipi con h ≥ 5; 32 tipi su 119 (27%) con h_indep ≥ 2.

**Regola di copertura** (sez. 1, H'), con h siti onesti:
- lo score respinge sempre K avversari se K ≤ 5h/7, cioè h ≥ ⌈7K/5⌉ = 2, 3, 5 per K = 1, 2, 3;
- il budget dichiarato regge se K/(K+h) ≤ 0,30, cioè h ≥ ⌈7K/3⌉ = 3, 5, 7;
- il quorum m = 2 respinge K = 1 per ogni h, quindi con m = 2 K = 1 è coperto su tutti i tipi.

Per K ≤ 3 il pareggio K = 5h/7 non si presenta, quindi i conteggi al margine coincidono con quelli di `hd_coverage_requirement.csv`, che usa la disuguaglianza stretta.

Numero di tipi coperti (CSV: `analysis_fs/out/hd_tolerance_k123.csv`). "score" = K ≤ 5h/7; "f_s" = K/(K+h) ≤ 0,30.

| Corpus | tipi (righe) | h min/med/max | K=1 score | K=1 f_s | K=2 score | K=2 f_s | K=3 score | K=3 f_s |
|---|---|---|---|---|---|---|---|---|
| Mon(IoT)r, US e UK fusi | 59 | 1/1/2 | 26 | 0 | 0 | 0 | 0 | 0 |
| Mon(IoT)r, 4 capture tree (non indipendenti) | 59 | 2/2/4 | 59 | 26 | 26 | 0 | 0 | 0 |
| YourThings | 46 | 1/1/1 | 0 | 0 | 0 | 0 | 0 | 0 |
| three_lab US+UK+YT (mapping v16) | 6 | 3/3/3 | 6 | 6 | 6 | 0 | 0 | 0 |
| federazione reale, 6 label | 10 | 2/3/6 | 10 | 5 | 5 | 4 | 4 | 0 |
| federazione reale, indipendenti | 10 | 2/2/4 | 10 | 4 | 4 | 0 | 0 | 0 |
| **unione, canonico, indipendenti** | 119 | 1/1/4 | 32 | 4 | 4 | 0 | 0 | 0 |
| unione, canonico + v16, indipendenti | 116 | 1/1/4 | 32 | 7 | 7 | 0 | 0 | 0 |
| unione, canonico, capture tree | 119 | 1/2/6 | 64 | 27 | 27 | 4 | 4 | 0 |
| UNSW 10 pseudo-siti, 20 seed (sintetico) | 540 | 2/10/10 | 540 | 520 | 520 | 519 | 519 | 509 |

Istogramma dell'unione (CSV: `analysis_fs/out/hd_union_histogram.csv`, solo conteggi):

| h_indep | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| canonico | 87 | 28 | 1 | 3 |
| canonico + v16 | 84 | 25 | 4 | 3 |

I 4 tipi con h_indep ≥ 3 nel mapping canonico sono `smartthings`, `ring-doorbell` e `philips-hue` (h = 4: UNSW, US, UK, YT) e `tp-link-plug` (h = 3). Con v16 si aggiungono `google-home-mini`, `insteon-hub` e `roku-tv` (h = 3).

**Lettura [D].**
1. Sui dati reali, la garanzia per tipo copre K = 2 colluder solo su 4–7 tipi su circa 117 (al margine) e su nessun tipo a f_s = 0,30. Non copre mai K = 3. K = 1 è coperto solo grazie al quorum. È un limite strutturale: con 4 siti indipendenti h ≤ 4, mentre K = 3 richiede h ≥ 5 al margine e h ≥ 7 a f_s.
2. I corpora con h alto (UNSW 10 pseudo-siti, mediana 10) sono partizioni sintetiche di un solo laboratorio. I capture tree di Mon(IoT)r gonfiano h (mediana 2 invece di 1) senza indipendenza.
3. Riproducibilità: `hd_heterogeneity.py` rieseguito nel worktree (3 min 18 s) riproduce byte per byte i 3 CSV `hd_*` committati. `hd_union.py` impiega circa 1 min.

### 2.4 Cosa servirebbe (nessun download fatto)

- **Raccolta Ahmed et al. (PETS 2022).** Rispetto a quanto già c'è, aggiunge NCSU 2020/2021 (un laboratorio, due anni: per la regola di sopra conta come **un** sito indipendente), PingPong (UCI, form e licenza non commerciale) e HomeSnitch (su richiesta). In tutto si arriva al più a 7 siti indipendenti. h ≥ 7 (K = 3 a f_s) richiederebbe un tipo presente in tutti e 7: [D] improbabile. Primo passo proposto: il campione NCSU da 476 MB (survey §3.A), fuori dalla repo, per misurare la sovrapposizione dei make-and-model con i 119 tipi. Licenza non dichiarata.
- **IoT Inspector** (aggiornamento: fuori dal percorso critico, nessuna risposta da due mesi; il repo GitHub citato da Mon(IoT)r IMC23 non espone i dati, vedi `12_test_realistici.md` sez. 1). È l'unica fonte con N reale grande (case come siti) e quindi l'unica che può dire se h ≥ 5–7 è realistico. Richiede una richiesta di accesso; formato atteso da `prepare_iot_inspector_conditional.py` (campi `home_id`, `device_id`, `timestamp`, `hostname`, `port`, `protocol`, `vendor`, `product`).
- **PCAP grezzi.** Non servono per h_d. Servono solo per rieseguire gli adapter (`prepare_*.py`).

### 2.4 bis Budget con N ≤ 7 laboratori (decisione utente)

Con al più N = 7 laboratori indipendenti (i 4 sul disco più NCSU, PingPong e HomeSnitch) e f_s = 0,30, il budget per tipo è **K ≤ 2**: K ≤ ⌊0,30·N⌋ = 2. Per K = 2 il budget regge solo se K/(K+h) ≤ 0,30, cioè h ≥ 5, e quindi K + h ≥ 7: il tipo deve essere presente in **tutti** i siti. K = 3 richiederebbe h ≥ 7 e N ≥ 10, fuori portata con laboratori reali.

### 2.6 Campione NCSU IoT-Lab (Ahmed et al., PETS 2022)

**Download.** Solo il campione (decisione utente), fuori dalla repo:
- origine: `https://privacy-datahub.csc.ncsu.edu/data/iot-device-fingerprinting/sample.zip`, scaricato il 2026-10-10 alle 15:18 UTC;
- destinazione: `/root/Desktop/DIB/data/external/ncsu_sample/sample.zip`;
- dimensione: 498.170.708 byte (`Last-Modified` 27 set 2024); sha256 `10143e349c02c35e9a347cfd7d747107c4867f7cc0a64435cd0df0a2c75dcd11`;
- licenza: la pagina non ne dichiara nessuna.

Lo zip non è stato estratto. Contiene 51 catture (1,50 GB non compressi, dal 28 gen 2021 18:46 al 29 gen 2021 19:16, circa 24 h) e `sample/device_mappings.csv` (15 righe: etichetta e IP LAN). **Le catture sono in formato pcapng** nonostante l'estensione `.pcap`. Non ho scaricato altro (i due `device_mappings.csv` completi da 4 KB sono disponibili ma esclusi).

**Script.** `analysis_fs/ncsu_overlap.py`, eseguito con `python3 -I` e solo `struct`, senza parser di terze parti; ~21 s. Ipotesi e criterio di falsificazione sono nel docstring, scritti prima dell'esecuzione. Un dispositivo conta come osservato solo se nelle catture c'è almeno un pacchetto IPv4 tra il suo IP e un indirizzo globale. NCSU conta come **un** sito indipendente in più. Output per etichetta fuori dalla repo, perché la licenza non è dichiarata: `/root/Desktop/DIB/outputs/tnsm_hd/ncsu_overlap.csv`.

**Mapping.** `canonical_device_name` e `label_mapping_v16.csv` non sono stati toccati.
- *stretto*: `canonical_device_name(label)` deve coincidere con uno dei 119 tipi. Nessuna etichetta NCSU colpisce la tabella di alias: verificato importando la funzione, l'output coincide con la sola normalizzazione di `profiles.py:143-144`.
- *per famiglia*: tabella manuale `FAMILY` nello script, per nome commerciale; generazione e modello non sono verificati.

| Etichetta NCSU | Traffico globale | Stretto | Per famiglia | h prima → dopo |
|---|---|---|---|---|
| Ring Doorbell | sì | ring-doorbell | ring-doorbell | 4 → 5 |
| Samsung SmartThings Hub 2 | sì | — | smartthings | 4 → 5 |
| Amazon Echo Plus 2nd Gen | sì | — | echoplus | 2 → 3 |
| Nestcam | sì | — | nestcamera (YT) | 1 → 2 |
| Google OnHub | sì | — | googleonhub (YT) | 1 → 2 |
| LG Smart TV | sì | — | lgtv-wired | 1 → 2 |
| Amcrest Camera | sì | — | amcrest-cam-wired | 1 → 2 |
| Amazon Echo Look | sì | — | — (nessun tipo) | — |
| Smart WiFi Plug (2 dispositivi) | sì | — | — (vendor ignoto) | — |
| Foscam | **no** (0 pacchetti con peer globale) | — | — | — |

Esclusi perché non IoT: Desktop, Router, Motog phone, Pixel 2 Phone. I due "Smart WiFi Plug" hanno la stessa etichetta e lo script ne somma i pacchetti. [?] `Nestcam` potrebbe corrispondere anche a `dropcam` (UNSW, tramite l'alias `nest-cam`): non unito.

**Esito.**
- Stretto: 1 tipo guadagna un sito (ring-doorbell, h = 5).
- Per famiglia: 7 tipi guadagnano un sito; istogramma di h dopo {2: 4, 3: 1, 5: 2}.
- In entrambi i casi **al più 2 tipi raggiungono h = 5 e nessuno h ≥ 7**: il criterio di falsificazione dichiarato non scatta.
- La previsione accessoria "al più 6 tipi guadagnano un sito" era sbagliata: con il mapping per famiglia sono 7.

**Lettura [D].** Con NCSU, K = 2 a f_s = 0,30 diventa coperto su 1 tipo (stretto) o 2 tipi (per famiglia), ring-doorbell e smartthings, presenti in tutti e 5 i siti indipendenti. K = 3 a f_s resta scoperto. Il campione copre circa 24 h di un solo anno (2021), quindi la raccolta completa 2020/2021 potrebbe aggiungere tipi ma non siti: NCSU resta un laboratorio.

### 2.7 Quale meccanismo produce i "sei tipi comuni" del paper

Il paper (fuori repo, solo letto) dice "only six device types are common to all three deployments" a `/root/Desktop/DIB_reframe/docs/main.tex:622` (sha256 `bf61868d…`, 853 righe; nella copia `DIB_clean/docs/main.tex` è la riga 627). I tre deployment sono Mon(IoT)r US, Mon(IoT)r UK e YourThings (`main.tex:543`, Tabella `tab:threelab`).

**Produce i sei tipi `docs/label_mapping_v16.csv`, non `canonical_device_name`** [C]:
- `code/scripts/moniotr_cross_lab.py:237-249` (`load_label_mapping`) legge il CSV e costruisce {etichetta grezza → canonico} per entrambe le colonne. `:187` applica `label_map.get(device, device)` alle etichette grezze, e `canonical_device_name` non interviene.
- `:111` scrive `aligned_device_types = sorted(set(label_map.values()))` nel manifest. I sei tipi sono quindi **per costruzione le righe del file**, non un conteggio fatto sui dati.
- `results/three_lab_loo/manifest.json` registra `aligned_device_types` = google-home-mini, insteon-hub, philips-hue, ring-doorbell, roku-tv, smartthings e `label_mapping_sha256` = `ff16da15…`, che coincide con `docs/label_mapping_v16.csv` e `results/three_lab_loo/label_mapping_v16.csv`.

Gli stessi sei tipi vengono usati da `v28_matched_ablation.py:21`, `pareto_frontier.py:97` e `union_ranked_budget.py:106`. Questi script cercano il file in `experiments/30_three_lab_loo/label_mapping_v16.csv`, un percorso **assente** dalla repo (il file è in `docs/` e in `results/three_lab_loo/`). `docs/data_provenance.md:123` cita invece `data/label_mapping_v16.csv`, assente anche quello. Il percorso esiste invece fuori repo, in `/root/Desktop/DIB_reframe/reproducibility/experiments/30_three_lab_loo/label_mapping_v16.csv`, con lo stesso hash `ff16da15…`: gli script girano nel layout di `DIB_reframe/reproducibility`, non in questa repo. Lo segnalo senza correggere.

**Quanto cambia h_d** (dati sul disco, `hd_union_by_type.csv` fuori repo):

| Tipo | h su US/UK/YT con v16 | con il solo `canonical_device_name` | h indipendente nell'unione (con UNSW): v16 / canonico |
|---|---|---|---|
| philips-hue, ring-doorbell, smartthings | 3 | 3 | 4 / 4 |
| google-home-mini, insteon-hub, roku-tv | 3 | **2** (YT resta un tipo separato: `googlehomemini`, `insteonhub`, `rokutv`) | 3 / 2 |

Con il solo mapping canonico i tipi comuni ai tre deployment sarebbero **3, non 6**. Il file v16 coincide con l'insieme dei tipi presenti in US, UK e YT dopo la sola rimozione di trattini e maiuscole. L'unica altra coppia di quel genere, `googlehome` (YT) / `google-home` (Mon(IoT)r), è esclusa correttamente perché `google-home` è solo a UK. Per K ≤ 3 la differenza non cambia la copertura al margine (h = 2 e h = 3 coprono entrambi K = 1 e non K = 3). A f_s cambia K = 1: h = 3 lo copre, h = 2 no. Da qui i 4 contro 7 tipi della tabella in 2.3.

### 2.5 Manifest

Python 3.10.13, Ubuntu 22.04.3, 2 × AMD EPYC 7313 (16 thread), 64 GiB. Nessun seed in `hd_union.py` e `ncsu_overlap.py` (deterministici). `hd_heterogeneity.py` usa i seed UNSW 0–19. Hash degli input nella tabella 2.1. Il file per tipo con le etichette (`/root/Desktop/DIB/outputs/tnsm_hd/hd_union_by_type.csv`) resta **fuori dalla repo**, perché elenca i dispositivi Mon(IoT)r (data sharing agreement, `docs/work/PRE_PUBLICATION_CHECKLIST.md`).
