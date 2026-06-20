"""Utilidades de recuperacion de contexto construidas sobre Chroma."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
import unicodedata

import chromadb

from f1_rag.config import AppConfig
from f1_rag.embeddings import OpenAIEmbedder
from f1_rag.nl2sql import ResolvedEntity, SqlIntentHint


@dataclass(slots=True)
class RetrievedChunk:
    """Fragmento recuperado junto con sus metadatos de trazabilidad."""

    document_id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None


def embed_query_text(query: str, config: AppConfig | None = None) -> list[float]:
    """Genera un vector de embedding para una consulta en lenguaje natural."""

    app_config = config or AppConfig.from_env()
    embedder = OpenAIEmbedder(app_config)
    return embedder.embed_query(query)


def search_similar_chunks(
    query_embedding: list[float],
    config: AppConfig | None = None,
    top_k: int | None = None,
    query_text: str = "",
    intent_hint: SqlIntentHint | None = None,
    resolved_entities: list[ResolvedEntity] | None = None,
) -> list[RetrievedChunk]:
    """Busca en Chroma los fragmentos indexados mas relevantes."""

    if not query_embedding:
        raise ValueError("El embedding de la consulta no puede estar vacio.")

    app_config = config or AppConfig.from_env()
    effective_top_k = top_k or app_config.retrieval_top_k
    if effective_top_k <= 0:
        raise ValueError("top_k debe ser mayor que cero.")
    overfetch_k = max(effective_top_k, min(effective_top_k * 4, 20))
    metadata_filter = build_metadata_prefilter(
        query_text=query_text,
        intent_hint=intent_hint,
        resolved_entities=resolved_entities or [],
    )

    try:
        client = chromadb.HttpClient(
            host=app_config.chroma_host,
            port=app_config.chroma_port,
            ssl=app_config.chroma_ssl,
        )
        collection = client.get_collection(name=app_config.chroma_collection)
    except Exception as exc:  # pragma: no cover - guardia de cliente / transporte
        raise RuntimeError(f"No fue posible conectarse a la coleccion de Chroma: {exc}") from exc

    result = _query_collection(
        collection=collection,
        query_embedding=query_embedding,
        n_results=overfetch_k,
        where=metadata_filter,
    )
    ids = result.get("ids", [[]])[0]

    # Si el prefiltro fue demasiado estricto, completamos con una consulta abierta.
    if metadata_filter is not None and len(ids) < effective_top_k:
        fallback_result = _query_collection(
            collection=collection,
            query_embedding=query_embedding,
            n_results=overfetch_k,
            where=None,
        )
        result = _merge_query_results(result, fallback_result)

    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    retrieved_chunks: list[RetrievedChunk] = []
    for document_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
        retrieved_chunks.append(
            RetrievedChunk(
                document_id=document_id,
                text=text or "",
                metadata=metadata or {},
                distance=distance,
            )
        )

    reranked_chunks = rerank_retrieved_chunks(
        chunks=retrieved_chunks,
        query_text=query_text,
        intent_hint=intent_hint,
        resolved_entities=resolved_entities or [],
    )
    return reranked_chunks[:effective_top_k]


def build_metadata_prefilter(
    query_text: str,
    intent_hint: SqlIntentHint | None,
    resolved_entities: list[ResolvedEntity],
) -> dict[str, Any] | None:
    """Construye un prefiltro de metadata para Chroma cuando hay alta confianza."""

    conditions: list[dict[str, Any]] = []
    normalized_query = _normalize_text(query_text)

    race_entities = [entity for entity in resolved_entities if entity.entity_type == "race"]
    if len(race_entities) == 1:
        conditions.append({"race_name": race_entities[0].canonical_value})

    query_years = sorted({int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", normalized_query)})
    if len(query_years) == 1:
        conditions.append({"season_year": query_years[0]})

    driver_entities = [entity for entity in resolved_entities if entity.entity_type == "driver"]
    if len(driver_entities) == 1 and _driver_filter_is_helpful(intent_hint):
        conditions.append({"driver_name": driver_entities[0].display_name})

    constructor_entities = [entity for entity in resolved_entities if entity.entity_type == "constructor"]
    if len(constructor_entities) == 1 and _constructor_filter_is_helpful(intent_hint):
        conditions.append({"constructor_name": constructor_entities[0].display_name})

    analytical_table_filter = _build_analytical_table_prefilter(intent_hint)
    if analytical_table_filter is not None:
        conditions.append(analytical_table_filter)

    analytical_position_filter = _build_analytical_position_prefilter(
        query_text=query_text,
        intent_hint=intent_hint,
    )
    if analytical_position_filter is not None:
        conditions.append(analytical_position_filter)

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def format_retrieved_context(chunks: list[RetrievedChunk]) -> str:
    """Formatea los fragmentos recuperados en un bloque de contexto legible."""

    if not chunks:
        return "No se recupero contexto relevante."

    parts: list[str] = []
    for position, chunk in enumerate(chunks, start=1):
        header = f"[{position}] id={chunk.document_id}"
        if chunk.distance is not None:
            header += f" distance={chunk.distance:.6f}"

        metadata_preview = ", ".join(
            [
                f"table={chunk.metadata.get('table_name', 'unknown')}",
                f"content_type={chunk.metadata.get('content_type', 'unknown')}",
                f"row_index={chunk.metadata.get('row_index', 'unknown')}",
                f"source_file={chunk.metadata.get('source_file', 'unknown')}",
            ]
        )

        parts.append("\n".join([header, metadata_preview, chunk.text]))

    return "\n\n".join(parts)


def retrieve_context(
    query: str,
    config: AppConfig | None = None,
    top_k: int | None = None,
    intent_hint: SqlIntentHint | None = None,
    resolved_entities: list[ResolvedEntity] | None = None,
) -> list[RetrievedChunk]:
    """Wrapper conveniente que combina embedding de consulta y busqueda vectorial."""

    app_config = config or AppConfig.from_env()
    query_embedding = embed_query_text(query=query, config=app_config)
    return search_similar_chunks(
        query_embedding=query_embedding,
        config=app_config,
        top_k=top_k,
        query_text=query,
        intent_hint=intent_hint,
        resolved_entities=resolved_entities,
    )


def rerank_retrieved_chunks(
    chunks: list[RetrievedChunk],
    query_text: str,
    intent_hint: SqlIntentHint | None = None,
    resolved_entities: list[ResolvedEntity] | None = None,
) -> list[RetrievedChunk]:
    """Reordena fragmentos para priorizar contexto mas util para preguntas estructuradas."""

    normalized_query = _normalize_text(query_text)
    entities = resolved_entities or []
    scored_chunks = [
        (
            _score_chunk(
                chunk=chunk,
                normalized_query=normalized_query,
                intent_hint=intent_hint,
                resolved_entities=entities,
            ),
            chunk,
        )
        for chunk in chunks
    ]
    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored_chunks]


def _query_collection(
    collection,
    query_embedding: list[float],
    n_results: int,
    where: dict[str, Any] | None,
) -> dict[str, Any]:
    """Ejecuta una consulta a Chroma con o sin prefiltro de metadata."""

    request_kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where is not None:
        request_kwargs["where"] = where

    try:
        return collection.query(**request_kwargs)
    except Exception as exc:  # pragma: no cover - guardia de API de Chroma
        raise RuntimeError(f"La busqueda vectorial en Chroma fallo: {exc}") from exc


def _merge_query_results(primary_result: dict[str, Any], fallback_result: dict[str, Any]) -> dict[str, Any]:
    """Fusiona dos respuestas de Chroma evitando ids duplicados."""

    merged_ids: list[str] = []
    merged_documents: list[str] = []
    merged_metadatas: list[dict[str, Any]] = []
    merged_distances: list[float | None] = []

    primary_ids = primary_result.get("ids", [[]])[0]
    primary_documents = primary_result.get("documents", [[]])[0]
    primary_metadatas = primary_result.get("metadatas", [[]])[0]
    primary_distances = primary_result.get("distances", [[]])[0]

    fallback_ids = fallback_result.get("ids", [[]])[0]
    fallback_documents = fallback_result.get("documents", [[]])[0]
    fallback_metadatas = fallback_result.get("metadatas", [[]])[0]
    fallback_distances = fallback_result.get("distances", [[]])[0]

    for document_id, document, metadata, distance in zip(
        primary_ids,
        primary_documents,
        primary_metadatas,
        primary_distances,
    ):
        merged_ids.append(document_id)
        merged_documents.append(document)
        merged_metadatas.append(metadata)
        merged_distances.append(distance)

    seen_ids = set(merged_ids)
    for document_id, document, metadata, distance in zip(
        fallback_ids,
        fallback_documents,
        fallback_metadatas,
        fallback_distances,
    ):
        if document_id in seen_ids:
            continue
        seen_ids.add(document_id)
        merged_ids.append(document_id)
        merged_documents.append(document)
        merged_metadatas.append(metadata)
        merged_distances.append(distance)

    return {
        "ids": [merged_ids],
        "documents": [merged_documents],
        "metadatas": [merged_metadatas],
        "distances": [merged_distances],
    }


def _score_chunk(
    chunk: RetrievedChunk,
    normalized_query: str,
    intent_hint: SqlIntentHint | None,
    resolved_entities: list[ResolvedEntity],
) -> float:
    """Asigna una puntuacion heuristica a un chunk recuperado."""

    score = 0.0
    distance = chunk.distance if chunk.distance is not None else 10.0
    score -= distance

    table_name = str(chunk.metadata.get("table_name", ""))
    content_type = str(chunk.metadata.get("content_type", ""))
    text = _normalize_text(chunk.text)

    if intent_hint is not None:
        if table_name in intent_hint.target_tables:
            score += 3.0
        if _content_type_matches_intent(content_type, intent_hint.intent_name):
            score += 2.0
        score += _get_intent_specific_bonus(
            intent_name=intent_hint.intent_name,
            table_name=table_name,
            content_type=content_type,
        )
        score += _get_priority_position_bonus(
            intent_name=intent_hint.intent_name,
            table_name=table_name,
            content_type=content_type,
            metadata=chunk.metadata,
            normalized_query=normalized_query,
        )

    query_years = set(re.findall(r"\b(?:19|20)\d{2}\b", normalized_query))
    chunk_year = str(chunk.metadata.get("season_year", "")).strip()
    if query_years:
        if chunk_year and chunk_year in query_years:
            score += 4.0
        elif chunk_year:
            score -= 3.5

    for entity in resolved_entities:
        if _chunk_matches_entity(chunk, entity):
            score += 2.5

    keyword_overlap = _count_keyword_overlap(normalized_query, text)
    score += min(keyword_overlap * 0.35, 2.0)

    if intent_hint is not None:
        score += _get_intent_specific_penalty(
            intent_name=intent_hint.intent_name,
            table_name=table_name,
            content_type=content_type,
        )

    return score


def _chunk_matches_entity(chunk: RetrievedChunk, entity: ResolvedEntity) -> bool:
    """Valida si un chunk contiene una entidad resuelta relevante."""

    normalized_display = _normalize_text(entity.display_name)
    normalized_canonical = _normalize_text(entity.canonical_value)

    metadata_candidates = [
        str(chunk.metadata.get("driver_name", "")),
        str(chunk.metadata.get("constructor_name", "")),
        str(chunk.metadata.get("race_name", "")),
        str(chunk.metadata.get("circuit_name", "")),
        str(chunk.metadata.get("nationality", "")),
        chunk.text,
    ]

    normalized_candidates = [_normalize_text(candidate) for candidate in metadata_candidates if candidate]
    return any(
        normalized_display in candidate or normalized_canonical in candidate
        for candidate in normalized_candidates
        if normalized_display or normalized_canonical
    )


def _content_type_matches_intent(content_type: str, intent_name: str) -> bool:
    """Relaciona tipos de chunks con intenciones SQL esperadas."""

    content_map = {
        "analytical_ranking": {"analitica_piloto", "analitica_constructores", "analitica_temporada"},
        "analytical_trend": {"analitica_piloto", "analitica_constructores", "analitica_temporada", "carrera"},
        "qualifying": {"clasificacion"},
        "driver_standings": {"standing_piloto"},
        "constructor_standings": {"standing_constructores"},
        "results": {"resultado_carrera", "carrera"},
        "race_status": {"resultado_carrera"},
        "sprint_results": {"resultado_sprint"},
    }
    return content_type in content_map.get(intent_name, set())


def _get_intent_specific_bonus(intent_name: str, table_name: str, content_type: str) -> float:
    """Aplica bonos adicionales segun el tipo de pregunta detectada."""

    if intent_name == "analytical_ranking":
        if content_type in {"analitica_piloto", "analitica_constructores"}:
            return 4.0
        if table_name in {"driver_analytics", "constructor_analytics"}:
            return 3.0
        if content_type == "analitica_temporada":
            return 1.5
        if table_name == "results":
            return 4.0
        if table_name in {"drivers", "constructors"}:
            return 2.0
        if table_name == "races":
            return 0.75
        if content_type == "resultado_carrera":
            return 2.5

    if intent_name == "analytical_trend":
        if content_type == "analitica_temporada":
            return 4.0
        if table_name == "season_analytics":
            return 3.0
        if content_type in {"analitica_piloto", "analitica_constructores"}:
            return 1.5
        if table_name in {"results", "driver_standings", "constructor_standings", "races"}:
            return 2.5
        if content_type in {"resultado_carrera", "standing_piloto", "standing_constructores", "carrera"}:
            return 1.5

    if intent_name == "driver_standings":
        if content_type == "standing_piloto":
            return 4.0
        if table_name == "driver_standings":
            return 2.5
        if table_name == "races":
            return 0.75
        if table_name == "results":
            return 0.25

    if intent_name == "constructor_standings":
        if content_type == "standing_constructores":
            return 4.0
        if table_name == "constructor_standings":
            return 2.5
        if table_name == "races":
            return 0.75
        if table_name == "results":
            return 0.25

    return 0.0


def _get_intent_specific_penalty(intent_name: str, table_name: str, content_type: str) -> float:
    """Aplica castigos cuando un chunk no es el tipo principal esperado."""

    if content_type in {"piloto", "circuito", "escuderia"} and intent_name in {
        "analytical_ranking",
        "analytical_trend",
        "driver_standings",
        "constructor_standings",
        "qualifying",
        "results",
        "sprint_results",
        "race_status",
    }:
        return -1.25

    if intent_name == "driver_standings":
        if table_name == "results":
            return -1.0
        if table_name == "races":
            return -0.5

    if intent_name == "constructor_standings":
        if table_name == "results":
            return -1.0
        if table_name == "races":
            return -0.5

    if intent_name == "analytical_ranking":
        if table_name in {"driver_standings", "constructor_standings"}:
            return -4.0
        if content_type in {"standing_piloto", "standing_constructores"}:
            return -3.0

    if intent_name == "analytical_trend":
        if table_name in {"drivers", "constructors"} and content_type in {"piloto", "escuderia"}:
            return -1.25

    return 0.0


def _get_priority_position_bonus(
    intent_name: str,
    table_name: str,
    content_type: str,
    metadata: dict[str, Any],
    normalized_query: str,
) -> float:
    """Prioriza filas lideres, poles o ganadores dentro del mismo tipo de chunk."""

    position_value = _safe_int_from_metadata(metadata.get("position"))
    position_order_value = _safe_int_from_metadata(metadata.get("position_order"))
    lower_position = _safe_int_from_metadata(metadata.get("positiontext"))

    if intent_name == "driver_standings":
        if content_type == "standing_piloto":
            if position_value == 1 or lower_position == 1:
                return 2.5
            if position_value is not None and position_value <= 3:
                return 0.75

    if intent_name == "constructor_standings":
        if content_type == "standing_constructores":
            if position_value == 1 or lower_position == 1:
                return 2.5
            if position_value is not None and position_value <= 3:
                return 0.75

    if intent_name == "qualifying":
        if content_type == "clasificacion":
            if "pole" in normalized_query or "clasificacion" in normalized_query:
                if position_value == 1:
                    return 4.0
                if position_value is not None and position_value <= 3:
                    return 1.0

    if intent_name == "sprint_results":
        if content_type == "resultado_sprint":
            if position_order_value == 1 or position_value == 1 or lower_position == 1:
                return 4.0
            if position_order_value is not None and position_order_value <= 3:
                return 1.0

    if intent_name == "results":
        if content_type == "resultado_carrera":
            if any(keyword in normalized_query for keyword in {"gano", "gano", "winner", "victoria"}):
                if position_order_value == 1 or position_value == 1 or lower_position == 1:
                    return 3.0

    if intent_name == "analytical_ranking":
        if content_type == "analitica_piloto":
            total_wins = _safe_int_from_metadata(metadata.get("total_wins")) or 0
            total_podiums = _safe_int_from_metadata(metadata.get("total_podiums")) or 0
            if any(keyword in normalized_query for keyword in {"victorias", "ganadores", "gana", "gano"}):
                if total_wins > 0:
                    return min(total_wins * 0.08, 6.0) + min(total_podiums * 0.02, 1.0)
                return -3.0
        if content_type == "analitica_constructores":
            total_wins = _safe_int_from_metadata(metadata.get("total_wins")) or 0
            total_podiums = _safe_int_from_metadata(metadata.get("total_podiums")) or 0
            if any(keyword in normalized_query for keyword in {"victorias", "ganadores", "gana", "gano"}):
                if total_wins > 0:
                    return min(total_wins * 0.08, 6.0) + min(total_podiums * 0.02, 1.0)
                return -3.0
        if content_type == "resultado_carrera":
            if any(keyword in normalized_query for keyword in {"victorias", "ganadores", "gano", "gana"}):
                if position_order_value == 1 or position_value == 1 or lower_position == 1:
                    return 4.0
                if position_order_value is not None and position_order_value > 1:
                    return -2.5

    return 0.0


def _driver_filter_is_helpful(intent_hint: SqlIntentHint | None) -> bool:
    """Indica si conviene filtrar por piloto antes de recuperar."""

    if intent_hint is None:
        return False
    return intent_hint.intent_name in {
        "analytical_trend",
        "results",
        "race_status",
        "qualifying",
        "sprint_results",
    }


def _constructor_filter_is_helpful(intent_hint: SqlIntentHint | None) -> bool:
    """Indica si conviene filtrar por escuderia antes de recuperar."""

    if intent_hint is None:
        return False
    return intent_hint.intent_name in {
        "analytical_trend",
        "results",
        "qualifying",
        "sprint_results",
        "constructor_standings",
    }


def _build_analytical_table_prefilter(intent_hint: SqlIntentHint | None) -> dict[str, Any] | None:
    """Construye un prefiltro por tablas para preguntas analíticas amplias."""

    if intent_hint is None:
        return None

    if intent_hint.intent_name == "analytical_ranking":
        return {
            "$or": [
                {"table_name": "driver_analytics"},
                {"table_name": "constructor_analytics"},
                {"table_name": "results"},
                {"table_name": "drivers"},
                {"table_name": "constructors"},
                {"table_name": "races"},
            ]
        }

    if intent_hint.intent_name == "analytical_trend":
        return {
            "$or": [
                {"table_name": "season_analytics"},
                {"table_name": "results"},
                {"table_name": "driver_standings"},
                {"table_name": "constructor_standings"},
                {"table_name": "races"},
            ]
        }

    return None


def _build_analytical_position_prefilter(
    query_text: str,
    intent_hint: SqlIntentHint | None,
) -> dict[str, Any] | None:
    """Agrega filtros por posicion cuando la pregunta analítica lo justifica claramente."""

    if intent_hint is None:
        return None

    normalized_query = _normalize_text(query_text)
    if intent_hint.intent_name == "analytical_ranking":
        if any(keyword in normalized_query for keyword in {"victorias", "ganadores", "gana", "gano"}):
            return {
                "$or": [
                    {"position": "1"},
                    {"table_name": "driver_analytics"},
                    {"table_name": "constructor_analytics"},
                ]
            }

    return None


def _count_keyword_overlap(normalized_query: str, normalized_text: str) -> int:
    """Cuenta superposicion de tokens significativos entre pregunta y chunk."""

    query_tokens = {token for token in normalized_query.split() if len(token) >= 4}
    text_tokens = set(normalized_text.split())
    return len(query_tokens & text_tokens)


def _safe_int_from_metadata(value: Any) -> int | None:
    """Convierte metadatos de posicion a entero cuando es posible."""

    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _normalize_text(value: str) -> str:
    """Normaliza texto para comparaciones insensibles a acentos."""

    normalized = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    lowered = without_accents.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()
