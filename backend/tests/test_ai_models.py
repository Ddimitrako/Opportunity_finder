from __future__ import annotations

import unittest

from app.ai_models import (
    AI_MODEL_CATALOG,
    UnsupportedAIModelError,
    model_request_options,
    resolve_ai_model,
)
from app.config import Settings


class AIModelSelectionTests(unittest.TestCase):
    def test_catalog_includes_requested_analysis_models(self) -> None:
        model_ids = {item.id for item in AI_MODEL_CATALOG}
        self.assertIn("gpt-5.5", model_ids)
        self.assertIn("gpt-5.6", model_ids)
        self.assertIn("gpt-5.6-terra", model_ids)

    def test_requested_model_is_validated_against_catalog(self) -> None:
        settings = Settings(openai_model="gpt-4.1-mini")
        self.assertEqual(resolve_ai_model(settings, "gpt-5.6"), "gpt-5.6")
        with self.assertRaises(UnsupportedAIModelError):
            resolve_ai_model(settings, "untrusted-model-id")
        self.assertEqual(resolve_ai_model(Settings(openai_model="legacy-custom-model")), "gpt-4.1-mini")

    def test_reasoning_models_omit_temperature(self) -> None:
        options = model_request_options("gpt-5.6", temperature=0.2)
        self.assertEqual(options, {"reasoning": {"effort": "medium"}})
        self.assertNotIn("temperature", options)

    def test_gpt_4_models_keep_temperature(self) -> None:
        self.assertEqual(model_request_options("gpt-4.1-mini", temperature=0.1), {"temperature": 0.1})


if __name__ == "__main__":
    unittest.main()
