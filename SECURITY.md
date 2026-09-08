# Security policy

AgentVerify analyzes untrusted repositories without importing or executing their application code.
Please report any code-execution, path-traversal, denial-of-service, or unsafe-output issue privately
to the maintainers rather than opening a public exploit report.

Use [GitHub private vulnerability reporting](https://github.com/AgentVerify/agentverify/security/advisories/new).
Include the AgentVerify version, operating system, smallest reproducer, and impact. Do not include
live credentials. The current 0.1.x line is supported; fixes will be released on the latest patch
version. There is no guaranteed response-time service level for this early community project.

False positives or missed detections in a scanned application normally belong in the public
[bug tracker](https://github.com/AgentVerify/agentverify/issues/new?template=bug-report.yml), using a
sanitized reproducer. If the example reveals an undisclosed vulnerability in another project,
coordinate with that project's maintainers privately first.
