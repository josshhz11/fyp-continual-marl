# **FYP Proposal: Continual Multi-Agent Workflow Orchestration (Manager Agent)**

## **1\. Background and Research Gap**

The MA-Gym paper (Masters et al., 2025, [arXiv:2510.02557](https://arxiv.org/abs/2510.02557)) formalizes workflow orchestration as a Partially Observable Stochastic Game and identifies four foundational challenges: (1) hierarchical decomposition, (2) multi-objective optimization under shifting stakeholder preferences, (3) coordination and planning in ad hoc teams, and (4) governance and compliance by design. Their benchmark results, using GPT-5-based managers under Chain-of-Thought, Random, and Assign-All policies across 20 workflows, show that current managers cannot jointly optimize goal completion, constraint adherence, and runtime.

Challenges (2) and (3) – objectives that shift over time and teams that change in composition – are directly the "continual" dimension named in this project's title. The MA-Gym paper identifies these as open but does not attempt a learned or continual solution to either. This project proposes to address that gap.

More broadly, recent work in continual reinforcement learning (e.g. Pan et al., 2025, [arXiv:2506.21872](https://arxiv.org/abs/2506.21872)) and inference-time adaptation methods for LLM agents (e.g. "Continual Learning, Not Training," 2025, [arXiv:2511.01093](https://arxiv.org/abs/2511.01093)) shows a shift away from gradient-based retraining toward memory- and retrieval-based adaptation at inference time, which avoids catastrophic forgetting and the cost of retraining. This project aligns with that direction: rather than fine-tuning the manager LLM or learning a policy over the full raw manager action space, I propose to keep the LLM frozen and place the learned/adaptive components around it.

This matters practically because deployed workflow managers cannot pause to retrain every time a worker leaves, a new task arrives, or a stakeholder's priorities change. A manager that generalizes to such changes without retraining is a meaningfully more deployable system than the static baselines MA-Gym currently benchmarks.

## **2\. Proposed Phases**

**Phase 1: Baseline Reproduction**  
Set up the MA-Gym environment and reproduce the Chain-of-Thought, Random, and Assign-All baseline results across the 20 published workflows. This establishes working tooling and a validated baseline against which all later phases are measured.

**Phase 2: Lightweight Learned Selection Layer**  
Rather than learning over MA-Gym's full, heterogeneous manager action space, the LLM will propose a small set of candidate actions or plans at each decision point, and a lightweight policy will be trained to select among them using MA-Gym's existing reward signals (goal completion, constraint adherence, runtime). This reduces the problem to a tractable decision-selection task. I propose to begin with a contextual bandit formulation, and extend to a small policy-gradient method (e.g. REINFORCE, and PPO if time permits) only if warranted by results. This phase will first be validated on static (non-continual) workflows to confirm the mechanism works before introducing non-stationarity.

**Phase 3: Episodic Memory for Continual Adaptation**  
This phase is the intended core contribution. Past episodes (workflow configuration, actions taken, outcomes) will be stored and retrieved into the manager's context at decision time, with no gradient updates or retraining required. Core components are an embedding scheme for workflow/task-graph state, a retrieval mechanism, and integration of retrieved memory into the manager's prompt. This phase is evaluated directly against the challenge tasks defined in Section 3\.

**Phase 4: Zero-Shot Generalization Evaluation (Stretch Goal)**  
Evaluate the Phase 3 system on held-out workflow configurations not seen during memory accumulation – new task graph structures, new team compositions, and new constraint types – to test whether the memory mechanism genuinely generalizes rather than overfitting to seen configurations. This phase would form the basis of a publishable results section if reached on schedule.

## **3\. Challenge Tasks & Evaluation Design**

Following the group's evaluation methodology, I defined **four challenge tasks** – constructed so that current MA-Gym baselines (CoT, Random, Assign-All) can be shown to fail on them specifically due to challenges (2) and (3), not due to unrelated task difficulty.

**Challenge Tasks:**

1. **Preference-shift task:** stakeholder preference weights change mid-episode (e.g. priority reweighted from speed to quality partway through). Baselines with no mechanism to re-anchor to updated preferences are expected to keep optimizing the stale objective.  
2. **Team-churn task:** a worker leaves or joins mid-episode, forcing reassignment across the remaining/new team. Baselines with no representation of the change are expected to fail to adapt allocation.  
3. **Compound task:** both preference shift and team churn occur within the same episode – the joint stress case directly corresponding to the MA-Gym paper's open problem.  
4. **Cross-episode task:** a sequence of related but distinct workflows is run consecutively with no retraining between them, testing whether Phase 3's memory produces measurable improvement across the sequence – the direct test of the "continual" claim, as opposed to within-episode replanning alone.

**Evaluation questions, per task:**

1. How does the memory-augmented manager compare to CoT/Random/Assign-All on **goal completion, constraint adherence, and runtime**?  
   1. Metrics: Goal completion rate (% of task graph nodes completed), constraint adherence (violation count/rate per episode, by constraint type), Runtime (wall-clock timesteps to completion), Composite/Pareto view across all three metrics  
2. How does **performance scale** with churn frequency, number of preference shifts per episode, and workflow size?  
   1. Metrics: Same three (goal completion, constraint adherence, runtime), **each plotted against churn count / shift count / workflow size**, with mean ± standard error across seeds at each point – the degradation slope, not just endpoints  
3. What is the individual contribution of the Phase 2 selector vs. Phase 3 memory vs their combination (ablation)?  
   1. Metrics: Same three, compared across – CoT baseline, Phase 2 only, Phase 3 only, combined; contribution margin (delta over baseline per component, and delta of combined over either alone)  
4. How does **performance degrade** if retrieved memory is irrelevant or misleading (robustness to a violated assumption)?  
   1. Metrics: **Performance delta under corrupted vs. clean retrieval**; **retrieval relevance rate** (fraction of retrieved memories from a genuinely similar workflow); check whether degraded performance floors at the no-memory baseline or drops below it (graceful vs. harmful failure)

**Baselines:**

* Bounds: an oracle upper bound with advance knowledge of preference/team changes, and a "frozen" lower-bound manager that never re-reads updated state after episode start.  
* Ablations: Phase 2 selector alone, Phase 3 memory alone, and the combined system.  
* State-of-the-art comparison: CoT (current published SOTA on MA-Gym), plus a naive full-history-in-context baseline (no retrieval) as a fair additional comparison point.

Statistics: each challenge task is run across multiple seeds/workflow instantiations per condition; results reported as **mean ± standard error, with significance tested** (e.g. paired t-test) between method and baseline before any performance claim is made.

## **4\. Timeline**

| Month | Phase | Tasks |
| ----- | ----- | ----- |
| Aug 2026 | Proposal & Literature Review | Finalize proposal; review MA-Gym paper and codebase, EPyMARL, continual RL literature; confirm compute/API budget with supervisor ($100 API Credits) |
| Sep 2026 | Phase 1 | Environment setup; reproduce baseline results across all 20 workflows; implement challenge task scenarios (preference-shift, team-churn, compound, cross-episode) as MA-Gym scenario variants  |
| Oct 2026 | Phase 2 (part 1\) | Define reduced action space with supervisor input; implement contextual bandit selector |
| Nov 2026 | Phase 2 (part 2\) | Train and tune selector on static workflows; compare against baselines (including bounds) on preference-shift and team-churn tasks; extend to policy-gradient method if warranted |
| Early Dec 2026 | Checkpoint | Interim report covering Phase 1, Phase 2 and initial challenge-task results |
| Dec 2026 | Transition | Buffer for Phase 2; design of memory architecture for Phase 3 |
| Jan 2027 | Phase 3 (part 1\) | Implement episodic memory store and retrieval mechanism; integrate into manager context |
| Feb 2027 | Phase 3 (part 2\) / Phase 4 | Full evaluation on all four challenge tasks incl. cross-episode task; ablations and significance testing; begin Phase 4 zero-shot evaluation if on schedule |
| Late Feb \- Mar 2027 | Write-up | FYP report and, if applicable, paper draft – core research work completed by this point |
| Mar \- Apr 2027 | Buffer | Revisions based on supervisor feedback, oral presentation preparation, final submission |

## **5\. Questions for Discussion**

**Challenge Tasks and Evaluation Design:** Are the four challenge tasks (preference-shift, team-churn, compound, cross-episode) and the evaluation questions suitable  for the various phases I wish to tackle? Are they detailed enough and appropriate?

**Publishing a paper:** Is there any possibility of publishing a paper based on the results of my project, given completion by Feb-Mar 2027? Doesn’t have to be a full-fledged paper at a top conference but even a workshop paper like ARCANE at the AAAI 2026 LLAMAS workshop for example

