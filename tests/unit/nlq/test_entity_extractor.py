"""
Unit tests for the entity extractor in the NLQ module.
"""

import unittest
from panflow.nlq.entity_extractor import EntityExtractor


class TestEntityExtractor(unittest.TestCase):
    """Test cases for the EntityExtractor class in the NLQ module."""

    def test_bulk_operation_extraction(self):
        """Test extraction of bulk operations from natural language queries."""
        extractor = EntityExtractor()
        
        # Test add_tag operation
        entities = extractor.extract("add tag 'test-tag' to all security policies")
        self.assertIn("operation", entities)
        self.assertEqual(entities["operation"], "add_tag")
        self.assertIn("value", entities)
        self.assertEqual(entities["value"], "test-tag")
        
        # Test set_action operation
        entities = extractor.extract("set action to deny for all security policies")
        self.assertIn("operation", entities)
        self.assertEqual(entities["operation"], "set_action")
        self.assertEqual(entities["value"], "deny")

        # Test a simpler pattern that should match the regex
        entities = extractor.extract("enable policy")
        self.assertIn("operation", entities, "Failed to extract 'enable' operation")

        # Check the value
        if "operation" in entities:
            self.assertEqual(entities["operation"], "enable", "Wrong operation type detected")
            self.assertEqual(entities["value"], "yes", "Wrong value for enable operation")

        # Test disable operation
        entities = extractor.extract("disable all security policies")
        self.assertIn("operation", entities)
        self.assertEqual(entities["operation"], "disable")
        self.assertEqual(entities["value"], "yes")

        # Test enable_logging operation
        entities = extractor.extract("enable logging")
        self.assertIn("operation", entities)
        self.assertEqual(entities["operation"], "enable_logging",
                         f"Wrong operation detected: {entities.get('operation', 'none')}")
        self.assertEqual(entities["value"], "yes")

        # Test disable_logging operation
        entities = extractor.extract("disable logging for all security policies")
        self.assertIn("operation", entities)
        self.assertEqual(entities["operation"], "disable_logging")
        self.assertEqual(entities["value"], "yes")


if __name__ == "__main__":
    unittest.main()