"""Print a credential-free curl example for every official developer operation.

python examples/list_examples.py --operation 'GET /developer/v1/account/user/me'
python examples/list_examples.py --all > /tmp/musecat-api-examples.sh
The output contains placeholders. Review it; do not execute the whole file.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from partner.api_examples import OPERATIONS, curl_example, select_media

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--operation", choices=OPERATIONS)
parser.add_argument("--all", action="store_true")
parser.add_argument("--issuer", default="https://db-dev.musecat.app")
args = parser.parse_args()
if args.all or args.operation:
    for operation in (
        [OPERATIONS[args.operation]] if args.operation else OPERATIONS.values()
    ):
        for media in operation["request_content"] or {"": {}}:
            selected = select_media(operation, media)
            print(
                "#", operation["id"], media, "scopes:", ", ".join(operation["scopes"])
            )
            print(curl_example(selected, args.issuer))
            print()
else:
    for name in OPERATIONS:
        print(name)
