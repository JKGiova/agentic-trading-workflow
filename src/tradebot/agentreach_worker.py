"""Isolated read-only Agent Reach backends; secrets arrive on stdin, never argv."""

import json
import logging
import sys

MAX_BYTES = 2_000_000


def execute(payload):
    if payload["operation"] == "web":
        from agent_reach.channels.web import WebChannel

        text = WebChannel().read(payload["url"])
        if len(text.encode()) > MAX_BYTES:
            raise ValueError("Oversize source")
        return {"text": text}
    if payload["operation"] == "x":
        # Agent Reach selects this backend. Do not call the upstream CLI auth loader:
        # it can read unrelated browser profiles after invalid explicit cookies.
        from twitter_cli.client import TwitterClient
        from twitter_cli.serialization import tweet_to_dict

        client = TwitterClient(
            payload["auth_token"],
            payload["ct0"],
            rate_limit_config={"maxRetries": 0, "requestDelay": 1, "maxCount": 50},
        )
        tweets = client.fetch_search(payload["query"], count=50, product="Latest")
        return {
            "tweets": [tweet_to_dict(tweet) for tweet in tweets[:50]],
            "capped": len(tweets) >= 50,
        }
    raise ValueError("Unsupported operation")


def main():
    logging.disable(logging.CRITICAL)
    try:
        raw = sys.stdin.buffer.read(16_385)
        if len(raw) > 16_384:
            raise ValueError("Oversize request")
        result = execute(json.loads(raw))
        encoded = json.dumps(result).encode()
        if len(encoded) > MAX_BYTES:
            raise ValueError("Oversize response")
        sys.stdout.buffer.write(encoded)
        return 0
    except Exception:
        # Provider bodies, URLs with credentials and cookies never cross the boundary.
        sys.stdout.write('{"error":"Source lookup failed; check access or renew X cookies"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
