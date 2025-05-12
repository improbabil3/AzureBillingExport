# Azure Billing Export

Strumento per recuperare le informazioni di fatturazione da Azure Cost Management API e salvarle in formato CSV.

## Caratteristiche

- Recupera i dati di fatturazione da Azure Cost Management API
- Supporta sia l'autenticazione tramite bearer token che tramite client credentials
- Esporta i dati in formato CSV con separatore punto e virgola
- Supporta la segmentazione automatica delle query per periodi superiori a un anno
- Formattazione dei numeri in formato europeo (virgola come separatore decimale)

## Requisiti

- Python 3.8 o superiore
- Account Azure con accesso alle informazioni di fatturazione
- Accesso alla sottoscrizione Azure e al Resource Group di interesse

## Project Structure

```
azure-billing-export
├── src
│   ├── api
│   │   ├── __init__.py
│   │   └── azure_client.py
│   ├── config
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── data_processor.py
│   │   └── export.py
│   ├── utils
│   │   ├── __init__.py
│   │   ├── logging_config.py
│   │   └── path_utils.py
│   ├── __init__.py
│   └── main.py
├── tests
│   ├── __init__.py
│   ├── test_azure_client.py
│   ├── test_data_processor.py
│   └── test_export.py
├── .env.example
├── .gitignore
├── requirements.txt
├── setup.py
└── README.md
```

## Installazione

1. Clona il repository
2. Crea un ambiente virtuale Python:

```bash
# Creazione ambiente virtuale
python -m venv C:\Path\To\azure-billing-export\venv

# Attivazione ambiente virtuale (Windows)
C:\Path\To\azure-billing-export\venv\Scripts\Activate.ps1
```

3. Installa le dipendenze:

```bash
pip install -r requirements.txt
```

4. Crea un file `.env` nella radice del progetto con le tue configurazioni (puoi usare `.env.example` come riferimento)

## Configurazione

Puoi configurare l'applicazione in diversi modi:

1. Tramite file `.env` (vedi `.env.example`)
2. Tramite variabili d'ambiente del sistema
3. Tramite parametri da riga di comando (hanno la precedenza)

## Utilizzo

### Autenticazione con Bearer Token

```bash
python -m src.main --auth-type bearer_token --bearer-token "YOUR_BEARER_TOKEN" --subscription-id "YOUR_SUBSCRIPTION_ID" --resource-group "YOUR_RESOURCE_GROUP" --services "SERVICE_NAME_1" "SERVICE_NAME_2" --from-date "2024-01-01" --to-date "2024-12-31" --output "path/to/output.csv"
```

### Autenticazione con Client Credentials

```bash
python -m src.main --auth-type client_credentials --tenant-id "YOUR_TENANT_ID" --client-id "YOUR_CLIENT_ID" --client-secret "YOUR_CLIENT_SECRET" --subscription-id "YOUR_SUBSCRIPTION_ID" --resource-group "YOUR_RESOURCE_GROUP" --services "SERVICE_NAME_1" "SERVICE_NAME_2" --from-date "2024-01-01" --to-date "2024-12-31" --output "path/to/output.csv"
```

### Parametri disponibili

- `--auth-type`: Tipo di autenticazione (`bearer_token` o `client_credentials`)
- `--bearer-token`: Token di accesso per autenticazione diretta
- `--tenant-id`: ID del tenant Azure (per client credentials)
- `--client-id`: ID del client Azure (per client credentials)
- `--client-secret`: Secret del client Azure (per client credentials)
- `--subscription-id`: ID della sottoscrizione Azure
- `--resource-group`: Nome del gruppo di risorse
- `--services`: Lista di nomi o ID dei servizi di cui recuperare i costi
- `--from-date`: Data di inizio nel formato YYYY-MM-DD
- `--to-date`: Data di fine nel formato YYYY-MM-DD
- `--output`: Percorso del file CSV di output

## Formato del file CSV di output

Il file CSV generato avrà il seguente formato:

```
Date;ResourceName;CostUSD;CostEUR
2024-03-01;france-gpt4;4859,63;4479,75
2024-04-01;france-gpt4;3509,84;3241,30
...
```

## Note

- Se il periodo indicato è superiore all'anno, lo strumento effettuerà automaticamente più chiamate API e aggrega i risultati
- I servizi possono essere specificati sia come nomi che come URL completi di risorsa

## Testing

To run the tests, use the following command:

```bash
python -m unittest discover -s tests
```

This will execute all unit tests defined in the `tests` directory.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.