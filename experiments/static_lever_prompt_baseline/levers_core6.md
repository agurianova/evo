Target mutations to the variables involved in the current fitness bottleneck — because only changes to the components defining the worst-performing substructure can improve the objective, and random exploration wastes effort on neutral or inactive degrees of freedom.

---

Use simulated annealing with temperature decay proportional to iteration count to escape local minima in non-convex geometric optimization — greedy acceptance traps search in near-collinear basins where no immediate improvement exists, but thermal jumps enable crossing fitness valleys to reach globally superior configurations.

---

Initialize via structured dispersion in parametric space using low-discrepancy sequences to avoid clustering and escape sharp local minima, because random seeding produces degenerate configurations that restrict basin reachability in non-convex geometric optimization.

---

Project out-of-bounds points to the nearest feasible location on the domain boundary using geometric projection to the closest edge or vertex, ensuring all updates remain valid without rejection and maintaining optimization continuity under gradient or large-step moves that frequently breach constraints.

---

Maintain multiple independent search trajectories from diverse or top-performing initializations to enable selection among refined basins, avoiding irreversible entrapment in degenerate or suboptimal regions — single-path optimization risks poor basin acquisition, while multi-path refinement raises expected fitness through competitive exploration of high-potential regions.

---

Cap adaptive step sizes in sensitivity-driven updates to prevent overshoot that resolves local degeneracies at the cost of global dispersion or feasibility, while allowing sufficient headroom to correct severe bottlenecks when the adaptive factor would otherwise be too restrictive — unbounded moves disrupt structure, but excessive capping blocks necessary large corrections.
