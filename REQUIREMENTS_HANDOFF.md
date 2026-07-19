# Requirements Definition Input from End User

## Executive Summary

Build a persona-based analysis system that extracts psychological insights from meeting notes. MVP targets public figures (celebrities, YouTubers); business deployment follows with real-world feedback cycles.

---

## Business Goal

After a client/stakeholder meeting:
1. Input meeting notes into the client's pre-built persona
2. Analyze deep psychological drivers (what they really mean, not surface statements)
3. Derive actionable next steps based on true intent

**Business context:** Sales, partnerships, negotiations where understanding client psychology improves success rate.

---

## MVP Strategy & Scope

**Target:** Public figures (celebrities, YouTubers, public business figures)

**Why:** Abundant public information + verifiable outcomes via news/media → can validate approach before business rollout

**MVP Validates:**
- Information input methods and integration approaches
- Analysis accuracy (can derived predictions be verified?)
- UI/UX for practical business use
- Theory-based analysis methodology

**MVP Output:** Hardened persona construction and analysis capability ready for business data

---

## Core Requirements

### 1. Persona Construction

**Input:** Multiple information sources about a single person
- YouTube videos / podcasts (edited/curated, bias toward production narrative)
- Blog posts / long-form articles (deep personal insight, emotional bias)
- News coverage, interviews, public statements
- (Future) Social media, audio/voice data, private business documents

**Output:** Standardized persona with:
- **Core Values** — what the person prioritizes and why
- **Decision-Making Framework** — how they evaluate choices, what criteria matter
- **Behavioral Patterns** — consistent responses to recurring situations
- **Needs & Concerns** — true wants and things they avoid
- **Communication Style** — effective approaches to reach them
- **Source Attribution** — for each inference, cite which information source(s) support it

**Key Constraint:** Both quantity AND quality of information needed
- Volume (multiple sources) prevents single-source bias
- Quality (deep, personal information) enables psychological accuracy

### 2. Meeting Notes Analysis & Next Action Derivation

**Input:** 
- Client's established persona (from phase 1)
- Meeting notes/transcript

**Output:**
- **Psychological Analysis** — What does this statement/behavior reveal about their true concerns/motivations?
- **Interpretation vs. Intent** — What did they say vs. what did they mean?
- **Recommended Next Step** — Based on psychology, what action should you take?
- **Risk Alert** — What happens if you misread this?

**Example:**
- Meeting note: *"Great, sounds good. We'll review internally and get back to you."*
- Persona-based analysis: *"Based on their past decision patterns, 'review internally' typically means budget concerns, not timeline. Recommend preemptively addressing cost next conversation rather than waiting for their objection."*

### 3. Information Input Process

**User Profile:** Business professional collecting information naturally through work
- No dedicated research team
- Information gathered over relationship duration
- Volume and depth vary by relationship type

**Requirement:** Simple, repeatable input workflow
- Must not friction business-as-usual work
- Must support URL input, text paste, document upload
- (Future) possibly audio/video transcripts

---

## Non-Functional Requirements

### Analysis Foundation
- **Theory-based approach** using psychographic AI research
- Specific framework TBD in design phase (academic papers, established models)
- Reproducible analysis, not ad-hoc heuristics

### Accuracy & Validation
- **Benchmark testing** required to measure persona accuracy and prediction success
- **Verification approach:** Do recommended actions appear in verifiable form (news, confirmed outcomes)?
- **Limitation:** Not all outcomes are publicly observable; "unknown accuracy" cases must be handled gracefully
- **Success criteria:** TBD (e.g., "60% of public-figure predictions verified" → ready for business pilot)

### Feedback & Refinement Cycle
- User operates with persona in real business context
- Captures outcomes (proposal accepted/rejected, decisions made, follow-up behaviors)
- Feeds results back to system for persona refinement
- No strict timing requirement; flexibility for later phases

### Data & Security (Current Scope)
- **Information leakage risk (operational):** User responsible for protecting non-public company info before input
- **System security:** Not in MVP scope; operationalized through user practices
- **Storage duration:** Address in later design phase

---

## Priority Assessment

### Phase 1: MVP Foundation (Must-Have)

1. Persona output format and schema
   - 5-7 core dimensions (values, decision-making, patterns, needs, communication)
   - Source attribution mechanism
   
2. Multi-source information integration
   - Text processing (articles, transcripts)
   - Metadata tracking (source type, date, context)
   - Bias acknowledgment (editorial vs. personal sources)

3. Theory-based analysis logic
   - Psychographic framework selection
   - Information → persona dimension mapping
   - Inference mechanism

4. Meeting notes analysis engine
   - Persona as context for interpretation
   - Next-action recommendation logic
   - Risk flagging

### Phase 2: MVP Validation (High Priority)

5. Benchmark testing design
   - Test methodology for public figures
   - Accuracy measurement approach
   - Success criteria for business readiness

6. Input UI/UX
   - Minimal, repeatable information collection
   - Error handling for incomplete data

### Phase 3: Business Readiness (Medium Priority)

7. Feedback mechanism
   - Capture business outcomes
   - Link outcomes to predictions
   - Persona refinement workflow

8. Data management
   - Storage optimization
   - Persona versioning
   - Audit trail for feedback cycles

---

## Questions for Requirements Definition

1. **Persona Schema Detail:**
   - Should each dimension have multiple sub-attributes? (e.g., Values: moral, professional, personal?)
   - Should confidence levels be attached to each inferred item?
   - Should persona include predictions about future behavior or just past patterns?

2. **Information Integration:**
   - Should system auto-detect information source type (video transcript vs. article) or require user to specify?
   - How to handle conflicting signals across sources? (e.g., public persona vs. private behavior)
   - Should system warn if information is too old or too sparse?

3. **Analysis Transparency:**
   - Should the analysis output show intermediate reasoning steps or just final conclusion?
   - Should user be able to ask "why did you conclude this?" and get sources pulled?

4. **MVP Validation:**
   - For public figures, should we test against known biographies or retrospective news?
   - How many test personas needed before moving to business pilot?

---

## Next Steps

1. **Architect team** → Research psychographic AI field, select theory, propose analysis architecture
2. **Requirements team** → Detail persona schema, input workflow, analysis output format
3. **Both teams** → Define benchmark testing methodology and business-readiness criteria
4. **End user** → Provide feedback on completeness and feasibility

