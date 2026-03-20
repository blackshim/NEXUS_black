# NEXUS Framework Catalog

> This file is a reference for the LLM.
> It is used in both Phase 1 (process.md refinement) and Phase 3 (skill.md generation).
>
> **Phase 1:** Select a framework, and refer to its methodology and question directions to refine process.md through interactive consulting.
> **Phase 3:** Refer to the selected framework's process structure guide to compose the process section of skill.md.
>
> Question patterns are not "ask this question verbatim" but rather "explore in this direction" guides.
> Ask naturally like a consultant, tailored to the context of process.md.

---

## How to Select a Framework

1. Read process.md and identify the core characteristics of the process
2. Select the most suitable one from the 7 frameworks below (primary)
3. For complex processes, you may additionally select a secondary
4. Explain the selection reasoning to the user and get approval

---

## A. Diagnostic-Branching (Judgment/Branching Focused)

### Applicable Targets
Processes that track causes from symptoms and branch to different paths based on conditions

### Value Chain Mapping
- Customer Service: CS/AS, Technical Support, IT Helpdesk
- Operations/Production: Quality Inspection, Equipment Maintenance, Defect Analysis
- Risk/Compliance: Internal Control, Audit

### Methodology Basis
- **Decision Tree** — The process itself is a tree structure of "condition->branch"
- **IDEF0 (ICOM)** — At each decision node: what to examine (Input), what criteria (Control), what result (Output), what tools (Mechanism)
- **5 Whys** — Ensuring depth from surface symptoms to root causes

### Question Directions (Phase 1 Consulting)
| Direction | Why Explore This | Reflected in skill.md |
|-----------|-----------------|----------------------|
| Branch structure | Identify points and conditions where paths diverge | Process branch step structure |
| Decision inputs | Data/information referenced at each branch | What data to reference at each step |
| Decision criteria | What criteria determine the path | Decision criteria table |
| Misjudgment recovery | Recovery procedure when wrong judgment is made | Recovery procedure for misjudgment |
| Deep branching | Additional verification paths when first judgment fails | Deep flow between steps |
| Root cause | Why this problem occurs (5 Whys) | Depth of cause detail fields |
| Escalation | Handling when final judgment is impossible | Escalation criteria |
| Result judgment | Criteria for distinguishing success/failure | Result judgment criteria |

### skill.md Process Structure Guide
**Pattern: Decision Tree — Condition->Branch->Loop-back**

The process section of this type has **branch tables** at its core.
At each step, evaluate conditions and proceed to different paths based on results.
On judgment failure, loop-back to a previous step is possible.

```
### Step N: [Judgment/Action Name]
**Entry condition:** [When does this step activate]
**Actions:**
1. [Check data] — Tool: `domain-search.search_knowledge`
2. [Perform judgment]
**Decision criteria:** [MUST: Judge based on these criteria]
**Branches:**
| Condition | Next |
|-----------|------|
| [Condition A] | -> Step X |
| [Condition B] | -> Step Y |
| [Cannot determine] | -> Escalation |
```

### Search Pattern Guide
**Core Strategy: Identifier exact match first, then gradual expansion via symptom keywords**

| Step | Search Strategy | Tool |
|------|----------------|------|
| 1st | Unique identifier (code, number, name, etc.) -> exact match | `domain-search.search_knowledge` |
| 2nd | Symptom/phenomenon keyword combination | `doc-search.search_documents` |
| 3rd | Similar symptom pattern -> expand to related cases | `domain-search.search_knowledge` |

**Pre-retrieval:** If a unique identifier exists, search immediately. Otherwise, ask symptom clarification questions first.
**Post-retrieval:** Identifier exact match has high reliability. Symptom matching requires comparing multiple results.
**Retry:** Expand from identifier -> symptom keywords -> parent category.

---

## B. Exploration-Discovery (Search/Discovery Focused)

### Applicable Targets
Processes that find something, form hypotheses, validate, and refine results

### Value Chain Mapping
- Product/Service Development: R&D, Technical Research, Patent Investigation
- Marketing: Market Research, Competitive Analysis, Trend Monitoring
- Support Activities: Benchmarking, Technology Trend Scanning

