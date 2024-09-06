from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import requests
from app.utils.elastic import get_es_client
from app.utils.logging import get_logger
from functools import lru_cache

router = APIRouter()
logger = get_logger()

INDEX_NAME = "movies"

@router.post("/movies/index")
async def index_movies(substr: Optional[str] = Query(None, max_length=100, min_length=1)):
    """
    Index movies from an external API into Elasticsearch.
    
    Parameters:
        - substr: Optional substring to search for in movie titles.
    """

    es = get_es_client()
    page = 1
    movies = []
    total_pages = 1  # Default value to start

    logger.info(
        f"Starting movie indexing process for substring: {substr or 'All titles'}"
    )

    try:
        
        while page <= total_pages:
            url = f"https://jsonmock.hackerrank.com/api/moviesdata/search/?Title={substr or ''}&page={page}"
            logger.info(f"Fetching movies from page {page}")
            response = requests.get(url)
            data = response.json()

            if response.status_code != 200:
                logger.error(
                    f"Failed to fetch movies from page {page}, status code: {response.status_code}"
                )

            movies.extend(data.get("data", []))

            total_pages = data.get("total_pages", 1)

            page += 1

        logger.info(f"Deleting existing index {INDEX_NAME} in Elasticsearch")
        es.indices.delete(index=INDEX_NAME, ignore=[400, 404])

        logger.info(f"Creating new index {INDEX_NAME} in Elasticsearch")
        es.indices.create(index=INDEX_NAME)

        for movie in movies:
            es.index(index=INDEX_NAME, body=movie)

        logger.info(f"Successfully indexed {len(movies)} movies")
        return {
            "indexed": len(movies),
            "status": "success",
        }

    except Exception as e:
        logger.error("An unexpected error occurred during the indexing process: %s", str(e))
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
