import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from tests.mock_data import MOCK_MOVIES
from app.utils.elastic import get_es_client


client = TestClient(app)
es = get_es_client()

INDEX_NAME = "movies_test"

@patch("app.routers.movies.get_es_client")
@patch("app.routers.movies.requests.get")
def test_index_movies(mock_get, mock_es_client, caplog):
    mock_get.return_value.json.return_value = MOCK_MOVIES

    # Mock the Elasticsearch client and its methods
    mock_es = mock_es_client.return_value
    mock_es.indices.delete.return_value = None
    mock_es.indices.create.return_value = None
    mock_es.index.return_value = None

    response = client.post("/movies/index/")

    assert response.status_code == 200
    data = response.json()

    # 2 pages * 10 movies per page
    assert data["indexed"] == 20

    assert mock_es.indices.delete.called
    assert mock_es.indices.create.called
    assert mock_es.index.call_count

@patch("app.routers.movies.get_es_client")
@patch("app.routers.movies.requests.get")
def test_index_movies_logging(mock_get, mock_es_client, caplog):
    mock_get.return_value.json.return_value = MOCK_MOVIES

    mock_es = mock_es_client.return_value
    mock_es.indices.delete.return_value = None
    mock_es.indices.create.return_value = None
    mock_es.index.return_value = None

    with caplog.at_level("INFO"):  # Use caplog to capture logs
        response = client.post("/movies/index/")
    
    assert "Starting movie indexing process" in caplog.text
    assert "Fetching movies from page 1" in caplog.text
    assert "Deleting existing index" in caplog.text
    assert "Creating new index" in caplog.text

@patch("app.routers.movies.get_es_client")
@patch("app.routers.movies.requests.get")
def test_index_movies_unexpected_error(mock_get, mock_es_client, caplog):
    mock_get.side_effect = Exception("Test Exception")
    
    with caplog.at_level("ERROR"):
        response = client.post("/movies/index/")

    assert "An unexpected error occurred during the indexing process" in caplog.text

    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected error occurred"}

def seed_elasticsearch():
    mapping = {
        "mappings": {
            "properties": {
                "Title": {"type": "text"},
                "Year": {"type": "integer"}
            }
        }
    }

    es.indices.delete(index=INDEX_NAME, ignore=[400, 404])
    es.indices.create(index=INDEX_NAME, body=mapping)

    for movie in MOCK_MOVIES["data"]:
        es.index(index=INDEX_NAME, document=movie)

    # This ensures data is available for search after seeding. "indexing lag"
    es.indices.refresh(index=INDEX_NAME)  

def clean_elasticsearch():
    es.indices.delete(index=INDEX_NAME, ignore=[400, 404])

@pytest.fixture(scope="function", autouse=True)
def setup_and_teardown():
    seed_elasticsearch()
    yield
    clean_elasticsearch()

@patch("app.routers.movies.INDEX_NAME", new=INDEX_NAME)
def test_search_by_title():
    response = client.get("/movies/search/?title=antman")
    assert response.status_code == 200
    movies = response.json()
    assert len(movies) == 1
    assert movies[0]["Title"] == "The Antman"

@patch("app.routers.movies.INDEX_NAME", new=INDEX_NAME)
def test_search_by_year():
    response = client.get("/movies/search/?year=2015")
    assert response.status_code == 200
    movies = response.json()
    assert len(movies) == 2
    assert movies[0]["Title"] == "Maze Runner: The Scorch Trials"

@patch("app.routers.movies.INDEX_NAME", new=INDEX_NAME)
def test_search_by_title_and_year():
    response = client.get("/movies/search/?title=Maze Runner&year=2015")
    assert response.status_code == 200
    movies = response.json()
    
    # This time retrieved the only correct option.
    assert len(movies) == 1
    assert movies[0]["Title"] == "Maze Runner: The Scorch Trials"

@patch("app.routers.movies.INDEX_NAME", new=INDEX_NAME)
def test_no_movies_found():
    response = client.get("/movies/search/?title=NonExistentMovie")
    assert response.status_code == 404
    assert response.json() == {"detail": "No movies found"}

@patch("app.routers.movies.INDEX_NAME", new=INDEX_NAME)
def test_pagination():
    response = client.get("/movies/search/?title=Maze&page=1&size=1")
    assert response.status_code == 200
    movies = response.json()
    assert len(movies) == 1
    assert movies[0]["Title"] == "The Maze Runner"

    response = client.get("/movies/search/?title=Maze&page=2&size=1")
    assert response.status_code == 200
    movies = response.json()
    assert len(movies) == 1
    assert movies[0]["Title"] == "Into the Grizzly Maze"