### Methodology Basis
- **OODA Loop** (Observe-Orient-Decide-Act) — Exploration is a cycle of observe->interpret->decide->act
- **Design Thinking** (Empathize-Define) — Define "for whom, what to find" on an empathy basis
- **MECE** — Structure the exploration scope completely and without overlap

### Question Directions (Phase 1 Consulting)
| Direction | Why Explore This | Reflected in skill.md |
|-----------|-----------------|----------------------|
| Exploration goal | Clarify what to find | Role + process starting point |
| Stakeholders | Who the exploration is for | Role's target definition |
| Information sources | Where to start searching | Tool mapping |
| Exploration scope | How to divide scope (MECE) | Process step structure |
| Discovery conditions | Criteria for "found it" | Result judgment criteria |
| Verification method | How to verify found information | Verification step |
| Insufficient response | What to do next if results are insufficient | Repeat/expand loop |
| Output format | Form of exploration results | Output format |

### skill.md Process Structure Guide
**Pattern: Search-Expand-Narrow — Search->Expand->Narrow cycle**

The process section of this type has **exploration cycles** at its core.
Define the goal, expand the scope while searching, and narrow when discovery conditions are met.
Since there may be no correct answer, **exploration termination conditions** are essential.

```
### Exploration Cycle
**Goal:** [What to find]
**Source:** [Where to search] — Tools: `doc-search.search_documents`, `domain-search.search_knowledge`
**Scope expansion:** [If results insufficient] -> Re-search in adjacent areas
**Discovery judgment:** [SHOULD: Terminate search when these criteria are met]
**Verification:** [Confirm reliability of found information]
**Termination condition:** [Max N iterations or user judgment]
```

### Search Pattern Guide
**Core Strategy: Broad keywords -> Gradual narrowing**

| Step | Search Strategy | Tool |
|------|----------------|------|
| 1st | Search with broad topic keywords | `doc-search.search_documents` |
| 2nd | Re-search with discovered terms/concepts (narrowing) | `domain-search.search_knowledge` |
| 3rd | Expand to adjacent areas (new direction) | `doc-search.search_documents` |

**Pre-retrieval:** If the exploration goal is clear, search immediately. If ambiguous, define scope first.
**Post-retrieval:** In exploration, "direction" matters more than "correct answer." Having related info is sufficient.
**Retry:** Keyword variations + adjacent area expansion. Since it's exploration, search broadly while respecting termination conditions.

---

## C. Sequential-Procedural (Sequential/Procedure Focused)

### Applicable Targets
Processes performed in a fixed order where each step must be completed before proceeding to the next

### Value Chain Mapping
- Operations/Production: Manufacturing Processes, Assembly, Packaging
- Inbound/Outbound Logistics: Receiving, Shipping, Returns Processing
- Support Activities: Onboarding, Accounting Close, Tax Filing, Licensing, Auditing

### Methodology Basis
- **SIPOC** — Define the Supplier-Input-Process-Output-Customer of the entire process
- **VSM** (Value Stream Mapping) — Identify lead time, wait time, and bottlenecks at each step
- **BPMN** — Detailed execution flow and exception handling

### Question Directions (Phase 1 Consulting)
| Direction | Why Explore This | Reflected in skill.md |
|-----------|-----------------|----------------------|
| Start trigger | Conditions that start the process | Process entry conditions |
| Step-by-step actions | What specifically happens at each step | Actions per step |
| Completion conditions | Completion criteria for each step | Entry criteria for next step |
| Required tools/permissions | Tools/systems/permissions needed | Tool calls + data references |
| Exception handling | Response to exceptions/errors at each step | Exception branches |
| Final deliverable | Result and recipient | Result judgment + final step |
| Time required | Overall and per-step time | Process metadata |
| Mandatory steps | Steps that must never be skipped | Mark as non-skippable |

### skill.md Process Structure Guide
**Pattern: Linear Checklist — 1->2->3->...->Complete**

The process section of this type has a **sequential checklist** at its core.
Minimal branching; the simplest runbook structure.
Each step must be completed before proceeding to the next.

```
### Step 1: [Step Name]
**Actions:**
1. [Action] — Tool: `tool.method`
2. [Action]
**Completion check:** [MUST: This must be confirmed before next step]
**Exception:** [On failure] -> [Response]

### Step 2: [Step Name]
...

### Completion Checklist
- [ ] Step 1 complete
- [ ] Step 2 complete
- [ ] ...
- [ ] Final deliverable delivered
```

