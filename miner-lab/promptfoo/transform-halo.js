/** Return classify JSON object, or a string error so assertions can flag it. */
module.exports = (json, text) => {
  if (json && json.detail) {
    return { _error: true, detail: json.detail, raw: text };
  }
  if (json && typeof json === "object") return json;
  try {
    return JSON.parse(String(text));
  } catch {
    return { _error: true, raw: text };
  }
};
