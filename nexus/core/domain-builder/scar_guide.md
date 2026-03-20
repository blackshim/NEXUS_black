# SCAR Guide — skill.md Writing Principles

> This file is a reference for the LLM when writing skill.md.
> SCAR is a set of writing **principles**, not a fixed structural template.

---

## 1. SCAR 4 Principles

### S — SOP (Standard Operating Procedure)

Convert the workflow in process.md into **procedural instructions**.
- Write as step-by-step commands, not prose
- Each step includes a clear action
- Write as "does X" not "can do X" (Third-Person Imperative)

### C — Constraint Language (RFC 2119)

Explicitly state constraint levels with keywords.
- **MUST:** Must be performed. Process halts on violation.
- **SHOULD:** Recommended. Perform if possible, alternatives allowed if not.
- **MAY:** Optional. Decide based on situation.

### A — Agent Skill Principles

Separate deterministic from non-deterministic behavior.
- **Deterministic (fixed in skill.md):** MCP tool call timing/method, source citation rules, data storage format
- **Non-deterministic (delegated to LLM):** Context interpretation, cause reasoning, response generation, conversation tone adjustment

Tool calls are specified clearly with conditions:
```
If [condition] -> Call `domain-search.search_knowledge`
```

### R — Runbook Style

Write like a checklist handed to a tired on-call engineer at 3 AM.
- Concise and clear
- This is not a marketing document
- Include verification conditions (pass/fail) at each step

---

## 2. skill.md Universal Skeleton

A skeleton that applies universally to all domains and all frameworks.
**The internal structure of the process section is determined by the selected framework** (see frameworks.md).

```markdown
# {Domain Display Name} Skill

## Role
[One-sentence role definition — for whom, doing what]

## Tools
[List of available MCP tools — one-line description per tool]

## Process
[Freely structured according to the selected framework]
[Each step includes action + tool call (deterministic) + judgment/verification criteria]

## Knowledge Extraction Fields
[Field list for domain_knowledge.json — items to extract from conversations]

## Result Criteria
[Define how a single task ends in what state]

## Rules
[Specify constraints with MUST / SHOULD / MAY keywords]

## On Completion
[Actions to perform after completing a single task — log saving, knowledge extraction, etc.]
```

---

## 3. Writing Guidelines

### Volume
- Under 500 lines, under 5000 words
- Put detailed content in process.md or separate references; skill.md focuses on procedures

### Progressive Disclosure
- skill.md is the core instruction the agent reads when performing tasks
- Don't put all background information in skill.md
- If needed, guide with "see process.md for details"

### Verification Conditions
- Include "check before proceeding to next" at each step
- Specify response for verification failure (retry, escalation, halt)

### Tool Calls
- Deterministically specify which tool to call under which condition
- Specify branching/actions based on tool call results
- Specify fallback when tool call fails

### Process Structure
- **The internal structure of the process section is determined by the framework**
- Follow the "process structure guide" of the selected framework in frameworks.md
- Do not force "trigger/branch" on all frameworks

---

## 4. Retrieval Decision (Search Judgment Guide)

> Refer to this guide when including search judgment logic in the skill.md process.
> The engine provides search capability, and skill.md decides **when/how** to search (NEXUS design principle).
> For framework-specific search strategies, refer to the "Search Pattern Guide" in frameworks.md.

### 4.1 Pre-retrieval — Determining Search Necessity

When receiving user input, **first determine if search is needed**, and if so, **always transform the query before** searching.

| Classification | Example | Search | Action |
|---------------|---------|--------|--------|
| Greeting/chat | "Hello", "Thank you" | Not needed | Respond directly |
| Previous conversation reference | "that thing earlier", "what you just said" | Not needed | Resolve from conversation context |
| Knowledge-required question | "What is error code E-301?", "What's the procedure?" | **Required** | Proceed with search |
| Ambiguous question | "Why isn't this working?" | **Deferred** | Ask clarifying question then decide |

**MUST:** Always perform search for knowledge-required questions.
**SHOULD:** For ambiguous questions, narrow intent with clarifying questions before searching.
**MAY:** Even for greetings/chat, you may supplement with domain-search for related knowledge.

### 4.2 Query Enhancement — Pre-search Query Transformation (MUST)

**When search is deemed necessary, do not search with the original question verbatim.**
Always transform the question into an **expected answer format** before searching.

Reason: The user's question ("How to fix E2001") and the document's expression ("Sensor calibration error replacement procedure") use different words.
Transforming the question into answer format includes the same words as the document, greatly improving search accuracy.

**Transformation method:**

Imagine "how would the answer to this question be written in a document?" and rephrase to match likely document expressions.

| Original Question | Transformation Reasoning | Transformed Search Query |
|------------------|-------------------------|--------------------------|
| "How to fix A" | Document likely says "The cause of A is ~, and the action procedure is ~" | "Cause of A and action procedure" |
| "How do I do B?" | Manual likely says "B procedure: Step 1 ~, Step 2 ~" | "B execution procedure and step-by-step method" |
| "What's the C regulation?" | Regulation manual likely says "The standard for C is specified in Article ~" | "C-related standards and regulation articles" |

**MUST:** Transform the question into expected answer format before searching. Never use the original question verbatim as the search query.
**MUST:** Include domain-specific terminology and concrete keywords in the transformation.
**SHOULD:** If transformation is difficult, extracting and listing core keywords is also acceptable.

### 4.3 Post-retrieval — Judging Search Result Sufficiency

After receiving search results, **judge if they are sufficient**.

| Judgment Criteria | Sufficient | Insufficient |
|------------------|-----------|--------------|
| Result count | 1+ relevant results exist | 0 results or all irrelevant |
| Relevance | Core keywords from the question directly match results | Only keywords overlap but context differs |
| Completeness | Results alone can form an answer | Only partial information, incomplete answer |
| Reliability | Clear source (official manual, verified case) | Unknown source or outdated information |

**MUST:** If sufficient, answer based on search results (cite sources).
**MUST:** If insufficient, proceed to Retry.

### 4.4 Retry — Retry Strategy

If results are insufficient, retry with a changed search strategy.

| Order | Strategy | Description |
|-------|----------|-------------|
| 1st | Change keywords | Retry with synonyms, abbreviations, formal names, etc. |
| 2nd | Expand scope | Specific keywords -> Expand to parent category |
| 3rd | Narrow scope | Complex question -> Narrow to one core element |
| 4th | Cross-search | Use domain-search + doc-search in parallel (don't rely on just one) |

**SHOULD:** Switch to Fallback after maximum 3 retries.
**MUST:** Use a different strategy for each retry (no identical search repetition).

### 4.5 Fallback — Final Alternatives

If results remain insufficient after retries, execute final alternatives.

| Order | Alternative | Condition |
|-------|------------|-----------|
| 1 | Partial answer + state limitations | If some related information exists |
| 2 | Escalation | If high-risk/safety-related question -> Connect to expert |
| 3 | Suggest web search | If general technical question not in internal docs -> Web search with user consent |
| 4 | State "no confirmed information" | If none of the above apply |

**MUST:** When stating "no confirmed information," do not answer with speculation.
**SHOULD:** Record Fallback situations in conversation logs to track knowledge gaps.
