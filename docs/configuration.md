# Configuration

Stoat reads configuration from:

```bash
~/.config/stoat/config.toml
```

You can override the config path for a single run with:

```bash
STOAT_CONFIG_PATH=/path/to/config.toml stoat doctor --json
```

## Active Configuration Keys

### `llm`

Optional parser-backend settings. The current CLI works without any LLM.

```toml
[llm]
model = "llama3.2:3b-instruct-q4_K_M"
base_url = "http://localhost:11434"
temperature = 0.1
max_tokens = 512
timeout = 30
```

### `safety`

```toml
[safety]
require_confirmation = ["delete", "move", "undo"]
protected_paths = ["/etc", "/usr", "/bin", "/boot", "/sys", "/proc"]
max_batch_size = 100
enable_undo = true
```

### `search`

```toml
[search]
index_hidden_files = false
max_results = 50
use_locate = true
fuzzy_threshold = 0.6
```

### `logging`

```toml
[logging]
level = "INFO"
format = "json"
file = "~/.local/share/stoat/logs/stoat.log"
max_size_mb = 10
backup_count = 5
```

### `undo`

```toml
[undo]
max_history = 50
retention_days = 7
storage_path = "~/.cache/stoat/undo"
```

## Example

```toml
[safety]
require_confirmation = ["delete", "move", "undo"]
protected_paths = ["/etc", "/usr", "/bin", "/boot", "/sys", "/proc"]
max_batch_size = 25
enable_undo = true

[search]
index_hidden_files = false
max_results = 20
use_locate = false
fuzzy_threshold = 0.6

[logging]
level = "INFO"
format = "json"
file = "~/.local/share/stoat/logs/stoat.log"
max_size_mb = 10
backup_count = 5

[undo]
max_history = 25
retention_days = 14
storage_path = "~/.cache/stoat/undo"
```

## Validation Notes

- Invalid logging levels fail config loading.
- Invalid `require_confirmation` actions fail config loading.
- Invalid numeric bounds, like a negative batch size, fail config loading.
- Use `stoat doctor --json` to verify the resolved config path and runtime paths.
