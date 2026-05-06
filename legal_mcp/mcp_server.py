import os
from typing import Any, Dict, List, Optional

from . import es_client, get_settings, logger, mcp

settings = get_settings()

INDEX_NAME = settings.index.name


@mcp.tool()
async def search_laws(
    query: str,
    era: Optional[str] = None,
    law_type: Optional[str] = None,
    limit: int = 5,
) -> str:
    """
    Search for Japanese laws and regulations based on a natural language query.

    Args:
        query: The search terms (e.g., "Constitution", "Tax", "Data Privacy").
        era: Optional filter for the Japanese Era (e.g., "Showa", "Heisei", "Reiwa").
        law_type: Optional filter for law type (e.g., "Act", "CabinetOrder", "MinisterialOrdinance").
        limit: Maximum number of results to return (default is 5).
    """
    logger.info(
        f"Searching for: '{query}' (Era: {era}, Type: {law_type}, Limit: {limit})"
    )

    # Build search body
    search_body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "meta.LawTitle_Kanji^3",
                                "meta.LawTitle_Kana",
                                "meta.LawTitle_Abbrev^2",
                                "meta.LawNum",
                                "legal_content.sentence",
                                "legal_content.article_title",
                                "legal_content.article_caption",
                                "legal_content.enact_statement",
                                "legal_content.appdx_table_title",
                                "legal_content.fig_struct_title",
                            ],
                            "type": "best_fields",
                        }
                    }
                ],
                "filter": [],
            }
        },
        "highlight": {
            "fields": {
                "legal_content.sentence": {
                    "fragment_size": 200,  # whole fragment size
                    "number_of_fragments": 1,  # only return the most relevant one
                    "no_match_size": 200,  # if nothing matches, return the first 200 characters
                },
                "legal_content.article_title": {
                    "fragment_size": 150,
                    "number_of_fragments": 1,
                    "no_match_size": 150,
                },
                "legal_content.article_caption": {
                    "fragment_size": 150,
                    "number_of_fragments": 1,
                    "no_match_size": 150,
                },
            },
            "pre_tags": ["<em>"],
            "post_tags": ["</em>"],
            "encoder": "html",
        },
    }

    if era:
        search_body["query"]["bool"]["filter"].append({"term": {"meta.Era": era}})
    if law_type:
        search_body["query"]["bool"]["filter"].append(
            {"term": {"meta.LawType": law_type}}
        )

    try:
        logger.debug(f"Executing search with body: {search_body}")
        response = es_client.search(index=INDEX_NAME, body=search_body, size=limit)
        hits = response["hits"]["hits"]
        logger.info(f"Search returned {len(hits)} results")

        if not hits:
            return "No matching laws found."

        results = []
        for hit in hits:
            source = hit["_source"]
            meta = source.get("meta", {})
            title = meta.get("LawTitle_Kanji", "Unknown Title")
            law_num = meta.get("LawNum", "Unknown Num")
            law_id = source.get("law_id")

            # Extract snippet from highlight if available, otherwise use content
            highlight = hit.get("highlight", {})

            # Try to get the best highlight from multiple fields
            snippet = None
            for field in [
                "legal_content.sentence",
                "legal_content.article_title",
                "legal_content.article_caption",
            ]:
                if field in highlight:
                    snippet_text = highlight[field][0]
                    # Remove highlight tags
                    snippet = snippet_text.replace("<em>", "").replace("</em>", "")
                    break

            # Fallback to content if no highlight available
            if not snippet:
                content = source.get("legal_content", {})
                sentence = content.get("sentence", "")
                snippet = (
                    sentence[:200] + "..." if sentence else "No content available."
                )

            results.append(
                f"ID: {law_id}\n"
                f"Title: {title}\n"
                f"Law Number: {law_num}\n"
                f"Snippet: {snippet}\n"
                f"---"
            )

        return "\n\n".join(results)

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return f"An error occurred during search: {str(e)}"


