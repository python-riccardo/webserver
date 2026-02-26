import yaml

try:
    with open('server_config.yaml', 'r', encoding='utf-8') as file:
        dati = yaml.safe_load(file)
        for route in dati["routes"]:
            if route["file"] == "index.html":
                route["file"] = "aaaaaaaa"
except FileNotFoundError:
    print("Il file non esiste!")

try:
    with open('server_config.yaml', 'w', encoding='utf-8') as file:
        yaml.safe_dump(dati, file, indent=2, allow_unicode=True)
except FileNotFoundError:
    print("Il file non esiste!")