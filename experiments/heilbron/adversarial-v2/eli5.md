# ELI5: heilbron/adversarial-v2

## The Problem We're Solving

Imagine two teams of AI-written programs playing a game:

- **Team A (Constructors)**: Place 11 dots inside a triangle. Goal: make sure every group of 3 dots forms a large triangle. Think of it like spreading dots out as evenly as possible.
- **Team B (Improvers)**: Look at Team A's dot arrangement and try to move dots to make it even better. If they succeed, it proves Team A's arrangement wasn't optimal yet.

In the first experiment (`heilbron-prover`), this worked — Team A got 97% of the way to the theoretical best. But **Team B gave up early**. After a few rounds, Improvers couldn't figure out how to beat the Constructors anymore. They stagnated at 0% success for 45 generations straight.

Why? Because the only feedback anyone got was **a number**: "you scored 85%" or "you improved by 3%." Nobody knew *why* they scored that way.

## The GAN Analogy

This is exactly like a GAN (Generative Adversarial Network) with broken gradients:

```
In a GAN:
  Generator makes fake images
  Discriminator says "real or fake"
  THE KEY: Discriminator sends GRADIENTS back — "change these pixels in this direction"

In our v1:
  Constructor places dots
  Improver says "I improved you by 0.003" or "I couldn't beat you"
  NO GRADIENT — Constructor has no idea what to change
```

A GAN with only pass/fail feedback (no gradients) would train terribly. That's what we had.

## The Fix: Show Them Each Other's Code

**Direction 1 (D→G): Improver code → Constructor**

When a Constructor is about to mutate, show it the source code of Improvers that beat it:

> "Hey Constructor, here's the program that cracked your arrangement. It found your weakest
> triangle (points 3,7,10), moved point 7 toward the centroid, and got +0.004 improvement.
> Maybe don't leave point 7 so exposed next time."

The Constructor's mutation LLM reads the attack code and evolves defenses against it.

**Direction 2 (G→D): Constructor code → Improver**

When an Improver is about to mutate, show it the source code of Constructors it couldn't crack:

> "Hey Improver, here's the program that resisted all your attacks. It uses simulated annealing
> with repulsion forces to place points along equidistant arcs. Maybe try disrupting the arc
> pattern instead of random perturbations."

The Improver's mutation LLM reads the defense code and evolves targeted attacks.

## What We're Actually Testing

Both pairs get bidirectional feedback. The question is: **how many opponent programs to show?**

| | Pair 1 (K=3) | Pair 2 (K=1) |
|---|---|---|
| Opponent codes shown per mutation | 3 | 1 |
| Extra tokens in prompt | ~1400 | ~600 |
| Pro | Richer signal, diverse strategies | Focused, less context bloat |
| Con | Might overwhelm the LLM | Might miss important strategies |

## The Runs

```
Pair 1 (K=3, "full minibatch"):
  P1_A: Constructor — sees code of 3 best Improvers
  P1_B: Improver   — sees code of 3 most resistant Constructors

Pair 2 (K=1, "single exemplar"):
  P2_A: Constructor — sees code of 1 best Improver
  P2_B: Improver   — sees code of 1 most resistant Constructor
```

4 runs total. All use the steady-state engine. All start from scratch (cold start).

## What Success Looks Like

1. **Both pairs beat the old experiment** (actual_fitness > 0.03462 + 0.002) → bidirectional feedback works
2. **Improvers stop stagnating** (acceptance rate > 5% after gen 20, vs 0% before) → Direction 2 solved the bottleneck
3. **K=3 vs K=1 tells us something** about context bloat vs richer signal

## One-Sentence Summary

> We're giving both sides of an adversarial evolution game access to each other's source code
> (like GAN gradients), and testing whether showing 1 vs 3 opponent programs per mutation
> makes a difference.
