# Mastering PAN-OS CLI for bulk policy operations

PAN-OS provides powerful tools for network administrators to query, filter, and modify security policies in bulk. While the exact term "PQL" isn't widely documented, the filtering syntax and operational capabilities of PAN-OS CLI enable sophisticated policy management at scale.

## What you need to know about PAN-OS policy operations

PAN-OS offers robust policy filtering capabilities through CLI that allow admins to identify and modify multiple security policies based on specific criteria. This filtering syntax is essential for bulk operations, allowing precise targeting of policies that need to be updated. Combined with bulk configuration techniques, these capabilities enable efficient management of complex policy environments.

Before diving into the technical details, it's important to understand that PAN-OS CLI supports several approaches to bulk policy operations, including direct CLI commands, XML API manipulation, and third-party tools. The methods in this guide are focused primarily on CLI-based approaches that can be implemented in any PAN-OS environment without additional dependencies.

### PAN-OS policy filtering syntax

The foundation of bulk policy operations is the ability to precisely identify which policies to modify. PAN-OS uses a consistent pattern for filtering security policies in the CLI:

```
(attribute/member operator 'value')
```

Where:
- `attribute` is the policy field to filter on
- `operator` can be `eq` (equals), `neq` (not equals), or `contains`
- `value` is what you're matching against

Multiple conditions can be combined using logical operators (`and`, `or`) and grouped with parentheses.

## Filtering security policies by criteria

### Finding policies by zone

To identify all policies with a specific source zone:

```
(from/member eq 'Trust')
```

Or destination zone:

```
(to/member eq 'Untrust')
```

### Finding policies by address objects

For policies using specific address objects:

```
(source/member eq 'internal-server')
(destination/member eq 'internet-services')
```

Or IP addresses:

```
(source/member eq '192.168.1.100')
(destination/member eq '10.0.0.0/24')
```

### Finding policies by services and applications

Filter by service:

```
(service/member eq 'service-http')
(service/member eq 'application-default')
```

Filter by application:

```
(application/member eq 'web-browsing')
(application/member eq 'ssl')
```

### Other useful filters

Find policies by action:

```
(action eq 'allow')
(action eq 'deny')
```

Find disabled policies:

```
(disabled eq yes)
```

Find policies with specific security profiles:

```
(profile-setting/profiles/virus/member eq 'strict-antivirus')
```

Find policies with specific tags:

```
(tag/member eq 'compliance')
```

### Complex filter examples

Find all policies allowing traffic from Trust to Untrust for web browsing:

```
(from/member eq 'Trust') and (to/member eq 'Untrust') and (application/member eq 'web-browsing') and (action eq 'allow')
```

Find all policies using either HTTP or HTTPS:

```
(service/member eq 'service-http') or (service/member eq 'service-https')
```

## Methods for bulk updates through CLI

The most direct approach for bulk policy operations is through the CLI using the "set" command format. This process involves:

1. Setting CLI to output in "set" format
2. Identifying policies to modify using filters
3. Performing bulk changes with set commands

### Step 1: Configure CLI output format

```
> set cli config-output-format set
> configure
```

### Step 2: Identify policies to modify

```
# show rulebase security rules | match "Trust"
```

### Step 3: Bulk update the identified policies

The following examples illustrate different types of bulk updates:

**Adding security profiles to multiple rules:**

```
# set rulebase security rules Rule-1 profile-setting profiles virus AV-Profile
# set rulebase security rules Rule-2 profile-setting profiles virus AV-Profile
# set rulebase security rules Rule-3 profile-setting profiles virus AV-Profile
# commit
```

**Applying security profile groups to multiple policies:**

```
# set rulebase security rules Rule-1 profile-setting group Security-Profile-Group
# set rulebase security rules Rule-2 profile-setting group Security-Profile-Group
# set rulebase security rules Rule-3 profile-setting group Security-Profile-Group
# commit
```

## Bulk tagging operations

Adding tags to multiple policies is straightforward:

```
# set rulebase security rules Internet-Outbound tag Compliance
# set rulebase security rules Database-Access tag Compliance
# set rulebase security rules Payment-Processing tag Compliance
# commit
```

To remove a tag from multiple policies:

```
# delete rulebase security rules Internet-Outbound tag Compliance
# delete rulebase security rules Database-Access tag Compliance
# commit
```

## Managing policies across different contexts

PAN-OS arranges policies in a hierarchical structure:
- Shared policies (applied globally)
- Device group policies (specific to device groups)
- Local firewall policies

When performing bulk operations, specify the context by adjusting your commands:

**For shared policies in Panorama:**

```
# set shared rulebase security rules Rule-1 profile-setting profiles virus AV-Profile
```

**For device group policies in Panorama:**

```
# set device-group DG1 rulebase security rules Rule-1 profile-setting profiles virus AV-Profile
```

