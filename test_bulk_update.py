#!/usr/bin/env python
"""
Test script for bulk policy operations in NLQ.

This script tests bulk policy operations through natural language queries.
"""

import os
import argparse
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("panflow_test")

# Import the NLQ processor
try:
    from panflow.nlq import NLQProcessor
except ImportError:
    logger.error("Could not import PANFlow. Make sure it's installed.")
    sys.exit(1)

def test_bulk_update_policies(config_file, output_file, operation_type):
    """
    Test bulk policy update operations using natural language queries.
    
    Args:
        config_file: Path to the configuration file
        output_file: Path to save the output file
        operation_type: Type of operation to test (add_tag, enable, disable, set_action, etc.)
    """
    processor = NLQProcessor(use_ai=False)  # Use pattern-based processing for consistent results
    
    # Define test queries for different operations
    queries = {
        "add_tag": f"add tag 'test-tag' to all policies",
        "enable": f"enable all policies",
        "disable": f"disable all policies",
        "set_action": f"set action to deny for all policies",
        "enable_logging": f"enable logging for all policies",
        "disable_logging": f"disable logging for all policies",
    }
    
    if operation_type not in queries:
        logger.error(f"Unknown operation type: {operation_type}")
        logger.info(f"Available operations: {', '.join(queries.keys())}")
        return
    
    # Process the query
    query = queries[operation_type]
    logger.info(f"Testing operation: {operation_type}")
    logger.info(f"Query: {query}")
    
    result = processor.process(query, config_file, output_file)
    
    # Check result
    if result["success"]:
        logger.info("Operation succeeded.")
        
        # Extract operation details from result
        if "result" in result and isinstance(result["result"], dict):
            result_data = result["result"]
            
            # Check for updated policies
            if "updated_policies" in result_data:
                updated_count = len(result_data["updated_policies"])
                logger.info(f"Updated {updated_count} policies")
                
                # Show the first 5 policies for verification
                policies_to_show = min(5, updated_count)
                if policies_to_show > 0:
                    logger.info(f"First {policies_to_show} updated policies:")
                    policies = result_data["updated_policies"][:policies_to_show]
                    for policy in policies:
                        if isinstance(policy, dict):
                            policy_name = policy.get("name", str(policy))
                            logger.info(f"  - {policy_name}")
                        else:
                            logger.info(f"  - {policy}")
            else:
                logger.warning("No updated_policies found in result.")
        else:
            logger.warning("No detailed result data returned.")
    else:
        logger.error(f"Operation failed: {result.get('message', 'Unknown error')}")

def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test bulk policy operations")
    parser.add_argument("--config", required=True, help="Path to the configuration file")
    parser.add_argument("--output", required=True, help="Path to save the output file")
    parser.add_argument("--operation", required=True, 
                        choices=["add_tag", "enable", "disable", "set_action", "enable_logging", "disable_logging"],
                        help="Type of operation to test")
    
    args = parser.parse_args()
    
    logger.info(f"Starting test with config: {args.config}, output: {args.output}")
    test_bulk_update_policies(args.config, args.output, args.operation)
    logger.info("Test completed.")

if __name__ == "__main__":
    main()