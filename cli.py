import pprint
import re
import requests
import click
import json

from api import create_app

clean_tags = re.compile('<.*?>')
body_tag = re.compile('<body(?:(?:.|\n)*?)>((?:.|\n)*?)</body>')

app = None


def remove_html_tags(text):
    return re.sub(clean_tags, ' ', text)


def extract_body(text):
    match = re.search(body_tag, text)
    if match:
        return match.group(1)
    return text


def load_elastic_conf(index_name, rebuild=False):
    url = '/'.join([app.config['ELASTICSEARCH_URL'], index_name])
    res = None
    print(url)
    try:
        if rebuild:
            res = requests.delete(url)
        with open(f'{app.config["ELASTICSEARCH_CONFIG_DIR"]}/_global.conf.json', 'r') as _global:
            global_settings = json.load(_global)

            with open(f'{app.config["ELASTICSEARCH_CONFIG_DIR"]}/{index_name}.conf.json', 'r') as f:
                payload = json.load(f)
                payload["settings"] = global_settings
                print("UPDATE INDEX CONFIGURATION:", url)
                res = requests.put(url, json=payload)
                assert str(res.status_code).startswith("20")

    except FileNotFoundError as e:
        print(str(e))
        print("conf not found", flush=True, end=" ")
    except Exception as e:
        print(res.text, str(e), flush=True, end=" ")
        raise e

def obtain_metadata(completeResponse, metadataDts):
    """
    Extract metadata from the DTS response
    """
    metadata = {}
    sources = [
        {"name": "data_bnf", "ext": "data.bnf.fr"},
        {"name": "dbpedia", "ext": "dbpedia.org"},
        {"name": "idref", "ext": "idref.fr"},
        {"name": "catalogue_bnf", "ext": "catalogue.bnf.fr"},
        {"name": "wikidata", "ext": "wikidata"},
        {"name": "wikipedia", "ext": "wikipedia"},
        {"name": "thenca", "ext": "thenca"},
        {"name": "hal", "ext": "hal"},
        {"name": "benc", "ext": "koha"}]
    for namespace in completeResponse["@context"]:
        if "html" in completeResponse["@context"][namespace]:
            htmlnamespace = namespace
        elif 'dc/elements' in completeResponse["@context"][namespace]:
            dcnamespace = namespace
    metadata["title"] = metadataDts["title"]
    metadata["title_rich"] = metadataDts["dts:extensions"]["{0}:h1".format(htmlnamespace)]
    metadata["author"] = metadataDts["dts:extensions"]["{0}:creator".format(dcnamespace)]
    metadata["date"] = metadataDts["dts:dublincore"]["dct:date"]
    metadata["genre"] = metadataDts["dts:extensions"]["{0}:description".format(dcnamespace)]

    return metadata

def make_cli(env='dev'):
    """ Creates a Command Line Interface for everydays tasks

    :return: Click groum
    """

    @click.group()
    def cli():
        global app
        app = create_app(env)
        app.all_indexes = f"{app.config['DOCUMENT_INDEX']},{app.config['COLLECTION_INDEX']}"

    @click.command("search")
    @click.argument('query')
    @click.option('--indexes', required=False, default=None, help="index names separated by a comma")
    @click.option('-t', '--term', is_flag=True, help="use a term instead of a whole query")
    def search(query, indexes, term):
        """
        Perform a search using the provided query. Use --term or -t to simply search a term.
        """
        if term:
            body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "query_string": {
                                    "query": query,
                                }
                            }
                        ]
                    },
                }
            }
        else:
            body = query

        config = {
            "index": indexes if indexes else app.all_indexes,
            "body": body
        }

        result = app.elasticsearch.search(**config)
        print("\n", "=" * 12, " RESULT ", "=" * 12)
        pprint.pprint(result)

    @click.command("update-conf")
    @click.option('--indexes', default=None, help="index names separated by a comma")
    @click.option('--rebuild', is_flag=True, help="truncate the index before updating its configuration")
    def update_conf(indexes, rebuild):
        """
        Update the index configuration and mappings
        """
        indexes = indexes if indexes else app.all_indexes
        for name in indexes.split(','):
            print(name)
            load_elastic_conf(name, rebuild=rebuild)

    @click.command("delete")
    @click.option('--indexes', required=True, help="index names separated by a comma")
    def delete_indexes(indexes):
        """
        Delete the indexes
        """
        indexes = indexes if indexes else app.all_indexes
        for name in indexes.split(','):
            url = '/'.join([app.config['ELASTICSEARCH_URL'], name])
            res = None
            try:
                res = requests.delete(url)
            except Exception as e:
                print(res.text, str(e), flush=True, end=" ")
                raise e

    @click.command("index")
    @click.option('--root_collection', required=True, default="all", help="give the dts root collection")
    def index(root_collection):
        """
        Rebuild the elasticsearch indexes
        """

        # BUILD THE METADATA DICT FROM THE GITHUB TSV FILE

        _DTS_URL = app.config['DTS_URL']
        metadata = {}
        # INDEXATION DES DOCUMENTS
        try:
            _index_name = app.config['DOCUMENT_INDEX']

            response_collection = requests.get(f'{_DTS_URL}/collections?id={root_collection}').json()
            list_wait_collections = []
            listDoc = []
            metadata = {}
            for member in response_collection["member"]:
                if member["@type"] == "Collection":
                    list_wait_collections.append(member["@id"])
                else:
                    listDoc.append(member["@id"])
                    # Ajout des metadonnées ici
                    metadata[member["@id"]] = {"title": member["title"]}

            while list_wait_collections != []:
                response_collection = requests.get(f'{_DTS_URL}/collections?id={list_wait_collections[0]}').json()
                for member in response_collection["member"]:
                    if member["@type"] == "Collection":
                        list_wait_collections.append(member["@id"])
                    else:
                        listDoc.append(member["@id"])
                        # Ajout des metadonnées ici
                        metadata[member["@id"]] = obtain_metadata(response_collection, member)

                list_wait_collections.pop(0)
            for miroir_id in listDoc:
                response = requests.get(f'{_DTS_URL}/document?id={miroir_id}')

                content = extract_body(response.text)
                content = remove_html_tags(content)

                app.elasticsearch.index(
                    index=_index_name,
                    id=miroir_id,
                    body={
                        "content": content,
                        "metadata": metadata[miroir_id]
                    })

        except Exception as e:
            print('Indexation error: ', str(e))

        # INDEXATION DES COLLECTIONS
        try:
            _index_name = app.config['COLLECTION_INDEX']
            # app.elasticsearch.index(index=_index_name, id=encpos_id,  body={})
        except Exception as e:
            print('Indexation error: ', str(e))

    cli.add_command(delete_indexes)
    cli.add_command(update_conf)
    cli.add_command(index)
    cli.add_command(search)
    return cli

