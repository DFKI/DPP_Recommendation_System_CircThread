"""Consistency checks between the shared vocabulary, the seed data and the ontology assets."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parents[1]
for path in (str(SERVICE_ROOT), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app import seed_data  # noqa: E402
from app.sssom import load_sssom_mapping_set  # noqa: E402
from shared.models import DataCategory  # noqa: E402
from shared.vocabulary import FIELD_CATEGORIES  # noqa: E402

ONTOLOGY_FILE = SERVICE_ROOT / "ontology" / "dpp_ontology.ttl"


class VocabularyConsistencyTests(unittest.TestCase):
    def test_shared_vocabulary_matches_seeded_data_fields(self) -> None:
        seeded = {name: category for name, _label, category, _desc in seed_data.DATA_FIELDS}
        self.assertEqual(seeded, FIELD_CATEGORIES)

    def test_categories_are_canonical(self) -> None:
        canonical = {c.value for c in DataCategory}
        self.assertEqual(set(FIELD_CATEGORIES.values()), canonical)

    def test_priorities_reference_known_fields_and_valid_values(self) -> None:
        roles = {"recycler", "consumer", "manufacturer", "repairer", "collector"}
        events = {"purchase", "repair", "recycling", "maintenance", "disposal", "resale"}
        for (role, event), fields in seed_data.ROLE_EVENT_MAPPINGS.items():
            self.assertIn(role, roles)
            self.assertIn(event, events)
            for field, priority in fields.items():
                self.assertIn(field, FIELD_CATEGORIES, f"{role}/{event}: unknown field {field}")
                self.assertTrue(0.0 <= priority <= 1.0)

    def test_sssom_mappings_use_declared_prefixes_and_known_subjects(self) -> None:
        mapping_set = load_sssom_mapping_set()
        prefixes = set(mapping_set["metadata"]["curie_map"]) | {"skos", "semapv"}
        ontology = ONTOLOGY_FILE.read_text(encoding="utf-8")
        declared = set(re.findall(r"^(dpp:\w+) rdf:type", ontology, flags=re.MULTILINE))
        for row in mapping_set["mappings"]:
            for curie in (row["subject_id"], row["object_id"], row["predicate_id"], row["mapping_justification"]):
                self.assertIn(curie.split(":")[0], prefixes, curie)
            self.assertIn(row["subject_id"], declared, f"{row['subject_id']} not declared in dpp_ontology.ttl")
            self.assertTrue(0.0 <= row["confidence"] <= 1.0)

    def test_term_aliases_point_to_known_fields_or_product_types(self) -> None:
        subjects = {row["subject_id"] for row in load_sssom_mapping_set()["mappings"]}
        self.assertTrue(set(seed_data.DPP_TERM_ALIASES) <= subjects)
        targets = set(FIELD_CATEGORIES) | set(seed_data.PRODUCT_TYPE_FIELDS)
        for subject, local_names in seed_data.DPP_TERM_ALIASES.items():
            for local_name in local_names:
                self.assertIn(local_name, targets, f"{subject} -> {local_name}")


if __name__ == "__main__":
    unittest.main()
