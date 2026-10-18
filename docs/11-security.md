# Security and privacy

## Threats

- prompt injection;
- malicious uploaded document;
- poisoned legal source;
- wrong-jurisdiction retrieval;
- cross-user data leakage;
- unauthorized source access;
- raw contract logging;
- malicious export;
- model/provider data leakage;
- admin abuse.

OWASP identifies prompt injection as a core LLM risk and separately highlights vector and embedding weaknesses in RAG systems. [genai.owasp](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

## Controls

- authentication;
- role-based access control;
- organization/tenant filtering;
- source approval;
- immutable audit events;
- file type and size validation;
- antivirus scanning if available;
- signed export URLs;
- encrypted storage;
- no raw contracts in normal logs;
- retrieval access filters;
- secret management;
- rate limiting;
- prompt/context separation;
- output schema validation;
- human approval.

## Security test cases

- user cannot access another organization's source;
- inactive source is not retrieved;
- wrong jurisdiction is excluded;
- malicious document instruction is ignored;
- unauthorized user cannot activate a pack;
- export cannot bypass blocker validation;
- expired source is excluded;
- secrets are not present in logs.