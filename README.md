# miroir-app

Surcouche d’API Elasticsearch 6.8, pour la recherche.


## Installation ES

Installer [ES 6.8.14](https://www.elastic.co/fr/downloads/past-releases/elasticsearch-6-8-14).

Howto : [https://www.elastic.co/guide/en/elasticsearch/reference/6.8/zip-targz.html](https://www.elastic.co/guide/en/elasticsearch/reference/6.8/zip-targz.html)

**Install**

```
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-6.8.14.zip
unzip elasticsearch-6.8.14.zip
cd elasticsearch-6.8.14
```

**Run**

```
./bin/elasticsearch
```

**Configure**

[ICU Analysis Plugin](https://www.elastic.co/guide/en/elasticsearch/plugins/current/analysis-icu.html), Unicode support

```
sudo bin/elasticsearch-plugin install analysis-icu
```

## Indexer le corpus


## Lancer l’application

Run ```python flask_app.py``` to launch the api server

And use the following for offline commands:
```bash

> python cli.py --help

Usage: cli.py [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  delete       Delete the indexes
  index        Rebuild the elasticsearch indexes
  search       Perform a search using the provided query.
  update-conf  Update the index configuration and mappings

```