@mcp.tool()
async def get_law_by_id(law_id: str) -> str:
    """
    Retrieve the full details of a specific law by its ID.

    Args:
        law_id: The unique identifier of the law (e.g., '101AC0000000001').
    """
    logger.info(f"Retrieving law: {law_id}")

    try:
        logger.info(f"Retrieving law by ID: {law_id}")
        response = es_client.get(index=INDEX_NAME, id=law_id)
        logger.info(f"Successfully retrieved law: {law_id}")
        source = response["_source"]

        meta = source.get("meta", {})
        content = source.get("legal_content", {})

        # Format the output
        output = [
            f"# {meta.get('LawTitle_Kanji', 'Unknown Law')}",
            f"ID: {law_id}",
            f"Law Number: {meta.get('LawNum')}",
            f"Type: {meta.get('LawType')}",
            f"Era: {meta.get('Era')} {meta.get('Year')}",
            "\n## Legal Content\n",
        ]

        # Group sentences by type if available
        for field in [
            "article_title",
            "article_caption",
            "sentence",
            "enact_statement",
        ]:
            if field in content and content[field]:
                output.append(f"### {field.replace('_', ' ').title()}")
                output.append(content[field])
                output.append("")

        # Note if raw JSON was omitted
        raw = source.get("raw_full_json", {})
        if isinstance(raw, dict) and raw.get("omitted"):
            output.append(
                "\n*Note: Full raw JSON structure was omitted for this document due to size.*"
            )

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Retrieval error: {str(e)}")
        return f"Law with ID '{law_id}' not found or error occurred: {str(e)}"


@mcp.tool()
async def get_cluster_status() -> Dict[str, Any]:
    """Get the current health and status of the legal document database."""
    logger.info("Checking cluster status")
    try:
        health = es_client.cluster.health()
        count = es_client.count(index=INDEX_NAME)["count"]
        logger.info(f"Cluster status: {health['status']}, Documents: {count}")
        return {
            "status": health["status"],
            "nodes": health["number_of_nodes"],
            "document_count": count,
            "index_name": INDEX_NAME,
        }
    except Exception as e:
        logger.error(f"Failed to get cluster status: {str(e)}")
        return {"error": str(e)}


@mcp.tool()
async def get_raw_json_by_id(law_id: str) -> Dict[str, Any]:
    """
    Retrieve the complete raw_full_json data for a specific law by its ID.

    This returns the full JSON structure including all nested fields that may
    be omitted in the regular search results due to size constraints.

    Args:
        law_id: The unique identifier of the law (e.g., '101AC0000000001').

    Returns:
        Dict containing the raw_full_json data or error information.
    """
    logger.info(f"Retrieving raw JSON for law: {law_id}")

    try:
        # Fetch the document from Elasticsearch
        response = es_client.get(index=INDEX_NAME, id=law_id)
        source = response["_source"]

        # Extract raw_full_json
        raw_full_json = source.get("raw_full_json", {})

        if not raw_full_json:
            logger.warning(f"No raw_full_json found for law ID: {law_id}")
            return {
                "law_id": law_id,
                "error": "raw_full_json field is empty or not available",
                "meta": source.get("meta", {}),
            }

        # Check if it was marked as omitted
        if isinstance(raw_full_json, dict) and raw_full_json.get("omitted"):
            logger.warning(f"raw_full_json was omitted for law ID: {law_id}")
            return {
                "law_id": law_id,
                "error": "raw_full_json was omitted due to size constraints",
                "note": "This document's full JSON structure was not stored",
                "meta": source.get("meta", {}),
            }

        logger.info(f"Successfully retrieved raw_full_json for law: {law_id}")
        logger.debug(
            f"raw_full_json type: {type(raw_full_json)}, keys: {list(raw_full_json.keys()) if isinstance(raw_full_json, dict) else 'N/A'}"
        )

        # Return the complete raw JSON along with metadata
        return {
            "law_id": law_id,
            "meta": source.get("meta", {}),
            "raw_full_json": raw_full_json,
        }

    except Exception as e:
        logger.error(f"Failed to retrieve raw JSON for law ID '{law_id}': {str(e)}")
        return {"law_id": law_id, "error": f"Law not found or error occurred: {str(e)}"}
