# Architecture Documentation - Team Metrics Dashboard

**Last Updated**: January 16, 2026

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [DORA Metrics Pipeline](#dora-metrics-pipeline)
5. [Caching Strategy](#caching-strategy)
6. [Deployment Architecture](#deployment-architecture)

---

## System Overview

The Team Metrics Dashboard is a Python-based application that collects, processes, and visualizes engineering team metrics from GitHub and Jira.

### High-Level Architecture

```mermaid
graph TB
    subgraph "Data Sources"
        GH[GitHub GraphQL API]
        JR[Jira REST API]
    end

    subgraph "Collection Layer"
        GHC[GitHub Collector]
        JRC[Jira Collector]
        RC[Repository Cache]
    end

    subgraph "Processing Layer"
        MC[Metrics Calculator]
        DORA[DORA Calculator]
        PS[Performance Scorer]
    end

    subgraph "Storage Layer"
        PKL[Pickle Cache Files]
        LOG[JSON Log Files]
    end

    subgraph "Presentation Layer"
        FLASK[Flask Dashboard]
        API[Export APIs]
        TPL[Jinja Templates]
    end

    subgraph "Users"
        WEB[Web Browser]
    end

    GH --> GHC
    JR --> JRC
    RC -.24h cache.-> GHC
    
    GHC --> MC
    JRC --> MC
    
    MC --> DORA
    MC --> PS
    
    MC --> PKL
    DORA --> PKL
    PS --> PKL
    
    PKL --> FLASK
    FLASK --> TPL
    FLASK --> API
    
    TPL --> WEB
    API --> WEB
    
    GHC -.logs.-> LOG
    JRC -.logs.-> LOG
    MC -.logs.-> LOG
    
    style GH fill:#2ecc71
    style JR fill:#3498db
    style PKL fill:#e74c3c
    style FLASK fill:#9b59b6
    style WEB fill:#f39c12
```

---

## Component Architecture

### Collectors

```mermaid
classDiagram
    class GitHubGraphQLCollector {
        +String token
        +String organization
        +Session session
        +collect_repository_metrics(owner, repo, since, until)
        +collect_team_repositories(team_slug)
        -_execute_graphql_query(query, variables)
        -_extract_pr_data(pr_node)
        -_extract_review_data(pr_node)
        -_extract_commit_data(pr_node)
        -_is_pr_in_date_range(pr, since, until)
    }

    class JiraCollector {
        +String server
        +String username
        +JIRA jira_client
        +collect_issue_metrics(project_key)
        +collect_person_issues(username)
        +collect_filter_results(filter_id)
        +collect_releases(project_key, team_members)
        -_parse_fix_version_name(version_name)
        -_get_issues_for_version(project, version)
    }

    class RepositoryCache {
        +get_cached_repositories(org, teams)
        +save_cached_repositories(org, teams, repos)
        -_get_cache_key(org, teams)
        -_is_cache_fresh(cache_data)
    }

    GitHubGraphQLCollector --> RepositoryCache : uses
```

### Models

The metrics calculation system is organized into 4 focused modules using mixin inheritance and delegation patterns:

```mermaid
classDiagram
    class MetricsCalculator {
        +Dict~DataFrame~ dfs
        +calculate_pr_metrics()
        +calculate_review_metrics()
        +calculate_contributor_metrics()
        +calculate_team_metrics(team_config, jira_data)
        +calculate_person_metrics(username, github_username)
        +calculate_team_comparison(teams_data)
    }

    class DORAMetrics {
        <<mixin>>
        +calculate_deployment_frequency(releases, days)
        +calculate_lead_time_for_changes(prs, releases)
        +calculate_change_failure_rate(releases, incidents)
        +calculate_mttr(incidents)
        +calculate_dora_performance_level(metrics)
        +_calculate_dora_trends(metrics, period)
    }

    class JiraMetrics {
        <<mixin>>
        +_process_jira_filters(team_config, jira_data)
        +_calculate_throughput_metrics(issues)
        +_calculate_wip_metrics(issues)
        +_calculate_bug_metrics(issues)
        +_calculate_scope_trend(issues)
    }

    class PerformanceScorer {
        <<static utility>>
        +normalize(value, min_val, max_val)$
        +calculate_performance_score(metrics, all_metrics)$
        +calculate_weighted_score(metrics, weights)$
        +normalize_team_size(metrics, team_size)$
        +DEFAULT_WEIGHTS
    }

    MetricsCalculator --|> DORAMetrics : inherits from
    MetricsCalculator --|> JiraMetrics : inherits from
    MetricsCalculator ..> PerformanceScorer : delegates to
```

**Module Organization:**
- **metrics.py** (605 lines) - Core MetricsCalculator with orchestration logic
- **dora_metrics.py** (635 lines) - DORAMetrics mixin for DevOps Research metrics
- **jira_metrics.py** (226 lines) - JiraMetrics mixin for Jira filter processing
- **performance_scoring.py** (270 lines) - PerformanceScorer static class for scoring utilities

---

## Data Flow

### Collection to Dashboard Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI as collect_data.py
    participant GHC as GitHub Collector
    participant JRC as Jira Collector
    participant MC as Metrics Calculator
    participant Cache
    participant Dashboard

    User->>CLI: python collect_data.py --date-range 90d
    
    CLI->>GHC: Initialize with token
    CLI->>JRC: Initialize with credentials
    
    par Parallel Collection
        GHC->>GHC: Collect PRs, Reviews, Commits
        JRC->>JRC: Collect Issues, Releases
    end
    
    GHC-->>CLI: Return raw data
    JRC-->>CLI: Return raw data
    
    CLI->>MC: Create calculator with DataFrames
    MC->>MC: Calculate all metrics
    MC-->>CLI: Return computed metrics
    
    CLI->>Cache: Save to metrics_cache_90d.pkl
    Cache-->>CLI: Confirm saved
    
    CLI-->>User: Collection complete
    
    Note over User,Dashboard: Later...
    
    User->>Dashboard: Access http://localhost:5001
    Dashboard->>Cache: Load metrics_cache_90d.pkl
    Cache-->>Dashboard: Return metrics data
    Dashboard->>Dashboard: Render templates
    Dashboard-->>User: Display HTML page
```

### Parallel Collection Strategy

```mermaid
graph TB
    subgraph "Main Thread"
        START[Start Collection]
        SETUP[Setup Collectors]
        POOL[Create ThreadPool]
        WAIT[Wait for Completion]
        CALC[Calculate Metrics]
        SAVE[Save Cache]
        END[Complete]
    end

    subgraph "Thread Pool (3-5 workers)"
        T1[Team 1 Collection]
        T2[Team 2 Collection]
        T3[Team 3 Collection]
        
        subgraph "Per Team (5 workers)"
            R1[Repo 1]
            R2[Repo 2]
            R3[Repo 3]
            R4[Repo 4]
            R5[Repo 5]
        end
        
        subgraph "Per Person (8 workers)"
            P1[Person 1]
            P2[Person 2]
            P3[Person 3]
        end
    end

    START --> SETUP
    SETUP --> POOL
    POOL --> T1
    POOL --> T2
    POOL --> T3
    
    T1 --> R1
    T1 --> R2
    T1 --> R3
    T1 --> R4
    T1 --> R5
    
    T2 --> P1
    T2 --> P2
    T2 --> P3
    
    R1 --> WAIT
    R2 --> WAIT
    R3 --> WAIT
    P1 --> WAIT
    P2 --> WAIT
    
    WAIT --> CALC
    CALC --> SAVE
    SAVE --> END

    style START fill:#2ecc71
    style END fill:#2ecc71
    style POOL fill:#3498db
    style CALC fill:#f39c12
```

---

## DORA Metrics Pipeline

### DORA Calculation Flow

```mermaid
flowchart TD
    START[Start DORA Calculation]
    
    subgraph "Data Collection"
        GH_REL[GitHub Releases]
        JIRA_REL[Jira Fix Versions]
        JIRA_INC[Jira Incidents]
        GH_PRS[GitHub PRs]
    end

    subgraph "Processing"
        FILTER[Filter Production Releases]
        MAP_PRS[Map PRs to Releases]
        CALC_DF[Calculate Deployment Frequency]
        CALC_LT[Calculate Lead Time]
        CALC_CFR[Calculate Change Failure Rate]
        CALC_MTTR[Calculate MTTR]
    end

    subgraph "Classification"
        METRICS[DORA Metrics Object]
        CLASSIFY[Classify Performance Level]
        LEVEL{Performance Level}
    end

    START --> GH_REL
    START --> JIRA_REL
    START --> JIRA_INC
    START --> GH_PRS

    GH_REL --> FILTER
    JIRA_REL --> FILTER
    
    FILTER --> CALC_DF
    FILTER --> MAP_PRS
    
    GH_PRS --> MAP_PRS
    MAP_PRS --> CALC_LT
    
    FILTER --> CALC_CFR
    JIRA_INC --> CALC_CFR
    JIRA_INC --> CALC_MTTR
    
    CALC_DF --> METRICS
    CALC_LT --> METRICS
    CALC_CFR --> METRICS
    CALC_MTTR --> METRICS
    
    METRICS --> CLASSIFY
    CLASSIFY --> LEVEL
    
    LEVEL -->|High DF, Low LT| ELITE[Elite]
    LEVEL -->|Good metrics| HIGH[High]
    LEVEL -->|Mixed metrics| MEDIUM[Medium]
    LEVEL -->|Poor metrics| LOW[Low]
    
    style START fill:#2ecc71
    style METRICS fill:#f39c12
    style ELITE fill:#2ecc71
    style HIGH fill:#3498db
    style MEDIUM fill:#f39c12
    style LOW fill:#e74c3c
```

### Release Filtering Logic

```mermaid
flowchart TD
    START[Raw Releases]
    
    CHECK1{Is Released?}
    CHECK2{Released >= Status Check?}
    CHECK3{Release Date < Now?}
    CHECK4{Matches Pattern?}
    CHECK5{Has Team Member?}
    
    SKIP1[Skip: Not Released]
    SKIP2[Skip: Future Release]
    SKIP3[Skip: Invalid Pattern]
    SKIP4[Skip: No Team Involvement]
    
    CLASSIFY{Environment?}
    PROD[Production Release]
    STAGING[Staging Release]
    
    COUNT[Count for DORA Metrics]
    
    START --> CHECK1
    CHECK1 -->|No| SKIP1
    CHECK1 -->|Yes| CHECK2
    CHECK2 -->|No| SKIP1
    CHECK2 -->|Yes| CHECK3
    CHECK3 -->|Yes| SKIP2
    CHECK3 -->|No| CHECK4
    CHECK4 -->|No| SKIP3
    CHECK4 -->|Yes| CHECK5
    CHECK5 -->|No| SKIP4
    CHECK5 -->|Yes| CLASSIFY
    
    CLASSIFY -->|Live, Website, RA_Web| PROD
    CLASSIFY -->|Beta, Preview| STAGING
    
    PROD --> COUNT
    
    style START fill:#3498db
    style COUNT fill:#2ecc71
    style SKIP1 fill:#95a5a6
    style SKIP2 fill:#95a5a6
    style SKIP3 fill:#95a5a6
    style SKIP4 fill:#95a5a6
    style PROD fill:#2ecc71
    style STAGING fill:#f39c12
```

---

## Caching Strategy

### Cache Layers

```mermaid
graph TB
    subgraph "Repository Cache (24h)"
        RC_KEY[Cache Key: MD5(org+teams)]
        RC_FILE[JSON File]
        RC_CHECK{Fresh?}
    end

    subgraph "Metrics Cache (User-defined)"
        MC_KEY[Cache Key: date_range]
        MC_FILE[Pickle File]
        MC_AGE{Age < duration?}
    end

    subgraph "Dashboard Memory Cache"
        DM_DATA[In-Memory Data]
        DM_TS[Timestamp]
    end

    APP[Application]
    
    APP -->|Request repos| RC_CHECK
    RC_CHECK -->|Yes| RC_FILE
    RC_CHECK -->|No| API1[GitHub API]
    API1 --> RC_FILE
    
    APP -->|Request metrics| MC_AGE
    MC_AGE -->|Yes| MC_FILE
    MC_AGE -->|No| COLLECT[Run Collection]
    COLLECT --> MC_FILE
    
    MC_FILE --> DM_DATA
    DM_TS -->|Check age| MC_AGE
    
    style RC_FILE fill:#3498db
    style MC_FILE fill:#e74c3c
    style DM_DATA fill:#9b59b6
    style API1 fill:#95a5a6
    style COLLECT fill:#f39c12
```

### Cache Filename Strategy

```mermaid
graph LR
    INPUT[Date Range Input]
    
    subgraph "Range Types"
        DAYS[30d, 90d, 365d]
        QUARTERS[Q1-2025, Q2-2024]
        YEARS[2024, 2025]
        CUSTOM[2024-01-01:2024-12-31]
    end

    subgraph "Cache Files"
        F1[metrics_cache_30d.pkl]
        F2[metrics_cache_Q1-2025.pkl]
        F3[metrics_cache_2024.pkl]
        F4[metrics_cache_custom_2024-01-01_2024-12-31.pkl]
    end

    INPUT --> DAYS
    INPUT --> QUARTERS
    INPUT --> YEARS
    INPUT --> CUSTOM

    DAYS --> F1
    QUARTERS --> F2
    YEARS --> F3
    CUSTOM --> F4

    style INPUT fill:#3498db
    style F1 fill:#2ecc71
    style F2 fill:#2ecc71
    style F3 fill:#2ecc71
    style F4 fill:#2ecc71
```

---

## Deployment Architecture

### Local Development

```mermaid
graph TB
    subgraph "Developer Machine"
        CODE[Source Code]
        VENV[Python venv]
        CONFIG[config.yaml]
        
        subgraph "Data Collection"
            SCRIPT[collect_data.py]
            CACHE[data/metrics_cache_*.pkl]
        end
        
        subgraph "Dashboard"
            FLASK[Flask Dev Server :5001]
            BROWSER[Web Browser]
        end
    end

    subgraph "External APIs"
        GITHUB[GitHub GraphQL]
        JIRA[Jira REST]
    end

    CODE --> VENV
    CONFIG --> SCRIPT
    SCRIPT --> GITHUB
    SCRIPT --> JIRA
    GITHUB --> CACHE
    JIRA --> CACHE
    
    CACHE --> FLASK
    FLASK --> BROWSER

    style CODE fill:#3498db
    style FLASK fill:#9b59b6
    style BROWSER fill:#f39c12
    style GITHUB fill:#2ecc71
    style JIRA fill:#3498db
```

### macOS Service Deployment

```mermaid
graph TB
    subgraph "macOS System"
        LAUNCHD[launchd]
        
        subgraph "Dashboard Service"
            PLIST1[com.team-metrics.dashboard.plist]
            SCRIPT1[scripts/start_dashboard.sh]
            FLASK[Flask App :5001]
            LOG1[logs/dashboard.log]
        end
        
        subgraph "Collection Service"
            PLIST2[com.team-metrics.collect.plist]
            SCRIPT2[scripts/collect_data.sh]
            COLLECT[collect_data.py]
            LOG2[logs/collect_data.log]
            CRON[Daily 10:00 AM]
        end
        
        subgraph "Storage"
            CACHE[data/*.pkl]
            REPO_CACHE[data/repo_cache/*.json]
        end
    end

    subgraph "Network"
        LOCALHOST[localhost:5001]
        GITHUB_API[GitHub API]
        JIRA_API[Jira API]
    end

    LAUNCHD --> PLIST1
    LAUNCHD --> PLIST2
    
    PLIST1 --> SCRIPT1
    SCRIPT1 --> FLASK
    FLASK -.logs.-> LOG1
    FLASK --> CACHE
    
    PLIST2 --> CRON
    CRON --> SCRIPT2
    SCRIPT2 --> COLLECT
    COLLECT -.logs.-> LOG2
    COLLECT --> GITHUB_API
    COLLECT --> JIRA_API
    COLLECT --> CACHE
    COLLECT --> REPO_CACHE
    
    FLASK --> LOCALHOST

    style LAUNCHD fill:#3498db
    style FLASK fill:#9b59b6
    style COLLECT fill:#f39c12
    style CACHE fill:#e74c3c
```

---

## Directory Structure

```
team_metrics/
├── src/
│   ├── collectors/          # Data collection
│   │   ├── github_graphql_collector.py
│   │   └── jira_collector.py
│   ├── models/              # Metrics calculation (4 focused modules)
│   │   ├── __init__.py                  # Backward compatibility exports
│   │   ├── metrics.py                   # Core MetricsCalculator (605 lines)
│   │   ├── dora_metrics.py              # DORAMetrics mixin (635 lines)
│   │   ├── jira_metrics.py              # JiraMetrics mixin (226 lines)
│   │   └── performance_scoring.py       # PerformanceScorer utilities (270 lines)
│   ├── dashboard/           # Flask app
│   │   ├── app.py
│   │   ├── templates/
│   │   └── static/
│   └── utils/               # Utilities
│       ├── date_ranges.py
│       ├── jira_filters.py
│       ├── repo_cache.py
│       └── logging/
├── tests/                   # Test suites
│   ├── unit/
│   ├── collectors/
│   ├── dashboard/
│   └── integration/
├── config/                  # Configuration
│   ├── config.yaml
│   └── logging.yaml
├── data/                    # Cache files
│   ├── metrics_cache_*.pkl
│   └── repo_cache/
├── logs/                    # Application logs
│   ├── team_metrics.log
│   └── team_metrics_error.log
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md
│   ├── API_DOCUMENTATION.md
│   └── TESTING.md
└── scripts/                 # Helper scripts
    ├── start_dashboard.sh
    └── collect_data.sh
```

---

## Performance Optimizations

### Optimization Stack

```mermaid
graph TB
    REQUEST[User Request]
    
    subgraph "Optimization Layers"
        L1[Repository Cache - 24h]
        L2[HTTP Connection Pool]
        L3[GraphQL Query Batching]
        L4[Parallel Collection]
        L5[Metrics Cache - Configurable]
    end

    subgraph "Performance Gains"
        G1[5-15s saved per collection]
        G2[5-10% speedup]
        G3[20-40% speedup + 50% fewer calls]
        G4[5-6x total speedup]
        G5[Zero latency for cached data]
    end

    REQUEST --> L1
    L1 --> L2
    L2 --> L3
    L3 --> L4
    L4 --> L5

    L1 -.-> G1
    L2 -.-> G2
    L3 -.-> G3
    L4 -.-> G4
    L5 -.-> G5

    style REQUEST fill:#3498db
    style L4 fill:#2ecc71
    style G4 fill:#f39c12
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Jinja2 + HTML/CSS/JS | Template rendering |
| **Charts** | Plotly.js | Interactive visualizations |
| **Backend** | Flask | Web framework |
| **Data Processing** | pandas | Metrics calculation |
| **APIs** | requests + GraphQL | Data collection |
| **Caching** | pickle + JSON | Data persistence |
| **Logging** | Python logging | Structured logs |
| **Testing** | pytest | Unit & integration tests |
| **CI/CD** | GitHub Actions | Automated testing |
| **Deployment** | launchd (macOS) | Service management |

---

## Security Considerations

1. **API Tokens**: Stored in `config.yaml` (gitignored)
2. **SSL Verification**: Optional for Jira (self-signed certs)
3. **Rate Limiting**: Built-in retry logic for GitHub API
4. **Input Validation**: All user inputs validated before processing
5. **XSS Protection**: Jinja2 auto-escaping enabled
6. **CORS**: Not required (same-origin policy)

---

## Scalability

### Current Limits

- **Teams**: Tested with 3-5 teams
- **Repositories**: Tested with 50+ repos per team
- **History**: 90-365 days of data
- **Team Members**: 5-15 members per team
- **API Calls**: ~1000-2000 per collection

### Scaling Strategies

1. **More Aggressive Caching**: Extend cache duration
2. **Incremental Updates**: Only fetch new data since last collection
3. **Database Backend**: Replace pickle with PostgreSQL/SQLite
4. **Async Collection**: Use asyncio instead of threads
5. **Multiple Instances**: Run separate instances per team

---

For more information, see:
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - API reference
- [CLAUDE.md](../CLAUDE.md) - Development guide
- [README.md](../README.md) - Project overview
