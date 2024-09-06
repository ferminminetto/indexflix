from elasticsearch import Elasticsearch

# TODO: Just use an env variable
es = Elasticsearch("http://elasticsearch:9200")

def get_es_client():
    return es