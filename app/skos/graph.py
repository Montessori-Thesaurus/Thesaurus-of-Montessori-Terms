from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import os
import threading

from rdflib import Graph, URIRef, Namespace, Literal
from rdflib.namespace import SKOS, RDF, DCTERMS


@dataclass
class ConceptSummary:
    iri: str
    pref_label: Optional[str]
    definition: Optional[str]


class SKOSGraphService:
    def __init__(self, ttl_path: str, default_language: str = "en") -> None:
        self._ttl_path = ttl_path
        self._default_language = default_language
        self._graph_lock = threading.Lock()
        self._graph: Optional[Graph] = None
        self._last_loaded_mtime: Optional[float] = None

    def _ensure_loaded(self) -> None:
        with self._graph_lock:
            mtime = None
            try:
                mtime = os.path.getmtime(self._ttl_path)
            except FileNotFoundError:
                pass

            if self._graph is not None and self._last_loaded_mtime == mtime:
                return

            g = Graph()
            if os.path.exists(self._ttl_path):
                g.parse(self._ttl_path, format="turtle")
            self._graph = g
            self._last_loaded_mtime = mtime

    def reload(self) -> None:
        with self._graph_lock:
            self._graph = None
            self._last_loaded_mtime = None
        self._ensure_loaded()

    def get_graph(self) -> Graph:
        self._ensure_loaded()
        assert self._graph is not None
        return self._graph

    # Query helpers
    def list_concepts(self, limit: int = 100, offset: int = 0, language: Optional[str] = None) -> Tuple[List[ConceptSummary], int]:
        g = self.get_graph()
        language = language or self._default_language
        concepts: List[ConceptSummary] = []

        all_concepts = list(g.subjects(RDF.type, SKOS.Concept))
        total = len(all_concepts)
        for subject in all_concepts[offset: offset + limit]:
            pref_label = self._get_best_label(g, subject, language)
            definition = self._get_best_definition(g, subject, language)
            concepts.append(ConceptSummary(iri=str(subject), pref_label=pref_label, definition=definition))
        return concepts, total

    def search_concepts(self, query: str, limit: int = 50, language: Optional[str] = None) -> List[ConceptSummary]:
        g = self.get_graph()
        language = language or self._default_language
        lower_q = query.lower()
        results: List[ConceptSummary] = []

        for subject in g.subjects(RDF.type, SKOS.Concept):
            labels = list(g.objects(subject, SKOS.prefLabel)) + list(g.objects(subject, SKOS.altLabel))
            matched_label: Optional[str] = None
            for label in labels:
                if isinstance(label, Literal):
                    if label.language is None or label.language == language:
                        label_text = str(label)
                        if lower_q in label_text.lower():
                            matched_label = label_text
                            break
            if matched_label is not None:
                definition = self._get_best_definition(g, subject, language)
                results.append(ConceptSummary(iri=str(subject), pref_label=matched_label, definition=definition))
            if len(results) >= limit:
                break
        return results

    def get_concept_detail(self, iri: str, language: Optional[str] = None) -> Optional[Dict]:
        g = self.get_graph()
        language = language or self._default_language
        subject = URIRef(iri)
        if (subject, RDF.type, SKOS.Concept) not in g:
            return None

        detail: Dict = {"iri": iri}
        detail["prefLabel"] = self._get_literals(g, subject, SKOS.prefLabel)
        detail["altLabel"] = self._get_literals(g, subject, SKOS.altLabel)
        detail["definition"] = self._get_literals(g, subject, SKOS.definition)
        detail["broader"] = [str(o) for o in g.objects(subject, SKOS.broader)]
        detail["narrower"] = [str(o) for o in g.objects(subject, SKOS.narrower)]
        detail["related"] = [str(o) for o in g.objects(subject, SKOS.related)]
        detail["inScheme"] = [str(o) for o in g.objects(subject, SKOS.inScheme)]
        detail["notation"] = [str(o) for o in g.objects(subject, SKOS.notation)]

        detail["bestPrefLabel"] = self._get_best_label(g, subject, language)
        detail["bestDefinition"] = self._get_best_definition(g, subject, language)
        return detail

    def serialize(self, format: str = "turtle") -> Tuple[str, str]:
        g = self.get_graph()
        fmt = format.lower()
        if fmt in {"ttl", "turtle"}:
            return g.serialize(format="turtle"), "text/turtle"
        if fmt in {"jsonld", "json-ld"}:
            return g.serialize(format="json-ld", indent=2), "application/ld+json"
        if fmt in {"xml", "rdf", "rdfxml", "rdf/xml"}:
            return g.serialize(format="xml"), "application/rdf+xml"
        if fmt in {"nt", "ntriples", "n-triples"}:
            return g.serialize(format="nt"), "application/n-triples"
        raise ValueError(f"Unsupported format: {format}")

    # Internal helpers
    def _get_best_label(self, g: Graph, subject: URIRef, language: str) -> Optional[str]:
        labels = list(g.objects(subject, SKOS.prefLabel))
        label = self._select_lang_literal(labels, language)
        return str(label) if label is not None else None

    def _get_best_definition(self, g: Graph, subject: URIRef, language: str) -> Optional[str]:
        defs = list(g.objects(subject, SKOS.definition))
        lit = self._select_lang_literal(defs, language)
        return str(lit) if lit is not None else None

    def _get_literals(self, g: Graph, subject: URIRef, predicate: URIRef) -> Dict[str, List[str]]:
        values: Dict[str, List[str]] = {}
        for lit in g.objects(subject, predicate):
            if isinstance(lit, Literal):
                lang = lit.language or "und"
                values.setdefault(lang, []).append(str(lit))
        return values

    def _select_lang_literal(self, literals: List[Literal], language: str) -> Optional[Literal]:
        best_exact: Optional[Literal] = None
        best_langless: Optional[Literal] = None
        for lit in literals:
            if not isinstance(lit, Literal):
                continue
            if lit.language == language:
                best_exact = lit
                break
            if lit.language is None:
                best_langless = lit
        return best_exact or best_langless or (literals[0] if literals else None)