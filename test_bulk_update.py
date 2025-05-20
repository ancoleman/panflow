#!/usr/bin/env python3
"""
Test script for bulk update policies with device group context and query filter.

This script tests the fix for the issue with device group context in graph queries.
"""

import argparse
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run the test for bulk update policies with device group context and query filter."""
    parser = argparse.ArgumentParser(description="Test bulk update policies with device group context")
    parser.add_argument("--config", default="test_files/comprehensive_test.xml", help="Path to config file")
    parser.add_argument("--operations", default="test_files/operations.json", help="Path to operations file")
    args = parser.parse_args()

    # Check if files exist
    if not os.path.exists(args.config):
        logger.error(f"Config file not found: {args.config}")
        return 1
    
    if not os.path.exists(args.operations):
        logger.error(f"Operations file not found: {args.operations}")
        return 1

    # Test different device groups and query filters
    test_cases = [
        {
            "name": "Device Group 1 with all rules query",
            "cmd": f"python cli.py policy bulk-update --config {args.config} --device-type panorama --context device_group --device-group test-dg-1 --operations {args.operations} --type security_pre_rules --output test_files/output_dg1_all.xml --query-filter \"MATCH (r:security-rule) RETURN r.name\"",
            "expected_success": True,
        },
        {
            "name": "Device Group 2 with all rules query",
            "cmd": f"python cli.py policy bulk-update --config {args.config} --device-type panorama --context device_group --device-group test-dg-2 --operations {args.operations} --type security_pre_rules --output test_files/output_dg2_all.xml --query-filter \"MATCH (r:security-rule) RETURN r.name\"",
            "expected_success": True,
        },
        {
            "name": "Device Group 1 with disabled rules query",
            "cmd": f"python cli.py policy bulk-update --config {args.config} --device-type panorama --context device_group --device-group test-dg-1 --operations {args.operations} --type security_pre_rules --output test_files/output_dg1_disabled.xml --query-filter \"MATCH (r:security-rule) WHERE r.disabled == 'yes' RETURN r.name\"",
            "expected_success": True,
        },
        {
            "name": "Device Group 2 with disabled rules query",
            "cmd": f"python cli.py policy bulk-update --config {args.config} --device-type panorama --context device_group --device-group test-dg-2 --operations {args.operations} --type security_pre_rules --output test_files/output_dg2_disabled.xml --query-filter \"MATCH (r:security-rule) WHERE r.disabled == 'yes' RETURN r.name\"",
            "expected_success": True,
        },
    ]

    success = True
    for test_case in test_cases:
        logger.info(f"Running test: {test_case['name']}")
        exit_code = os.system(test_case["cmd"])
        
        if (exit_code == 0) == test_case["expected_success"]:
            logger.info(f"✅ Test passed: {test_case['name']}")
        else:
            logger.error(f"❌ Test failed: {test_case['name']}")
            logger.error(f"Command: {test_case['cmd']}")
            logger.error(f"Exit code: {exit_code}")
            success = False

    # Test NLQ operations to make sure they still work
    nlq_test = {
        "name": "NLQ query for disabled rules",
        "cmd": f"python cli.py nlq query \"show all disabled security rules\" --config {args.config}",
        "expected_success": True,
    }
    
    logger.info(f"Running test: {nlq_test['name']}")
    exit_code = os.system(nlq_test["cmd"])
    
    if (exit_code == 0) == nlq_test["expected_success"]:
        logger.info(f"✅ Test passed: {nlq_test['name']}")
    else:
        logger.error(f"❌ Test failed: {nlq_test['name']}")
        logger.error(f"Command: {nlq_test['cmd']}")
        logger.error(f"Exit code: {exit_code}")
        success = False

    # Test policy listing with query filter
    list_test = {
        "name": "List policies with query filter",
        "cmd": f"python cli.py policy list --config {args.config} --type security_pre_rules --context device_group --device-group test-dg-1 --query-filter \"MATCH (r:security-rule) RETURN r.name\"",
        "expected_success": True,
    }
    
    logger.info(f"Running test: {list_test['name']}")
    exit_code = os.system(list_test["cmd"])
    
    if (exit_code == 0) == list_test["expected_success"]:
        logger.info(f"✅ Test passed: {list_test['name']}")
    else:
        logger.error(f"❌ Test failed: {list_test['name']}")
        logger.error(f"Command: {list_test['cmd']}")
        logger.error(f"Exit code: {exit_code}")
        success = False

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())