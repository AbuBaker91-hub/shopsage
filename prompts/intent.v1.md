You classify one shopper question for an online outdoor-gear store.

Shopper question: {{question}}

Classify the question and pull out any product references: names or rough
descriptions of specific products the shopper mentions.

kind must be exactly one of:
- "find": the shopper wants product suggestions or is browsing
- "compare": the shopper wants two or more products compared
- "availability": the shopper asks whether something is in stock or available
- "other": anything else (greetings, unrelated questions, things a gear store may not sell)

Respond with only a JSON object, no prose:
{"kind": "<find|compare|availability|other>", "product_refs": ["<mentioned product>", ...]}
