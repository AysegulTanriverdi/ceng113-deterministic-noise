# ceng113-deterministic-noise
# Order Through Entropy

An exploration of how increasingly strict deterministic rules applied to a pseudorandom sequence can coexist with — and even preserve — full statistical randomness. The stricter the constraint, the stronger the structural guarantee, yet the output remains indistinguishable from noise.

---

## The Question

Can a sequence be so heavily restricted that an informed observer can verify its origin with certainty, while an uninformed observer sees nothing but random noise?

This project attempts to answer that question empirically and mathematically. The result is a Base-7 digit stream that is heavily constrained by construction and yet passes standard statistical tests for randomness.

---

## The Experience

Running this program is intentionally interactive. On first launch a password is created. Every subsequent run prompts for it. The password is not there for security — it is converted directly into Seed B, meaning the same password always produces the same sequence.

---

## How It Works

### Expanding Blocks

The generator divides its output into blocks of size $2k$, where $k$ starts at 2 and increments after every block ($k = 2, 3, 4, \dots$).

**First half — Historical Baseline** ($k$ digits): generated freely with no constraints.

**Second half — The Strict Sieve** ($k$ digits): every digit must differ from its **Historical Twin** — the digit exactly $k$ positions behind it in the archive. Candidates that match are discarded and re-rolled until a non-matching digit lands.

As $k$ grows the constrained region grows with it. By large values of $k$ the generator is forcing every position across a massive second half to individually break its local pattern — and the output still looks like noise.

### The Two Seeds

| Seed | Role |
|------|------|
| **Seed A** (System) | Hardcoded constant. Initialises the first Mersenne Twister engine. |
| **Seed B** (User) | Derived from the password via SHA-256. Initialises the second Mersenne Twister engine. |

Every digit is produced by mixing both engines:

$$\text{digit} = (\text{gen\_a.sample} + \text{gen\_b.sample}) \bmod 7$$

Two independent Mersenne Twister instances (Python `random.Random`, MT19937) run in parallel, their outputs summed and compressed into Base-7. The password is never stored — it is converted to Seed B at runtime via the first 8 bytes of its SHA-256 hash and then forgotten.

---

## Design History

### The Original Design

The first version constrained every position in the second half of every block — exactly what the current version does.

### The Detour

A concern arose during development: would constraining every second-half position introduce statistical bias? In response, a third seed — **Seed C** — was introduced as a scheduler, selecting only a sparse logarithmic subset of positions ($\lfloor \log_2 k \rfloor$ per block) where the constraint would fire. This reduced architectural simplicity significantly: verification could no longer operate on the sequence alone and required replaying Seed C's full timeline to reconstruct which positions had been constrained.

### Why It Was Reverted

The concern turned out to be unfounded. Empirical testing on 10,000 digits under both rules:

| Metric | Sparse (Seed C) | Strict (all second half) |
|--------|----------------|--------------------------|
| Chi-squared | 2.32 | 4.35 |
| P-value (uniformity) | 0.888 | 0.629 |
| Max \|autocorrelation\| lags 1–100 | 0.0234 | 0.0228 |
| Second-half digits only — P-value | — | 0.250 |

Both pass comfortably. The rejection loop is self-correcting for uniformity because the Historical Twin at any position is equally likely to be any of the seven digits. The sparse version was reverted — it added complexity without statistical benefit and weakened both the verification and the authorship proof.

---

## Statistical Results

Testing on 10,000 generated digits:

| Test | Result | Threshold |
|------|--------|-----------|
| Chi-squared (uniformity) | 4.35 | — |
| P-value | 0.629 | > 0.05 to pass |
| Max absolute autocorrelation (lags 1–100) | 0.0228 | — |
| Second-half digits only — P-value | 0.250 | > 0.05 to pass |

The second-half result is the more meaningful one — it directly tests whether the constrained positions in isolation are biased. They are not.

---

## Proof of Non-Periodicity

**Assumption:** suppose the sequence eventually becomes purely periodic with period $P$, meaning for all indices $n$ beyond some finite transient point:

$$\text{Digit}_n = \text{Digit}_{n-P}$$

**Two properties of the architecture:**

1. **Unbounded growth.** $k$ increases without limit. For any transient length $T$ and any period $P$, there exists a block with $k = P$ beginning after index $T$ — entirely within the periodic region.

2. **Total second-half coverage.** Every position in $[k,\ 2k)$ is constrained without exception.

**The contradiction:** in the block where $k = P$, let $n$ be any second-half position. The discard-and-re-roll rule enforces:

$$\text{Digit}_n \neq \text{Digit}_{n-k}$$

Substituting $k = P$:

$$\text{Digit}_n \neq \text{Digit}_{n-P}$$

This contradicts the assumption. Since this holds for every choice of $P$, the sequence can never become periodic. $\blacksquare$

---

## How Unlikely Is This By Chance?

At each constrained position the probability that a random Base-7 digit differs from its Historical Twin is $\frac{6}{7}$. Since each twin comes from the free first half — independently of the constrained position — the constraints are independent events and the probability that a purely random sequence satisfies all of them is:

$$P = \left(\frac{6}{7}\right)^n$$

| Sequence length | Constrained positions | Probability of random match |
|----------------|----------------------|----------------------------|
| 100 digits | 36 | $1$ in $10^{2.4}$ |
| 500 digits | 230 | $1$ in $10^{15.4}$ |
| 1,000 digits | 485 | $1$ in $10^{32.5}$ |
| 2,000 digits | 989 | $1$ in $10^{66.2}$ |
| 10,000 digits | 4,949 | $1$ in $10^{331.3}$ |

The number of atoms in the observable universe is approximately $10^{80}$. At 2,000 digits, satisfying the constraints by chance is $10^{13}$ times less likely than picking one specific atom from the entire universe.

---

## Verification and Public Verifiability

After every run the program audits the full archive. The verification function is entirely seedless — it requires only the sequence and the block structure, which is deterministic from the sequence length alone.

Verification operates at two levels:

**Anyone who knows the rule** can confirm the sequence is authentic by checking that every second-half position differs from its Historical Twin. No password or seed is needed — a complete stranger can run the same audit and reach the same conclusion.

**Anyone who knows the password** can additionally reproduce the exact sequence from scratch.

This property is known as **public verifiability** — verification is open to anyone, reproduction remains private. A sufficiently long sequence is practically unforgeable without the password, and the sequence authenticates itself through structural compliance rather than any shared secret.

---

## Broader Context

The tension between strict deterministic structure and perceived randomness is related to questions in digital watermarking and content authentication. This project explores one version of that question: how much order can be embedded in a sequence before the randomness breaks down.

---

## How to Run

**Requirements:** Python 3.x — no external libraries needed.

```bash
python generator.py
```

1. Indicate whether it is a first run or returning session
2. Enter a password (first run asks for confirmation)
3. Seed B is derived and displayed
4. Enter how many digits to generate
5. Sequence prints live, followed by digit distribution and audit

No files are created. The password is never stored.

---

## Files

| File | Purpose |
|------|---------|
| `generator.py` | The entire program |
| `.gitignore` | Standard Python gitignore |

