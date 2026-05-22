# CP-8 Founding Engineer Interview Loop and Evaluation Kit

Date: 2026-05-22
Owner: CTO
Issue: CP-8

## Hiring target
Founding engineer able to:
- Architect v1 for fast iteration with strong reliability fundamentals.
- Ship independently across backend, frontend, and infra.
- Take ownership of ambiguous product problems and drive outcomes.

## Interview loop overview
Total loop time: 8-10 days from first call to decision.
Decision SLA: final debrief and decision within 24 hours after the practical exercise submission.

Stages:
1. Recruiter/Founder alignment screen (30 min)
2. Technical deep-dive and architecture interview (75 min)
3. 90-minute asynchronous practical system exercise
4. Practical review + code walkthrough (60 min)
5. Founder values and ownership interview (45 min)
6. Structured debrief and hiring decision (30 min panel)

Hard gate rule:
- Candidate must pass stages 2, 3, and 4 to receive an offer recommendation.

## Stage-by-stage scripts and must-pass signals

### Stage 1: Recruiter/Founder alignment screen (30 min)
Purpose: confirm baseline fit and communication quality before spending panel time.

Script:
- "Walk me through your last two roles and what you personally shipped end-to-end."
- "Why this company stage, and why now?"
- "Tell me about one time you disagreed with product direction and what you did."
- "What is your preferred way of working in the first 90 days at a startup?"

Must-pass signals:
- Can clearly describe own contributions with concrete outcomes.
- Motivation aligns with early-stage ambiguity and ownership.
- Communicates crisply and collaborates without blame language.

Fail signals:
- Repeatedly vague ownership language ("we did" without specifics).
- Motivation centered on title/status rather than build impact.

### Stage 2: Technical deep-dive and architecture interview (75 min)
Purpose: evaluate systems judgment, tradeoff quality, and practical architecture depth.

Script:
- 10 min: Candidate project deep-dive
- 45 min: Architecture scenario
- 20 min: Failure modes and operational strategy

Architecture prompt:
"Design the backend and data model for a short-form content planning app used by 100k creators. Requirements:
- Idea board and script drafts
- Asset upload and versioning
- Team collaboration and comments
- Basic analytics dashboard
- p95 API latency < 300ms for core reads
- 99.9% monthly uptime target"

Follow-up prompts:
- "What do you build in week 1 versus month 3?"
- "Where do you accept technical debt and why?"
- "How do you handle schema evolution and backward compatibility?"
- "What alerts and SLOs are mandatory at launch?"

Must-pass signals:
- Produces coherent v1 architecture with realistic phased delivery plan.
- Makes explicit tradeoffs (speed vs durability) and justifies them.
- Identifies core failure modes and proposes practical mitigations.
- Shows strong data modeling fundamentals and API boundary clarity.

Fail signals:
- Overengineers with no phase strategy.
- Cannot explain operational risks (data loss, abuse, downtime).
- Incoherent or contradictory architecture decisions.

### Stage 3: Practical 90-minute asynchronous system exercise
Purpose: verify shipping velocity, code quality, and judgment under a bounded time box.

Format:
- Candidate receives prompt + starter repo + submission instructions.
- Candidate has 24 hours to start and 90 minutes max to complete once started.
- Submission: repo link or patch + brief design note (max 400 words).

Exercise prompt:
"Build a minimal API service for a content calendar.

Requirements:
- Entities: User, ContentIdea, ScheduledPost.
- Endpoints:
  - POST /ideas
  - GET /ideas?status=
  - POST /schedule
  - GET /schedule?from=&to=
- Validation: reject schedule if date is in the past.
- Add one derived field: idea_priority_score from inputs (document formula).
- Provide a short README with run instructions and tradeoffs.

Constraints:
- Any mainstream language/framework.
- Persist data in SQLite/Postgres/in-memory (candidate choice, justify).
- Include at least 3 tests covering happy path and one edge case."

Scoring rubric (100 pts):
- Correctness and requirement coverage: 35
- Code clarity and maintainability: 20
- Data modeling and API design: 20
- Testing quality: 15
- Tradeoff explanation in README: 10

Must-pass threshold:
- Overall score >= 75/100
- AND no zero score in correctness/data modeling/testing dimensions

### Stage 4: Practical review + code walkthrough (60 min)
Purpose: validate authorship, reasoning quality, and ability to improve own implementation.

Script:
- 20 min: Candidate walkthrough
- 25 min: Panel challenge questions
- 15 min: Improvement and scaling discussion

Challenge prompts:
- "What would break first with 50x load?"
- "Show one refactor you would do with 2 more hours."
- "How would you make this observable in production?"

Must-pass signals:
- Defends implementation choices coherently and acknowledges tradeoffs.
- Can identify concrete next improvements with priority reasoning.
- Demonstrates authorship confidence and deep familiarity with code.

Fail signals:
- Cannot explain core implementation details.
- Avoids tradeoff discussion or blames timebox for design gaps.

### Stage 5: Founder values and ownership interview (45 min)
Purpose: assess ownership behavior, execution temperament, and company-building fit.

Script:
- "Tell me about the hardest production incident you owned."
- "What standards do you hold for quality when speed pressure is high?"
- "Describe a conflict with a teammate and how it was resolved."
- "What do you need from a founder to do your best work?"

Must-pass signals:
- Demonstrates accountability during failures.
- Balances urgency and quality with explicit decision heuristics.
- Shows low-ego, high-ownership collaboration style.

Fail signals:
- Deflects responsibility for outcomes.
- Strongly rigid collaboration stance incompatible with early-stage work.

## Debrief template (consistent decision framework)
Use this template immediately after stage completion; final panel debrief happens after stage 5.

### Candidate summary
- Name:
- Date:
- Interviewers:
- Final recommendation: Hire / No Hire / Hold

### Stage outcomes
- Stage 1 result: Pass/Fail + notes
- Stage 2 result: Pass/Fail + notes
- Stage 3 score: X/100 + Pass/Fail
- Stage 4 result: Pass/Fail + notes
- Stage 5 result: Pass/Fail + notes

### Competency ratings (1-4)
- Architecture depth:
- Shipping velocity:
- Ownership and reliability:
- Product judgment:
- Communication:

Rating legend:
- 1 = below bar
- 2 = mixed/unclear
- 3 = meets bar
- 4 = exceeds bar

### Evidence highlights
- Top strengths (with concrete examples)
- Top risks (with concrete examples)
- Risk mitigation plan if hiring

### Pass/fail decision rules
Automatic no-hire if any condition is true:
- Fails stage 2, 3, or 4
- Stage 3 score < 75/100
- Evidence of low integrity or non-ownership behavior

Hire recommendation requires all conditions:
- Passes stages 2, 3, and 4
- No critical values red flags in stage 5
- At least two interviewers independently recommend "Hire"

### Final decision statement
- Decision:
- Why now:
- 30-day onboarding focus if hired:

## Operations rules for the loop
- Interviewers submit written feedback within 2 hours of each stage.
- Hiring manager schedules debrief within 24 hours of practical submission review.
- No offer decision without completed template fields and explicit pass/fail evidence.
- Candidate communication SLA: update within 1 business day at each stage boundary.

## Acceptance criteria traceability
- Every stage has explicit must-pass signal: satisfied.
- Exercise can run asynchronously and be scored within 24h: satisfied (90-min task with 24h submission window + scoring rubric).
- Debrief template enables consistent hiring decision: satisfied (structured scoring + hard-gate rules).