### Search Pattern Guide
**Core Strategy: Exact search by procedure/step name, maintain sequence context**

| Step | Search Strategy | Tool |
|------|----------------|------|
| 1st | Exact search by procedure/step name | `domain-search.search_knowledge` |
| 2nd | Search documents by parent process name | `doc-search.search_documents` |
| 3rd | Context search including preceding and following steps | `doc-search.search_documents` |

**Pre-retrieval:** When user asks about a specific step, search that step + preceding/following steps.
**Post-retrieval:** Sequence order matters. If only a single step appears, supplement with full flow context.
**Retry:** Step name -> Process name -> Related documents, in expanding order.

---

## D. Relational-Persuasive (Relationship/Persuasion Focused)

### Applicable Targets
Processes that understand the counterpart, make proposals tailored to needs, and reach agreement

### Value Chain Mapping
- Marketing/Sales: B2B Sales, Contract Closing, Channel Management
- Customer Service: Claims Processing, Customer Relationship Management (CRM)
- Support Activities: Investor Relations, Partnerships, Negotiations

### Methodology Basis
- **JTBD** (Jobs-to-be-Done) — Identify what the counterpart is "truly trying to accomplish"
- **RACI** — Role distinction in multi-party relationships (Responsible/Accountable/Consulted/Informed)
- **Cynefin** — Since counterpart reactions are non-linear, respond based on situation complexity

### Question Directions (Phase 1 Consulting)
| Direction | Why Explore This | Reflected in skill.md |
|-----------|-----------------|----------------------|
| True goal | What the counterpart is trying to achieve (JTBD) | Process start (needs analysis) |
| Stakeholders | Who is involved and their roles (RACI) | Roles + relationship structure |
| Objections/concerns | Counterpart's main objections/concerns | Objection handling step |
| Agreement conditions | What conditions lead to agreement/contract | Result judgment criteria |
| Deadlock alternatives | What alternatives exist if relationship stalls | Alternative branches |
| Documentation requirements | What must be documented | Required record items |
| Follow-up activities | Follow-up for relationship maintenance | Last step of process |
| Failure handling | How to handle rejection/attrition | Rejection/attrition handling |

### skill.md Process Structure Guide
**Pattern: State-Based Dialog — Strategy shifts based on counterpart's response/state**

The process section of this type has **relationship states and strategies** at its core.
Not if/else branching, but strategy switching based on the counterpart's response/attitude/state.
Emotion/attitude recognition is important.

```
### Needs Assessment
**Context:** [Current relationship state with counterpart]
**Actions:**
1. Identify the counterpart's true goal — Tool: `domain-search.search_knowledge`
2. Confirm stakeholder structure
**Conversation tone:** [Empathetic, listening-focused]

### Proposal
**Actions:**
1. Compose a proposal tailored to needs
2. Prepare responses to anticipated objections
**Strategy by counterpart response:**
| Response | Strategy |
|----------|----------|
| Positive | -> Move to agreement stage |
| Concern expressed | -> Address concerns then re-propose |
| Rejection | -> Present alternatives or maintain relationship |
| Deadlock | -> Escalation or time interval |
```

### Search Pattern Guide
**Core Strategy: Search centered on counterpart/relationship history, reference similar cases**

| Step | Search Strategy | Tool |
|------|----------------|------|
| 1st | Search history by counterpart/customer name | `domain-search.search_knowledge` |
| 2nd | Search similar situations/cases by type | `doc-search.search_documents` |
| 3rd | Search response strategy/guide documents | `doc-search.search_documents` |

**Pre-retrieval:** If counterpart info (name, org, type) is available, search history first.
**Post-retrieval:** If past history exists, reflect context. If not, use general type-based guides.
**Retry:** Expand from counterpart-specific -> general type -> related strategy documents.

---

## E. Analytical-Decision (Analysis/Decision-Making Focused)

### Applicable Targets
Processes that collect data, analyze based on criteria, compare alternatives, and make decisions

