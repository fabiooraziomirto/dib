# Checklist prima di rendere pubblica la repo

Raccoglie in un solo posto le cose da fare prima della pubblicazione. Aggiungere qui quanto emerge durante il lavoro.

- [ ] Rimuovere `docs/work/` (contiene `DIB_piano_completo.md`, copia di lavoro interna, e questa checklist).
- [ ] Titolo e autori (README, `pyproject.toml`, intestazioni).
- [ ] Licenza di osMUD: verificare compatibilità e riportarla dove si redistribuisce/si cita il testbed.
- [ ] Versione del jar TLC (`tla2tools.jar`) usata per i log in `formal/logs/` (i log citano TLC2 2026.05.26.235334, rev 4ba7d88): dichiararla.
- [ ] Autori della citazione (CITATION / README).
- [ ] `GET /health` del sito non è autenticato ed espone `reconcile.last_error` (repr troncato a 200 car., può contenere URL interni dell'evidence): rivedere insieme a mTLS (audit 06) e decidere se oscurarlo o proteggerlo.
- [ ] Mon(IoT)r: verificare il data sharing agreement prima di pubblicare i derivati. `analysis_fs/out/hd_by_device.csv` (già committato) contiene solo aggregati per tipo (h_d, etichette di sito US/UK/YT, tolleranze), ma elenca i nomi dei dispositivi dei laboratori Mon(IoT)r; controllare anche gli altri CSV di `analysis_fs/out/` con corpora `moniotr_*` (audit 00).
