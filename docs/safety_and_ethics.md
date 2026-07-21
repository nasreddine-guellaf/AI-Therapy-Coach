# Safety and ethics

## Product boundary

AI Therapy Coach is a non-medical coaching tool. It is **not a psychologist, a
doctor, an emergency service, or a medical device**. It must not diagnose a
condition, prescribe or modify medication, claim professional credentials, or
suggest that it replaces qualified care.

The intended scope is active listening, reflective questions, positive
psychology, motivational interviewing, and general coaching support. Even when
the system uses retrieved documents, that content is not automatically safe,
clinically valid, or appropriate for an individual.

## Initial user-message screening

`SafetyService` uses a small, version-controlled list of explicit English and
French phrases. It reports the matching indicators and one or more named
categories:

- `self_harm`;
- `suicidal_ideation`;
- `medical_diagnosis_request`;
- `crisis`;
- `severe_distress`.

The resulting levels are intentionally operational rather than clinical:

| Level | Meaning | Current action |
| --- | --- | --- |
| `none` | No configured phrase matched | Continue normal coaching flow |
| `caution` | Diagnosis request detected | Require referral to a professional |
| `high` | Severe distress phrase detected | Require referral to a professional |
| `critical` | Self-harm, suicide, or immediate-crisis phrase detected | Stop normal generation and show fixed emergency guidance |

Critical handling does not invoke the LLM. It tells the user to contact local
emergency services or a trusted person and not remain alone. Country-specific
crisis resources must eventually be selected from verified configuration rather
than invented by a model.

### Limitations

Keyword rules do not understand intent, negation, quotation, sarcasm, language
variation, or clinical context. They can miss dangerous situations and can flag
benign text. A match is **not** a risk assessment or diagnosis. No numeric
confidence or fabricated medical classification is produced.

Future improvements require clinically reviewed multilingual datasets, explicit
negation/context handling, adversarial testing, monitoring, and a human-owned
incident process. A future LLM-based safety classifier may only supplement these
rules if its version, rationale, thresholds, failure modes, and escalation path
remain auditable.

## Assistant-response validation

`ResponseValidator` applies explicit patterns after generation and returns named
violations. It rejects responses that:

- claim to be the user's psychologist;
- assert a medical diagnosis;
- prescribe, start, stop, or change medication;
- omit a professional-help referral when the user-message assessment requires
  one;
- contain no usable text.

Rejected model text is not returned to the user. These rules enforce product
scope only; they do not prove that an accepted response is medically or ethically
safe. Production validation should also cover unsupported citations, prompt
injection leakage, coercive language, dependency encouragement, privacy leakage,
and country-specific regulatory requirements.

## Data and governance requirements

Before production, the project needs:

- informed consent and an appropriate minimum-age policy;
- clear privacy, retention, export, correction, and deletion controls;
- encryption, least-privilege access, and audited administrative access;
- explicit consent for long-term conversational memory;
- bias and multilingual performance evaluation;
- clinically informed review of crisis wording and escalation procedures;
- legal and regulatory review for every deployment jurisdiction;
- monitoring that avoids logging sensitive message content or secrets.

Safety rules, prompts, retrieved sources, provider models, and validator versions
should be traceable so incidents can be investigated without pretending that
automation replaces professional judgment.
## Authentication and personal coaching data

Authentication is required before chat access so future session history and
personal coaching data can be associated with, and authorized for, the correct
owner. The MVP uses short-lived signed access tokens and one-way password
hashes. Authentication is only an access-control baseline: production still
requires HTTPS, secure token storage, retention controls, audit logging, and a
reviewed privacy policy.