### Value Chain Mapping
- Strategy: Strategic Planning, Business Model Design
- Marketing: Pricing, Demand Forecasting
- Support Activities: Financial Analysis, Budgeting, Risk Assessment, Investment Decisions, Performance Evaluation

### Methodology Basis
- **DMAIC** — Define->Measure->Analyze->Improve->Control
- **MECE** — Ensure classification completeness of analysis targets
- **Decision Matrix** — Quantitatively evaluate multiple alternatives by criteria

### Question Directions (Phase 1 Consulting)
| Direction | Why Explore This | Reflected in skill.md |
|-----------|-----------------|----------------------|
| Decision target | What needs to be decided | Role + process scope |
| Key variables | Factors influencing the decision | Data references per step |
| Analysis criteria | Criteria/indicators used (KPIs) | Analysis criteria table |
| Alternative list | Number and content of alternatives | Comparison step |
| Evaluation criteria/weights | How to evaluate each alternative | Evaluation matrix |
| Decision authority | Who has decision-making authority | RACI or explicit rule |
| Execution monitoring | How to track after decision | Final step (monitoring) |
| Rollback criteria | Criteria for correcting a wrong decision | Re-analysis conditions |

### skill.md Process Structure Guide
**Pattern: Data-Gather-Evaluate — Collect->Analyze->Evaluate->Decide**

The process section of this type has **evaluation matrices and decision criteria** at its core.
Quantitative criteria are essential, and alternative comparison must be structured.

```
### Data Collection
**Actions:**
1. Collect relevant data — Tools: `doc-search.search_documents`, `data-analysis.query_data`
2. Verify data quality
**Sufficiency judgment:** [SHOULD: Secure N+ key variables]

### Analysis
**Actions:**
1. Perform analysis by criteria/indicators
2. Calculate scores per alternative
**Evaluation matrix:**
| Alternative | Criteria 1 (w=?) | Criteria 2 (w=?) | Total |
|-------------|-------------------|-------------------|-------|

### Decision
**Judgment:** [Select the alternative with highest weighted total]
**Verification:** [MUST: Decision authority approval]
**Rollback:** [If results fall below criteria] -> Re-analysis
```

### Search Pattern Guide
**Core Strategy: Multi-source comparative search, focused on numbers/criteria**

| Step | Search Strategy | Tool |
|------|----------------|------|
| 1st | Search related data by analysis target keywords | `doc-search.search_documents` |
| 2nd | Search comparative materials by criteria/indicator/KPI keywords | `domain-search.search_knowledge` |
| 3rd | Directly analyze spreadsheet data | `data-analysis.analyze_spreadsheet` |

**Pre-retrieval:** Analysis questions always require search. Choose tool based on data source type (document vs. numerical).
**Post-retrieval:** Cross-verification with multiple sources recommended over single source. Check freshness of numerical data.
**Retry:** Keyword variations + data analysis tools in parallel. If no numbers, collect qualitative information.

---

## F. Creative-Design (Creation/Design Focused)

### Applicable Targets
Processes that create something new, prototype, and iteratively improve through feedback

### Value Chain Mapping
- Product/Service Development: Product Design, Service Design
- Marketing: Campaign Planning, Content Creation
- Support Activities: Training Program Design, Process Improvement, UX/UI Design

### Methodology Basis
- **Design Thinking** — Empathize->Define->Ideate->Prototype->Test
- **PDCA** — Plan->Do->Check->Act iterative improvement
- **Cynefin** — Exploratory approach in complex domains where there are no correct answers

### Question Directions (Phase 1 Consulting)
| Direction | Why Explore This | Reflected in skill.md |
|-----------|-----------------|----------------------|
| End user | Who it's being made for | Role > target definition |
| Core problem | The problem/need being solved | Process start |
| Previous attempts | Approaches tried so far and their limitations | Context step |
| Completion criteria | Criteria for success (completion) | Result judgment criteria |
| Verification method | How to verify prototype/draft | Test step |
| Feedback integration | How to collect and integrate feedback | Iteration loop |
| Constraints | Time/budget/technical constraints | Constraint items |
| Output format | Form of final deliverable and recipient | Final step + output format |

### skill.md Process Structure Guide
**Pattern: Ideate-Prototype-Validate — Generate->Validate iteration cycle**

