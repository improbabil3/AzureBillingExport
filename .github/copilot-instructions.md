# GitHub Copilot Instructions

## Configurazione del Progetto Backend in Python su Windows

### 1. Ambiente di Sviluppo

Il progetto sarà sviluppato su un sistema operativo **Windows**. Tutte le configurazioni e i comandi dovranno essere compatibili con questo ambiente, utilizzando **PowerShell** per l'esecuzione dei comandi.

### 2. Struttura del Progetto

Il progetto sarà principalmente un **backend in Python**, con la possibilità di integrare componenti frontend in futuro. La struttura del progetto deve essere organizzata per facilitare estensioni o modifiche future.

### 3. Gestione dei Percorsi

* Utilizzare **percorsi assoluti** anziché relativi per garantire coerenza e affidabilità.

### 4. Installazione dei Pacchetti Necessari

Prima di generare o eseguire codice, assicurarsi che tutti i pacchetti Python richiesti siano installati. Utilizzare un **ambiente virtuale** per gestire le dipendenze del progetto.

#### Creazione dell'Ambiente Virtuale

```powershell
# Creazione di un ambiente virtuale nella directory del progetto
python -m venv C:\Percorso\Assoluto\al\Progetto\venv

# Attivazione dell'ambiente virtuale
C:\Percorso\Assoluto\al\Progetto\venv\Scripts\Activate.ps1
```

#### Installazione dei Pacchetti

```powershell
# Aggiornamento di pip
python -m pip install --upgrade pip

# Installazione dei pacchetti da requirements.txt
pip install -r C:\Percorso\Assoluto\al\Progetto\requirements.txt
```

### 5. Chiamate API

Il progetto interagirà con **API specifiche** che verranno definite durante l'implementazione. Assicurarsi di:

* Gestire errori e timeout
* Utilizzare librerie come `requests` o `httpx`
* Proteggere eventuali credenziali

### 6. Esecuzione e Verifica del Codice

Dopo aver generato il codice:

* Eseguirlo nel terminale PowerShell
* Verificare il risultato nella **finestra di output**
* Analizzare eventuali errori o warning

### 7. Best Practices

#### Gestione dei Percorsi (in Python)

```python
from pathlib import Path

base_dir = Path("C:/Percorso/Assoluto/al/Progetto")
file_path = base_dir / "subdir" / "file.txt"
```

#### Variabili d'Ambiente

Utilizzare `os.environ` o librerie come `python-dotenv` per leggere configurazioni sensibili:

```python
import os
api_key = os.getenv("API_KEY")
```

#### Logging

```python
import logging
logging.basicConfig(level=logging.INFO)
logging.info("Avvio dell'applicazione")
```

Prevedere quattro colori per il logging:
I messaggi di errore (come problemi di configurazione o errori di esecuzione) visualizzati in rosso
I messaggi di successo (come il recupero delle metriche) visualizzati in verde
I messaggi di warning visualizzati in giallo
Le informazioni generali (come il conteggio dei risultati) visualizzate in blu

#### Testing

Utilizzare `unittest` o `pytest` per scrivere test automatizzati:

```python
import unittest

class TestAPI(unittest.TestCase):
    def test_status_code(self):
        self.assertEqual(200, 200)

if __name__ == '__main__':
    unittest.main()
```

---

Seguire queste istruzioni guiderà GitHub Copilot nella generazione di un progetto backend Python efficiente, modulare, compatibile con Windows e facilmente estendibile con un frontend.
