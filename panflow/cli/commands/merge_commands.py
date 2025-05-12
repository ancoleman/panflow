"""
Merge commands for the PANFlow CLI.

This module provides commands for merging objects and policies between configurations.
"""

import json
import typer
import logging
from typing import Optional, Dict, Any, List

from panflow.core.object_merger import ObjectMerger
from panflow.core.policy_merger import PolicyMerger
from panflow.core.conflict_resolver import ConflictStrategy
from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type
from panflow.core.graph_utils import ConfigGraph
from panflow.core.query_language import Query
from panflow.core.query_engine import QueryExecutor
from panflow.constants import POLICY_TYPES, OBJECT_TYPES

from ..app import merge_app
from ..common import ConfigOptions, ContextOptions, ObjectOptions, PolicyOptions, MergeOptions

# Get logger
logger = logging.getLogger("panflow")


@merge_app.command("policy")
def merge_policy(
    source_config: str = typer.Option(
        ..., "--source-config", help="Path to source XML configuration file"
    ),
    target_config: str = typer.Option(
        ..., "--target-config", help="Path to target XML configuration file"
    ),
    policy_type: str = PolicyOptions.policy_type(),
    policy_name: str = PolicyOptions.policy_name(),
    source_context: str = typer.Option(
        "shared", "--source-context", help="Source context (shared, device_group, vsys)"
    ),
    target_context: str = typer.Option(
        "shared", "--target-context", help="Target context (shared, device_group, vsys)"
    ),
    source_device_group: Optional[str] = typer.Option(
        None, "--source-dg", help="Source device group name"
    ),
    target_device_group: Optional[str] = typer.Option(
        None, "--target-dg", help="Target device group name"
    ),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option(
        "panorama", "--source-type", help="Source device type (firewall or panorama)"
    ),
    target_device_type: str = typer.Option(
        "panorama", "--target-type", help="Target device type (firewall or panorama)"
    ),
    source_version: Optional[str] = typer.Option(
        None, "--source-version", help="Source PAN-OS version"
    ),
    target_version: Optional[str] = typer.Option(
        None, "--target-version", help="Target PAN-OS version"
    ),
    position: str = PolicyOptions.position(),
    ref_policy: Optional[str] = PolicyOptions.ref_policy(),
    skip_if_exists: bool = typer.Option(
        True,
        "--skip-if-exists/--replace",
        help="Skip if policy already exists (deprecated, use conflict_strategy instead)",
    ),
    copy_references: bool = MergeOptions.copy_references(),
    conflict_strategy: Optional[ConflictStrategy] = MergeOptions.conflict_strategy(),
    dry_run: bool = ConfigOptions.dry_run(),
    output_file: str = ConfigOptions.output_file(),
):
    """Merge a policy from source configuration to target configuration"""
    try:
        # Load source and target configurations
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)

        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)

        # Create policy merger
        merger = PolicyMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version,
        )

        # Merge the policy
        result = merger.copy_policy(
            policy_type,
            policy_name,
            source_context,
            target_context,
            skip_if_exists,
            copy_references,
            position,
            ref_policy,
            conflict_strategy=conflict_strategy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys,
        )

        if result:
            logger.info(f"Successfully merged policy '{policy_name}'")

            # Log copied objects
            if copy_references and merger.copied_objects:
                logger.info(f"Copied {len(merger.copied_objects)} referenced objects")
                for obj_type, obj_name in merger.copied_objects:
                    logger.debug(f"  - {obj_type}: {obj_name}")

            # Save the updated configuration if not in dry run mode
            if not dry_run:
                if save_config(target_tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.info(f"Dry run mode: Changes NOT saved to {output_file}")
                logger.info(
                    f"If this was not a dry run, the following changes would have been made:"
                )
                logger.info(f"  - Policy '{policy_name}' would be added to {target_context}")
                if copy_references and merger.copied_objects:
                    logger.info(
                        f"  - {len(merger.copied_objects)} referenced objects would be copied"
                    )
        else:
            logger.error(f"Failed to merge policy '{policy_name}'")

            if merger.skipped_policies:
                for name, reason in merger.skipped_policies:
                    logger.warning(f"  - {name}: {reason}")

            raise typer.Exit(1)

    except Exception as e:
        logger.error(f"Error merging policy: {e}")
        raise typer.Exit(1)


@merge_app.command("policies")
def merge_policies(
    source_config: str = typer.Option(
        ..., "--source-config", help="Path to source XML configuration file"
    ),
    target_config: str = typer.Option(
        ..., "--target-config", help="Path to target XML configuration file"
    ),
    policy_type: str = PolicyOptions.policy_type(),
    policy_names_file: Optional[str] = typer.Option(
        None, "--names-file", help="File containing policy names to merge (one per line)"
    ),
    criteria_file: Optional[str] = typer.Option(
        None, "--criteria", help="JSON file with filter criteria"
    ),
    query_filter: Optional[str] = typer.Option(
        None,
        "--query-filter",
        "-q",
        help="Graph query filter to select policies (e.g., 'MATCH (r:security-rule)-[:uses-source]->(a:address) WHERE a.name == \"any\"')",
    ),
    source_context: str = typer.Option(
        "shared", "--source-context", help="Source context (shared, device_group, vsys)"
    ),
    target_context: str = typer.Option(
        "shared", "--target-context", help="Target context (shared, device_group, vsys)"
    ),
    source_device_group: Optional[str] = typer.Option(
        None, "--source-dg", help="Source device group name"
    ),
    target_device_group: Optional[str] = typer.Option(
        None, "--target-dg", help="Target device group name"
    ),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option(
        "panorama", "--source-type", help="Source device type (firewall or panorama)"
    ),
    target_device_type: str = typer.Option(
        "panorama", "--target-type", help="Target device type (firewall or panorama)"
    ),
    source_version: Optional[str] = typer.Option(
        None, "--source-version", help="Source PAN-OS version"
    ),
    target_version: Optional[str] = typer.Option(
        None, "--target-version", help="Target PAN-OS version"
    ),
    skip_if_exists: bool = typer.Option(
        True,
        "--skip-if-exists/--replace",
        help="Skip if policy already exists (deprecated, use conflict_strategy instead)",
    ),
    copy_references: bool = MergeOptions.copy_references(),
    conflict_strategy: Optional[ConflictStrategy] = MergeOptions.conflict_strategy(),
    dry_run: bool = ConfigOptions.dry_run(),
    output_file: str = ConfigOptions.output_file(),
):
    """Merge multiple policies from source configuration to target configuration

    Example:
        panflow merge policies --source-config source.xml --target-config target.xml --type security_pre_rules --names-file policy_names.txt
    """
    try:
        # Load source and target configurations
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)

        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)

        # Create policy merger
        merger = PolicyMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version,
        )

        # Get policy names or criteria
        policy_names = None
        filter_criteria = None

        if policy_names_file:
            with open(policy_names_file, "r") as f:
                policy_names = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(policy_names)} policy names from {policy_names_file}")

        if criteria_file:
            with open(criteria_file, "r") as f:
                filter_criteria = json.load(f)
            logger.info(f"Loaded criteria from {criteria_file}: {filter_criteria}")

        # Process query filter if specified
        if query_filter:
            logger.info(f"Using graph query filter: {query_filter}")

            # Build the graph from source configuration
            graph = ConfigGraph()
            graph.build_from_xml(source_tree)

            # Prepare a query that returns policy names
            # If the query doesn't already have a RETURN clause, append one that returns policy names
            if "RETURN" not in query_filter.upper():
                query_text = f"{query_filter} RETURN r.name"
            else:
                query_text = query_filter

            # Execute the query
            query = Query(query_text)
            executor = QueryExecutor(graph)
            results = executor.execute(query)

            # Extract policy names from the results
            query_policy_names = []
            for row in results:
                if "r.name" in row:
                    query_policy_names.append(row["r.name"])

            logger.info(f"Query matched {len(query_policy_names)} policies")

            # If policy_names is already set, extend it with query results
            if policy_names:
                policy_names.extend(query_policy_names)
            # Otherwise, set policy_names to query results
            else:
                policy_names = query_policy_names

        if not policy_names and not filter_criteria:
            logger.error(
                "Either policy names file, criteria file, or query filter must be provided"
            )
            raise typer.Exit(1)

        # Merge the policies
        copied, total = merger.copy_policies(
            policy_type,
            source_context,
            target_context,
            policy_names,
            filter_criteria,
            skip_if_exists,
            copy_references,
            conflict_strategy=conflict_strategy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys,
        )

        if copied > 0:
            logger.info(f"Successfully merged {copied} of {total} policies")

            # Log copied objects
            if copy_references and merger.copied_objects:
                logger.info(f"Copied {len(merger.copied_objects)} referenced objects")
                for obj_type, obj_name in merger.copied_objects[:10]:  # Show first 10
                    logger.debug(f"  - {obj_type}: {obj_name}")

                if len(merger.copied_objects) > 10:
                    logger.debug(f"  ... and {len(merger.copied_objects) - 10} more")

            # Save the updated configuration if not in dry run mode
            if not dry_run:
                if save_config(target_tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.info(f"Dry run mode: Changes NOT saved to {output_file}")
                logger.info(
                    f"If this was not a dry run, the following changes would have been made:"
                )
                logger.info(
                    f"  - {copied} policies of type {policy_type} would be added to {target_context}"
                )
                if copy_references and merger.copied_objects:
                    logger.info(
                        f"  - {len(merger.copied_objects)} referenced objects would be copied"
                    )
        else:
            logger.warning(f"No policies were merged (attempted {total})")

            if merger.skipped_policies:
                for name, reason in merger.skipped_policies[:10]:  # Show first 10
                    logger.warning(f"  - {name}: {reason}")

                if len(merger.skipped_policies) > 10:
                    logger.warning(f"  ... and {len(merger.skipped_policies) - 10} more")

            raise typer.Exit(1)

    except Exception as e:
        logger.error(f"Error merging policies: {e}")
        raise typer.Exit(1)


@merge_app.command("object")
def merge_object(
    source_config: str = typer.Option(
        ..., "--source-config", help="Path to source XML configuration file"
    ),
    target_config: str = typer.Option(
        ..., "--target-config", help="Path to target XML configuration file"
    ),
    object_type: str = ObjectOptions.object_type(),
    object_name: str = ObjectOptions.object_name(),
    source_context: str = typer.Option(
        "shared", "--source-context", help="Source context (shared, device_group, vsys)"
    ),
    target_context: str = typer.Option(
        "shared", "--target-context", help="Target context (shared, device_group, vsys)"
    ),
    source_device_group: Optional[str] = typer.Option(
        None, "--source-dg", help="Source device group name"
    ),
    target_device_group: Optional[str] = typer.Option(
        None, "--target-dg", help="Target device group name"
    ),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option(
        "panorama", "--source-type", help="Source device type (firewall or panorama)"
    ),
    target_device_type: str = typer.Option(
        "panorama", "--target-type", help="Target device type (firewall or panorama)"
    ),
    source_version: Optional[str] = typer.Option(
        None, "--source-version", help="Source PAN-OS version"
    ),
    target_version: Optional[str] = typer.Option(
        None, "--target-version", help="Target PAN-OS version"
    ),
    skip_if_exists: bool = typer.Option(
        True,
        "--skip-if-exists/--replace",
        help="Skip if object already exists (deprecated, use conflict_strategy instead)",
    ),
    copy_references: bool = MergeOptions.copy_references(),
    conflict_strategy: Optional[ConflictStrategy] = MergeOptions.conflict_strategy(),
    dry_run: bool = ConfigOptions.dry_run(),
    output_file: str = ConfigOptions.output_file(),
):
    """Merge a single object from source configuration to target configuration

    Example:
        panflow merge object --source-config source.xml --target-config target.xml --type address --name web-server
    """
    try:
        # Load source and target configurations
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)

        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)

        # Create object merger
        merger = ObjectMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version,
        )

        # Merge the object
        result = merger.copy_object(
            object_type,
            object_name,
            source_context,
            target_context,
            skip_if_exists,
            copy_references,
            conflict_strategy=conflict_strategy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys,
        )

        if result:
            logger.info(f"Successfully merged object '{object_name}'")

            # Log referenced/copied objects
            if copy_references and merger.referenced_objects:
                logger.info(f"Referenced {len(merger.referenced_objects)} objects")
                for obj_type, obj_name in merger.referenced_objects:
                    logger.debug(f"  - {obj_type}: {obj_name}")

            # Save the updated configuration if not in dry run mode
            if not dry_run:
                if save_config(target_tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.info(f"Dry run mode: Changes NOT saved to {output_file}")
                logger.info(
                    f"If this was not a dry run, the following changes would have been made:"
                )
                logger.info(
                    f"  - Object '{object_name}' of type {object_type} would be added to {target_context}"
                )
                if copy_references and merger.referenced_objects:
                    logger.info(
                        f"  - {len(merger.referenced_objects)} referenced objects would be copied"
                    )
        else:
            logger.error(f"Failed to merge object '{object_name}'")

            if merger.skipped_objects:
                for obj_type, name, reason in merger.skipped_objects:
                    logger.warning(f"  - {obj_type} '{name}': {reason}")

            raise typer.Exit(1)

    except Exception as e:
        logger.error(f"Error merging object: {e}")
        raise typer.Exit(1)


@merge_app.command("all")
def merge_all_policies(
    source_config: str = typer.Option(
        ..., "--source-config", help="Path to source XML configuration file"
    ),
    target_config: str = typer.Option(
        ..., "--target-config", help="Path to target XML configuration file"
    ),
    source_context: str = typer.Option(
        "shared", "--source-context", help="Source context (shared, device_group, vsys)"
    ),
    target_context: str = typer.Option(
        "shared", "--target-context", help="Target context (shared, device_group, vsys)"
    ),
    source_device_group: Optional[str] = typer.Option(
        None, "--source-dg", help="Source device group name"
    ),
    target_device_group: Optional[str] = typer.Option(
        None, "--target-dg", help="Target device group name"
    ),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option(
        "panorama", "--source-type", help="Source device type (firewall or panorama)"
    ),
    target_device_type: str = typer.Option(
        "panorama", "--target-type", help="Target device type (firewall or panorama)"
    ),
    source_version: Optional[str] = typer.Option(
        None, "--source-version", help="Source PAN-OS version"
    ),
    target_version: Optional[str] = typer.Option(
        None, "--target-version", help="Target PAN-OS version"
    ),
    skip_if_exists: bool = typer.Option(
        True,
        "--skip-if-exists/--replace",
        help="Skip if policy already exists (deprecated, use conflict_strategy instead)",
    ),
    copy_references: bool = MergeOptions.copy_references(),
    conflict_strategy: Optional[ConflictStrategy] = MergeOptions.conflict_strategy(),
    dry_run: bool = ConfigOptions.dry_run(),
    output_file: str = ConfigOptions.output_file(),
):
    """Merge all policy types from source configuration to target configuration

    Example:
        panflow merge all --source-config source.xml --target-config target.xml
    """
    try:
        # Load source and target configurations
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)

        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)

        # Create policy merger
        merger = PolicyMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version,
        )

        # Determine policy types based on device type
        policy_types = POLICY_TYPES.get(source_device_type.lower(), [])

        if not policy_types:
            logger.error(f"Unknown device type: {source_device_type}")
            raise typer.Exit(1)

        # Merge all policy types
        results = merger.merge_all_policies(
            policy_types,
            source_context,
            target_context,
            skip_if_exists,
            copy_references,
            conflict_strategy=conflict_strategy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys,
        )

        # Calculate total policies merged
        total_copied = sum(copied for copied, _ in results.values())
        total_attempted = sum(total for _, total in results.values())

        if total_copied > 0:
            logger.info(
                f"Successfully merged {total_copied} of {total_attempted} policies across all policy types"
            )

            # Log details per policy type
            for policy_type, (copied, total) in results.items():
                if total > 0:
                    logger.info(f"  - {policy_type}: {copied} of {total} policies merged")

            # Log copied objects
            if copy_references and merger.copied_objects:
                logger.info(f"Copied {len(merger.copied_objects)} referenced objects")

                # Count by type
                object_counts = {}
                for obj_type, _ in merger.copied_objects:
                    object_counts[obj_type] = object_counts.get(obj_type, 0) + 1

                for obj_type, count in object_counts.items():
                    logger.info(f"  - {obj_type}: {count} objects copied")

            # Save the updated configuration if not in dry run mode
            if not dry_run:
                if save_config(target_tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.info(f"Dry run mode: Changes NOT saved to {output_file}")
                logger.info(
                    f"If this was not a dry run, the following changes would have been made:"
                )
                logger.info(
                    f"  - {total_copied} policies would be added to {target_context} across all policy types"
                )
                for policy_type, (copied, total) in results.items():
                    if total > 0:
                        logger.info(
                            f"    - {policy_type}: {copied} of {total} policies would be merged"
                        )
                if copy_references and merger.copied_objects:
                    logger.info(
                        f"  - {len(merger.copied_objects)} referenced objects would be copied"
                    )
        else:
            logger.warning(f"No policies were merged (attempted {total_attempted})")

            if merger.skipped_policies:
                for name, reason in merger.skipped_policies[:10]:  # Show first 10
                    logger.warning(f"  - {name}: {reason}")

                if len(merger.skipped_policies) > 10:
                    logger.warning(f"  ... and {len(merger.skipped_policies) - 10} more")

            raise typer.Exit(1)

    except Exception as e:
        logger.error(f"Error merging all policies: {e}")
        raise typer.Exit(1)


@merge_app.command("objects")
def merge_objects(
    source_config: str = typer.Option(
        ..., "--source-config", help="Path to source XML configuration file"
    ),
    target_config: str = typer.Option(
        ..., "--target-config", help="Path to target XML configuration file"
    ),
    object_type: str = ObjectOptions.object_type(),
    names_file: Optional[str] = typer.Option(
        None, "--names-file", help="File containing object names to merge (one per line)"
    ),
    criteria_file: Optional[str] = typer.Option(
        None, "--criteria", help="JSON file with filter criteria"
    ),
    query_filter: Optional[str] = typer.Option(
        None,
        "--query-filter",
        "-q",
        help="Graph query filter to select objects (e.g., 'MATCH (a:address) WHERE a.value CONTAINS \"10.1.1\"')",
    ),
    source_context: str = typer.Option(
        "shared", "--source-context", help="Source context (shared, device_group, vsys)"
    ),
    target_context: str = typer.Option(
        "shared", "--target-context", help="Target context (shared, device_group, vsys)"
    ),
    source_device_group: Optional[str] = typer.Option(
        None, "--source-dg", help="Source device group name"
    ),
    target_device_group: Optional[str] = typer.Option(
        None, "--target-dg", help="Target device group name"
    ),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option(
        "panorama", "--source-type", help="Source device type (firewall or panorama)"
    ),
    target_device_type: str = typer.Option(
        "panorama", "--target-type", help="Target device type (firewall or panorama)"
    ),
    source_version: Optional[str] = typer.Option(
        None, "--source-version", help="Source PAN-OS version"
    ),
    target_version: Optional[str] = typer.Option(
        None, "--target-version", help="Target PAN-OS version"
    ),
    skip_if_exists: bool = typer.Option(
        True,
        "--skip-if-exists/--replace",
        help="Skip if object already exists (deprecated, use conflict_strategy instead)",
    ),
    copy_references: bool = MergeOptions.copy_references(),
    conflict_strategy: Optional[ConflictStrategy] = MergeOptions.conflict_strategy(),
    dry_run: bool = ConfigOptions.dry_run(),
    output_file: str = ConfigOptions.output_file(),
):
    """Merge multiple objects from source configuration to target configuration

    Example:
        panflow merge objects --source-config source.xml --target-config target.xml --type address --names-file address_names.txt
    """
    try:
        # Load source and target configurations
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)

        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)

        # Create object merger
        merger = ObjectMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version,
        )

        # Get object names or criteria
        object_names = None
        filter_criteria = None

        if names_file:
            with open(names_file, "r") as f:
                object_names = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(object_names)} object names from {names_file}")

        if criteria_file:
            with open(criteria_file, "r") as f:
                filter_criteria = json.load(f)
            logger.info(f"Loaded criteria from {criteria_file}: {filter_criteria}")

        # Process query filter if specified
        if query_filter:
            logger.info(f"Using graph query filter: {query_filter}")

            # Build the graph from source configuration
            graph = ConfigGraph()
            graph.build_from_xml(source_tree)

            # Prepare a query that returns object names
            # If the query doesn't already have a RETURN clause, append one that returns object names
            if "RETURN" not in query_filter.upper():
                query_text = f"{query_filter} RETURN a.name"
            else:
                query_text = query_filter

            # Execute the query
            query = Query(query_text)
            executor = QueryExecutor(graph)
            results = executor.execute(query)

            # Extract object names from the results
            query_object_names = []
            for row in results:
                if "a.name" in row:
                    query_object_names.append(row["a.name"])

            logger.info(f"Query matched {len(query_object_names)} objects")

            # If object_names is already set, extend it with query results
            if object_names:
                object_names.extend(query_object_names)
            # Otherwise, set object_names to query results
            else:
                object_names = query_object_names

        if not object_names and not filter_criteria:
            logger.error(
                "Either object names file, criteria file, or query filter must be provided"
            )
            raise typer.Exit(1)

        # Merge the objects
        copied, total = merger.copy_objects(
            object_type,
            source_context,
            target_context,
            object_names,
            filter_criteria,
            skip_if_exists,
            copy_references,
            conflict_strategy=conflict_strategy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys,
        )

        if copied > 0:
            logger.info(f"Successfully merged {copied} of {total} {object_type} objects")

            # Save the updated configuration if not in dry run mode
            if not dry_run:
                if save_config(target_tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.info(f"Dry run mode: Changes NOT saved to {output_file}")
                logger.info(
                    f"If this was not a dry run, the following changes would have been made:"
                )
                logger.info(
                    f"  - {copied} {object_type} objects would be added to {target_context}"
                )
        else:
            logger.warning(f"No {object_type} objects were merged (attempted {total})")

            if merger.skipped_objects:
                for obj_type, name, reason in merger.skipped_objects[:10]:  # Show first 10
                    logger.warning(f"  - {obj_type} '{name}': {reason}")

                if len(merger.skipped_objects) > 10:
                    logger.warning(f"  ... and {len(merger.skipped_objects) - 10} more")

            raise typer.Exit(1)

    except Exception as e:
        logger.error(f"Error merging objects: {e}")
        raise typer.Exit(1)


@merge_app.command("all-objects")
def merge_all_objects(
    source_config: str = typer.Option(
        ..., "--source-config", help="Path to source XML configuration file"
    ),
    target_config: str = typer.Option(
        ..., "--target-config", help="Path to target XML configuration file"
    ),
    source_context: str = typer.Option(
        "shared", "--source-context", help="Source context (shared, device_group, vsys)"
    ),
    target_context: str = typer.Option(
        "shared", "--target-context", help="Target context (shared, device_group, vsys)"
    ),
    source_device_group: Optional[str] = typer.Option(
        None, "--source-dg", help="Source device group name"
    ),
    target_device_group: Optional[str] = typer.Option(
        None, "--target-dg", help="Target device group name"
    ),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option(
        "panorama", "--source-type", help="Source device type (firewall or panorama)"
    ),
    target_device_type: str = typer.Option(
        "panorama", "--target-type", help="Target device type (firewall or panorama)"
    ),
    source_version: Optional[str] = typer.Option(
        None, "--source-version", help="Source PAN-OS version"
    ),
    target_version: Optional[str] = typer.Option(
        None, "--target-version", help="Target PAN-OS version"
    ),
    skip_if_exists: bool = typer.Option(
        True,
        "--skip-if-exists/--replace",
        help="Skip if object already exists (deprecated, use conflict_strategy instead)",
    ),
    copy_references: bool = MergeOptions.copy_references(),
    conflict_strategy: Optional[ConflictStrategy] = MergeOptions.conflict_strategy(),
    dry_run: bool = ConfigOptions.dry_run(),
    output_file: str = ConfigOptions.output_file(),
):
    """Merge all object types from source configuration to target configuration

    Example:
        panflow merge all-objects --source-config source.xml --target-config target.xml
    """
    try:
        # Load source and target configurations
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)

        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)

        # Create object merger
        merger = ObjectMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version,
        )

        # Determine object types to merge
        object_types = [
            "address",
            "address_group",
            "service",
            "service_group",
            "application_group",
            "tag",
        ]

        # Merge all object types
        results = merger.merge_all_objects(
            object_types,
            source_context,
            target_context,
            skip_if_exists,
            copy_references,
            conflict_strategy=conflict_strategy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys,
        )

        # Calculate total objects merged
        total_copied = sum(copied for copied, _ in results.values())
        total_attempted = sum(total for _, total in results.values())

        if total_copied > 0:
            logger.info(
                f"Successfully merged {total_copied} of {total_attempted} objects across all types"
            )

            # Log details per object type
            for object_type, (copied, total) in results.items():
                if total > 0:
                    logger.info(f"  - {object_type}: {copied} of {total} objects merged")

            # Save the updated configuration if not in dry run mode
            if not dry_run:
                if save_config(target_tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            else:
                logger.info(f"Dry run mode: Changes NOT saved to {output_file}")
                logger.info(
                    f"If this was not a dry run, the following changes would have been made:"
                )
                logger.info(
                    f"  - {total_copied} objects would be added to {target_context} across all object types"
                )
                for object_type, (copied, total) in results.items():
                    if total > 0:
                        logger.info(
                            f"    - {object_type}: {copied} of {total} objects would be merged"
                        )
        else:
            logger.warning(f"No objects were merged (attempted {total_attempted})")

            if merger.skipped_objects:
                for obj_type, name, reason in merger.skipped_objects[:10]:  # Show first 10
                    logger.warning(f"  - {obj_type} '{name}': {reason}")

                if len(merger.skipped_objects) > 10:
                    logger.warning(f"  ... and {len(merger.skipped_objects) - 10} more")

            raise typer.Exit(1)

    except Exception as e:
        logger.error(f"Error merging all objects: {e}")
        raise typer.Exit(1)