The process section of this type has **iteration and quality gates** at its core.
Not branching but iteration, and "when to stop" is the key question.

```
### Problem Definition
**Actions:**
1. Identify user/stakeholder needs
2. Review existing approaches and their limitations — Tool: `doc-search.search_documents`
**Completion criteria:** [MUST: Problem defined in one sentence]

### Generate-Validate Cycle
**Iteration:**
1. Generate draft/prototype
2. Validate (evaluate against completion criteria)
3. Collect feedback
4. Incorporate and improve
**Iteration termination condition:** [Completion criteria met or constraints reached]

### Final Output
**Actions:** Organize and deliver final deliverable
**Format:** [Deliverable format]
```

### Search Pattern Guide
**Core Strategy: Broad similar case search, inspiration-focused**

| Step | Search Strategy | Tool |
|------|----------------|------|
| 1st | Search similar cases/prior work | `doc-search.search_documents` |
| 2nd | Expand search to related domains/areas | `doc-search.search_documents` |
| 3rd | Search existing deliverables/templates | `domain-search.search_knowledge` |

**Pre-retrieval:** Even creative requests benefit from searching existing cases/references. Don't start from scratch.
**Post-retrieval:** Purpose is inspiration/reference, not exact match. Broad results have value.
**Retry:** Keyword expansion + adjacent field exploration. Actively consider suggesting web search.

---

## G. Monitor-Respond (Monitoring/Response Focused)

### Applicable Targets
Processes that continuously observe, detect anomalies, and respond in stages based on severity

### Value Chain Mapping
- Operations/Production: Production Line Monitoring, Inventory Management
- Service: SLA Monitoring
- Support Activities: System Operations, Security Operations Center, Crisis Management (BCP)

### Methodology Basis
- **OODA Loop** — Fast cycle of real-time observe->judge->act
- **IDEF0 (ICOM)** — Each monitoring point's input (sensors/logs), control (thresholds), output (alarms), mechanism (systems)
- **PDCA** — Post-response analysis and root cause improvement

### Question Directions (Phase 1 Consulting)
| Direction | Why Explore This | Reflected in skill.md |
|-----------|-----------------|----------------------|
| Monitoring target | What is being monitored | Process start |
| Normal/abnormal criteria | Thresholds for normal vs. abnormal | Threshold table |
| Initial response | First response upon anomaly detection | Immediate response step |
| Response failure | What if normalization fails after response | Escalation path |
| Severity system | Severity levels and response per level | Severity table |
| Monitoring frequency | Monitoring cycle/frequency | Process metadata |
| Response recording | How response history is recorded | Knowledge extraction + log saving |
| Root countermeasures | Improvement for recurring anomalies | Post-analysis step |

### skill.md Process Structure Guide
**Pattern: Watch-Alert-Act — Monitor->Alert->Respond (event-driven)**

The process section of this type has **threshold tables and severity-based responses** at its core.
Operates on an event basis, not a time basis.

```
### Monitoring
**Target:** [What is being monitored]
**Frequency:** [How often]
**Threshold table:**
| Item | Normal | Caution | Critical |
|------|--------|---------|----------|

### Response
**Response by severity:**
| Severity | Response | Tool |
|----------|----------|------|
| Caution | [First response] | `domain-search.search_knowledge` |
| Critical | [Immediate response + escalation] | Send alert |
| Emergency | [Emergency response + manager call] | System halt |

### Post-Analysis
**Actions:** Root cause analysis after response completion
**Recurring anomalies:** [If same anomaly occurs N times] -> Establish root countermeasures
```

### Search Pattern Guide
**Core Strategy: Exact match on thresholds/criteria, history pattern search**

| Step | Search Strategy | Tool |
|------|----------------|------|
| 1st | Search criteria by anomaly item/alert keywords | `domain-search.search_knowledge` |
| 2nd | Search past similar anomaly history | `domain-search.search_knowledge` |
| 3rd | Search response procedures/manual documents | `doc-search.search_documents` |

**Pre-retrieval:** Search immediately upon anomaly detection. No search needed in normal state.
**Post-retrieval:** High reliability if thresholds/criteria match clearly. Prioritize past history pattern check.
**Retry:** Expand from specific item -> category -> manual search.
