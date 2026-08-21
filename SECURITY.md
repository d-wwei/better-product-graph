# Security Policy

## Supported versions

The current Developer Alpha line is `0.2.x`. Earlier `0.1.x` builds are historical local candidates and are not supported as public releases.

## Report a vulnerability privately

Do not open a public Issue for path traversal, permission bypass, evidence forgery, incorrect Ready/Release, state corruption, secret exposure, or other security-sensitive behavior.

Use GitHub’s private vulnerability reporting entry:

https://github.com/d-wwei/better-product-graph/security/advisories/new

Include the affected version or commit, Host, operating system, installation method, reproduction steps, expected boundary, and the smallest safe evidence needed to reproduce the problem. Remove credentials, customer data, private PRDs, and unrelated local paths.

We will acknowledge a valid report on a best-effort basis, reproduce it against an exact artifact, and publish a fix and advisory when the issue is confirmed. Please allow time for coordinated disclosure before sharing details publicly.

## Security boundaries

Better Product Graph is local-first, but the Host Agent may use capabilities granted by its Host. Review Host permissions before running it in a sensitive repository. A local Handoff is not external delivery, and a passing mechanical contract is not a security audit or product-quality guarantee.
