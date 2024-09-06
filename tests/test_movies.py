from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from tests.mock_data import MOCK_MOVIES
from app.routers.movies import index_movies


client = TestClient(app)

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

@patch("app.routers.movies.get_es_client")  # Mock Elasticsearch client
@patch("app.routers.movies.requests.get")   # Mock external API call
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