# Challenge Tasks

1. **Preference-shift task:** stakeholder preference weights change mid-episode (e.g. priority reweighted from speed to quality partway through). Baselines with no mechanism to re-anchor to updated preferences are expected to keep optimizing the stale objective.  
2. **Team-churn task:** a worker leaves or joins mid-episode, forcing reassignment across the remaining/new team. Baselines with no representation of the change are expected to fail to adapt allocation.  
3. **Compound task:** both preference shift and team churn occur within the same episode – the joint stress case directly corresponding to the MA-Gym paper's open problem.  
4. **Cross-episode task:** a sequence of related but distinct workflows is run consecutively with no retraining between them, testing whether Phase 3's memory produces measurable improvement across the sequence – the direct test of the "continual" claim, as opposed to within-episode replanning alone.