**For local firewall policies:**

```
# set rulebase security rules Rule-1 profile-setting profiles virus AV-Profile
```

## Practical examples for production environments

### Example 1: Bulk zone update

Scenario: Move all policies from an old DMZ zone to a new DMZ zone.

```
> set cli config-output-format set
> configure

# Show affected rules
# show rulebase security rules | match "old-dmz"

# Update source zone
# set rulebase security rules Rule-1 from new-dmz
# set rulebase security rules Rule-2 from new-dmz

# Update destination zone
# set rulebase security rules Rule-3 to new-dmz
# set rulebase security rules Rule-4 to new-dmz

# Commit changes
# commit
```

### Example 2: Update all outbound rules with new URL filtering profile

```
> set cli config-output-format set
> configure

# First identify all outbound rules
# show rulebase security rules | match "(from/member eq 'Trust') and (to/member eq 'Internet')"

# Then apply the URL filtering profile to each
# set rulebase security rules Outbound-Web profile-setting profiles url-filtering Strict-URL-Filter
# set rulebase security rules Outbound-Apps profile-setting profiles url-filtering Strict-URL-Filter

# Commit
# commit
```

### Example 3: Complex policy modification using predefined filters

First, identify rules using a critical application that need security profile updates:

```
> configure
# show rulebase security rules | match "(application/member eq 'salesforce') and (action eq 'allow')"
```

Then update all matching rules with a new security profile group:

```
# set rulebase security rules Sales-App-1 profile-setting group Enhanced-Security
# set rulebase security rules Sales-App-2 profile-setting group Enhanced-Security
# set rulebase security rules Partner-Access profile-setting group Enhanced-Security
# commit
```

### Example 4: Log forwarding profile bulk update

To apply a new log forwarding profile to all rules with a specific tag:

```
> configure
# show rulebase security rules | match "(tag/member eq 'PCI')"

# Then update all matching rules
# set rulebase security rules PCI-Web log-setting Enhanced-Logging
# set rulebase security rules PCI-DB log-setting Enhanced-Logging
# set rulebase security rules PCI-Auth log-setting Enhanced-Logging
# commit
```

## Best practices for configuration management

### 1. Verify changes before committing

Always validate your configuration before committing changes:

```
# validate full
```

Check the difference between running and candidate configurations:

```
# show config diff
```

### 2. Test traffic matching after changes

Use the test command to verify policy matches:

```
> test security-policy-match source 10.1.1.100 destination 8.8.8.8 destination-port 443 application web-browsing protocol 6
```

### 3. Commit with partial scope

When making extensive changes, consider limiting the commit scope:

```
# commit partial policy-and-objects
```

### 4. Use the CLI scripting mode for large batches

For very large sets of commands:

```
> configure
# set cli scripting-mode on
# [paste multiple commands]
# set cli scripting-mode off
# commit
```

### 5. Staged approach for critical environments

For production environments, use a phased approach:
1. Export the current configuration
2. Make changes in a non-production environment first
3. Test thoroughly
4. Apply to production during a maintenance window

## Limitations and potential issues

1. **Transaction size limits**: Very large bulk operations may need to be broken into smaller batches to prevent timeout issues.

2. **Session management**: Long-running operations might time out, especially when dealing with hundreds of policies.

3. **Concurrency issues**: Avoid having multiple administrators making simultaneous bulk changes, which can cause conflicts.

4. **Performance impact**: Extensive use of filtering with complex criteria can be resource-intensive on the management plane.

5. **Validation complexity**: Changes across different policy contexts (shared, device group, local) require careful validation.

## Using XML API for more advanced bulk operations

For more complex operations beyond CLI capabilities, the XML API offers a programmatic approach:

1. Obtain an API key:
```
https://<firewall>/api/?type=keygen&user=<username>&password=<password>
```

2. Use XPath to identify policies:
```
https://<firewall>/api/?type=config&action=get&xpath=/config/devices/entry/vsys/entry/rulebase/security/rules/entry[to/member='untrust']&key=<API_KEY>
```

3. Apply changes to identified policies:
```
https://<firewall>/api/?type=config&action=set&xpath=/config/devices/entry/vsys/entry/rulebase/security/rules/entry[@name='Rule-1']/profile-setting/profiles/virus&element=<member>AV-Profile</member>&key=<API_KEY>
```

## Conclusion

Mastering PAN-OS CLI capabilities for bulk policy operations can dramatically improve efficiency in managing complex firewall environments. By combining the filtering syntax with bulk update techniques, administrators can implement changes quickly and consistently across large policy sets.

Whether you're updating security profiles, adding tags, or modifying rule actions, the approaches outlined in this guide provide practical methods that can be adapted to a wide range of operational requirements. Always follow the verification steps and best practices to ensure changes are applied correctly and securely in your environment.