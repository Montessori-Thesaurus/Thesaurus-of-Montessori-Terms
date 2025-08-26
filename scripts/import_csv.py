#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
from urllib.parse import quote

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import SKOS, DCTERMS, RDF


DEFAULT_BASE_IRI = os.getenv("BASE_IRI", "https://vocabulary.montessoriglossary.org/")


def slugify(value: str) -> str:
	return quote(value.strip().lower().replace(" ", "-"), safe="")


def import_csv_to_skos(input_csv: str, output_ttl: str, base_iri: str = DEFAULT_BASE_IRI, language: str = "en") -> None:
	g = Graph()
	scheme = URIRef(base_iri.rstrip("/") + "/scheme")
	g.add((scheme, RDF.type, SKOS.ConceptScheme))
	g.add((scheme, DCTERMS.title, Literal("Montessori Glossary Vocabulary", lang=language)))

	with open(input_csv, newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		for row in reader:
			label = (row.get("prefLabel") or row.get("label") or row.get("term") or "").strip()
			if not label:
				continue
			slug = row.get("id") or slugify(label)
			iri = URIRef(base_iri.rstrip("/") + f"/concept/{slug}")
			g.add((iri, RDF.type, SKOS.Concept))
			g.add((iri, SKOS.inScheme, scheme))
			g.add((iri, SKOS.prefLabel, Literal(label, lang=language)))

			definition = (row.get("definition") or row.get("desc") or "").strip()
			if definition:
				g.add((iri, SKOS.definition, Literal(definition, lang=language)))

			alt = (row.get("altLabel") or row.get("alt") or "").strip()
			if alt:
				for alt_item in [a.strip() for a in alt.split("|") if a.strip()]:
					g.add((iri, SKOS.altLabel, Literal(alt_item, lang=language)))

	g.serialize(destination=output_ttl, format="turtle")
	print(f"Wrote SKOS TTL to {output_ttl} with {len(list(g.subjects(RDF.type, SKOS.Concept)))} concepts")


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Import CSV into SKOS Turtle")
	parser.add_argument("input_csv", help="Path to input CSV with columns: prefLabel, altLabel, definition")
	parser.add_argument("output_ttl", nargs="?", default=os.path.abspath(os.path.join(os.getcwd(), "data", "vocabulary.ttl")))
	parser.add_argument("--base-iri", dest="base_iri", default=DEFAULT_BASE_IRI)
	parser.add_argument("--lang", dest="lang", default="en")
	args = parser.parse_args()
	os.makedirs(os.path.dirname(args.output_ttl), exist_ok=True)
	import_csv_to_skos(args.input_csv, args.output_ttl, base_iri=args.base_iri, language=args.lang)