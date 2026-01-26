# time_offset_days Configuration Design Decision

## Question

Why is `time_offset_days` configured under `jira.environments` when it applies to BOTH GitHub and Jira collectors?

## Answer

Although `time_offset_days` affects both collectors (as of 2026-01-26), it remains under `jira.environments` for the following reasons:

### 1. Backward Compatibility

The multi-environment configuration was introduced with `time_offset_days` under `jira.environments`. Moving it would be a breaking change requiring all users to update their configs.

### 2. Jira-Driven Use Case

The primary reason for time offsets is **Jira UAT databases**:
- Jira UAT: Database snapshot from the past (e.g., 6 months old)
- GitHub: Always current (no historical snapshots)

The offset exists to align GitHub's current data with Jira's historical snapshot. Since Jira drives this need, it makes sense to configure it there.

### 3. Single Source of Truth

Having `time_offset_days` in one location prevents duplication and configuration drift:

**Current (Good):**
```yaml
jira:
  environments:
    uat:
      time_offset_days: 180  # Single source of truth
```

**Alternative (Prone to Drift):**
```yaml
github:
  time_offset_days: 180
jira:
  environments:
    uat:
      time_offset_days: 180  # Duplicate! Could get out of sync
```

### 4. Environment Context

UAT vs Production environments are primarily differentiated by their Jira configuration:
- Different servers (jira.company.com vs jira-uat.company.com)
- Different credentials
- Different time offsets
- Different pagination settings

GitHub configuration is largely the same across environments (same token, same organization).

## Implementation Details

The code in `collect_data.py` reads the offset from Jira config:

```python
jira_env_config = config.get_jira_environment(env)
time_offset_days = jira_env_config.get("time_offset_days", 0)

# Apply to BOTH collectors
github_collector = GitHubGraphQLCollector(
    token=github_token,
    # ...
    time_offset_days=time_offset_days  # Pass from Jira config
)

jira_collector = JiraCollector(
    server=jira_env_config["server"],
    # ...
    time_offset_days=time_offset_days
)
```

## Documentation

The config example clearly states:

```yaml
jira:
  environments:
    uat:
      time_offset_days: 180  # UAT is 6 months behind
                            # NOTE: Applies to BOTH GitHub and Jira collectors
                            # GitHub: Queries current API, filters by dates from 180 days ago
                            # Jira: Queries UAT database (snapshot from 180 days ago)
```

## Alternative Design (Future Consideration)

In a future major version (2.0), we could restructure to make this more explicit:

```yaml
environments:
  prod:
    time_offset_days: 0
    github:
      token: "..."
      organization: "..."
    jira:
      server: "https://jira.company.com"
      username: "..."
      api_token: "..."
  uat:
    time_offset_days: 180
    github:
      # Same as prod (or omit and inherit)
    jira:
      server: "https://jira-uat.company.com"
      username: "..."
      api_token: "..."
```

**Benefits:**
- More explicit that offset applies to entire environment
- GitHub and Jira are clearly peers under environment

**Drawbacks:**
- Breaking change (requires all users to update configs)
- More complex migration path
- GitHub config duplication (most fields are identical across environments)

## Conclusion

The current design (`time_offset_days` under `jira.environments`) is:
- ✅ Backward compatible
- ✅ Clearly documented
- ✅ Appropriate for the Jira-driven use case
- ✅ Single source of truth (no duplication)

The alternative design would be cleaner conceptually but requires a major version bump and migration effort. For now, the pragmatic choice is to keep the current structure with clear documentation.

## Related Documentation

- `docs/TIME_OFFSET_FIX.md` - Implementation details
- `CLAUDE.md` - Usage documentation
- `config/config.example.yaml` - Configuration examples
