/** Defense in depth for evidence. This runs on the server before data leaves it. */
const sensitiveKey =
  /(?:password|passwd|secret|authorization|api[_-]?key|access[_-]?token|control[_-]?token|private[_-]?key|database[_-]?url|broker[_-]?url)/i;
export function redact(value: unknown, key = ""): unknown {
  if (sensitiveKey.test(key)) return "[redacted]";
  if (Array.isArray(value)) return value.map((item) => redact(item));
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.entries(value).map(([name, item]) => [name, redact(item, name)]),
    );
  if (typeof value !== "string") return value;
  return value
    .replace(
      /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/g,
      "[redacted private key]",
    )
    .replace(
      /\b(?:gh[pousr]_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}|sk-(?:proj-)?[a-zA-Z0-9_-]{25,})\b/g,
      "[redacted token]",
    )
    .replace(/(\w+(?:\+\w+)?:\/\/)[^\s/@]+:[^\s/@]+@/g, "$1[redacted]@")
    .replace(
      /(?:\/(?:Users|home|private|tmp|srv|workspace|var)\/[^\s"'<>]+|[A-Z]:\\[^\s"'<>]+)/g,
      "[redacted local path]",
    );
}
