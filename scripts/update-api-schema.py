"""Convert the official YAML/JSON contract into the runtime's dependency-free snapshot.

Usage: python scripts/update-api-schema.py /path/to/developer-openapi.yaml
YAML input requires the optional development package PyYAML; JSON needs only Python.
"""

import json
from pathlib import Path
import sys

source = Path(sys.argv[1])
if source.suffix == ".json":
    spec = json.loads(source.read_text())
else:
    import yaml

    spec = yaml.safe_load(source.read_text())
assert spec["info"]["title"] == "Musecat Developer API"
assert "paths" in spec and all(path.startswith("/") for path in spec["paths"])
output = Path(__file__).resolve().parents[1] / "partner/developer-openapi.json"
output.write_text(json.dumps(spec, ensure_ascii=False, indent=2, default=str) + "\n")
print(f"Updated {len(spec['paths'])} paths from {source.name}")
