# UDIF — Universal Data Interchange Format

**An open standard for portable, sovereign data.**

*Invented by Angela Benton. Originally developed at Streamlytics, Inc. (2018–2021). Released as an open standard under Apache License 2.0.*

---

## What UDIF Is

UDIF is an open data format designed to make your data genuinely portable — not portable in the way platforms use that word, but portable in the literal sense: a file you own, stored where you choose, readable by any system without anyone's permission.

Most data portability features are migration tools. They move your data from one company's servers to another company's servers. When the transfer completes, you've changed platforms but you haven't changed your relationship to your data. It still lives inside infrastructure you don't control, in a format you don't own, under terms that can change without your consent.

UDIF is the alternative. A file format that belongs to the person who generated the data — not to the platform that processed it.

---

## Origin

UDIF was created in 2018 during the development of Streamlytics, a consumer data company that processed over ten billion data points from fifty thousand users across a hundred and twenty-five countries. The problem was clear: even when users could access their data, there was no standard format that allowed them to do anything meaningful with it across systems.

A patent application was filed in March 2021 — US20220300636A1, *System and Method for Standardizing Data* — explicitly describing the UDIF architecture. Following the dissolution of Streamlytics, all intellectual property associated with UDIF was transferred to Angela Benton as founder and originating inventor.

UDIF 2.0 extends the original standard into the AI interaction layer.

---

## UDIF 2.0

The original UDIF standard addressed streaming behavior, social data, and consumption patterns. UDIF 2.0 extends the format to cover the AI interaction layer — the data that matters most in 2025 and beyond:

- AI conversation history
- Preferences and values
- Intellectual history and creative output
- Identity and behavioral context
- Cryptographic provenance metadata

The goal is the same as the original: a file you own, that any system can read, that moves with you.

---

## UDIF 3.0 — Generative Human Intelligence (GHI)

UDIF 3.0 introduces a third data class: Generative Human Intelligence. GHI is the knowledge that exists inside people — not recorded in any platform, not captured in any export, not stored in any database. It has to be drawn out before it can be structured.

GHI data is organized into three types:

- **Perspective Data** — how you see. The distinctive lens you bring to a domain, shaped by your specific experience. What you noticed that others in the same room did not.
- **Judgment Data** — how you act on what you know. The decisions you made, what was at stake, how you reasoned through it, what happened, and what you learned.
- **Interpretive Data** — how you make sense of what you see. The frameworks that emerged from your experience, the principles you crystallized, and the patterns you identified that transfer beyond their original context.

GHI data does not exist in exportable form on any platform. It must be elicited — through structured interviews, guided reflection, or other deliberate processes — before it can be captured in a portable format. UDIF 3.0 defines the interchange schema for GHI records once they have been elicited and structured. It does not define the elicitation methodology or the meaning of the data itself.

The GHI taxonomy and the protocols governing its valuation and licensing are defined by the [PAVE Protocol](https://github.com/PAVE-Protocol/pave), owned by Fruit Ventures LLC. UDIF references the PAVE taxonomy but does not replicate it.

The UDIF v3 converter is in development as part of the [Prova](https://yourheirloom.ai) product.

---

## Why This Matters Now

In early 2026, the two largest AI companies launched features called "data portability" — ways to move memories and context from one AI platform to another. Neither feature produces a file the user owns. Both deposit data into the new platform's infrastructure under the new platform's terms.

The context layer is the new lock-in. The company that holds your AI memory holds your switching cost. UDIF is the format that breaks that architecture — an open standard that any AI system can read, that lives on infrastructure you control, with provenance that proves the data originated from you.

---

## Specification

*The UDIF 2.0 specification is under active development. Initial release forthcoming.*

Core components:
- **Schema** — JSON Schema definition of the UDIF data structure
- **Provenance layer** — cryptographic verification of data origin and integrity
- **Converters** — tools for converting platform exports (ChatGPT, Claude, Gemini) into UDIF format
- **Validator** — reference implementation for validating UDIF files
- **Reference implementations** — Python and JavaScript

---

## Contributing

UDIF is an open standard. Contributions, implementations, and feedback are welcome.

If you're building something on top of UDIF or have questions about the specification, open an issue or start a discussion.

---

## License

Apache License 2.0

See [LICENSE](./LICENSE) for full terms.

---

## Links

- [Heirloom](https://yourheirloom.ai) — the data sovereignty protocol built on UDIF
- [Angela Benton](https://angelabenton.com) — inventor
- [PAVE Protocol](https://github.com/PAVE-Protocol/pave) — GHI taxonomy and licensing protocol
- Patent record: [US20220300636A1](https://patents.google.com/patent/US20220300636A1)

